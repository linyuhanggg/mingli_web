import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import InvitePage from "@/app/invite/[code]/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getReferralInvite: vi.fn(),
  recordReferralAttribution: vi.fn(),
  clearReferralAttribution: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getReferralInvite: api.getReferralInvite,
  recordReferralAttribution: api.recordReferralAttribution,
  clearReferralAttribution: api.clearReferralAttribution,
}));

const activeInvite = {
  code: "ACTIVE-1",
  campaign_key: "summer-invite",
  version: "v1",
  status: "active",
  starts_at: "2026-08-13T05:00:00Z",
  ends_at: "2026-08-21T05:00:00Z",
  per_inviter_limit: 10,
  attribution_recorded: false,
  self_invite: false,
};

const STATUS_LABELS = {
  planned: "计划中",
  active: "进行中",
  paused: "已暂停",
  full: "名额已满",
  ended: "已结束",
} as const;

beforeEach(() => {
  api.getReferralInvite.mockReset();
  api.recordReferralAttribution.mockReset();
  api.clearReferralAttribution.mockReset();
  api.recordReferralAttribution.mockResolvedValue({ status: "recorded" });
  api.clearReferralAttribution.mockResolvedValue(undefined);
});

function expectInviteChrome() {
  expect(screen.getByRole("heading", { level: 1, name: "邀请" })).toBeVisible();
  expect(screen.getByText("查看这次邀请活动的状态。")).toBeVisible();
  expect(screen.queryByText(/来自.+的邀请/)).not.toBeInTheDocument();
  expect(screen.queryByText("待接入")).not.toBeInTheDocument();
  expect(screen.queryByText("邀请活动暂不可用")).not.toBeInTheDocument();
}

describe("public invite route wiring", () => {
  it("renders server-backed active status and records then clears attribution", async () => {
    api.getReferralInvite.mockResolvedValue(activeInvite);

    render(await InvitePage({ params: Promise.resolve({ code: "ACTIVE-1" }) }));

    expectInviteChrome();
    expect(await screen.findByText("进行中")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "记录本次邀请" }));
    expect(await screen.findByText(/临时归因已记录/)).toBeVisible();
    expect(api.recordReferralAttribution).toHaveBeenCalledWith("ACTIVE-1");

    fireEvent.click(screen.getByRole("button", { name: "清除本次邀请" }));
    expect(await screen.findByRole("button", { name: "记录本次邀请" })).toBeVisible();
    expect(api.clearReferralAttribution).toHaveBeenCalledWith("ACTIVE-1");
  });

  it("keeps paused and self invitations from offering a capture action", async () => {
    api.getReferralInvite.mockResolvedValue({
      ...activeInvite,
      status: "paused",
      self_invite: true,
    });

    render(await InvitePage({ params: Promise.resolve({ code: "ACTIVE-1" }) }));

    expectInviteChrome();
    expect(await screen.findByText("已暂停")).toBeVisible();
    expect(screen.getByText("这是你的邀请码，不能自邀。")).toBeVisible();
    expect(screen.queryByRole("button", { name: "记录本次邀请" })).not.toBeInTheDocument();
    expect(api.recordReferralAttribution).not.toHaveBeenCalled();
  });

  it("turns a missing server projection into an invalid invite state", async () => {
    api.getReferralInvite.mockRejectedValue(new ApiError("Invitation code not found", 404));

    render(await InvitePage({ params: Promise.resolve({ code: "MISSING" }) }));

    expectInviteChrome();
    expect(await screen.findByText("邀请无效")).toBeVisible();
    expect(screen.getByText("链接无效，不会写入邀请归因。")).toBeVisible();
    expect(screen.queryByRole("button", { name: "记录本次邀请" })).not.toBeInTheDocument();
    expect(api.recordReferralAttribution).not.toHaveBeenCalled();
    expect(api.clearReferralAttribution).not.toHaveBeenCalled();
  });

  it.each(Object.entries(STATUS_LABELS))(
    "maps server status %s to frozen label %s without a guessed inviter",
    async (status, label) => {
      api.getReferralInvite.mockResolvedValue({
        ...activeInvite,
        status,
        self_invite: false,
      });

      render(await InvitePage({ params: Promise.resolve({ code: "ACTIVE-1" }) }));

      expectInviteChrome();
      expect(await screen.findByText(label)).toBeVisible();
      expect(screen.queryByText(/来自.+的邀请/)).not.toBeInTheDocument();
      if (status !== "active") {
        expect(screen.queryByRole("button", { name: "记录本次邀请" })).not.toBeInTheDocument();
        expect(api.recordReferralAttribution).not.toHaveBeenCalled();
      }
    },
  );
});

describe("invite production shell lock", () => {
  it("keeps the production title and AuthShell tokens without construction chrome", () => {
    const css = readFileSync(
      resolve(process.cwd(), "src/components/auth-shell.module.css"),
      "utf8",
    );
    expect(css).toMatch(/\.header h1\s*\{[^}]*font-size:\s*var\(--font-size-page\)/s);
    expect(css).toMatch(/button\.submit[^}]*background:\s*var\(--color-action\)/s);
    expect(css).toMatch(/button\.submit[^}]*min-height:\s*var\(--target-submit\)/s);

    for (const file of [
      "src/app/invite/[code]/page.tsx",
      "src/components/surfaces/invite-surface.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/development_code|调试码/);
      expect(source).not.toMatch(/SecondaryStatus|StatusPanel|authGrid|SecondarySurfaceFrame/);
      expect(source).not.toMatch(/来自.+的邀请|inviter_name|inviterName|邀请人姓名/);
    }

    const page = readFileSync(
      resolve(process.cwd(), "src/app/invite/[code]/page.tsx"),
      "utf8",
    );
    expect(page).toContain("AuthShell");
    expect(page).toContain('title="邀请"');

    const surface = readFileSync(
      resolve(process.cwd(), "src/components/surfaces/invite-surface.tsx"),
      "utf8",
    );
    expect(surface).toContain('label: "计划中"');
    expect(surface).toContain('label: "进行中"');
    expect(surface).toContain('label: "已暂停"');
    expect(surface).toContain('label: "名额已满"');
    expect(surface).toContain('label: "已结束"');
    expect(surface).toContain('type="submit"');
  });
});
