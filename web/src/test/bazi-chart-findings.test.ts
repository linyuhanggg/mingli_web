import { describe, expect, it } from "vitest";

import { projectBaziRuntimeFindings } from "@/components/readings/bazi-chart-findings";

function finding(claimUnitId: string, publicText = `${claimUnitId} 的公开文本`) {
  return {
    kind_id: "kind.tendency",
    support_mode: "exact",
    public_text: publicText,
    fact_refs: ["fact:bazi/chart"],
    evidence_refs: ["evidence:bazi/rule"],
    data: {
      claim_unit_id: claimUnitId,
      hard_verdict: null,
    },
  };
}

describe("Bazi Runtime finding projection", () => {
  it("maps only admitted claim units to stable Chinese titles", () => {
    const projected = projectBaziRuntimeFindings([
      finding("bazi.month-order-state-v1"),
      finding("bazi.day-master-root-support-v1"),
      finding("bazi.ziping-pattern-entry-v1"),
      finding("bazi.tiaohou-priority-v1"),
      finding("bazi.pillar-roles-v1"),
      finding("bazi.three-yuan-structure-v1"),
      finding("bazi.element-flow-inventory-v1"),
    ]);

    expect(projected.map((item) => item.title)).toEqual([
      "月令状态",
      "日主根气与生扶证据",
      "子平格局入口",
      "调候候选次序",
      "四柱判读次序",
      "天地人三元结构",
      "五行流通事实",
    ]);
    expect(projected.every((item) => !item.title.includes("_"))).toBe(true);
  });

  it("fails closed for unknown, ungrounded, non-exact, or verdict-bearing units", () => {
    expect(projectBaziRuntimeFindings([
      finding("bazi.unknown_runtime_unit-v1", "未知单元不应出现"),
      { ...finding("bazi.month-order-state-v1"), support_mode: "shared_turn" },
      { ...finding("bazi.month-order-state-v1"), fact_refs: [] },
      {
        ...finding("bazi.month-order-state-v1"),
        data: {
          claim_unit_id: "bazi.month-order-state-v1",
          hard_verdict: "偏强",
        },
      },
    ])).toEqual([]);
  });
});
