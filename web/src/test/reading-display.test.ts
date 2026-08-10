import { describe, expect, it } from "vitest";

import type { ReadingFact } from "@/lib/api";
import { buildBaziChartView, formatReadingFact, formatReadingFacts, splitAcceptedCopy } from "@/lib/reading-display";

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
      fact("出生时间: 2000-10-18T05:10:00+08:00"),
    ]);
    expect(facts.map((item) => [item.label, item.text])).toEqual([
      ["性别", "男"],
      ["时间口径", "民用时"],
      ["子时策略", "按午夜换日"],
      ["出生时间", expect.stringMatching(/2000年10月18日/)],
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
});


describe("buildBaziChartView", () => {
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
});

describe("splitAcceptedCopy", () => {
  it("uses the first paragraph as headline when available", () => {
    expect(splitAcceptedCopy("先给结论。\n\n再说明依据，原字原序。")).toEqual({
      headline: "先给结论",
      body: "再说明依据，原字原序。",
    });
  });
});
