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
  it("renders raw relation types, neutral arcs, and a semantic table", async () => {
    const user = userEvent.setup();
    render(<BaziChart chart={denseChart()} evidence={[]} />);

    const relationTable = screen.getByRole("table", { name: "地支关系事实" });
    expect(within(relationTable).getByText("寅午半合")).toBeVisible();
    expect(screen.getByRole("img", { name: "地支关系连线" })).toBeVisible();
    expect(document.querySelectorAll('path[data-relation-type="寅午半合"]')).toHaveLength(1);
    expect(document.body.textContent).not.toMatch(/冲.*红|红.*冲/);

    await user.click(pillarButton(/月柱/));
    expect(
      document.querySelector('path[data-relation-type="寅午半合"][data-fact-highlight="true"]'),
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

  it("keeps the luck track on the natal surface and covers all three Runtime statuses", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<BaziChart chart={denseChart()} evidence={[]} />);

    // M8：大运轨常驻本命盘面，不再藏在单独页签里。
    const luckSection = screen.getByRole("region", { name: "大运" });
    const track = within(luckSection).getByRole("list", { name: "大运序列" });
    expect(within(track).getAllByRole("listitem")).toHaveLength(4);
    expect(within(track).getByText("31–41 岁")).toBeVisible();
    expect(within(luckSection).getByText("已计算")).toHaveAttribute(
      "data-status",
      "calculated",
    );
    await user.click(within(luckSection).getByText("起运依据"));
    expect(within(luckSection).getByText("夏至 · 1992年6月21日 12:14")).toBeVisible();
    expect(within(luckSection).getByText("顺行")).toBeVisible();

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
    const sequenceSection = screen.getByRole("region", { name: "大运" });
    expect(within(sequenceSection).getByText("仅返回序列")).toHaveAttribute(
      "data-status",
      "sequence_only",
    );
    // sequence_only：年龄列整列不渲染（flow-spec S3-M8）。
    expect(within(sequenceSection).queryByText(/–.*岁/)).toBeNull();
    expect(within(sequenceSection).getByText("起运岁数未返回")).toBeVisible();

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
    const missingSection = screen.getByRole("region", { name: "大运" });
    expect(
      within(missingSection).getByText("未提供性别，无法确定大运顺逆。"),
    ).toHaveAttribute("data-status", "not_calculated_missing_gender");
  });

  it("switches time layers without unmounting the matrix and shows no raw enum text", async () => {
    const user = userEvent.setup();
    render(<BaziChart chart={denseChart()} evidence={[]} />);

    const chips = screen.getByRole("group", { name: "时间层" });
    expect(within(chips).getByRole("button", { name: /本命/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    // 流年：矩阵右侧追加流年柱列（§21.2 容器不卸载），右栏出现机械候选模块。
    await user.click(within(chips).getByRole("button", { name: /流年/ }));
    expect(screen.getByRole("table", { name: "四柱矩阵" })).toBeVisible();
    expect(screen.getByText("流年柱 · 2026")).toBeVisible();
    const yearModule = screen.getByRole("region", { name: "流年 2026" });
    expect(within(yearModule).getByText(/流年天干十神：比肩/)).toBeVisible();
    expect(within(yearModule).getByText(/本年机械候选（未裁定）/)).toBeVisible();
    expect(within(yearModule).getByText(/当年所在大运：丁未/)).toBeVisible();
    const luckSection = screen.getByRole("region", { name: "大运" });
    expect(
      within(luckSection).getByText("当年所在").closest("li"),
    ).toHaveAttribute("data-active", "true");
    await user.click(within(yearModule).getByText(/年内分段/));
    expect(within(yearModule).getByRole("table", { name: "分段事实" })).toBeVisible();
    expect(screen.queryByText(/mechanical_candidates_only/)).toBeNull();

    // 流月 / 流日：同构模块，粒度标签区分。
    await user.click(within(chips).getByRole("button", { name: /流月/ }));
    const monthModule = screen.getByRole("region", { name: "流月 2026-08" });
    expect(within(monthModule).getByText(/代表时刻：2026年8月8日 12:00/)).toBeVisible();
    expect(within(monthModule).getByRole("table", { name: "分段事实" })).toBeVisible();
    expect(screen.getByRole("table", { name: "四柱矩阵" })).toBeVisible();

    await user.click(within(chips).getByRole("button", { name: /流日/ }));
    const dayModule = screen.getByRole("region", { name: "流日 2026-08-15" });
    expect(within(dayModule).getByText(/代表时刻：2026年8月15日 12:00/)).toBeVisible();
    expect(screen.queryByText(/mechanical_candidates_only|hard_verdict/)).toBeNull();
  });

  it("declares unavailable layers with the server reason instead of hiding them", () => {
    const chart = {
      ...denseChart({ year_layers: null, month_layers: null, day_layers: null }),
      timeLayers: [
        { layer_id: "year", label: "流年", available: false, unavailable_reason: "流年层数据尚未产出" },
        { layer_id: "month", label: "流月", available: false, unavailable_reason: null },
        { layer_id: "day", label: "流日", available: true, unavailable_reason: null },
      ],
    } as BaziChartView;
    render(<BaziChart chart={chart} evidence={[]} />);

    const chips = screen.getByRole("group", { name: "时间层" });
    const yearChip = within(chips).getByRole("button", { name: /流年/ });
    expect(yearChip).toBeDisabled();
    expect(yearChip).toHaveTextContent("流年层数据尚未产出");
    expect(within(chips).getByRole("button", { name: /流月/ })).toBeDisabled();
    // 声明可用但数据缺失的层同样禁用并写明原因（GAP-BZ-01 fail closed）。
    const dayChip = within(chips).getByRole("button", { name: /流日/ });
    expect(dayChip).toBeDisabled();
    expect(dayChip).toHaveTextContent("该时间层数据尚未产出");
  });

  it("locks highlight and layer overlays to border/background/weight without skeletons", () => {
    const chartCss = readFileSync(
      join(process.cwd(), "src/components/readings/bazi-chart.module.css"),
      "utf8",
    );
    expect(chartCss).toMatch(/overflow-x:\s*auto/);
    expect(chartCss).not.toMatch(/@keyframes|animation:/);
    expect(chartCss).not.toMatch(/skeleton|shimmer/i);
    // 时间层叠加只允许 220ms 透明度，禁止翻面。
    expect(chartCss).toMatch(
      /\.transitHead,\s*\n\.matrix td\[data-active="true"\]\s*\{\s*\n\s*transition: opacity var\(--duration-overlay\) var\(--ease-out\);/,
    );
    expect(chartCss).not.toMatch(/pillarCard[^{]*\{[^}]*animation-delay/s);
    const factHighlightBlock = chartCss.match(/\.factHighlight,[\s\S]*?\n}\n/)?.[0] ?? "";
    expect(factHighlightBlock).toContain("border: 1px solid var(--color-accent)");
    expect(factHighlightBlock).not.toContain("box-shadow");
    expect(factHighlightBlock).not.toContain("color:");
  });
});
