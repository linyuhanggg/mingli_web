import { describe, expect, it } from "vitest";

import { buildBaziFactDisplay } from "@/lib/bazi-fact-display";
import type { ReadingFact } from "@/lib/api";

const SUBJECT = "profile-version:22222222-2222-4222-8222-222222222222";

function fact(key: string, value: unknown): ReadingFact {
  return {
    ref: `fact:${SUBJECT}/calculated/bazi/${key}`,
    subject_ref: SUBJECT,
    kind_id: "kind.fact",
    value,
    display_text: `${key}：此字段故意不作为展示输入`,
  };
}

describe("buildBaziFactDisplay", () => {
  it("maps the four pillar detail columns from public ref/value facts in canonical order", () => {
    const view = buildBaziFactDisplay([
      fact("four_pillars", {
        hour: "丁卯",
        day: "己酉",
        year: "庚辰",
        month: "丙戌",
      }),
      fact("hidden_stems", {
        hour: { branch: "卯", stems: ["乙"] },
        day: { branch: "酉", stems: ["辛"] },
        year: { branch: "辰", stems: ["戊", "乙", "癸"] },
        month: { branch: "戌", stems: ["戊", "辛", "丁"] },
      }),
      fact("ten_gods", {
        hidden_stems: {
          hour: [{ stem: "乙", ten_god: "七杀" }],
          day: [{ stem: "辛", ten_god: "食神" }],
          year: [
            { stem: "戊", ten_god: "劫财" },
            { stem: "乙", ten_god: "七杀" },
            { stem: "癸", ten_god: "偏财" },
          ],
          month: [
            { stem: "戊", ten_god: "劫财" },
            { stem: "辛", ten_god: "食神" },
            { stem: "丁", ten_god: "偏印" },
          ],
        },
        heavenly_stems: {
          hour: { stem: "丁", ten_god: "偏印" },
          day: { stem: "己", ten_god: "日主" },
          year: { stem: "庚", ten_god: "伤官" },
          month: { stem: "丙", ten_god: "正印" },
        },
      }),
      fact("nayin", {
        hour: "炉中火",
        day: "大驿土",
        year: "白蜡金",
        month: "屋上土",
      }),
    ]);

    expect(view.pillars).toEqual([
      {
        position: "year",
        label: "年柱",
        pillar: "庚辰",
        branch: "辰",
        heavenlyStemTenGod: { stem: "庚", tenGod: "伤官" },
        hiddenStems: ["戊", "乙", "癸"],
        hiddenStemTenGods: [
          { stem: "戊", tenGod: "劫财" },
          { stem: "乙", tenGod: "七杀" },
          { stem: "癸", tenGod: "偏财" },
        ],
        nayin: "白蜡金",
      },
      expect.objectContaining({
        position: "month",
        label: "月柱",
        pillar: "丙戌",
        hiddenStems: ["戊", "辛", "丁"],
        nayin: "屋上土",
      }),
      expect.objectContaining({
        position: "day",
        label: "日柱",
        pillar: "己酉",
        heavenlyStemTenGod: { stem: "己", tenGod: "日主" },
        nayin: "大驿土",
      }),
      expect.objectContaining({
        position: "hour",
        label: "时柱",
        pillar: "丁卯",
        hiddenStemTenGods: [{ stem: "乙", tenGod: "七杀" }],
        nayin: "炉中火",
      }),
    ]);
  });

  it("maps visible and hidden element inventory counts and fills omitted elements with zero", () => {
    const view = buildBaziFactDisplay([
      fact("element_inventory", {
        visible_stem_branch_counts: { 木: 2, 火: 1, 土: 4, 金: 1 },
        hidden_stem_occurrence_counts: {
          木: 2,
          火: 2,
          土: 3,
          金: 2,
          水: 1,
        },
        scope: "inventory only; these counts do not determine 旺衰 or 用神",
      }),
    ]);

    expect(view.elements).toEqual([
      { element: "木", visibleCount: 2, hiddenCount: 2 },
      { element: "火", visibleCount: 1, hiddenCount: 2 },
      { element: "土", visibleCount: 4, hiddenCount: 3 },
      { element: "金", visibleCount: 1, hiddenCount: 2 },
      { element: "水", visibleCount: 0, hiddenCount: 1 },
    ]);
  });

  it("projects shensha only from calculated_items and omits rule metadata", () => {
    const view = buildBaziFactDisplay([
      fact("shensha_auxiliary", {
        evaluated_rules: [
          {
            id: "yima",
            name: "驿马",
            anchor_position: "year",
            matched: false,
          },
        ],
        calculated_items: [
          {
            id: "taohua",
            name: "桃花",
            target_branch: "卯",
            anchor_positions: ["year", "day"],
            matched_positions: ["hour"],
            source_dependency_id: "internal-source-id",
          },
        ],
      }),
    ]);

    expect(view.shenshaAuxiliary).toEqual({
      items: [
        {
          name: "桃花",
          targetBranch: "卯",
          anchorPositions: ["year", "day"],
          matchedPositions: ["hour"],
        },
      ],
    });
    expect(JSON.stringify(view.shenshaAuxiliary)).not.toContain("驿马");
    expect(JSON.stringify(view.shenshaAuxiliary)).not.toContain(
      "internal-source-id",
    );
  });

  it("marks the four Runtime 5.1 gaps as unprojected without deriving them", () => {
    const view = buildBaziFactDisplay([]);

    expect(view.unprojected).toEqual([
      { id: "kongwang", label: "空亡", status: "5.1 未投影" },
      { id: "dishi", label: "地势", status: "5.1 未投影" },
      { id: "zizuo", label: "自坐", status: "5.1 未投影" },
      { id: "sangong", label: "三宫", status: "5.1 未投影" },
    ]);
  });

  it("ignores display_text and non-calculated refs", () => {
    const calculatedWithMisleadingText: ReadingFact = {
      ...fact("four_pillars", null),
      display_text:
        'four_pillars：{"year":"庚辰","month":"丙戌","day":"己酉","hour":"丁卯"}',
    };
    const inputFact: ReadingFact = {
      ...fact("four_pillars", {
        year: "庚辰",
        month: "丙戌",
        day: "己酉",
        hour: "丁卯",
      }),
      ref: `fact:${SUBJECT}/input/four_pillars`,
    };

    const view = buildBaziFactDisplay([
      calculatedWithMisleadingText,
      inputFact,
    ]);

    expect(view.pillars.map((pillar) => pillar.pillar)).toEqual([
      null,
      null,
      null,
      null,
    ]);
  });
});
