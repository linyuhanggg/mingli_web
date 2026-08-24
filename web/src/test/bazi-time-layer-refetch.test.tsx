import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  BaziChart,
  countPreviewTargets,
  previewQueryForTimeLayer,
  singleLayerPreviewTarget,
} from "@/components/readings/bazi-chart";
import { ReadingResult } from "@/components/readings/reading-result";
import { BAZI_EVIDENCE_RESULT_VIEW_MODEL } from "@/fixtures/bazi-evidence-result";
import { buildBaziChartViewFromViewModel } from "@/lib/reading-display";
import type { BaziChartView } from "@/lib/reading-display";
import type { BaziChartViewModel } from "@/view-models/registry";

const api = vi.hoisted(() => ({
  pollReading: vi.fn(),
  getReadingResult: vi.fn(),
  startPreviewReading: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    pollReading: api.pollReading,
    getReadingResult: api.getReadingResult,
    startPreviewReading: api.startPreviewReading,
  };
});

const NATAL_ID = "33333333-3333-4333-8333-333333333333";
const YEAR_ID = "55555555-5555-4555-8555-555555555555";
const PROFILE_ID = "22222222-2222-4222-8222-222222222222";

const baziCapabilityA = {
  capability_id: "bazi",
  label: "八字",
  tier: "A" as const,
  source_system: "bazi",
  runtime_active_rule_count: 24,
  judgment_rule_count: 19,
  source_status: "available" as const,
};

const unavailableYear = {
  layer_id: "year",
  label: "流年",
  available: false,
  unavailable_reason: "本次结果只返回本命四柱，尚未返回逐年盘面。",
};
const unavailableMonth = {
  layer_id: "month",
  label: "流月",
  available: false,
  unavailable_reason: "本次结果只返回本命四柱，尚未返回逐月盘面。",
};
const unavailableDay = {
  layer_id: "day",
  label: "流日",
  available: false,
  unavailable_reason: "本次结果只返回本命四柱，尚未返回逐日盘面。",
};

function natalViewModel(): BaziChartViewModel {
  return {
    ...BAZI_EVIDENCE_RESULT_VIEW_MODEL,
    time_layers: [unavailableYear, unavailableMonth, unavailableDay],
    core_facts: {
      ...BAZI_EVIDENCE_RESULT_VIEW_MODEL.core_facts!,
      year_layers: [],
      month_layers: [],
      day_layers: [],
    },
  };
}

function yearViewModel(): BaziChartViewModel {
  return {
    ...BAZI_EVIDENCE_RESULT_VIEW_MODEL,
    time_layers: [
      {
        layer_id: "year",
        label: "流年",
        available: true,
        unavailable_reason: null,
      },
      unavailableMonth,
      unavailableDay,
    ],
    core_facts: {
      ...BAZI_EVIDENCE_RESULT_VIEW_MODEL.core_facts!,
      month_layers: [],
      day_layers: [],
    },
  };
}

function natalChart(): BaziChartView {
  return buildBaziChartViewFromViewModel(natalViewModel());
}

function readingSummary(id: string) {
  return {
    reading_version_id: id,
    reading_root_id: "44444444-4444-4444-8444-444444444444",
    profile_version_id: PROFILE_ID,
    capability_id: "bazi",
    product_id: "bazi",
    version: 1,
    status: "accepted" as const,
    object_id: "natal",
    dimension_ids: ["career"],
    horizon: { kind_id: "life", start: null, end: null },
    prior_answer: null,
    input_request: null,
    created_at: "2026-08-22T01:00:00Z",
  };
}

function readingResultPayload(viewModel: BaziChartViewModel, id: string) {
  return {
    reading_version_id: id,
    status: "accepted",
    accepted_copy: null,
    capability: baziCapabilityA,
    fact_panel: {
      question: "请预览我的八字命盘。",
      vocabulary: [],
      facts: [],
      evidence: [],
      findings: [],
      claim_scopes: [],
      limits: [],
      prior_answer: null,
      request_view: {
        subject_refs: ["profile-version:test"],
        capability_ids: ["bazi"],
        object_id: "natal",
        dimension_ids: ["career"],
        horizon: { kind_id: "life", start: null, end: null },
      },
    },
    verification: null,
    input_request: null,
    view_model: viewModel,
  };
}

describe("single-layer preview target", () => {
  const now = new Date(2026, 7, 22, 12, 0, 0);

  it("emits only target_year for the year chip", () => {
    const target = singleLayerPreviewTarget("year", now);
    expect(target).toEqual({ target_year: 2026 });
    expect(countPreviewTargets(target)).toBe(1);
    expect(target).not.toHaveProperty("target_month");
    expect(target).not.toHaveProperty("target_date");
  });

  it("emits only target_month for the month chip", () => {
    const target = singleLayerPreviewTarget("month", now);
    expect(target).toEqual({ target_month: "2026-08" });
    expect(countPreviewTargets(target)).toBe(1);
    expect(target).not.toHaveProperty("target_year");
    expect(target).not.toHaveProperty("target_date");
  });

  it("emits only target_date for the day chip", () => {
    const target = singleLayerPreviewTarget("day", now);
    expect(target).toEqual({ target_date: "2026-08-22" });
    expect(countPreviewTargets(target)).toBe(1);
  });

  it("emits no target fields for natal", () => {
    expect(singleLayerPreviewTarget("natal", now)).toEqual({});
    expect(countPreviewTargets(singleLayerPreviewTarget("natal", now))).toBe(0);
    expect(previewQueryForTimeLayer("year")).toMatch(/流年/);
  });
});

describe("BaziChart time-layer chips", () => {
  it("keeps missing layers disabled when no refetch callback is provided", () => {
    render(<BaziChart chart={natalChart()} evidence={[]} />);
    const chips = screen.getByRole("group", { name: "时间层" });
    expect(within(chips).getByRole("button", { name: /流年/ })).toBeDisabled();
    expect(within(chips).getByRole("button", { name: /流月/ })).toBeDisabled();
    expect(within(chips).getByRole("button", { name: /流日/ })).toBeDisabled();
  });

  it("requests only the clicked layer and does not request unselected layers", async () => {
    const user = userEvent.setup();
    const onRequestLayer = vi.fn();
    render(
      <BaziChart
        chart={natalChart()}
        evidence={[]}
        onRequestLayer={onRequestLayer}
      />,
    );
    const chips = screen.getByRole("group", { name: "时间层" });
    await user.click(within(chips).getByRole("button", { name: /流年/ }));
    expect(onRequestLayer).toHaveBeenCalledTimes(1);
    expect(onRequestLayer).toHaveBeenCalledWith("year");
    expect(onRequestLayer).not.toHaveBeenCalledWith("month");
    expect(onRequestLayer).not.toHaveBeenCalledWith("day");
  });

  it("does not refetch when the current result already has that layer", async () => {
    const user = userEvent.setup();
    const onRequestLayer = vi.fn();
    render(
      <BaziChart
        chart={buildBaziChartViewFromViewModel(yearViewModel())}
        evidence={[]}
        onRequestLayer={onRequestLayer}
      />,
    );
    await user.click(screen.getByRole("button", { name: /流年/ }));
    expect(onRequestLayer).not.toHaveBeenCalled();
    expect(screen.getByText("流年柱 · 2026")).toBeVisible();
  });

  it("shows a pending state on the in-flight chip and keeps the natal chart", () => {
    render(
      <BaziChart
        chart={natalChart()}
        evidence={[]}
        onRequestLayer={vi.fn()}
        pendingLayerId="year"
      />,
    );
    const yearChip = screen.getByRole("button", { name: /流年/ });
    expect(yearChip).toHaveAttribute("aria-busy", "true");
    expect(yearChip).toBeDisabled();
    expect(yearChip).toHaveTextContent("正在取该层盘面");
    expect(screen.getByRole("button", { name: /本命/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.queryByText("流年柱 · 2026")).not.toBeInTheDocument();
  });

  it("shows an honest error and does not invent a transit pillar", () => {
    render(
      <BaziChart
        chart={natalChart()}
        evidence={[]}
        onRequestLayer={vi.fn()}
        layerError="这次时间层请求没有成功，仍显示刚才那张已确认的盘。"
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "这次时间层请求没有成功，仍显示刚才那张已确认的盘。",
    );
    expect(screen.queryByText("流年柱 · 2026")).not.toBeInTheDocument();
  });
});

describe("ReadingResult time-layer refetch", () => {
  beforeEach(() => {
    vi.setSystemTime(new Date(2026, 7, 22, 12, 0, 0));
    api.pollReading.mockReset();
    api.getReadingResult.mockReset();
    api.startPreviewReading.mockReset();
    api.pollReading.mockImplementation(async (id: string) => readingSummary(id));
    api.getReadingResult.mockImplementation(async (id: string) =>
      readingResultPayload(id === YEAR_ID ? yearViewModel() : natalViewModel(), id),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("sends only target_year when the year chip is clicked", async () => {
    const user = userEvent.setup();
    api.startPreviewReading.mockResolvedValue(readingSummary(YEAR_ID));
    render(<ReadingResult readingId={NATAL_ID} />);
    expect(await screen.findByRole("group", { name: "时间层" })).toBeVisible();

    await user.click(screen.getByRole("button", { name: /流年/ }));

    await waitFor(() => expect(api.startPreviewReading).toHaveBeenCalledTimes(1));
    const payload = api.startPreviewReading.mock.calls[0]?.[0] as Record<
      string,
      unknown
    >;
    expect(payload).toMatchObject({
      profile_version_id: PROFILE_ID,
      target_year: 2026,
    });
    expect(payload).not.toHaveProperty("target_month");
    expect(payload).not.toHaveProperty("target_date");
    expect(countPreviewTargets(payload)).toBe(1);
  });

  it("sends only target_month when the month chip is clicked", async () => {
    const user = userEvent.setup();
    api.startPreviewReading.mockResolvedValue(readingSummary(YEAR_ID));
    render(<ReadingResult readingId={NATAL_ID} />);
    await screen.findByRole("group", { name: "时间层" });
    await user.click(screen.getByRole("button", { name: /流月/ }));
    await waitFor(() => expect(api.startPreviewReading).toHaveBeenCalledTimes(1));
    const payload = api.startPreviewReading.mock.calls[0]?.[0] as Record<
      string,
      unknown
    >;
    expect(payload.target_month).toBe("2026-08");
    expect(payload).not.toHaveProperty("target_year");
    expect(payload).not.toHaveProperty("target_date");
  });

  it("keeps the natal chart and reports the failure when refetch errors", async () => {
    const user = userEvent.setup();
    api.startPreviewReading.mockRejectedValue(new Error("排盘服务暂时不可用"));
    render(<ReadingResult readingId={NATAL_ID} />);
    await screen.findByRole("group", { name: "时间层" });
    await user.click(screen.getByRole("button", { name: /流年/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "这次时间层请求没有成功，仍显示刚才那张已确认的盘。",
    );
    expect(screen.queryByText("流年柱 · 2026")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /本命/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
