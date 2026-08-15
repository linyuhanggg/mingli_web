import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AccountEntitlementsPage from "@/app/account/entitlements/page";
import AccountOrdersPage from "@/app/account/orders/page";
import { ApiError } from "@/lib/api";

const api = vi.hoisted(() => ({
  getAccount: vi.fn(),
  listAccountEntitlements: vi.fn(),
  listAccountOrders: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAccount: api.getAccount,
  listAccountEntitlements: api.listAccountEntitlements,
  listAccountOrders: api.listAccountOrders,
}));

const account = {
  user_id: "4f9c3d6a-2f5e-4a8b-9c1d-3e7a5b9f2c41",
  identities: [],
};

beforeEach(() => {
  api.getAccount.mockReset();
  api.getAccount.mockRejectedValue(new ApiError("Authentication required", 401));
  api.listAccountEntitlements.mockReset();
  api.listAccountEntitlements.mockResolvedValue({ entitlements: [] });
  api.listAccountOrders.mockReset();
  api.listAccountOrders.mockResolvedValue({ orders: [] });
});

describe("account commerce route wiring", () => {
  it("keeps orders private for signed-out users", async () => {
    render(<AccountOrdersPage />);

    expect(await screen.findByRole("status", { name: "需要登录" })).toBeVisible();
    expect(api.listAccountOrders).not.toHaveBeenCalled();
  });

  it("renders owner-scoped order facts without raw identifiers", async () => {
    api.getAccount.mockResolvedValue(account);
    api.listAccountOrders.mockResolvedValue({
      orders: [
        {
          order_id: "11111111-1111-4111-8111-111111111111",
          product_label: "八字深读",
          amount_minor: 9900,
          currency: "CNY",
          status: "paid",
          fulfillment_status: "delivered",
          created_at: "2026-08-14T05:00:00Z",
          paid_at: "2026-08-14T05:01:00Z",
        },
      ],
    });

    render(<AccountOrdersPage />);

    expect(await screen.findByText("八字深读")).toBeVisible();
    expect(screen.getByText("已支付")).toBeVisible();
    expect(screen.getByText("99.00 CNY")).toBeVisible();
    expect(screen.queryByText("11111111-1111-4111-8111-111111111111")).not.toBeInTheDocument();
  });

  it("renders append-only entitlement projections rather than a fake wallet balance", async () => {
    api.getAccount.mockResolvedValue(account);
    api.listAccountEntitlements.mockResolvedValue({
      entitlements: [
        {
          label: "权益 1",
          granted: 1,
          reserved: 0,
          consumed: 1,
          released: 0,
          reversed: 0,
          expired: 0,
          available: 0,
          events: [
            { kind: "GRANT", quantity: 1, occurred_at: "2026-08-14T05:00:00Z" },
            { kind: "RESERVE", quantity: 1, occurred_at: "2026-08-14T05:01:00Z" },
            { kind: "CONSUME", quantity: 1, occurred_at: "2026-08-14T05:02:00Z" },
          ],
        },
      ],
    });

    render(<AccountEntitlementsPage />);

    expect(await screen.findByText("权益 1")).toBeVisible();
    expect(screen.getByText("可用").parentElement).toHaveTextContent("0");
    expect(screen.getByText("已消耗").parentElement).toHaveTextContent("1");
    expect(screen.getAllByText("已发放").length).toBeGreaterThan(0);
    expect(screen.getByText(/已消费/)).toBeVisible();
  });
});
