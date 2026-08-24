import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { BaziChart } from "@/components/readings/bazi-chart";
import {
  collectNatalFindingSource,
  looksInternal,
  natalFindingCards,
} from "@/components/readings/bazi-chart-findings";
import type { BaziChartView } from "@/lib/reading-display";
import type { BaziCoreFacts } from "@/view-models/registry";

afterEach(cleanup);

const PILLAR_BODY =
  "四柱以日干己为主：年柱庚辰为本，月柱丙戌为提纲，时柱丁卯为辅佐。这只是四柱判读次序的定位，格局、旺衰与吉凶仍未裁定。";
const THREE_YUAN_BODY =
  "四柱天干庚、丙、己、丁为天元；地支辰、戌、酉、卯为地元；支中所藏为人元。这只是干支藏三元的结构陈列，格局与吉凶仍未裁定。";
const ELEMENT_FLOW_BODY =
  "盘中五行（含支藏）出现次数为木3、火3、土5、金4、水2；五行顺则相生、逆则相克。这只是五行计数与生克次序的陈列，整盘旺衰、喜忌与吉凶仍未裁定。";

const PILLAR_FINDING = {
  claim_unit_id: "bazi.pillar-roles-v1",
  public_text: PILLAR_BODY,
  year_pillar: "庚辰",
  custom_payload: { nested: true },
};

const THREE_YUAN_FINDING = {
  data: { claim_unit_id: "bazi.three-yuan-structure-v1" },
  public_text: THREE_YUAN_BODY,
};

const ELEMENT_FLOW_FINDING = {
  unit_id: "element-flow-inventory",
  public_text: ELEMENT_FLOW_BODY,
};

const OPAQUE_FINDING = {
  ref: "finding:opaque-1",
  kind_id: "finding:trend",
  data: { candidate: "不要显示", year_pillar: "庚辰" },
  support_mode: "exact",
};

const INTERNAL_ON_SCREEN =
  /bazi\.pillar-roles-v1|bazi\.three-yuan-structure-v1|claim_unit_id|year_pillar|pillar_roles|finding:opaque|kind_id|support_mode|custom_payload|finding:trend|element-flow-inventory/;

function chart(overrides: Partial<BaziChartView> = {}): BaziChartView {
  return {
    pillars: { year: "庚辰", month: "丙戌", day: "己酉", hour: "丁卯" },
    coreFacts: {
      day_master: { stem: "己", element: "earth", polarity: "阴" },
      month_command: {
        branch: "戌",
        label: "戌月",
        main_qi: "戊",
        main_qi_element: "earth",
      },
    } as unknown as BaziCoreFacts,
    timeLayers: [],
    dayMaster: "己（土·阴）",
    monthCommand: "戌月",
    activeLuck: null,
    birthTime: "2000-10-18T05:10:00+08:00",
    gender: null,
    location: "莆田",
    timeBasis: "longitude_mean_solar-v1",
    ziHour: "早子时按当日",
    timezone: "Asia/Shanghai",
    targetDay: null,
    targetPeriod: null,
    calendarSummary: null,
    highlights: [],
    secondary: [],
    ...overrides,
  };
}

describe("natalFindingCards", () => {
  it("maps known claim units to Chinese title and body and hides unknown keys", () => {
    const cards = natalFindingCards([
      PILLAR_FINDING,
      THREE_YUAN_FINDING,
      ELEMENT_FLOW_FINDING,
      OPAQUE_FINDING,
    ]);
    expect(cards).toEqual([
      { title: "柱位职分", body: PILLAR_BODY },
      { title: "三元结构", body: THREE_YUAN_BODY },
      { title: "五行流转盘点", body: ELEMENT_FLOW_BODY },
    ]);
  });

  it("skips items that only have internal ids or unknown keys", () => {
    expect(natalFindingCards([OPAQUE_FINDING])).toEqual([]);
    expect(
      natalFindingCards([{ public_text: PILLAR_BODY, kind_id: "finding:other" }]),
    ).toEqual([]);
    expect(
      natalFindingCards([{ claim_unit_id: "bazi.pillar-roles-v1" }]),
    ).toEqual([]);
    expect(
      natalFindingCards([
        { claim_unit_id: "bazi.pillar-roles-v1", public_text: "year_pillar 不可上屏" },
      ]),
    ).toEqual([]);
  });

  it("uses GAP-10 natal findings title and body and never surfaces machine ids", () => {
    expect(
      natalFindingCards([
        {
          finding_ref: "finding:natal/bazi/public-claim/pillar-roles",
          claim_unit_id: "bazi.pillar-roles-v1",
          title: "柱位职分",
          body: PILLAR_BODY,
        },
        {
          finding_ref: "finding:natal/bazi/public-claim/month-command",
          claim_unit_id: "bazi.month-command-state-v1",
          title: "月令状态",
          body: "月令戌土当令。这只是月令状态的陈列，旺衰与吉凶仍未裁定。",
        },
      ]),
    ).toEqual([
      { title: "柱位职分", body: PILLAR_BODY },
      {
        title: "月令状态",
        body: "月令戌土当令。这只是月令状态的陈列，旺衰与吉凶仍未裁定。",
      },
    ]);
  });

  it("accepts a Chinese title field when the unit id is absent", () => {
    expect(
      natalFindingCards([{ title: "柱位职分", public_text: PILLAR_BODY }]),
    ).toEqual([{ title: "柱位职分", body: PILLAR_BODY }]);
  });

  it("collects findings and claim_units bags without duplicating the same card", () => {
    const items = collectNatalFindingSource(
      { findings: [OPAQUE_FINDING, PILLAR_FINDING] },
      { claim_units: [PILLAR_FINDING, THREE_YUAN_FINDING] },
    );
    expect(natalFindingCards(items)).toEqual([
      { title: "柱位职分", body: PILLAR_BODY },
      { title: "三元结构", body: THREE_YUAN_BODY },
    ]);
  });

  it("treats dotted ids and snake_case as internal", () => {
    expect(looksInternal("bazi.pillar-roles-v1")).toBe(true);
    expect(looksInternal("year_pillar")).toBe(true);
    expect(looksInternal("finding:opaque-1")).toBe(true);
    expect(looksInternal("柱位职分")).toBe(false);
    expect(looksInternal(PILLAR_BODY)).toBe(false);
  });
});

describe("BaziChart natal findings", () => {
  it("renders Chinese title and body for each finding and hides internal keys", () => {
    render(
      <BaziChart
        chart={chart()}
        findings={[PILLAR_FINDING, THREE_YUAN_FINDING, ELEMENT_FLOW_FINDING, OPAQUE_FINDING]}
      />,
    );

    expect(screen.getByRole("region", { name: "盘面说明" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "柱位职分" })).toBeVisible();
    expect(screen.getByText(PILLAR_BODY)).toBeVisible();
    expect(screen.getByRole("heading", { name: "三元结构" })).toBeVisible();
    expect(screen.getByText(THREE_YUAN_BODY)).toBeVisible();
    expect(screen.getByRole("heading", { name: "五行流转盘点" })).toBeVisible();
    expect(screen.getByText(ELEMENT_FLOW_BODY)).toBeVisible();
    expect(screen.getByRole("link", { name: "盘面说明" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
    expect(document.body.textContent ?? "").not.toMatch(INTERNAL_ON_SCREEN);
    expect(screen.queryByText("不要显示")).not.toBeInTheDocument();
  });

  it("does not render the findings block when the payload is missing or empty", () => {
    const { rerender } = render(<BaziChart chart={chart()} />);
    expect(screen.queryByRole("region", { name: "盘面说明" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "柱位职分" })).not.toBeInTheDocument();

    rerender(<BaziChart chart={chart()} findings={[]} />);
    expect(screen.queryByRole("region", { name: "盘面说明" })).not.toBeInTheDocument();

    rerender(<BaziChart chart={chart()} findings={[OPAQUE_FINDING]} />);
    expect(screen.queryByRole("region", { name: "盘面说明" })).not.toBeInTheDocument();
    expect(screen.queryByText("不要显示")).not.toBeInTheDocument();
    expect(screen.queryByText("finding:opaque-1")).not.toBeInTheDocument();
  });

  it("still renders findings when interpretive sections are hidden", () => {
    render(
      <BaziChart
        chart={chart()}
        findings={{ claim_units: [PILLAR_FINDING] }}
        showInterpretiveSections={false}
      />,
    );
    expect(screen.getByRole("heading", { name: "柱位职分" })).toBeVisible();
    expect(screen.getByText(PILLAR_BODY)).toBeVisible();
    expect(screen.queryByText("古法命中")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "深读" })).toBeVisible();
  });
});
