import { describe, expect, it } from "vitest";

import type { ReadingFact } from "@/lib/api";
import type { BaziInterpretiveCandidates } from "@/view-models/registry";
import {
  buildBaziChartView,
  buildBaziChartViewFromViewModel,
  formatCapabilityIds,
  formatBaziInterpretiveCandidateRows,
  formatDimensionIds,
  formatLiuyaoRoleAdjudicationRows,
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

    const fortuneTargetCalendar = formatReadingFact(
      fact(
        'calendar_normalization: {"time_basis":{"policy":"civil"},"true_solar_time":{"status":"not_applied"}}',
      ),
    );
    expect(fortuneTargetCalendar.text).toContain("时间策略：民用时");
    expect(fortuneTargetCalendar.text).toContain(
      "太阳时修正未应用（当前周期按民用日边界）",
    );
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

  it("hides unknown structured and truncated Runtime payloads instead of printing JSON or English keys", () => {
    const presentations = formatReadingFacts([
      fact(
        'branch_relations: [{"branches":["辰","戌"],"positions":["year","month"],"type":"六冲"}]',
      ),
      fact(
        'interpretive_candidates: {"following_and_transformation":{"boundary":"a combination does not prove transformation"...',
      ),
      fact(
        'luck_cycles: {"approximate_start_datetime":"2007-07-17T17:55:59+08:00"...',
      ),
    ]);

    expect(presentations).toEqual([]);
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

  it("keeps Runtime fortune mechanisms visible without turning them into a verdict", () => {
    const presentation = formatReadingFact(
      fact("周期确定性标记：已由服务端计算", {
        kind_id: "fact:period_markers",
        value: [
          {
            date: "2026-08-14",
            day_pillar: "庚申",
            primary_mechanism_ids: ["day-stem-ten-god"],
            unresolved_boundaries: ["specific_life_event_cannot_be_determined"],
          },
        ],
      }),
    );

    expect(presentation.text).toContain("机制 日干十神");
    expect(presentation.text).not.toContain("吉");
    expect(presentation.text).not.toContain("凶");
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
        twelve_growth_stages: [
          {
            position: "year",
            stem: "甲",
            branch: "戌",
            stage: "养",
            stage_index: 12,
            direction: "forward",
            source_dependency_id: "bazi.chart.twelve-growth-stages-v1",
            boundary: "十二长生位置事实；不能单独推出旺衰、格局、用神或事件结论",
          },
        ],
        xunkong: {
          day_pillar: "丙戌",
          xun: "甲申",
          branches: ["午", "未"],
          source_dependency_id: "bazi.chart.xunkong-sexagenary-v1",
          boundary: "按日柱所属旬计算旬空事实；不能单独推出吉凶、六亲或事件结论",
        },
        san_yuan: {
          tai_yuan: "己未",
          ming_gong: "甲戌",
          shen_gong: "庚午",
          source: "lunar-typescript-auxiliary",
          source_dependency_id: "bazi.chart.san-yuan-lunar-typescript-v1",
          boundary: "胎元、命宫、身宫位置事实；不能单独推出格局、旺衰、吉凶或事件结论",
        },
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
        source_conditioned_patterns: [],
        branch_relations: null,
        shensha_auxiliary: null,
        luck_cycles: null,
        calendar_normalization: null,
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
    expect(chart.dayMaster).toBe("丙（火·阳）");
    expect(chart.dayMaster).not.toContain("fire");
    expect(chart.monthCommand).toContain("主气 戊");
    expect(chart.coreFacts?.twelve_growth_stages?.[0]?.stage).toBe("养");
    expect(chart.coreFacts?.xunkong?.branches).toEqual(["午", "未"]);
    expect(chart.coreFacts?.san_yuan?.tai_yuan).toBe("己未");
    expect(chart.secondary[0]?.text).toContain("不等同旺衰裁决");
  });
});

describe("formatBaziInterpretiveCandidateRows", () => {
  it("renders the verified Ziping pattern entry as a bounded adjudication", () => {
    const candidates = {
      strength: {
        status: "evidence_only",
        hard_verdict: null,
        day_element: "fire",
        month_command_element: "earth",
        seasonal_state: "休",
        seasonal_state_source_rule_id: "bazi/sanming-tonghui#R-02-04",
        same_element_occurrences: 1,
        resource_element: "wood",
        resource_occurrences: 2,
        all_element_occurrences: [
          { element: "wood", value: 2 },
          { element: "fire", value: 1 },
          { element: "earth", value: 4 },
        ],
        month_order_adjudication: {
          status: "adjudicated_month_order_state",
          decision_scope: "bazi_month_order_seasonal_state",
          day_master_element: "fire",
          month_command_element: "earth",
          seasonal_state: "休",
          whole_chart_strength_verdict: null,
          useful_god_verdict: null,
          source_ref: {
            pack: "bazi/sanming-tonghui",
            rule_id: "R-02-04",
            source_anchor: "references/books/bazi/sanming-tonghui/rules.md#R-02-04",
            verification_status: "verified",
            binding_digest: "77b387e17e65b50c7cbcdba3cc8ef5b170499c6d5c07461856b710d5aa50759e",
          },
          unresolved_checks: ["全局根气、生扶、克泄与合化"],
        },
        boundary: "强弱证据不等于旺衰定论",
      },
      structure: {
        status: "candidate_only",
        hard_verdict: null,
        month_main_qi: "戊",
        month_main_qi_ten_god: "食神",
        main_qi_visible: true,
        visible_positions: ["month"],
        boundary: "格局成败仍待裁决",
      },
      following_and_transformation: {
        status: "requires_classical_adjudication",
        hard_verdict: null,
        stem_combination_candidates: [],
        branch_formation_candidates: [],
        boundary: "合化与从格仍待裁决",
      },
      salience_signals: [],
      reasoning_tools: {
        tiaohou_candidates: {
          output: {
            status: "adjudicated_seasonal_priority",
            rule_id: "QR-02-01",
            priority_stems: ["丙", "甲"],
            coverage_status: "partial_visible_or_hidden",
            hard_verdict: null,
          },
        },
        ziping_month_pattern_adjudication: {
          output: {
            status: "adjudicated_pattern_entry",
            pattern_label: "食神格入口",
            hard_verdict: null,
            unresolved_checks: ["格局成败与救应", "旺衰、调候与行运"],
          },
        },
      },
    } as unknown as BaziInterpretiveCandidates;

    expect(formatBaziInterpretiveCandidateRows(candidates)).toContainEqual([
      "月令状态裁定",
      "火日主在土月令为“休”；已按 R-02-04 核验，全局身强身弱与唯一用神仍未裁定",
    ]);
    expect(formatBaziInterpretiveCandidateRows(candidates)).toContainEqual([
      "子平月令裁决",
      "食神格入口；已裁定月令格局入口；待完成：格局成败与救应、旺衰、调候与行运",
    ]);
    expect(formatBaziInterpretiveCandidateRows(candidates)).toContainEqual([
      "调候季节裁决",
      "QR-02-01；季节优先：丙、甲；已裁定来源规则内的季节优先项；可见性：部分透藏",
    ]);
  });
});

describe("formatLiuyaoRoleAdjudicationRows", () => {
  it("shows a uniquely identified visible wealth line without implying an outcome verdict", () => {
    expect(
      formatLiuyaoRoleAdjudicationRows({
        status: "evidence_bound",
        role_adjudication: {
          status: "adjudicated_question_role_set",
          decision_scope: "finance_useful_spirit_role_set",
          question_class: "finance",
          primary_relative: "妻财",
          supporting_relatives: ["子孙"],
          obstacle_attention_relatives: ["兄弟", "官鬼", "父母"],
          specific_line_selection: 4,
          specific_line_adjudication: {
            status: "adjudicated_unique_visible_line",
            decision_scope: "finance_primary_relative_line_identity",
            primary_relative: "妻财",
            visible_candidate_count: 1,
            visible_candidate_lines: [4],
            moving_visible_candidate_count: 1,
            moving_visible_candidate_lines: [4],
            specific_line_selection: 4,
            derivation_basis: "verified_role_plus_runtime_unique_visible_candidate",
            selection_source_ref: {
              pack: "divination/huangjin-ce",
              rule_id: "HJC-R009",
              verification_status: "verified",
            },
            hard_verdict: null,
          },
          hard_verdict: null,
          source_ref: {
            pack: "divination/huangjin-ce",
            rule_id: "HJC-R009",
            verification_status: "verified",
          },
          unresolved_checks: ["月日旺衰与空破冲合", "成败、应期与事件结果"],
        },
      }),
    ).toEqual([
      ["问题角色裁决", "求财：妻财为主，子孙为辅"],
      ["具体用神爻", "第4爻（盘内唯一可见妻财爻）"],
      ["阻碍关注", "兄弟、官鬼、父母"],
      ["来源", "HJC-R009 · divination/huangjin-ce（已核验）"],
      ["裁决边界", "已定位具体爻位；未判断旺衰、成败与应期"],
      ["待完成", "月日旺衰与空破冲合、成败、应期与事件结果"],
    ]);
  });

  it("shows the checked moving line when wealth appears twice and only one line moves", () => {
    expect(
      formatLiuyaoRoleAdjudicationRows({
        status: "evidence_bound",
        role_adjudication: {
          status: "adjudicated_question_role_set",
          decision_scope: "finance_useful_spirit_role_set",
          question_class: "finance",
          primary_relative: "妻财",
          supporting_relatives: ["子孙"],
          obstacle_attention_relatives: ["兄弟", "官鬼", "父母"],
          specific_line_selection: 3,
          specific_line_adjudication: {
            status: "adjudicated_single_moving_visible_line",
            decision_scope: "finance_primary_relative_line_identity",
            primary_relative: "妻财",
            visible_candidate_count: 2,
            visible_candidate_lines: [3, 6],
            moving_visible_candidate_count: 1,
            moving_visible_candidate_lines: [3],
            specific_line_selection: 3,
            derivation_basis:
              "verified_two_present_rule_plus_runtime_single_moving_candidate",
            selection_source_ref: {
              pack: "divination/zengshan-buyi",
              rule_id: "ZR-04-04",
              verification_status: "verified",
            },
            hard_verdict: null,
          },
          hard_verdict: null,
          source_ref: {
            pack: "divination/huangjin-ce",
            rule_id: "HJC-R009",
            verification_status: "verified",
          },
          unresolved_checks: ["月日旺衰与空破冲合", "成败、应期与事件结果"],
        },
      }),
    ).toEqual([
      ["问题角色裁决", "求财：妻财为主，子孙为辅"],
      ["具体用神爻", "第3爻（妻财两现，仅此爻发动，按核验规则取用）"],
      ["阻碍关注", "兄弟、官鬼、父母"],
      ["来源", "HJC-R009 · divination/huangjin-ce（已核验）"],
      ["取爻依据", "ZR-04-04 · divination/zengshan-buyi（已核验）"],
      ["裁决边界", "已定位具体爻位；未判断旺衰、成败与应期"],
      ["待完成", "月日旺衰与空破冲合、成败、应期与事件结果"],
    ]);
  });

  it("does not invent finance roles when no structured question class was supplied", () => {
    expect(
      formatLiuyaoRoleAdjudicationRows({
        status: "evidence_bound",
        role_adjudication: {
          status: "not_requested",
          question_class: null,
        },
      }),
    ).toEqual([]);
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
