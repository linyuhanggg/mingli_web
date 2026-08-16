import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminReferralsSurface } from "@/components/admin-referrals-surface";
import type { AdminReferralsResponse } from "@/lib/admin-referrals";

const campaign = {
  id: "campaign-1",
  campaign_key: "summer-2026",
  version: "v1",
  state: "active",
  starts_at: "2026-08-13T00:00:00Z",
  ends_at: "2026-09-13T00:00:00Z",
  total_limit: 100,
  per_inviter_limit: 5,
  reward_quantity: 2,
  reward_window_seconds: 7776000,
  code_count: 1,
  temporary_attribution_count: 1,
  attribution_count: 1,
  reservation_count: 1,
  created_at: "2026-08-13T00:00:00Z",
};

describe("AdminReferralsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows campaign funnel counts and redacted detail facts", async () => {
    const user = userEvent.setup();
    const response: AdminReferralsResponse = { campaigns: [campaign] };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: response })
      .mockResolvedValueOnce({
        ok: true,
        data: {
          campaign,
          codes: [
            {
              id: "code-1",
              campaign_version_id: "campaign-1",
              code: "SUMMER-ABC",
              inviter_user_id: "user-1",
              status: "active",
              created_at: "2026-08-13T00:00:00Z",
            },
          ],
          attributions: [
            {
              id: "attribution-1",
              campaign_version_id: "campaign-1",
              code_id: "code-1",
              referred_user_id: "user-2",
              inviter_user_id: "user-1",
              locked_at: "2026-08-14T00:00:00Z",
              status: "locked",
            },
          ],
          slots: [
            {
              id: "slot-1",
              campaign_version_id: "campaign-1",
              product_version_id: "product-1",
              slot_key: "inviter_reward",
              enabled: true,
              total_limit: 10,
              quantity: 2,
              created_at: "2026-08-13T00:00:00Z",
            },
          ],
          rewards: [
            {
              id: "reward-1",
              campaign_version_id: "campaign-1",
              attribution_id: "attribution-1",
              referred_user_id: "user-2",
              inviter_user_id: "user-1",
              product_version_id: "product-1",
              payment_attempt_id: "payment-attempt-1",
              quantity: 2,
              status: "committed",
              reserved_at: "2026-08-14T00:00:00Z",
              committed_at: "2026-08-14T00:00:00Z",
            },
          ],
        },
      });

    render(<AdminReferralsSurface role="ops" />);

    expect(await screen.findByText("summer-2026")).toBeVisible();
    expect(screen.getByText(/活动配置通过受控 Admin 命令 API 执行/)).toBeVisible();
    expect(screen.getByText("1 个码 · 1 次临时归因 · 1 次归因 · 1 个奖励")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "查看活动详情 campaign-1" }));
    expect(await screen.findByText("SUMMER-ABC · 活动中")).toBeVisible();
    expect(screen.getByText("商品名额")).toBeVisible();
    expect(screen.getByText("product-1 · inviter_reward · 10 个名额")).toBeVisible();
    expect(screen.getByText("product-1 · 已绑定支付 payment-attempt-1")).toBeVisible();
    expect(screen.getByText("visitor_key_hash 不展示")).toBeVisible();
  });

  it("does not show referral facts to support", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Referral reader permission required",
    });

    render(<AdminReferralsSurface role="support" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
