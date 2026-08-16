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

beforeEach(() => {
  api.getReferralInvite.mockReset();
  api.recordReferralAttribution.mockReset();
  api.clearReferralAttribution.mockReset();
  api.recordReferralAttribution.mockResolvedValue({ status: "recorded" });
  api.clearReferralAttribution.mockResolvedValue(undefined);
});

describe("public invite route wiring", () => {
  it("renders server-backed active status and records then clears attribution", async () => {
    api.getReferralInvite.mockResolvedValue(activeInvite);

    render(await InvitePage({ params: Promise.resolve({ code: "ACTIVE-1" }) }));

    expect(await screen.findByText("活动进行中")).toBeVisible();
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

    expect(await screen.findByText("活动已暂停")).toBeVisible();
    expect(screen.getByText("这是你的邀请码，不能自邀。")).toBeVisible();
    expect(screen.queryByRole("button", { name: "记录本次邀请" })).not.toBeInTheDocument();
    expect(api.recordReferralAttribution).not.toHaveBeenCalled();
  });

  it("turns a missing server projection into an invalid invite state", async () => {
    api.getReferralInvite.mockRejectedValue(new ApiError("Invitation code not found", 404));

    render(await InvitePage({ params: Promise.resolve({ code: "MISSING" }) }));

    expect(await screen.findByText("邀请无效")).toBeVisible();
    expect(screen.getByText("链接无效，不会写入邀请归因。")).toBeVisible();
  });
});
