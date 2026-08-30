import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  BaziChart,
  visibleFactDomainLabels,
  visibleProductBoundary,
} from "@/components/readings/bazi-chart";
import {
  looksInternal,
  natalFindingCards,
} from "@/components/readings/bazi-chart-findings";
import { BAZI_EVIDENCE_RESULT_VIEW_MODEL } from "@/fixtures/bazi-evidence-result";
import { buildBaziChartViewFromViewModel } from "@/lib/reading-display";

afterEach(cleanup);

const PILLAR_BODY =
  "四柱以日干己为主：年柱庚辰为本，月柱丙戌为提纲，时柱丁卯为辅佐。这只是四柱判读次序的定位，格局、旺衰与吉凶仍未裁定。";
const ROOT_SUPPORT_BODY =
  "日主五行火，月令主气五行为火，月令对日主为“旺”（当令同气生扶）；同党出现7处，印星木出现1处，五行计数为木1、火7、土3、金5、水1，同党根气在月、日、时支，透干生扶1、克泄2；这只是根气与月令生扶、克泄证据，整盘身强身弱仍未裁定，用神与吉凶仍未裁定。";
const THREE_YUAN_BODY =
  "四柱天干乙、辛、丙、癸为天元；地支酉、巳、午、巳为地元；支中所藏为人元；这只是干支藏三元的结构陈列，格局与吉凶仍未裁定。";
const ELEMENT_FLOW_BODY =
  "盘中五行出现次数为木1、火7、土3、金5、水1；这只是五行计数与生克次序的陈列，整盘旺衰、喜忌与吉凶仍未裁定。";

const baseChart = buildBaziChartViewFromViewModel(BAZI_EVIDENCE_RESULT_VIEW_MODEL);

describe("natalFindingCards", () => {
  it("keeps Chinese title+body and drops opaque engineering payloads", () => {
    expect(
      natalFindingCards([
        {
          claim_unit_id: "bazi.pillar-roles-v1",
          public_text: PILLAR_BODY,
          year_pillar: "庚辰",
        },
      ]),
    ).toEqual([{ title: "柱位职分", body: PILLAR_BODY }]);
    expect(natalFindingCards([{ public_text: PILLAR_BODY, kind_id: "finding:other" }])).toEqual([]);
    expect(natalFindingCards([{ claim_unit_id: "bazi.pillar-roles-v1" }])).toEqual([]);
    expect(looksInternal("month_command")).toBe(true);
    expect(looksInternal("柱位职分")).toBe(false);
  });

  it("reads a supported nested claim id before a generic top-level kind", () => {
    expect(
      natalFindingCards([
        {
          kind_id: "kind.tendency",
          data: { claim_unit_id: "bazi.pillar-roles-v1" },
          public_text: PILLAR_BODY,
        },
      ]),
    ).toEqual([{ title: "柱位职分", body: PILLAR_BODY }]);
  });

  it("keeps every admitted Runtime claim unit and fails closed for unknown ids", () => {
    const monthOrderBody =
      "月令主气五行为火，日主五行火在该月令状态表中为“旺”；这只确定月令季节状态，整盘身强身弱仍未裁定。";
    const zipingBody =
      "子平月令入口按日干与月令主气的关系确定为“正财格入口”；这里只确定格局入口，格局成败、救应、旺衰和行运仍未裁定。";
    const tiaohouBody =
      "按丙日主、巳月的已核验调候规则，候选次序为“壬、庚”；当前只记录候选与显藏缺失，唯一用神或吉凶仍未裁定。";

    expect(
      natalFindingCards([
        {
          ref: "finding:subject:test/bazi/public-claim/month-order-state",
          kind_id: "kind.tendency",
          data: {
            claim_unit_id: "bazi.month-order-state-v1",
            seasonal_state: "旺",
            hard_verdict: null,
          },
          public_text: monthOrderBody,
        },
        {
          ref: "finding:subject:test/bazi/public-claim/day-master-root-support",
          kind_id: "kind.tendency",
          data: {
            claim_unit_id: "bazi.day-master-root-support-v1",
            same_element_root_positions: ["month", "day", "hour"],
            hard_verdict: null,
          },
          public_text: ROOT_SUPPORT_BODY,
        },
        {
          ref: "finding:subject:test/bazi/public-claim/ziping-pattern-entry",
          kind_id: "kind.tendency",
          data: {
            claim_unit_id: "bazi.ziping-pattern-entry-v1",
            status: "adjudicated_pattern_entry",
            hard_verdict: null,
          },
          public_text: zipingBody,
        },
        {
          ref: "finding:subject:test/bazi/public-claim/tiaohou-priority",
          kind_id: "kind.tendency",
          data: {
            claim_unit_id: "bazi.tiaohou-priority-v1",
            priority_stems: ["壬", "庚"],
            hard_verdict: null,
          },
          public_text: tiaohouBody,
        },
        {
          kind_id: "kind.tendency",
          data: { claim_unit_id: "bazi.pillar-roles-v1" },
          public_text: PILLAR_BODY,
        },
        {
          kind_id: "kind.tendency",
          data: { claim_unit_id: "bazi.three-yuan-structure-v1" },
          public_text: THREE_YUAN_BODY,
        },
        {
          kind_id: "kind.tendency",
          data: { claim_unit_id: "bazi.element-flow-inventory-v1" },
          public_text: ELEMENT_FLOW_BODY,
        },
        {
          kind_id: "kind.tendency",
          data: {
            claim_unit_id: "bazi.future-opaque-unit-v1",
            raw_engineering_field: { verdict_score: 99 },
          },
          public_text: "未知工程单元不得直接上屏。",
        },
      ]),
    ).toEqual([
      { title: "月令状态", body: monthOrderBody },
      { title: "日主根气与生扶", body: ROOT_SUPPORT_BODY },
      { title: "子平格局入口", body: zipingBody },
      { title: "调候候选次序", body: tiaohouBody },
      { title: "柱位职分", body: PILLAR_BODY },
      { title: "三元结构", body: THREE_YUAN_BODY },
      { title: "五行流转盘点", body: ELEMENT_FLOW_BODY },
    ]);
  });
});

describe("F3 product copy lock", () => {
  it("maps engineering boundaries and domain keys to Chinese", () => {
    expect(
      visibleProductBoundary(
        "no Shensha item may override month command, structure, strength, Tiaohou, Ten Gods, or luck/transit facts",
      ),
    ).toMatch(/神煞/);
    expect(
      visibleProductBoundary("inventory only; these counts do not determine 旺衰 or 用神"),
    ).toMatch(/五行计数/);
    expect(
      visibleFactDomainLabels([
        "month_command",
        "structure",
        "strength",
        "tiaohou",
        "ten_gods",
        "luck_cycles",
        "transit_facts",
      ]),
    ).toBe("月令、格局、旺衰、调候、十神、大运、流年流月事实");
  });

  it("does not leak snake_case or English engineering sentences from findings", () => {
    render(
      <BaziChart
        chart={baseChart}
        findings={[
          {
            claim_unit_id: "bazi.pillar-roles-v1",
            public_text: PILLAR_BODY,
            month_command: "should-not-render",
          },
          {
            claim_unit_id: "opaque",
            public_text: "no Shensha item may override month command",
          },
        ]}
      />,
    );
    expect(screen.getByRole("heading", { name: "柱位职分" })).toBeVisible();
    expect(screen.getByText(PILLAR_BODY)).toBeVisible();
    expect(screen.queryByText("month_command")).not.toBeInTheDocument();
    expect(screen.queryByText(/no Shensha item may override/i)).not.toBeInTheDocument();
  });
});
