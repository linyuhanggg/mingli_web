import { readFileSync } from "node:fs";
import { join } from "node:path";

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { BAZI_EVIDENCE_RESULT_VIEW_MODEL } from "@/fixtures/bazi-evidence-result";
import { BaziChart } from "@/components/readings/bazi-chart";
import { buildBaziChartViewFromViewModel } from "@/lib/reading-display";
import type { BaziChartView } from "@/lib/reading-display";
import type { TimeLayerEntitlement } from "@/lib/chart-workspace";
import type { BaziCoreFacts, BaziTemporalLayer } from "@/view-models/registry";

const baseChart = buildBaziChartViewFromViewModel(BAZI_EVIDENCE_RESULT_VIEW_MODEL);
const baseFacts = baseChart.coreFacts as BaziCoreFacts;

const grantedEntitlement: TimeLayerEntitlement = {
  schemaVersion: "time-layer-entitlement/v1",
  capabilityId: "bazi",
  resolution: "granted",
  freeBoundaryLayerId: "year",
  paidLayerIds: ["month", "day", "hour"],
  freeYearSet: [2026],
  layers: [
    { layerId: "life", tier: "free", access: "readable", upgradeCta: null },
    { layerId: "luck_cycles", tier: "free", access: "readable", upgradeCta: null },
    { layerId: "year", tier: "free", access: "readable", upgradeCta: null },
    { layerId: "month", tier: "paid", access: "readable", upgradeCta: null },
    { layerId: "day", tier: "paid", access: "readable", upgradeCta: null },
    { layerId: "hour", tier: "paid", access: "unavailable", upgradeCta: null },
  ],
};

const temporalSegment = {
  start_inclusive: "2026-08-01T00:00:00+08:00",
  end_exclusive: "2026-08-16T00:00:00+08:00",
  ganzhi: "丙午",
  stem_ten_god: "比肩",
  branch_hidden_ten_gods: [{ stem: "丁", ten_god: "劫财" }],
  branch_relations: [{ relation_type: "半合", natal_position: "month", natal_branch: "午", transit_branch: "寅" }],
  seasonal_effect: { status: "returned" },
  tiaohou_effect: { status: "returned" },
  structural_changes: {
    status: "mechanical_candidates_only",
    transit_pillar: "丙午",
    stem_ten_god: "比肩",
    branch_relations: [],
    hard_verdict: null,
  },
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
    stem_ten_god: "比肩",
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

const otherYearLayer = {
  ...yearLayer,
  year: 2027,
  ganzhi: "丁未",
  ganzhi_segments: [{ ...temporalSegment, ganzhi: "戊申" }],
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
  it("keeps the basic and professional disclosures distinct while notes stay unavailable", async () => {
    const user = userEvent.setup();
    render(<BaziChart chart={denseChart()} evidence={[]} />);

    let matrix = screen.getByRole("table", { name: "四柱专业矩阵" });
    expect(within(matrix).getByRole("row", { name: /主星/ })).toBeVisible();
    expect(within(matrix).getByRole("row", { name: /藏干/ })).toBeVisible();
    expect(within(matrix).getByRole("row", { name: /副星/ })).toBeVisible();
    expect(within(matrix).getByRole("row", { name: /自坐/ })).toBeVisible();
    expect(within(matrix).getByRole("row", { name: /纳音/ })).toBeVisible();
    expect(within(matrix).getAllByText("待接入").length).toBeGreaterThan(0);
    expect(within(matrix).getAllByText("暂无该项事实").length).toBeGreaterThan(0);
    expect(matrix.querySelector('[data-element="fire"][data-shape="△"]')).not.toBeNull();
    expect(screen.getByText("公历起止年份区间待接入。")).toBeVisible();
    expect(screen.getByText("农历起运文本待接入。")).toBeVisible();
    expect(screen.queryByText(/ALGO-GAP-/)).not.toBeInTheDocument();
    const chartSource = readFileSync(
      join(process.cwd(), "src/components/readings/bazi-chart.tsx"),
      "utf8",
    );
    for (const gapId of ["ALGO-GAP-1", "ALGO-GAP-2", "ALGO-GAP-3", "ALGO-GAP-4"]) {
      expect(chartSource).toContain(gapId);
    }
    expect(screen.getByRole("button", { name: "基本排盘" })).toBeVisible();
    expect(screen.getByRole("button", { name: "专业细盘" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    const notes = screen.getByRole("button", { name: /解读笔记/ });
    expect(notes).toBeVisible();
    expect(notes).toBeDisabled();
    expect(notes).toHaveAttribute("aria-disabled", "true");

    await user.click(screen.getByRole("button", { name: "基本排盘" }));
    expect(screen.queryByRole("table", { name: "四柱专业矩阵" })).not.toBeInTheDocument();
    expect(screen.queryByText("候选事实")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "专业细盘" }));
    matrix = screen.getByRole("table", { name: "四柱专业矩阵" });
    expect(matrix).toBeVisible();
    expect(screen.getByText("候选事实")).toBeVisible();
  });

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

  it("keeps six layer panels mounted and exposes paid facts only with a server grant", async () => {
    const user = userEvent.setup();
    render(
      <BaziChart
        chart={denseChart({ year_layers: [yearLayer, otherYearLayer] })}
        evidence={[]}
        timeLayerEntitlement={grantedEntitlement}
      />,
    );

    expect(screen.getAllByRole("tabpanel", { hidden: true })).toHaveLength(6);
    await user.click(screen.getByRole("tab", { name: /流年/ }));
    const yearlyPanel = screen.getByRole("tabpanel", { name: /流年/ });
    const yearlyTable = within(yearlyPanel).getByRole("table", { name: "完整流年事实" });
    expect(yearlyTable).toBeVisible();
    expect(within(yearlyTable).getByRole("row", { name: /2026/ })).toBeVisible();
    expect(within(yearlyTable).queryByRole("row", { name: /2027/ })).not.toBeInTheDocument();
    expect(yearlyPanel).not.toHaveTextContent("2027");
    expect(within(yearlyPanel).getAllByText("仅机械候选").length).toBeGreaterThan(0);
    expect(yearlyPanel.textContent).not.toMatch(/mechanical_candidates_only|active_luck_cycle/);
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

    const hourly = screen.getByRole("tab", { name: /流时/ });
    expect(hourly).toBeDisabled();
    const hourlyPanel = document.getElementById(hourly.getAttribute("aria-controls") ?? "");
    expect(hourlyPanel).toHaveTextContent("流时待接入");
    expect(hourlyPanel).toHaveAttribute("aria-hidden", "true");
    expect(
      within(hourlyPanel as HTMLElement).queryByRole("link", { name: "了解专业版" }),
    ).not.toBeInTheDocument();
  });

  it("keeps paid layer facts out of the DOM when entitlement is absent", async () => {
    const user = userEvent.setup();
    render(<BaziChart chart={denseChart()} evidence={[]} />);

    await user.click(screen.getByRole("tab", { name: /流月/ }));
    const monthlyPanel = screen.getByRole("tabpanel", { name: /流月/ });
    expect(within(monthlyPanel).getByText("流月已锁定")).toBeVisible();
    expect(within(monthlyPanel).getByText("权益状态未确认")).toBeVisible();
    expect(within(monthlyPanel).queryByText("2026-08")).not.toBeInTheDocument();
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
    expect(shellCss).toMatch(/\.layerPanel\[data-active="true"\][\s\S]*?animation:\s*layer-panel-forward var\(--duration-overlay\)/);
    expect(shellCss).toMatch(/@keyframes layer-panel-forward[\s\S]*?translateX\(8px\)/);
    expect(shellCss).toMatch(/@keyframes layer-panel-backward[\s\S]*?translateX\(-8px\)/);
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
