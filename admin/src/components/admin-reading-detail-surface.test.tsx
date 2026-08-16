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
        product_id: "hecan",
        version: 2,
        status: "accepted",
        dimension_count: 3,
        job_count: 1,
        verification_event_count: 3,
        document_available: false,
        document_view_model_schema: null,
        physiognomy_source_summary: null,
        time_check_summary: null,
        created_at: "2026-08-14T01:00:00Z",
      },
    });

    render(<AdminReadingDetailSurface readingVersionId="reading-version-1" role="support" />);

    expect(await screen.findByText("bazi")).toBeVisible();
    expect(screen.getByText("hecan")).toBeVisible();
    expect(screen.getByText("2")).toBeVisible();
    expect(screen.getAllByText("3")).toHaveLength(2);
    expect(screen.getByText("未生成")).toBeVisible();
    expect(screen.queryByText("private reading note")).not.toBeInTheDocument();
    expect(adminFetchMock).toHaveBeenCalledWith(
      "/api/v1/admin/readings/reading-version-1",
    );
  });

  it("shows only safe physiognomy source aggregates", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        reading_version_id: "reading-version-2",
        reading_root_id: "reading-root-2",
        capability_id: "physiognomy",
        product_id: "jianxiang",
        version: 1,
        status: "accepted",
        dimension_count: 2,
        job_count: 1,
        verification_event_count: 0,
        document_available: true,
        document_view_model_schema: "physiognomy-view/v1",
        physiognomy_source_summary: {
          source_count: 3,
          disagreement_count: 1,
          disagreements_retained: true,
          forced_resolution: false,
          active_rule_count: 2,
        },
        time_check_summary: null,
        created_at: "2026-08-14T01:00:00Z",
      },
    });

    render(<AdminReadingDetailSurface readingVersionId="reading-version-2" role="ops" />);

    expect(await screen.findByText("physiognomy-view/v1")).toBeVisible();
    expect(screen.getByText(/3 层，保留 1 项分歧/)).toBeVisible();
    expect(screen.queryByText("physiognomy\/mali-shenxiang#secret")).not.toBeInTheDocument();
  });

  it("shows only safe time-check aggregates", async () => {
    adminFetchMock.mockResolvedValueOnce({
      ok: true,
      data: {
        reading_version_id: "reading-version-3",
        reading_root_id: "reading-root-3",
        capability_id: "time-check",
        product_id: "time-check",
        version: 1,
        status: "accepted",
        dimension_count: 1,
        job_count: 1,
        verification_event_count: 0,
        document_available: true,
        document_view_model_schema: "time-check-view/v1",
        physiognomy_source_summary: null,
        time_check_summary: {
          candidate_count: 12,
          known_event_count: 2,
          event_input_status: "structured_valid",
          ranking_status: "candidate_evidence_ranked",
          event_matching_status: "structured_evidence",
          ranked_candidate_count: 12,
          event_match_count: 2,
        },
        created_at: "2026-08-14T01:00:00Z",
      },
    });

    render(<AdminReadingDetailSurface readingVersionId="reading-version-3" role="ops" />);

    expect(await screen.findByText(/12 个候选，2 条结构化事件/)).toBeVisible();
    expect(screen.getByText(/12 条排序，2 条事件匹配/)).toBeVisible();
    expect(screen.queryByText("synthetic-career")).not.toBeInTheDocument();
    expect(screen.queryByText("最可能时辰")).not.toBeInTheDocument();
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
