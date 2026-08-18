import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RuntimeChart } from "@/components/readings/runtime-chart";
import type { ZiweiChartViewModel } from "@/view-models/registry";

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

describe("Runtime capability tier gate", () => {
  it("keeps B-tier facts and removes interpretive candidate blocks", () => {
    render(<RuntimeChart viewModel={ziweiView} capability={bTier} />);

    expect(screen.getByRole("table", { name: "十二宫与主星" })).toBeVisible();
    expect(screen.queryByRole("table", { name: "古籍来源条件候选" })).toBeNull();
    expect(screen.queryByText("TR-01 · 至玄至微")).toBeNull();
  });
});
