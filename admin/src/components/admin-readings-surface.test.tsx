import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminReadingsSurface } from "@/components/admin-readings-surface";

describe("AdminReadingsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows reading version metadata without private birth inputs", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        readings: [
          {
            reading_version_id: "reading-version-1",
            reading_root_id: "reading-root-1",
            capability_id: "bazi",
            product_id: "hecan",
            version: 1,
            status: "accepted",
            dimension_count: 2,
            created_at: "2026-08-14T01:00:00Z",
          },
        ],
      },
    });

    render(<AdminReadingsSurface title="报告" role="support" />);

    expect(await screen.findByText("bazi")).toBeVisible();
    expect(screen.getByText("hecan")).toBeVisible();
    expect(screen.getByText("已接受")).toBeVisible();
    expect(screen.getByText("2")).toBeVisible();
    expect(screen.queryByText("encrypted-birth-data")).not.toBeInTheDocument();
    expect(screen.queryByText("natal")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith("/api/v1/admin/readings?limit=100");
  });

  it("does not expose reading metadata to finance staff", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Reading version read permission required",
    });

    render(<AdminReadingsSurface title="盘面" role="finance" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByText("bazi")).not.toBeInTheDocument();
  });
});
