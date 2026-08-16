import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminReconciliationSurface } from "@/components/admin-reconciliation-surface";
import type { AdminReconciliationResponse, AdminReconciliationRun } from "@/lib/admin-reconciliation";

const run: AdminReconciliationRun = {
  id: "run-1",
  channel: "closed",
  run_at: "2026-08-14T01:00:00Z",
  status: "has_differences",
  item_count: 1,
  matched_count: 0,
  difference_count: 1,
  created_at: "2026-08-14T01:00:00Z",
  items: [
    {
      id: "item-1",
      kind: "payment",
      reference: "tx-remote",
      payment_id: null,
      refund_id: null,
      local_status: null,
      provider_status: "succeeded",
      local_amount_minor: null,
      provider_amount_minor: 100,
      local_currency: null,
      provider_currency: "CNY",
      discrepancy: "provider_only",
      created_at: "2026-08-14T01:00:00Z",
    },
  ],
};

describe("AdminReconciliationSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows real batches and submits structured snapshots through the audited API", async () => {
    const user = userEvent.setup();
    const response: AdminReconciliationResponse = { runs: [run] };
    adminFetchMock
      .mockResolvedValueOnce({ ok: true, data: response })
      .mockResolvedValueOnce({ ok: true, data: run })
      .mockResolvedValueOnce({ ok: true, data: response });

    render(<AdminReconciliationSurface role="finance" />);

    expect(await screen.findByRole("button", { name: "查看差异 run-1" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "查看差异 run-1" }));
    expect(screen.getByText("provider_only")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "关闭" }));
    expect(screen.getByText("对账事实已接入")).toBeVisible();
    expect(screen.getByRole("button", { name: "执行并记录对账" })).toBeEnabled();

    await user.type(screen.getByLabelText("操作原因"), "核对测试渠道到账事实");
    await user.type(screen.getByLabelText("交易号"), "tx-remote");
    await user.click(screen.getByRole("button", { name: "执行并记录对账" }));

    expect(adminFetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/admin/reconciliation/runs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          channel: "closed",
          reason: "核对测试渠道到账事实",
          payments: [
            {
              transaction_id: "tx-remote",
              status: "succeeded",
              amount_minor: 0,
              currency: "CNY",
            },
          ],
          refunds: [],
        }),
      }),
    );
    expect(await screen.findByText("对账批次已完成，差异事实已保存。")).toBeVisible();
  });

  it("keeps the command form away from a support role", async () => {
    adminFetchMock.mockResolvedValueOnce({ ok: true, data: { runs: [] } });

    render(<AdminReconciliationSurface role="support" />);

    expect(await screen.findByText("暂无对账批次")).toBeVisible();
    expect(screen.queryByRole("button", { name: "执行并记录对账" })).not.toBeInTheDocument();
  });
});
