import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProfileForm } from "@/components/profile-form";
import { IANA_TIME_ZONES } from "@/lib/iana-timezones";


const { routerPush } = vi.hoisted(() => ({ routerPush: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerPush,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
}));

const api = vi.hoisted(() => ({
  createProfileDraft: vi.fn(),
  confirmProfileDraft: vi.fn(),
}));

vi.mock("@/lib/api", () => api);


beforeEach(() => {
  routerPush.mockReset();
  api.createProfileDraft.mockReset();
  api.confirmProfileDraft.mockReset();
  api.createProfileDraft.mockResolvedValue({
    draft_id: "55555555-5555-4555-8555-555555555555",
    status: "draft",
  });
  api.confirmProfileDraft.mockResolvedValue({
    profile_id: "11111111-1111-4111-8111-111111111111",
    profile_version_id: "22222222-2222-4222-8222-222222222222",
    subject_ref: "profile-version:22222222-2222-4222-8222-222222222222",
    version: 1,
    created_at: "2026-08-09T12:00:00Z",
  });
});

describe("ProfileForm", () => {
  it("uses modern canonical IANA names instead of deprecated aliases", () => {
    for (const canonical of [
      "Asia/Kolkata",
      "Asia/Yangon",
      "Asia/Ho_Chi_Minh",
      "Europe/Kyiv",
    ]) {
      expect(IANA_TIME_ZONES).toContain(canonical);
    }
    for (const deprecated of [
      "Asia/Calcutta",
      "Asia/Rangoon",
      "Asia/Saigon",
      "Europe/Kiev",
    ]) {
      expect(IANA_TIME_ZONES).not.toContain(deprecated);
    }
  });

  it("offers the complete searchable IANA list and rejects values outside it", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    const timezone = screen.getByLabelText("出生时区");
    expect(timezone).toHaveAttribute("list", "profile-timezone-options");
    expect(
      document.querySelectorAll("#profile-timezone-options option").length,
    ).toBeGreaterThan(300);
    expect(
      document.querySelector(
        '#profile-timezone-options option[value="America/New_York"]',
      ),
    ).not.toBeNull();

    await user.clear(timezone);
    await user.type(timezone, "Foo/Bar");
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    expect(await screen.findByText("请选择列表中的有效 IANA 时区")).toBeVisible();
    expect(api.createProfileDraft).not.toHaveBeenCalled();
    expect(api.confirmProfileDraft).not.toHaveBeenCalled();
  });

  it("validates required and malformed birth datetime with accessible errors and focus", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    const birthInput = screen.getByLabelText("出生时间");
    await waitFor(() => expect(birthInput).toHaveFocus());
    expect(birthInput).toHaveAttribute("aria-required", "true");
    expect(birthInput).toHaveAttribute("aria-invalid", "true");
    expect(await screen.findByText("请填写出生时间")).toBeVisible();
    expect(screen.getByText("请填写出生地点")).toBeVisible();

    fireEvent.change(birthInput, { target: { value: "not-a-date" } });
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    expect(await screen.findByText("请填写出生时间")).toBeVisible();
    expect(api.createProfileDraft).not.toHaveBeenCalled();
  });

  it("enforces the stricter location length cap before any API call", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    fireEvent.change(screen.getByLabelText("出生地点"), {
      target: { value: "长".repeat(81) },
    });
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    expect(await screen.findByText("地点最多 80 个字")).toBeVisible();
    expect(api.createProfileDraft).not.toHaveBeenCalled();
  });

  it("submits the confirmed profile through the real draft and confirm API", async () => {
    const user = userEvent.setup();
    render(<ProfileForm />);

    await user.type(screen.getByLabelText("出生时间"), "1994-04-30T05:55");
    await user.type(screen.getByLabelText("出生地点"), "北京市朝阳区");
    await user.click(screen.getByRole("button", { name: /保存档案/ }));

    await waitFor(() =>
      expect(routerPush).toHaveBeenCalledWith("/app/profiles?created=1"),
    );
    expect(api.createProfileDraft).toHaveBeenCalledWith("本人");
    expect(api.confirmProfileDraft).toHaveBeenCalledWith(
      "55555555-5555-4555-8555-555555555555",
      expect.objectContaining({
        timezone: "Asia/Shanghai",
        location: "北京市朝阳区",
        gender: "female",
        time_basis_policy: "civil",
        zi_hour_policy: "midnight",
      }),
    );
  });
});
