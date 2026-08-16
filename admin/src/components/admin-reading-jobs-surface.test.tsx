import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const adminFetchMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, adminFetch: adminFetchMock };
});

import { AdminReadingJobsSurface } from "@/components/admin-reading-jobs-surface";

describe("AdminReadingJobsSurface", () => {
  beforeEach(() => {
    adminFetchMock.mockReset();
  });

  it("shows safe persisted job metadata without private inputs", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        jobs: [
          {
            id: "job-1",
            reading_version_id: "reading-version-1",
            reading_root_id: "reading-root-1",
            reading_version: 1,
            capability_id: "bazi",
            product_id: "hecan",
            reading_status: "input_ready",
            job_status: "queued",
            language: "zh-CN",
            narrative_policy_version: "narrative-v1",
            max_attempts: 3,
            available_at: "2026-08-14T01:00:00Z",
            lease_generation: 0,
            created_at: "2026-08-14T01:00:00Z",
          },
        ],
      },
    });

    render(<AdminReadingJobsSurface role="support" />);

    expect(await screen.findByText("bazi")).toBeVisible();
    expect(screen.getByText("hecan")).toBeVisible();
    expect(screen.getByText("已排队")).toBeVisible();
    expect(screen.getByText("输入就绪")).toBeVisible();
    expect(screen.queryByText("encrypted-birth-data")).not.toBeInTheDocument();
    expect(screen.queryByText("narrative-v1")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith("/api/v1/admin/reading-jobs?limit=100");
  });

  it("does not expose job metadata to finance staff", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: false,
      status: 403,
      title: "Reading job read permission required",
    });

    render(<AdminReadingJobsSurface role="finance" />);

    expect(await screen.findByText("无权限")).toBeVisible();
    expect(screen.queryByText("bazi")).not.toBeInTheDocument();
  });
});
