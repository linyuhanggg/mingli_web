import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminReadingDetailSurface } from "@/components/admin-reading-detail-surface";

describe("AdminReadingDetailSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows safe reading aggregates without private output material", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        reading_version_id: "reading-version-1",
        reading_root_id: "reading-root-1",
        capability_id: "bazi",
        version: 2,
        status: "accepted",
        dimension_count: 3,
        job_count: 1,
        verification_event_count: 3,
        document_available: false,
        created_at: "2026-08-14T01:00:00Z",
      },
    });

    render(<AdminReadingDetailSurface readingVersionId="reading-version-1" role="support" />);

    expect(await screen.findByText("bazi")).toBeVisible();
    expect(screen.getByText("2")).toBeVisible();
    expect(screen.getAllByText("3")).toHaveLength(2);
    expect(screen.getByText("未生成")).toBeVisible();
    expect(screen.queryByText("private reading note")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/readings/reading-version-1",
    );
  });

  it("does not expose reading details to finance staff", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Reading version read permission required",
    });

    render(<AdminReadingDetailSurface readingVersionId="reading-version-1" role="finance" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByText("bazi")).not.toBeInTheDocument();
  });
});
