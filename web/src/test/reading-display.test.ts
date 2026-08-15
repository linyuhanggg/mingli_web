import { describe, expect, it } from "vitest";

import type { ReadingFact } from "@/lib/api";
import {
  buildBaziChartView,
  buildBaziChartViewFromViewModel,
  formatCapabilityIds,
  formatDimensionIds,
  formatObjectId,
  formatReadingFact,
  formatReadingFacts,
  splitAcceptedCopy,
} from "@/lib/reading-display";

function fact(display_text: string, overrides: Partial<ReadingFact> = {}): ReadingFact {
  return {
    ref: "fact:test",
    subject_ref: "profile-version:secret",
    kind_id: "fact:test",
    value: null,
    display_text,
    ...overrides,
  };
}

describe("formatReadingFact", () => {
  it("keeps plain human sentences intact", () => {
    const presentation = formatReadingFact(
      fact("当前结构更支持持续积累。"),
    );
    expect(presentation.text).toBe("当前结构更支持持续积累。");
    expect(presentation.emphasis).toBe("primary");
  });

  it("humanizes gender, time basis, and datetime fields", () => {
    const facts = formatReadingFacts([
      fact("性别: male"),
      fact("时间口径: civil"),
      fact("子时策略: midnight"),
      fact("出生时间: 1994-04-30T05:55:00+08:00"),
    ]);
    expect(facts.map((item) => [item.label, item.text])).toEqual([
      ["性别", "男"],
      ["时间口径", "民用时"],
      ["子时策略", "按午夜换日"],
      ["出生时间", expect.stringMatching(/1994年4月30日/)],
    ]);
  });

  it("renders natal pillars as structured cards and collapses calendar JSON", () => {
    const pillars = formatReadingFact(
      fact(
        'natal_pillars: {"day":"己酉","hour":"丁卯","month":"丙戌","year":"庚辰"}',
      ),
    );
    expect(pillars.label).toBe("四柱");
    expect(pillars.pillars).toEqual({
      year: "庚辰",
      month: "丙戌",
      day: "己酉",
      hour: "丁卯",
    });

    const calendar = formatReadingFact(
      fact(
        'calendar_normalization: {"algorithm_version":"sxtwl-2.0.7/exact-jie-boundary-v1.2","calendar_convention":{"hour_basis":"civil","engine":"sxtwl","engine_version":"2.0.7"}}',
      ),
    );
    expect(calendar.label).toBe("历法口径");
    expect(calendar.emphasis).toBe("secondary");
    expect(calendar.text).toContain("sxtwl-2.0.7");
    expect(calendar.text).toContain("民用时");
    expect(calendar.text).not.toContain("calendar_convention");
  });

  it("never dumps sensitive value payloads when display_text is usable", () => {
    const presentation = formatReadingFact(
      fact("当前结构更支持持续积累。", {
        value: {
          state_token: "opaque-runtime-token",
          prompt: "内部提示词",
          candidate: "模型草稿",
        },
      }),
    );
    expect(presentation.text).toBe("当前结构更支持持续积累。");
    expect(JSON.stringify(presentation)).not.toMatch(
      /state_token|opaque-runtime-token|内部提示词|模型草稿/,
    );
  });

  it("renders every weekly period marker instead of dropping days after the first", () => {
    const presentation = formatReadingFact(
      fact("周期确定性标记：已由服务端计算", {
        kind_id: "fact:period_markers",
        value: [
          {
            date: "2026-08-10",
            day_pillar: "甲子",
            day_role: "正财",
            active_luck_cycle: "戊子",
          },
          {
            date: "2026-08-11",
            day_pillar: "乙丑",
            day_role: "偏财",
            active_luck_cycle: "戊子",
          },
          {
            date: "2026-08-12",
            day_pillar: "丙寅",
            day_role: "正官",
            active_luck_cycle: "戊子",
          },
        ],
      }),
    );

    expect(presentation.label).toBe("周期标记");
    expect(presentation.text).toContain("2026年8月10日");
    expect(presentation.text).toContain("甲子");
    expect(presentation.text).toContain("2026年8月11日");
    expect(presentation.text).toContain("乙丑");
    expect(presentation.text).toContain("2026年8月12日");
    expect(presentation.text).toContain("丙寅");
  });
});

describe("format reading scope", () => {
  it("uses product labels for every installed Runtime capability", () => {
    expect(
      formatCapabilityIds([
        "bazi",
        "fortune",
        "liuyao",
        "meihua",
        "qimen",
        "liuren",
        "luming-nayin",
        "physiognomy",
        "selection",
        "taiyi",
        "xingming",
        "ziwei",
        "time-check",
      ]),
    ).toBe(
      "八字、日运与周运、六爻、梅花易数、奇门遁甲、大六壬、禄命/纳音、相法、择日、太乙神数、七政四余、紫微斗数、寻时定盘",
    );
  });

  it("uses product labels for P10 objects and dimensions", () => {
    expect(formatObjectId("spatial_observation")).toBe("空间观察");
    expect(formatObjectId("visible_observation")).toBe("可见观察");
    expect(formatDimensionIds(["current_state", "direction", "time_options"])).toBe(
      "当前状态、方位、时辰候选",
    );
  });
});


describe("buildBaziChartView", () => {
  it("uses the real Runtime four_pillars value even when display text is truncated", () => {
    const chart = buildBaziChartView([
      fact('four_pillars：{"day":"己酉","hour":"丁卯"…', {
        ref: "fact:profile-version:secret/calculated/bazi/four_pillars",
        kind_id: "fact:calculation",
        value: {
          year: "庚辰",
          month: "丙戌",
          day: "己酉",
          hour: "丁卯",
        },
      }),
    ]);

    expect(chart.pillars).toEqual({
      year: "庚辰",
      month: "丙戌",
      day: "己酉",
      hour: "丁卯",
    });
  });

  it("extracts pillars and day master for the chart board", () => {
    const chart = buildBaziChartView([
      fact('natal_pillars: {"day":"己酉","hour":"丁卯","month":"丙戌","year":"庚辰"}'),
      fact('day_master: {"element":"土","polarity":"阴","stem":"己"}'),
      fact("active_luck_cycle: 戊子"),
      fact("当前结构更支持持续积累。"),
    ]);
    expect(chart.pillars).toEqual({
      year: "庚辰",
      month: "丙戌",
      day: "己酉",
      hour: "丁卯",
    });
    expect(chart.dayMaster).toContain("己");
    expect(chart.activeLuck).toBe("戊子");
    expect(chart.highlights.some((item) => item.text.includes("持续积累"))).toBe(true);
  });

  it("maps the typed Runtime ViewModel without recalculating the pillars", () => {
    const chart = buildBaziChartViewFromViewModel({
      schema_version: "bazi-chart/v1",
      subject_ref: "profile-version:test",
      pillars: [
        { position: "year", stem: "甲", branch: "戌" },
        { position: "month", stem: "戊", branch: "辰" },
        { position: "day", stem: "丙", branch: "戌" },
        { position: "hour", stem: "辛", branch: "卯" },
      ],
      element_balance: [
        {
          element: "earth",
          value: 4,
          display_text: "土 · 可见干支计数 4（不等同旺衰裁决）",
        },
      ],
      time_layers: [],
      core_facts: {
        day_master: { stem: "丙", element: "fire", polarity: "阳" },
        hidden_stems: null,
        ten_gods: null,
        nayin: null,
        month_command: {
          branch: "辰",
          label: "辰月",
          main_qi: "戊",
          main_qi_element: "earth",
        },
        seasonal_profile: null,
        tiaohou_markers: null,
        element_inventory: null,
        interpretive_candidates: null,
        branch_relations: null,
        shensha_auxiliary: null,
        luck_cycles: null,
        year_layers: null,
      },
    });

    expect(chart.pillars).toEqual({
      year: "甲戌",
      month: "戊辰",
      day: "丙戌",
      hour: "辛卯",
    });
    expect(chart.dayMaster).toContain("丙");
    expect(chart.monthCommand).toContain("主气 戊");
    expect(chart.secondary[0]?.text).toContain("不等同旺衰裁决");
  });
});

describe("splitAcceptedCopy", () => {
  it("uses the first paragraph as headline when available", () => {
    expect(splitAcceptedCopy("先给结论。\n\n再说明依据，原字原序。")).toEqual({
      headline: "先给结论",
      body: "再说明依据，原字原序。",
    });
  });
});
