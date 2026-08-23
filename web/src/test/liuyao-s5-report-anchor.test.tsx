import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LiuyaoLineTower } from "@/components/readings/liuyao-line-tower";
import { RuntimeChart } from "@/components/readings/runtime-chart";
import { resolveLiuyaoS5Anchors } from "@/components/readings/liuyao-s5-anchors";
import type { LiuyaoChartViewModel } from "@/view-models/registry";

afterEach(cleanup);

type CoreFacts = NonNullable<LiuyaoChartViewModel["core_facts"]>;

function emptyFacts(overrides: Partial<CoreFacts> = {}): CoreFacts {
  return {
    calendar: null,
    casting: null,
    casting_method: null,
    changed_najia: null,
    changed_plate_lines: null,
    changed_six_relatives: null,
    hidden_lines: null,
    interpretation_status: null,
    line_facts: null,
    lines: null,
    month_day_strength: null,
    moving_lines: null,
    najia: null,
    relation_facts: null,
    returning_relations: null,
    requested_useful_spirit_candidates: null,
    shi_ying: null,
    shi_ying_moving_relations: null,
    six_relatives: null,
    six_spirit_profile: null,
    six_spirits: null,
    useful_spirit_candidates: null,
    useful_spirit_selection: null,
    xunkong: null,
    ...overrides,
  };
}

const NAJIA = [
  { stem: "丁", branch: "巳", ganzhi: "丁巳", element: "火", source_dependency_id: "liuyao.chart.najia" },
  { stem: "丁", branch: "卯", ganzhi: "丁卯", element: "木", source_dependency_id: "liuyao.chart.najia" },
  { stem: "丁", branch: "丑", ganzhi: "丁丑", element: "土", source_dependency_id: "liuyao.chart.najia" },
  { stem: "丙", branch: "申", ganzhi: "丙申", element: "金", source_dependency_id: "liuyao.chart.najia" },
  { stem: "丙", branch: "午", ganzhi: "丙午", element: "火", source_dependency_id: "liuyao.chart.najia" },
  { stem: "丙", branch: "辰", ganzhi: "丙辰", element: "土", source_dependency_id: "liuyao.chart.najia" },
] as const;

function chart(overrides: Partial<LiuyaoChartViewModel> = {}): LiuyaoChartViewModel {
  return {
    schema_version: "liuyao-chart/v1",
    subject_ref: "liuyao:s5-fixture",
    question: "这次求财如何？",
    primary_hexagram: {
      name: "山泽损",
      upper_trigram: "艮",
      lower_trigram: "兑",
    },
    changed_hexagram: {
      name: "风泽中孚",
      upper_trigram: "巽",
      lower_trigram: "兑",
    },
    lines: [
      { position: 1, value: 9, moving: true },
      { position: 2, value: 8, moving: false },
      { position: 3, value: 7, moving: false },
      { position: 4, value: 6, moving: true },
      { position: 5, value: 8, moving: false },
      { position: 6, value: 7, moving: false },
    ],
    core_facts: emptyFacts({
      najia: [...NAJIA],
      relation_facts: [
        {
          changed: {
            stem: "辛",
            branch: "未",
            ganzhi: "辛未",
            element: "土",
            source_dependency_id: "liuyao.chart.najia",
          },
          original: NAJIA[0],
          relations: ["回头生"],
          fact_status: "calculated_relation_not_verdict",
          source_dependency_id: "liuyao.relations.returning-and-useful-spirit-candidates",
        },
      ],
      source_conditioned_patterns: [
        {
          rule_id: "divination/huangjin-ce#HJC-M001",
          local_rule_id: "HJC-M001",
          title: "求财先看妻财",
          source_pack: "divination/huangjin-ce",
          source_anchor: "references/books/divination/huangjin-ce/rules.md#HJC-M001",
          status: "predicate_matched_not_verdict",
          fact_paths: ["fact:/chart_facts/output/line_facts/3/six_relative"],
          predicate_audit: ["四爻妻财可见"],
        },
      ],
    }),
    ...overrides,
  };
}

describe("六爻 S5 报告态锚点回跳 S3", () => {
  it("maps line, relation and pattern refs onto existing S3 targets", () => {
    const view = chart();
    expect(
      resolveLiuyaoS5Anchors(["fact:liuyao:s5-fixture/chart_facts/output/line_facts/0"], view),
    ).toEqual([
      {
        kind: "line",
        line: 1,
        relationKey: null,
        patternId: null,
        label: "初爻",
      },
    ]);
    expect(
      resolveLiuyaoS5Anchors(
        ["fact:liuyao:s5-fixture/chart_facts/output/relation_facts/0"],
        view,
      ),
    ).toEqual([
      {
        kind: "relation",
        line: 1,
        relationKey: "relation:0",
        patternId: null,
        label: "关系事实",
      },
    ]);
    expect(
      resolveLiuyaoS5Anchors(
        ["fact:liuyao:s5-fixture/chart_facts/output/source_conditioned_patterns/0"],
        view,
      ),
    ).toEqual([
      {
        kind: "pattern",
        line: 4,
        relationKey: null,
        patternId: "HJC-M001",
        label: "古法命中",
      },
    ]);
    expect(resolveLiuyaoS5Anchors(["fact:unrelated/other"], view)).toEqual([]);
  });

  it("does not invent a report when no deliverable claims are supplied", () => {
    render(<RuntimeChart viewModel={chart()} />);

    expect(screen.queryByRole("heading", { name: "报告" })).not.toBeInTheDocument();
    expect(document.querySelector('nav a[href="#liuyao-s5-report"]')).toBeNull();
    expect(screen.queryByRole("button", { name: "初爻" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "关系事实" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "古法命中" })).not.toBeInTheDocument();
  });

  it("jumps a line claim back to the S3 tower row", async () => {
    const user = userEvent.setup();
    const scrollIntoView = vi.fn();
    HTMLElement.prototype.scrollIntoView = scrollIntoView;

    render(
      <LiuyaoLineTower
        view={chart()}
        reportClaims={[
          {
            claim_id: "claim-line-1",
            text: "初爻发动。",
            fact_refs: ["fact:liuyao:s5-fixture/chart_facts/output/line_facts/0"],
          },
        ]}
      />,
    );

    expect(screen.getByText("初爻发动。")).toBeVisible();
    expect(screen.queryByText(/fact:liuyao/)).not.toBeInTheDocument();
    expect(document.querySelector('nav a[href="#liuyao-s5-report"]')).toHaveTextContent("报告");

    await user.click(screen.getByRole("button", { name: "初爻" }));

    expect(document.getElementById("liuyao-line-1")).toHaveAttribute("data-focus", "true");
    expect(scrollIntoView).toHaveBeenCalled();
  });

  it("jumps a relation claim back to the S3 relation row and tower line", async () => {
    const user = userEvent.setup();
    HTMLElement.prototype.scrollIntoView = vi.fn();

    render(
      <RuntimeChart
        viewModel={chart()}
        reportClaims={[
          {
            claim_id: "claim-relation-1",
            text: "初爻动化回头生。",
            fact_refs: ["fact:liuyao:s5-fixture/chart_facts/output/relation_facts/0"],
          },
        ]}
      />,
    );

    await user.click(screen.getByRole("button", { name: "关系事实" }));
    expect(document.getElementById("liuyao-relation-relation:0")).toHaveAttribute("data-active", "true");
    expect(document.getElementById("liuyao-line-1")).toHaveAttribute("data-focus", "true");
  });

  it("jumps a pattern claim back to the S3 classical hit and mapped line", async () => {
    const user = userEvent.setup();
    HTMLElement.prototype.scrollIntoView = vi.fn();

    render(
      <LiuyaoLineTower
        view={chart()}
        reportClaims={[
          {
            claim_id: "claim-pattern-1",
            text: "求财先看妻财已命中。",
            fact_refs: ["fact:liuyao:s5-fixture/chart_facts/output/source_conditioned_patterns/0"],
          },
        ]}
      />,
    );

    await user.click(screen.getByRole("button", { name: "古法命中" }));
    expect(document.getElementById("liuyao-s3-patterns")?.querySelector("details")).toHaveAttribute("open");
    expect(document.getElementById("liuyao-pattern-HJC-M001")).toHaveAttribute("data-active", "true");
    expect(document.getElementById("liuyao-line-4")).toHaveAttribute("data-focus", "true");
  });
});
