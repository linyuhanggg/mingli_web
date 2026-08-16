import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountInvitationsPage from "@/app/account/invitations/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  listAccountReferrals: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  listAccountReferrals: api.listAccountReferrals,
}));

const account = {
  user_id: "4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41",
  identities: [],
};

const progress = {
  campaigns: [
    {
      campaign_key: "account-view",
      version: "v1",
      state: "active",
      starts_at: "2026-08-13T05:00:00Z",
      ends_at: "2026-08-21T05:00:00Z",
      per_inviter_limit: 10,
      codes: ["MY-CODE"],
      invited_count: 1,
      my_attribution_stage: null,
      rewards: [{ status: "committed", occurred_at: "2026-08-14T06:00:00Z" }],
    },
  ],
};

beforeEach(() => {
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.listAccountReferrals.mockReset();
  api.listAccountReferrals.mockResolvedValue({ campaigns: [] });
});

describe("account referrals route wiring", () => {
  it("keeps referral progress private for signed-out users", async () => {
    render(<AccountInvitationsPage />);

    expect(await screen.findByRole("status", { name: "需要登录" })).toBeVisible();
    expect(api.listAccountReferrals).not.toHaveBeenCalled();
  });

  it("renders only safe campaign progress returned by the account API", async () => {
    api.getAccount.mockResolvedValue(account);
    api.listAccountReferrals.mockResolvedValue(progress);

    render(<AccountInvitationsPage />);

    expect(await screen.findByText("MY-CODE")).toBeVisible();
    expect(screen.getByRole("heading", { name: "邀请进度" })).toBeVisible();
    expect(screen.getByText("已邀请 1 / 10")).toBeVisible();
    expect(screen.getByText("奖励已确认")).toBeVisible();
    expect(screen.queryByText(account.user_id)).not.toBeInTheDocument();
  });
});
