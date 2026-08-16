import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminCommerceSurface } from "@/components/admin-commerce-surface";

describe("AdminCommerceSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows real order facts without payment attempt secrets", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        orders: [
          {
            id: "order-1",
            owner_user_id: "user-1",
            product_version_id: "version-1",
            purchase_target_ref: "reading-1",
            amount_minor: 9900,
            currency: "CNY",
            status: "refunded",
            fulfillment_status: null,
            created_at: "2026-08-14T01:00:00Z",
            paid_at: "2026-08-14T01:01:00Z",
          },
        ],
      },
    });

    render(<AdminCommerceSurface kind="orders" role="finance" />);

    expect(await screen.findByText("order-1")).toBeVisible();
    expect(screen.getByText("已退款")).toBeVisible();
    expect(screen.getByText("99.00 CNY")).toBeVisible();
    expect(screen.queryByText("idempotency_key_hash")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith("/api/v1/admin/commerce/orders");
  });

  it("renders the server permission boundary for support", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Commerce reader permission required",
    });

    render(<AdminCommerceSurface kind="refunds" role="support" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows bound referral refund confirmation evidence", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        refunds: [
          {
            id: "refund-1",
            payment_id: "payment-1",
            order_id: "order-1",
            channel: "closed",
            channel_refund_id: "channel-refund-1",
            amount_minor: 9900,
            currency: "CNY",
            reason: "活动退款确认",
            status: "succeeded",
            created_at: "2026-08-14T01:00:00Z",
            confirmed_at: "2026-08-14T01:01:00Z",
            referral_confirmation_id: "confirmation-1",
            referral_confirmation_policy_version: "development-preview-v0.1",
            referral_confirmation_at: "2026-08-14T00:59:00Z",
          },
        ],
      },
    });

    render(<AdminCommerceSurface kind="refunds" role="finance" />);

    expect(await screen.findByText(/confirmation-1/)).toBeVisible();
    expect(screen.getByText(/development-preview-v0\.1/)).toBeVisible();
  });
});
