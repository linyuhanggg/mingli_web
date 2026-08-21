import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { AdminCatalogSurface } from "@/components/admin-catalog-surface";
import { AdminHealthSurface } from "@/components/admin-health-surface";
import { AdminOverviewPage } from "@/components/admin-overview-page";
import { buildLiveAdminCatalogViewModel } from "@/lib/admin-catalog";
import { resolveAdminRoute } from "@/lib/admin-route-catalog";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/api")>();
  return { ...original, adminFetch: adminFetchMock };
});

vi.mock("@/components/admin-shell", () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <main>{children}</main>,
  useAdminStaff: () => ({ role: "ops" }),
}));

describe("admin overview + catalog shell", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("uses frozen stub and empty titles without construction copy", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        generated_at: "2026-08-19T00:00:00Z",
        is_stub: true,
        kpis: [],
        queues: [],
      },
    });
    const { unmount } = render(<AdminOverviewPage />);
    expect(await screen.findByRole("status", { name: "总览暂时不可用。" })).toBeVisible();
    expect(screen.queryByText("占位合同")).not.toBeInTheDocument();
    expect(screen.queryByText("待接入")).not.toBeInTheDocument();
    unmount();

    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        generated_at: "2026-08-19T00:00:00Z",
        is_stub: false,
        kpis: [],
        queues: [],
      },
    });
    render(<AdminOverviewPage />);
    expect(await screen.findByRole("status", { name: "还没有可展示的总览" })).toBeVisible();
  });

  it("does not stack a ready success bar or the live-aggregation chip", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        generated_at: "2026-08-19T00:00:00Z",
        is_stub: false,
        kpis: [{ id: "refunds_pending", label: "待审退款", value: 1, is_stub: false }],
        queues: [{ id: "refund_queue", label: "退款审批队列", count: 1, is_stub: false }],
      },
    });
    render(<AdminOverviewPage />);
    expect(await screen.findByText("待审退款")).toBeVisible();
    expect(screen.queryByText("实时聚合")).not.toBeInTheDocument();
    expect(screen.queryByText("占位合同")).not.toBeInTheDocument();

    const route = resolveAdminRoute("/users");
    expect(route).not.toBeNull();
    render(<AdminCatalogSurface model={buildLiveAdminCatalogViewModel(route!)} role="support" />);
    expect(screen.queryByRole("status", { name: /已就绪/ })).not.toBeInTheDocument();
    expect(screen.getByRole("status", { name: "平台数据暂时不可用。" })).toBeVisible();
  });

  it("maps health failure to 平台数据暂时不可用。 and hides Runtime", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      title: "Service unavailable",
    });
    render(<AdminHealthSurface role="ops" />);
    expect(await screen.findByRole("status", { name: "平台数据暂时不可用。" })).toBeVisible();
    expect(screen.queryByText(/Runtime|Provider|适配器|待接入|占位合同/)).not.toBeInTheDocument();
  });

  it("keeps construction words out of the production files", () => {
    for (const file of [
      "src/components/admin-overview-page.tsx",
      "src/components/admin-catalog-surface.tsx",
      "src/components/admin-health-surface.tsx",
    ]) {
      const source = readFileSync(resolve(process.cwd(), file), "utf8");
      expect(source).not.toMatch(/占位合同|待接入|实时聚合|§10|§6\.2/);
      if (file.endsWith("admin-catalog-surface.tsx") || file.endsWith("admin-health-surface.tsx")) {
        expect(source).not.toMatch(/Runtime|Provider/);
      }
    }
  });
});
