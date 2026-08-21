import { render, screen, within } from "@testing-library/react";

import { AdminOverviewPage } from "@/components/admin-overview-page";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api")>();
  return { ...original, adminFetch: adminFetchMock };
});

vi.mock("@/components/admin-shell", () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <main>{children}</main>,
}));

describe("AdminOverviewPage", () => {
  it("renders persisted platform facts as business KPIs", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        generated_at: "2026-08-13T00:00:00Z",
        is_stub: false,
        kpis: [
          { id: "refunds_pending", label: "待审退款", value: 1, is_stub: false },
          { id: "readings_failed", label: "失败解读", value: 2, is_stub: false },
        ],
        queues: [{ id: "refund_queue", label: "退款审批队列", count: 1, is_stub: false }],
      },
    });

    render(<AdminOverviewPage />);

    const kpis = await screen.findByRole("region", { name: "业务关键指标" });
    expect(within(kpis).getByText("待审退款")).toBeVisible();
    expect(within(kpis).getByText("1")).toBeVisible();
    expect(within(kpis).getByText("失败解读")).toBeVisible();
    expect(screen.getByText("退款审批队列")).toBeVisible();
    expect(screen.queryByRole("status", { name: "总览暂时不可用。" })).not.toBeInTheDocument();
  });

  it("does not render stub zeroes as normal business KPIs", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        generated_at: "2026-08-13T00:00:00Z",
        is_stub: true,
        kpis: [{ id: "refunds_pending", label: "待审退款", value: 0, is_stub: true }],
        queues: [{ id: "refund_queue", label: "退款审批队列", count: 0, is_stub: true }],
      },
    });

    render(<AdminOverviewPage />);

    expect(await screen.findByRole("status", { name: "总览暂时不可用。" })).toBeVisible();
    expect(screen.queryByText("待审退款")).not.toBeInTheDocument();
    expect(screen.queryByText(/退款审批队列/)).not.toBeInTheDocument();
  });
});
