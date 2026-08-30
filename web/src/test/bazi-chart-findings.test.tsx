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
