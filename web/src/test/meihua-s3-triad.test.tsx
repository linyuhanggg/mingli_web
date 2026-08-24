import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import {
  MEIHUA_FACTS_ONLY_CAPTION,
  MEIHUA_POLARITY_FOOTER,
  MEIHUA_SEASONAL_CAPTION,
} from "@/components/readings/meihua-copy";
import { RuntimeChart } from "@/components/readings/runtime-chart";
import type { MeihuaChartViewModel } from "@/view-models/registry";

afterEach(cleanup);

function meihuaCss() {
  return readFileSync(resolve(process.cwd(), "src/components/readings/meihua-chart.module.css"), "utf8");
}

function glyphCss() {
  return readFileSync(resolve(process.cwd(), "src/components/readings/hexagram-glyphs.module.css"), "utf8");
}

function chart(overrides: Partial<MeihuaChartViewModel> = {}): MeihuaChartViewModel {
  return {
    schema_version: "meihua-chart/v1",
    subject_ref: "meihua:fixture",
    question: "这件事后续如何",
    casting_method: "time",
    primary_hexagram: { name: "风雷益", upper_trigram: "巽", lower_trigram: "震" },
    mutual_hexagram: { name: "山地剥", upper_trigram: "艮", lower_trigram: "坤" },
    changed_hexagram: { name: "风泽中孚", upper_trigram: "巽", lower_trigram: "兑" },
    moving_lines: [2],
    body_use: {
      body: { position: "upper", trigram: "巽", element: "木" },
      use: { position: "lower", trigram: "震", element: "木" },
      relation: "比和",
      status: "calculated_relation_not_verdict",
    },
    core_facts: {
      body_relation_facts: [],
      seasonal_strength: {
        巽: {
          trigram: "巽",
          month_branch: "酉",
          season: "秋",
          state: "相",
          status: "calculated",
        },
        震: {
          trigram: "震",
          month_branch: "酉",
          season: "秋",
          state: "休",
          status: "calculated",
        },
      },
      interpretation_status: "source_adjudicated_relations",
      interpretive_candidates: {
        schema_version: "mingli-meihua-interpretive-candidates-v1",
        status: "source_adjudicated_relations",
        hard_verdict: null,
        verification_status: "verified",
        relation_candidates: [
          {
            candidate_id: "meihua.primary_use.upper.same_element",
            source_plate: "primary_use",
            position: "upper",
            relation: "比和",
            relation_key: "same_element",
            actor: { position: "upper", trigram: "巽", element: "木" },
            body: { position: "upper", trigram: "巽", element: "木" },
            seasonal_state: "旺",
            rule_id: "MR-04-02",
            status: "relation_adjudicated_not_event_verdict",
            hard_verdict: null,
            verification_status: "verified",
            source_pack: "divination/meihua-yishu",
            source_anchor: "references/books/divination/meihua-yishu/rules.md#MR-04-02",
            source_dependency_id: "meihua.classical-adjudication.body-use-candidates",
            relation_adjudication: {
              status: "adjudicated_relation_polarity",
              decision_scope: "meihua_body_use_relation",
              relation_key: "same_element",
              source_polarity: "harmonious",
              hard_verdict: null,
              event_verdict: null,
              source_refs: [
                {
                  pack: "divination/meihua-yishu",
                  rule_id: "MR-04-02",
                  source_anchor: "references/fulltext/divination/meihua-yishu/fulltext.md#L875",
                  verification_status: "verified",
                  binding_digest: "202662eb4c023883aab61febf3de3d7d42137740f31d50ba1a7ada25149db50f",
                },
              ],
              unresolved_checks: ["具体问题中的体用取义、领域例外与外应"],
            },
          },
        ],
        requires_classical_adjudication: false,
        requires_synthesis_adjudication: true,
        boundary: "关系极性已裁定，综合事件结论仍待裁决",
      },
    },
    ...overrides,
  };
}

describe("梅花 S3 三卦盘面", () => {
  it("renders triad, body/use, seasonal facts and polarity without verdict dye", () => {
    render(<RuntimeChart viewModel={chart()} />);

    expect(screen.getByRole("heading", { name: "盘面" })).toBeVisible();
    expect(screen.getByText("风雷益")).toBeVisible();
    expect(screen.getByText("山地剥")).toBeVisible();
    expect(screen.getByText("风泽中孚")).toBeVisible();
    expect(screen.getByText("按时间起卦")).toBeVisible();
    expect(screen.getAllByText("动爻：二爻").length).toBeGreaterThan(0);
    expect(screen.getByText("体")).toBeVisible();
    expect(screen.getByText("用")).toBeVisible();
    expect(screen.getByText("已计算的五行关系，不是吉凶")).toBeVisible();
    expect(screen.getByText("巽（体）")).toBeVisible();
    expect(screen.getAllByText("酉月 · 秋").length).toBe(2);
    expect(screen.getByText(MEIHUA_SEASONAL_CAPTION)).toBeVisible();
    expect(screen.queryByRole("columnheader", { name: "状态句" })).not.toBeInTheDocument();
    expect(screen.getAllByText("比和").length).toBeGreaterThan(0);
    expect(screen.getByText("关系极性已裁定")).toBeVisible();
    expect(screen.getByText("关系极性已裁定，综合事件结论仍待裁决")).toBeVisible();
    expect(screen.getByText(MEIHUA_POLARITY_FOOTER)).toBeVisible();
    expect(screen.queryByText("以上为古籍已裁定的关系极性，事件成败不在本页判断")).not.toBeInTheDocument();
    expect(screen.getByRole("table", { name: "三卦语义表" })).toBeVisible();
    expect(screen.queryByText("体用关系候选（非最终结论）")).not.toBeInTheDocument();
    expect(screen.queryByText("calculated_relation_not_verdict")).not.toBeInTheDocument();
    expect(screen.queryByText("大吉")).not.toBeInTheDocument();
    expect(screen.queryByText("大凶")).not.toBeInTheDocument();
  });

  it("omits mutual/changed slots and seasonal/polarity modules when those fields are null", () => {
    render(
      <RuntimeChart
        viewModel={chart({
          mutual_hexagram: null,
          changed_hexagram: null,
          moving_lines: [],
          core_facts: null,
        })}
      />,
    );

    expect(screen.getByText("风雷益")).toBeVisible();
    expect(screen.getByText("静卦")).toBeVisible();
    expect(screen.queryByText("山地剥")).not.toBeInTheDocument();
    expect(screen.queryByText("风泽中孚")).not.toBeInTheDocument();
    expect(screen.queryByText("动爻：")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "旺衰" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "古籍极性" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "体用" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "可核验起卦" })).not.toBeInTheDocument();
    expect(screen.queryByText("推导过程暂缺")).not.toBeInTheDocument();
    expect(screen.queryByText("互卦暂缺")).not.toBeInTheDocument();
  });

  it("renders the verifiable casting chain from core_facts.casting, calendar and totals", () => {
    const facts = chart().core_facts;
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: {
            ...facts!,
            casting: {
              method: "time",
              casting_digest: "a".repeat(64),
              inputs: {
                hour_branch_number: 7,
                lunar_year: 2026,
                lunar_month: 5,
                lunar_day: 8,
                lunar_leap_month: false,
                year_branch_number: 6,
              },
            },
            calendar: {
              hour_ganzhi: "壬午",
              month_branch: "午",
              month_ganzhi: "丙午",
            },
            totals: { upper: 21, lower: 15, moving: 36 },
          } as MeihuaChartViewModel["core_facts"],
        })}
      />,
    );

    expect(screen.getByRole("heading", { name: "可核验起卦" })).toBeVisible();
    expect(screen.getAllByText("按时间起卦").length).toBeGreaterThan(0);
    expect(screen.getByText("年支数")).toBeVisible();
    expect(screen.getByText("6")).toBeVisible();
    expect(screen.getByText("时支数")).toBeVisible();
    expect(screen.getByText("7")).toBeVisible();
    expect(screen.getByText("农历年")).toBeVisible();
    expect(screen.getByText("2026")).toBeVisible();
    expect(screen.getByText("月干支")).toBeVisible();
    expect(screen.getByText("丙午")).toBeVisible();
    expect(screen.getByText("时干支")).toBeVisible();
    expect(screen.getByText("壬午")).toBeVisible();
    expect(screen.getByText("上卦原始和")).toBeVisible();
    expect(screen.getByText("21")).toBeVisible();
    expect(screen.getByText("下卦原始和")).toBeVisible();
    expect(screen.getByText("15")).toBeVisible();
    expect(screen.getByText("动爻原始和")).toBeVisible();
    expect(screen.getByText("36")).toBeVisible();
    expect(screen.queryByText("a".repeat(64))).not.toBeInTheDocument();
    expect(screen.queryByText("casting_digest")).not.toBeInTheDocument();
    expect(screen.queryByText("hour_branch_number")).not.toBeInTheDocument();
    expect(screen.queryByText("推导过程暂缺")).not.toBeInTheDocument();
    expect(screen.queryByText("source_dependency_id")).not.toBeInTheDocument();
  });

  it("highlights the matching triad unit when a polarity row is clicked", async () => {
    const user = userEvent.setup();
    render(<RuntimeChart viewModel={chart()} />);

    await user.click(screen.getByRole("button", { name: /本卦上卦 巽（木）→ 体/ }));
    expect(document.getElementById("meihua-unit-primary-upper")).toHaveAttribute("data-active", "true");
  });

  it("keeps three columns through 768 and only stacks the triad at 360", () => {
    const css = meihuaCss();
    expect(css).toMatch(
      /\.triad\s*\{[^}]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/s,
    );
    expect(css).toMatch(/@media \(max-width: 63\.999rem\)[\s\S]*\.triad\s*\{[^}]*gap:\s*1rem/s);
    expect(css).toMatch(/@media \(max-width: 47\.999rem\)[\s\S]*max-width:\s*12\.5rem/s);
    const tablet = css.split("@media (max-width: 47.999rem)")[1]?.split("@media")[0] ?? "";
    expect(tablet).not.toMatch(/\.triad[^{]*\{[^}]*grid-template-columns/);
    expect(css).toMatch(
      /@media \(max-width: 22\.499rem\)[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\) minmax\(0,\s*1fr\)/s,
    );
    expect(css).toMatch(/@media \(max-width: 22\.499rem\)[\s\S]*\.arrow\s*\{[^}]*display:\s*none/s);
    expect(glyphCss()).toMatch(
      /@media \(max-width: 47\.999rem\)[\s\S]*\.hexName\s*\{[^}]*font-size:\s*var\(--font-size-emphasis\)/s,
    );
    expect(css).not.toMatch(/color-success|color-danger|surface-success|surface-danger/);
  });

  it("hides unknown internal keys, maps autumn, and dedupes seasonal rows", () => {
    const facts = chart().core_facts!;
    render(
      <RuntimeChart
        viewModel={chart({
          core_facts: {
            ...facts,
            interpretation_status: "facts_only",
            seasonal_strength: {
              坎: {
                trigram: "坎",
                month_branch: "申",
                season: "autumn",
                state: "平",
                status: "calculated_strength_not_verdict",
              },
              坎复: {
                trigram: "坎",
                month_branch: "申",
                season: "autumn",
                state: "平",
                status: "calculated_strength_not_verdict",
              },
              坎再: {
                trigram: "坎",
                month_branch: "申",
                season: "autumn",
                state: "平",
                status: "calculated_strength_not_verdict",
              },
            },
            interpretive_candidates: {
              ...facts.interpretive_candidates!,
              boundary:
                "body/use relation polarity is source-adjudicated; seasonal strength still requires synthesis",
            },
          },
        })}
      />,
    );

    expect(screen.getByText(MEIHUA_FACTS_ONLY_CAPTION)).toBeVisible();
    expect(screen.queryByText("facts_only")).not.toBeInTheDocument();
    expect(screen.queryByText("古籍已裁定关系极性")).not.toBeInTheDocument();
    expect(screen.getByText("申月 · 秋")).toBeVisible();
    expect(screen.queryByText("autumn")).not.toBeInTheDocument();
    expect(screen.queryByText("calculated_strength_not_verdict")).not.toBeInTheDocument();
    expect(screen.queryByText(/body\/use/)).not.toBeInTheDocument();
    expect(screen.queryByText(/source-adjudicated/)).not.toBeInTheDocument();
    expect(screen.getByText(MEIHUA_POLARITY_FOOTER)).toBeVisible();
    const table = screen.getByRole("table", { name: "月令旺衰事实" });
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(within(table).getAllByText("坎")).toHaveLength(1);
  });
});
