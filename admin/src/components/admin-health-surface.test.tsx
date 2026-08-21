import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminHealthSurface } from "@/components/admin-health-surface";

describe("AdminHealthSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows the actual readiness dependency returned by the API", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: { status: "ok", service: "database" },
    });

    render(<AdminHealthSurface role="ops" />);

    expect(await screen.findByText("database")).toBeVisible();
    expect(screen.queryByText("依赖已就绪")).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: /已就绪/ })).not.toBeInTheDocument();
    expect(screen.getByText("database")).toBeVisible();
    expect(adminFetchMock).toHaveBeenCalledWith("/api/v1/health/ready");
  });

  it("does not render an ok state when readiness is unavailable", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      title: "Service unavailable",
    });

    render(<AdminHealthSurface role="ops" />);

    expect(await screen.findByRole("status", { name: "平台数据暂时不可用。" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "健康检查面" })).toBeVisible();
    expect(screen.queryByText("依赖已就绪")).not.toBeInTheDocument();
  });
});
