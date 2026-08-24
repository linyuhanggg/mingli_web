import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { RuntimeChart } from "@/components/readings/runtime-chart";
import type { DaliurenChartViewModel, ZiweiChartViewModel } from "@/view-models/registry";

afterEach(cleanup);

const ziweiView = {
  schema_version: "ziwei-chart/v1",
  subject_ref: "profile-version:fixture",
  life_palace_id: "0",
  body_palace_id: "1",
  palaces: [],
  time_layers: [],
  core_facts: {
    source_conditioned_patterns: [
      {
        rule_id: "ziwei/taiwei-fu#TR-01",
        local_rule_id: "TR-01",
        title: "至玄至微",
        source_pack: "ziwei/taiwei-fu",
        source_anchor: "rules.md#L9-L16",
        status: "predicate_matched_not_verdict",
        fact_paths: ["fact:/chart_facts/output/palaces/0/name"],
        predicate_audit: ["/output/palaces:descendant_eq:命宫"],
      },
    ],
    interpretive_candidates: {
      status: "candidate_only",
      matched_rules: ["TR-01"],
      transformation_facts: [],
      boundary: "仅展示盘面候选",
    },
  },
} as unknown as ZiweiChartViewModel;

const bTier = {
  capability_id: "ziwei",
  label: "紫微",
  tier: "B" as const,
  source_system: "ziwei",
  runtime_active_rule_count: 2,
  judgment_rule_count: 0,
  source_status: "available" as const,
};

const daliurenView = {
  schema_version: "daliuren-chart/v1",
  subject_ref: "daliuren:capability-gate",
  question: "这件事何时可能出现回应？",
  lessons: [
    { lesson_id: "一课·日干", upper: "巳", lower: "丁" },
    { lesson_id: "二课·日支", upper: "卯", lower: "巳" },
    { lesson_id: "三课·辰干", upper: "酉", lower: "亥" },
    { lesson_id: "四课·辰支", upper: "未", lower: "酉" },
  ],
  transmissions: [
    { stage: "initial", branch: "酉", general: "贵人" },
    { stage: "middle", branch: "未", general: "太阴" },
    { stage: "final", branch: "巳", general: "白虎" },
  ],
  core_facts: {
    day_hour: { day: "丙午", hour: "卯" },
    dimension_facts: {
      relationship: {
        canonical_dimension: "relationship",
        requested_dimension: "relationship",
        rule_evidence: {
          catalog_schema: "mingli-liuren-executable-rules-v1",
          hard_verdict: null,
          matched: [
            {
              activation_id: "liuren.relationship.branch_overcomes_day",
              dependency_group: "liuren.subject_object_relation",
              fact_paths: ["dimension_facts.relationship.subject_object_relation"],
              observation: { relation: "object_overcomes_subject" },
              polarity: "oppose",
              rule_id: "LR-17",
              rule_key: "relationship_day_branch_overcomes_stem",
              source_refs: [],
              status: "matched",
              weight_class: "primary",
            },
          ],
          not_evaluated: [],
          requires_school_adjudication: true,
          scope_boundaries: [],
          status: "matched_evidence",
        },
      },
    },
    earth_plate: null,
    heaven_plate: null,
    heavenly_generals: null,
    lesson_method: {
      calculated_transmissions: "初传酉，中传未，末传巳",
      calculation_source: "runtime_core_facts",
      direct_direction: null,
      primary: "贼克课",
      selected_initial: "酉",
      source_anchor: "references/books/san-shi/liuren-miben/rules.md#LM-METHOD",
      use_method: "下贼上发用",
    },
    month_general: null,
    noble_person: null,
    plate_offset: null,
    structural_patterns: ["伏吟"],
    timing_candidates: [
      {
        id: "initial_group_upper_candidate",
        role: "event_response_candidate",
        anchor_earth_branch: "巳",
        branch: "酉",
        solar_date: "2026-09-02",
        day_ganzhi: "庚申",
        days_after_cast: 7,
        source_pack: "san-shi/liuren-miben",
        source_rule: "LM-R21",
        candidate_not_guarantee: true,
      },
    ],
    xunkong: null,
  },
} satisfies DaliurenChartViewModel;

const daliurenBTier = {
  ...bTier,
  capability_id: "daliuren",
  label: "大六壬",
  source_system: "liuren",
};

const daliurenATier = {
  ...daliurenBTier,
  tier: "A" as const,
  judgment_rule_count: 5,
};

describe("Runtime capability tier gate", () => {
  it("keeps B-tier facts and removes interpretive candidate blocks", () => {
    render(<RuntimeChart viewModel={ziweiView} capability={bTier} />);

    expect(screen.getByRole("table", { name: "十二宫与主星" })).toBeVisible();
    expect(screen.queryByRole("table", { name: "古籍来源条件候选" })).toBeNull();
    expect(screen.queryByText("TR-01 · 至玄至微")).toBeNull();
  });

  it("keeps Daliuren B-tier board facts while removing evidence, candidates, summary and deep read", () => {
    render(<RuntimeChart viewModel={daliurenView} capability={daliurenBTier} />);

    expect(screen.getByRole("region", { name: "课传" })).toBeVisible();
    expect(screen.getByRole("table", { name: "四课" })).toBeVisible();
    expect(screen.getByRole("region", { name: "课式与传法" })).toBeVisible();
    expect(screen.getByText("贼克课")).toBeVisible();
    expect(screen.queryByRole("region", { name: "维度证据" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "应期候选" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "基础摘要" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "深读" })).not.toBeInTheDocument();
    expect(screen.queryByText("测试期未开放")).not.toBeInTheDocument();
  });

  it("keeps Daliuren interpretive sections available for an A-tier projection", () => {
    render(<RuntimeChart viewModel={daliurenView} capability={daliurenATier} />);

    expect(screen.getByRole("region", { name: "维度证据" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "应期候选" })).toBeVisible();
    expect(screen.getByRole("region", { name: "基础摘要" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
    expect(screen.getByText("测试期未开放")).toBeVisible();
  });
});
