import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { BAZI_EVIDENCE_RESULT_VIEW_MODEL } from "@/fixtures/bazi-evidence-result";
import { BaziChart } from "@/components/readings/bazi-chart";
import { buildBaziChartViewFromViewModel } from "@/lib/reading-display";
import type { BaziChartView } from "@/lib/reading-display";
import type { BaziCoreFacts, BaziTemporalLayer } from "@/view-models/registry";

const baseChart = buildBaziChartViewFromViewModel(BAZI_EVIDENCE_RESULT_VIEW_MODEL);
const baseFacts = baseChart.coreFacts as BaziCoreFacts;

const temporalSegment = {
  start_inclusive: "2026-08-01T00:00:00+08:00",
  end_exclusive: "2026-08-16T00:00:00+08:00",
  ganzhi: "丙午",
  stem_ten_god: "比肩",
  branch_hidden_ten_gods: [{ stem: "丁", ten_god: "劫财" }],
  branch_relations: [{ relation_type: "半合", natal_position: "month", natal_branch: "午", transit_branch: "寅" }],
  seasonal_effect: { status: "returned" },
  tiaohou_effect: { status: "returned" },
  structural_changes: { status: "mechanical_candidates_only", hard_verdict: null },
  seasonal_tiaohou_delta: { status: "returned" },
  shensha_auxiliary: { status: "returned" },
} as const;

const monthLayer = {
  granularity: "month",
  period: "2026-08",
  year: 2026,
  month: 8,
  date: null,
  ganzhi_segments: [temporalSegment],
  active_transits: { status: "returned", pillar: "丙午" },
  structural_changes: { status: "mechanical_candidates_only", hard_verdict: null },
  seasonal_tiaohou_delta: { status: "returned" },
  shensha_auxiliary: { status: "returned" },
  active_luck_cycle: { status: "calculated", pillar: "丁未" },
  calendar_normalization: { status: "calculated" },
  representative_instant: "2026-08-08T12:00:00+08:00",
  rule_trace: [{ rule_id: "bazi.month.test", source_dependency_id: "test", operation: "project" }],
} as unknown as BaziTemporalLayer;

const dayLayer = {
  ...monthLayer,
  granularity: "day",
  period: "2026-08-15",
  month: 8,
  date: "2026-08-15",
  representative_instant: "2026-08-15T12:00:00+08:00",
} as unknown as BaziTemporalLayer;

const yearLayer = {
  year: 2026,
  ganzhi: "丙午",
  stem_ten_god: "比肩",
  branch_hidden_ten_gods: [{ stem: "丁", ten_god: "劫财" }],
  branch_relations: [{ relation_type: "半合", natal_position: "month", natal_branch: "午", transit_branch: "寅" }],
  structural_changes: {
    status: "mechanical_candidates_only",
    transit_pillar: "丙午",
    branch_relations: [],
    hard_verdict: null,
  },
  shensha_auxiliary: { status: "returned" },
  active_luck_cycle: { status: "calculated", pillar: "丁未" },
  seasonal_effect: { status: "returned" },
  tiaohou_effect: { status: "returned" },
  seasonal_tiaohou_delta: { status: "returned" },
  calendar_normalization: { status: "calculated" },
  rule_trace: [{ rule_id: "bazi.year.test", source_dependency_id: "test", operation: "project" }],
  ganzhi_segments: [temporalSegment, { ...temporalSegment, ganzhi: "丁未" }],
} as const;

function denseChart(overrides: Partial<BaziCoreFacts> = {}): BaziChartView {
  return {
    ...baseChart,
    coreFacts: {
      ...baseFacts,
      luck_cycles: {
        ...baseFacts.luck_cycles!,
        cycles: [
          { sequence: 1, pillar: "丁未", start_age_years: 1, end_age_years: 11 },
          { sequence: 2, pillar: "戊申", start_age_years: 11, end_age_years: 21 },
          { sequence: 3, pillar: "己酉", start_age_years: 21, end_age_years: 31 },
          { sequence: 4, pillar: "庚戌", start_age_years: 31, end_age_years: 41 },
        ],
      },
      year_layers: [yearLayer],
      month_layers: [monthLayer],
      day_layers: [dayLayer],
      ...overrides,
    } as BaziCoreFacts,
  };
}

function pillarButton(label: RegExp) {
  return within(screen.getByRole("group", { name: "四柱" })).getByRole("button", {
    name: label,
  });
}

describe("BaziChart fact-density workspace", () => {
  it("renders raw relation types, neutral lines, and a semantic table", async () => {
    const user = userEvent.setup();
    render(<BaziChart chart={denseChart()} evidence={[]} />);

    const relationTable = screen.getByRole("table", { name: "地支关系事实" });
    expect(within(relationTable).getByText("寅午半合")).toBeVisible();
    expect(screen.getByRole("img", { name: "地支关系连线" })).toBeVisible();
    expect(document.querySelectorAll('line[data-relation-type="寅午半合"]')).toHaveLength(1);
    expect(document.body.textContent).not.toMatch(/冲.*红|红.*冲/);

    await user.click(pillarButton(/月柱/));
    expect(
      document.querySelector('line[data-relation-type="寅午半合"][data-fact-highlight="true"]'),
    ).not.toBeNull();
  });

  it("renders only returned element counts and links their contribution to pillar focus", async () => {
    const user = userEvent.setup();
    render(<BaziChart chart={denseChart()} evidence={[]} />);

    const elementTable = screen.getByRole("table", { name: "五行计数" });
    expect(within(elementTable).getByRole("row", { name: /木 2 2/ })).toBeVisible();
    expect(within(elementTable).getByRole("row", { name: /火 3 2/ })).toBeVisible();
    expect(document.body.textContent).not.toMatch(/需补|补某行/);

    await user.click(pillarButton(/月柱/));
    const fireRow = within(elementTable).getByRole("row", { name: /火 3 2/ });
    expect(fireRow.querySelector('[data-fact-highlight="true"]')).not.toBeNull();
  });

  it("highlights ten-god labels through their linked stem", async () => {
    const user = userEvent.setup();
    const monthStem = baseChart.pillars?.month?.slice(0, 1) ?? "甲";
    const monthBranch = baseChart.pillars?.month?.slice(1, 2) ?? "子";
    render(
      <BaziChart
        chart={denseChart({
          hidden_stems: [
            { position: "month", branch: monthBranch, stems: ["丙"] },
          ],
          element_inventory: {
            ...baseFacts.element_inventory!,
            visible_stem_branch_counts: [{ element: "wood", value: 1 }],
            hidden_stem_occurrence_counts: [{ element: "fire", value: 1 }],
          },
          ten_gods: {
            heavenly_stems: [
              {
                position: "month",
                layer: "heavenly_stem",
                stem: monthStem,
                ten_god: "月柱十神",
              },
            ],
            hidden_stems: [
              {
                position: "month",
                layer: "hidden_stem",
                stem: monthStem,
                ten_god: "藏干十神",
              },
            ],
          },
        })}
        evidence={[]}
      />,
    );

    await user.click(pillarButton(/月柱/));
    expect(screen.getByText("月柱十神")).toHaveAttribute(
      "data-fact-highlight",
      "true",
    );
    expect(
      screen
        .getAllByText("藏干十神")
        .some((element) => element.getAttribute("data-fact-highlight") === "true"),
    ).toBe(true);
    const fireRow = within(screen.getByRole("table", { name: "五行计数" })).getByRole(
      "row",
      { name: /火 未返回 1/ },
    );
    expect(fireRow.querySelector('[data-fact-highlight="true"]')).not.toBeNull();
  });

  it("renders the complete luck sequence and tests all three Runtime statuses", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<BaziChart chart={denseChart()} evidence={[]} />);

    await user.click(screen.getByRole("tab", { name: /大运/ }));
    const luckPanel = screen.getByRole("tabpanel", { name: /大运/ });
    const luckTable = within(luckPanel).getByRole("table", { name: "完整大运序列" });
    expect(within(luckTable).getByRole("row", { name: /4 庚戌 31 41/ })).toBeVisible();
    expect(within(luckPanel).getByText("夏至 · 1992年6月21日 12:14")).toBeVisible();
    expect(within(luckPanel).getByText("顺行")).toBeVisible();
    expect(within(luckPanel).getByText("已计算")).toHaveAttribute("data-status", "calculated");

    const sequenceOnly = denseChart({
      luck_cycles: {
        ...baseFacts.luck_cycles!,
        status: "sequence_only",
        direction: null,
        cycles: [{ sequence: 1, pillar: "丁未", start_age_years: null, end_age_years: null }],
        unavailable: ["起运岁数未返回"],
      },
    });
    rerender(<BaziChart chart={sequenceOnly} evidence={[]} />);
    await user.click(screen.getByRole("tab", { name: /大运/ }));
    const sequencePanel = screen.getByRole("tabpanel", { name: /大运/ });
    expect(within(sequencePanel).getByText("仅返回序列")).toHaveAttribute("data-status", "sequence_only");
    expect(within(sequencePanel).getByText("起运岁数未返回")).toBeVisible();

    const missingGender = denseChart({
      luck_cycles: {
        ...baseFacts.luck_cycles!,
        status: "not_calculated_missing_gender",
        direction: null,
        cycles: [],
        unavailable: [],
      },
    });
    rerender(<BaziChart chart={missingGender} evidence={[]} />);
    await user.click(screen.getByRole("tab", { name: /大运/ }));
    const missingGenderPanel = screen.getByRole("tabpanel", { name: /大运/ });
    expect(within(missingGenderPanel).getByText("因性别缺失未计算")).toHaveAttribute(
      "data-status",
      "not_calculated_missing_gender",
    );
    expect(within(missingGenderPanel).getByText("缺少性别，无法计算顺逆与起运序列")).toBeVisible();
  });

  it("keeps five layer panels mounted and exposes year, month, and day facts", async () => {
    const user = userEvent.setup();
    render(<BaziChart chart={denseChart()} evidence={[]} />);

    expect(screen.getAllByRole("tabpanel", { hidden: true })).toHaveLength(5);
    await user.click(screen.getByRole("tab", { name: /流年/ }));
    const yearlyPanel = screen.getByRole("tabpanel", { name: /流年/ });
    expect(within(yearlyPanel).getByRole("table", { name: "完整流年事实" })).toBeVisible();
    expect(within(yearlyPanel).getAllByText("mechanical_candidates_only").length).toBeGreaterThan(0);
    expect(screen.getByRole("tab", { name: /流年/ })).toHaveAttribute("aria-selected", "true");

    await user.click(screen.getByRole("tab", { name: /流月/ }));
    expect(screen.getByRole("table", { name: "流月总览" })).toBeVisible();
    expect(screen.getByText("2026-08")).toBeVisible();
    const monthlyPanel = screen.getByRole("tabpanel", { name: /流月/ });
    expect(monthlyPanel).toHaveAttribute("aria-hidden", "false");
    const natalPanel = document.getElementById(
      screen.getByRole("tab", { name: /^本命/ }).getAttribute("aria-controls") ?? "",
    );
    expect(natalPanel).toHaveAttribute(
      "aria-hidden",
      "true",
    );

    await user.click(screen.getByRole("tab", { name: /流日/ }));
    const dailyPanel = screen.getByRole("tabpanel", { name: /流日/ });
    expect(within(dailyPanel).getByRole("table", { name: "流日总览" })).toBeVisible();
    expect(within(dailyPanel).getAllByText("2026-08-15").length).toBeGreaterThan(0);
  });

  it("locks the layer transition to opacity and transform without skeletons", () => {
    const shellCss = readFileSync(
      join(process.cwd(), "src/components/readings/chart-workspace-shell.module.css"),
      "utf8",
    );
    const chartCss = readFileSync(
      join(process.cwd(), "src/components/readings/bazi-chart.module.css"),
      "utf8",
    );
    expect(shellCss).toMatch(/\.layerPanel[\s\S]*?transition:[\s\S]*?opacity 150ms ease,[\s\S]*?transform 150ms ease/);
    expect(shellCss).toMatch(/\.layerPanel[\s\S]*?opacity:\s*0/);
    expect(shellCss).toMatch(/\.layerPanel\[data-active="true"\][\s\S]*?opacity:\s*1/);
    expect(shellCss).not.toMatch(/skeleton|shimmer/i);
    expect(chartCss).toMatch(/overflow-x:\s*auto/);
    expect(chartCss).not.toMatch(/@keyframes|animation:/);
    const factHighlightBlock = chartCss.match(/\.factHighlight,[\s\S]*?\n}\n/)?.[0] ?? "";
    expect(factHighlightBlock).toContain("border: 1px solid var(--color-action)");
    expect(factHighlightBlock).not.toContain("box-shadow");
    expect(factHighlightBlock).not.toContain("color:");
  });
});
