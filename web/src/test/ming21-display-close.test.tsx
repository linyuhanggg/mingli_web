import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReadingResult } from "@/components/readings/reading-result";
import { RuntimeChart } from "@/components/readings/runtime-chart";
import type { DaliurenChartViewModel, MeihuaChartViewModel } from "@/view-models/registry";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

const VERSION_ID = "33333333-3333-4333-8333-333333333333";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function guestSession() {
  return jsonResponse(
    {
      status: "active",
      expires_at: "2026-08-11T00:00:00Z",
      csrf_token: "csrf-token-with-at-least-thirty-two-characters",
    },
    201,
  );
}

const meihuaView: MeihuaChartViewModel = {
  schema_version: "meihua-chart/v1",
  subject_ref: "meihua:test",
  question: "这件事如何推进？",
  casting_method: "time",
  primary_hexagram: { name: "水雷屯", upper_trigram: "坎", lower_trigram: "震" },
  mutual_hexagram: null,
  changed_hexagram: null,
  moving_lines: [3],
  body_use: {
    body: { position: "lower", trigram: "震", element: "木" },
    use: { position: "upper", trigram: "坎", element: "水" },
    relation: "生",
    status: "calculated_relation_not_verdict",
  },
  core_facts: {
    body_relation_facts: null,
    seasonal_strength: {
      autumn: { trigram: "兑", season: "autumn", status: "calculated_strength_not_verdict" },
    },
    interpretive_candidates: null,
    interpretation_status: null,
  },
  public_labels: [
    { key: "calculated_relation_not_verdict", label: "关系已计算，尚非断语" },
    { key: "calculated_strength_not_verdict", label: "旺衰已计算，尚非断语" },
    { key: "autumn", label: "秋" },
  ],
};

const daliurenView = {
  schema_version: "daliuren-chart/v1",
  subject_ref: "daliuren:test",
  question: "何时回应？",
  lessons: [
    { lesson_id: "一课", upper: "巳", lower: "丁" },
    { lesson_id: "二课", upper: "卯", lower: "巳" },
    { lesson_id: "三课", upper: "酉", lower: "亥" },
    { lesson_id: "四课", upper: "未", lower: "酉" },
  ],
  transmissions: [
    { stage: "initial", branch: "酉", general: "贵人" },
    { stage: "middle", branch: "未", general: "太阴" },
    { stage: "final", branch: "巳", general: "白虎" },
  ],
  core_facts: {
    day_hour: null,
    dimension_facts: null,
    earth_plate: null,
    heaven_plate: null,
    heavenly_generals: null,
    lesson_method: null,
    month_general: null,
    noble_person: null,
    plate_offset: null,
    structural_patterns: null,
    timing_candidates: null,
    xunkong: null,
  },
  public_labels: [
    { key: "transmissions_to_day", label: "传至日辰" },
    { key: "initial_final_relation", label: "初末关系" },
    { key: "subject_object_relation", label: "主客关系" },
    { key: "stage_flow", label: "三传流转" },
  ],
} satisfies DaliurenChartViewModel;

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("MING-21 display close", () => {
  it("stops polling immediately when poll_required is false", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url) => {
      const path = String(url);
      if (path === "/api/v1/guest-sessions") return guestSession();
      if (path.endsWith("/result")) {
        return jsonResponse({
          reading_version_id: VERSION_ID,
          status: "prepared",
          accepted_copy: null,
          fact_panel: null,
          view_model: meihuaView,
          capability: null,
          verification: null,
          input_request: null,
          document: null,
          result_available: true,
          poll_required: false,
          poll_after_seconds: null,
        });
      }
      return jsonResponse({
        reading_version_id: VERSION_ID,
        reading_root_id: "44444444-4444-4444-8444-444444444444",
        profile_version_id: null,
        capability_id: "meihua",
        version: 1,
        status: "prepared",
        object_id: "concrete_event",
        dimension_ids: ["outcome"],
        horizon: { kind_id: "instant", start: null, end: null },
        prior_answer: null,
        input_request: null,
        created_at: "2026-08-10T01:00:00Z",
        result_available: true,
        poll_required: false,
        poll_after_seconds: null,
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ReadingResult readingId={VERSION_ID} />);
    expect(await screen.findByText("事实已准备")).toBeVisible();
    const callsAfterReady = fetchMock.mock.calls.length;
    await new Promise((resolve) => setTimeout(resolve, 2500));
    expect(fetchMock.mock.calls.length).toBe(callsAfterReady);
  }, 10_000);

  it("renders meihua and daliuren public_labels instead of internal keys", () => {
    const { rerender } = render(<RuntimeChart viewModel={meihuaView} />);
    expect(screen.getAllByText("关系已计算，尚非断语").length).toBeGreaterThan(0);
    expect(screen.getAllByText("秋").length).toBeGreaterThan(0);
    expect(screen.queryByText("calculated_relation_not_verdict")).not.toBeInTheDocument();
    expect(screen.queryByText("calculated_strength_not_verdict")).not.toBeInTheDocument();

    rerender(<RuntimeChart viewModel={daliurenView} />);
    expect(screen.getByText("传至日辰")).toBeVisible();
    expect(screen.getByText("初末关系")).toBeVisible();
    expect(screen.getByText("主客关系")).toBeVisible();
    expect(screen.getByText("三传流转")).toBeVisible();
    expect(screen.queryByText("transmissions_to_day")).not.toBeInTheDocument();
  });
});
