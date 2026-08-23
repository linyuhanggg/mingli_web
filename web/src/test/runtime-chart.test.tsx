import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { RuntimeChart } from "@/components/readings/runtime-chart";

it("renders Fortune Runtime facts without adding a daily verdict", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "fortune-facts-view/v1",
        subject_ref: "fortune:fixture",
        natal_pillars: { year: "甲戌", month: "戊辰", day: "丙戌", hour: "辛卯" },
        day_master: { stem: "丙", element: "fire", polarity: "阳" },
        month_command: {
          branch: "辰",
          label: "辰月",
          main_qi: "戊",
          main_qi_element: "earth",
        },
        active_luck_cycle: "乙丑",
        target_day: "2026-08-14",
        target_period: { kind: "day", start: "2026-08-14", end: "2026-08-14" },
        available_periods: ["2026-08-14"],
        period_markers: [
          {
            date: "2026-08-14",
            day_pillar: "甲子",
            day_role: "日运",
            active_luck_cycle: "乙丑",
            primary_mechanism_ids: ["fortune.day_pillar"],
            decisive_mechanism_ids: [],
            relations: [],
            specific_event_policy: "事实标记，不推出具体事件",
            unresolved_boundaries: [],
          },
        ],
        calendar_normalization: {
          status: "calculated",
          algorithm_version: "fixture-v1",
          time_basis: {
            policy: "local_apparent_solar-v1",
            standard_meridian_degrees: 120,
            longitude_correction_seconds: 0,
            equation_of_time_seconds: 0,
            total_correction_seconds: 0,
            algorithm: {
              id: null,
              version: null,
              source: null,
              uncertainty_seconds: null,
            },
            boundary: {
              distance_seconds: null,
              correction_changes_hour_branch: false,
              within_uncertainty: null,
            },
          },
          true_solar_time: {
            status: "apparent_solar_applied",
            policy: "local_apparent_solar-v1",
            longitude_correction_seconds: 0,
            equation_of_time_seconds: 0,
            total_correction_seconds: 0,
          },
          calendar_convention: {
            id: null,
            version: null,
            year_boundary: null,
            month_boundary: null,
            day_rollover: null,
            hour_basis: "true_solar",
            zi_hour_policy: null,
          },
        },
      }}
    />
  );

  expect(screen.getByText("日运本命四柱事实")).toBeVisible();
  expect(screen.getAllByText("2026-08-14").length).toBeGreaterThanOrEqual(3);
  expect(screen.getByText("fortune.day_pillar")).toBeVisible();
  expect(screen.getByText(/不追加具体事件、吉凶或人生判断/)).toBeVisible();
});

it("renders Wenshi Runtime evidence without turning it into a verdict", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "wenshi-view/v1",
        subject_ref: "wenshi:fixture",
        question: "这次合作能否推进？",
        selected_art_ids: ["liuyao", "qimen", "daliuren"],
        dimensions: [
          {
            dimension_id: "outcome",
            signals: [
              {
                art_id: "daliuren",
                subject_refs: ["wenshi:fixture"],
                signal_id: "daliuren.outcome.rule_evidence.subject_object_relation",
                display_text: "大六壬已提供来源绑定规则证据（LR-17）；当前仍不形成问事合参结论。",
                fact_refs: ["fact:wenshi:fixture/calculated/liuren/dimension_facts"],
              },
            ],
            convergence: [],
            disagreements: [],
            missing_art_ids: ["liuyao", "qimen"],
          },
        ],
      }}
    />,
  );

  expect(screen.getByText("六爻、奇门、大六壬")).toBeVisible();
  expect(screen.getByText(/来源绑定规则证据/)).toBeVisible();
  expect(screen.getByText("缺少三术结构事实：六爻、奇门")).toBeVisible();
  expect(screen.queryByText(/fact:wenshi:fixture/)).toBeNull();
  expect(screen.queryByText(/生成吉凶|直接判断成败/)).toBeNull();
});

it("renders the source-bound Liuyao role adjudication without a line verdict", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "liuyao-chart/v1",
        subject_ref: "liuyao:finance-fixture",
        question: "这次求财如何？",
        primary_hexagram: {
          name: "山泽损",
          upper_trigram: "艮",
          lower_trigram: "兑",
        },
        changed_hexagram: {
          name: "风泽中孚",
          upper_trigram: "巽",
          lower_trigram: "兑",
        },
        lines: [
          { position: 1, value: 6, moving: true },
          { position: 2, value: 7, moving: false },
          { position: 3, value: 8, moving: false },
          { position: 4, value: 9, moving: true },
          { position: 5, value: 6, moving: true },
          { position: 6, value: 7, moving: false },
        ],
        core_facts: {
          calendar: null,
          casting: null,
          casting_method: "supplied_complete_cast",
          changed_najia: null,
          changed_plate_lines: null,
          changed_six_relatives: null,
          hidden_lines: null,
          interpretation_status: "facts_only",
          line_facts: null,
          lines: null,
          month_day_strength: null,
          moving_lines: [1, 4, 5],
          najia: null,
          relation_facts: null,
          returning_relations: null,
          requested_useful_spirit_candidates: null,
          shi_ying: null,
          shi_ying_moving_relations: null,
          six_relatives: null,
          six_spirit_profile: null,
          six_spirits: null,
          useful_spirit_candidates: null,
          useful_spirit_selection: {
            status: "evidence_bound",
            reason: "school-dependent adjudication is outside deterministic calculation",
            query_word_matching: false,
            source_dependency_id: "liuyao.relations.returning-and-useful-spirit-candidates",
            chain_candidates: { status: "candidate_only" },
            strength_evidence: {
              status: "candidate_only",
              by_relative: {
                妻财: {
                  status: "candidate_only",
                  candidates: [{
                    source: "visible_line",
                    line: 4,
                    moving: true,
                    xunkong: false,
                    najia: { element: "金" },
                    month_day_strength: { seasonal_state: "旺" },
                    seasonal_adjudication: {
                      status: "adjudicated_seasonal_strength_band",
                      decision_scope: "liuyao_candidate_month_order_strength_band",
                      candidate_source: "visible_line",
                      line: 4,
                      line_element: "金",
                      month_element: "金",
                      seasonal_state: "旺",
                      strength_band: "旺相",
                      whole_candidate_strength_verdict: null,
                      outcome_verdict: null,
                      source_ref: {
                        pack: "divination/zengshan-buyi",
                        rule_id: "ZR-05-05",
                        source_anchor: "references/books/divination/zengshan-buyi/rules.md#ZR-05-05",
                        verification_status: "verified",
                        binding_digest: "strength-binding-digest",
                      },
                      unresolved_checks: ["日辰与空破动变"],
                    },
                    signals: [
                      { signal: "seasonal_support", value: "旺", status: "candidate_signal" },
                      { signal: "moving_line", value: true, status: "candidate_signal" },
                    ],
                    status: "candidate_only",
                    hard_verdict: null,
                  }],
                  hard_verdict: null,
                },
              },
              source_rules: [{
                pack: "divination/zengshan-buyi",
                rule_id: "ZR-05-05",
                source_anchor: "references/books/divination/zengshan-buyi/rules.md#ZR-05-05",
                verification_status: "verified",
                binding_digest: "strength-binding-digest",
                role: "useful_spirit_month_order_strength_band",
              }],
              fact_status: "calculated_relation_not_verdict",
              hard_verdict: null,
              requires_school_adjudication: true,
              source_dependency_id: "liuyao.interpretation.useful-spirit-strength-evidence",
            },
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
                  source_anchor: "references/books/divination/huangjin-ce/rules.md#HJC-R009",
                  verification_status: "verified",
                  binding_digest: "test-binding-digest",
                },
                hard_verdict: null,
              },
              hard_verdict: null,
              source_ref: {
                pack: "divination/huangjin-ce",
                rule_id: "HJC-R009",
                source_anchor: "references/books/divination/huangjin-ce/rules.md#HJC-R009",
                verification_status: "verified",
                binding_digest: "test-binding-digest",
              },
              unresolved_checks: ["月日旺衰与空破冲合", "成败、应期与事件结果"],
            },
            question_context: {
              question_class: "finance",
              classification_source: "explicit_structured_input",
            },
          },
          xunkong: null,
        },
      }}
    />,
  );

  expect(screen.getByText("六爻问题角色裁决")).toBeVisible();
  expect(screen.getByText("求财：妻财为主，子孙为辅")).toBeVisible();
  expect(screen.getByText("第4爻（盘内唯一可见妻财爻）")).toBeVisible();
  expect(screen.getByText("第4爻：旺（旺相带；ZR-05-05 已核验）")).toBeVisible();
  expect(
    screen.getByText("已定位具体爻位；仅裁定月令季节带，未判断综合旺衰、成败与应期"),
  ).toBeVisible();
});

it("renders every Runtime Qimen star when a palace has a duplicated star", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "qimen-chart/v1",
        subject_ref: "qimen:fixture",
        question: "这次合作能否推进？",
        dun_type: "yang",
        ju_number: 3,
        palaces: Array.from({ length: 9 }, (_, index) => ({
          palace_id: String(index + 1),
          stem: "戊",
          heaven_stems: index === 0 ? ["乙", "戊"] : [],
          stars: index === 0 ? ["天辅", "天禽"] : [],
          star: index === 0 ? "天辅" : null,
          door: index === 0 ? "生门" : null,
          deity: index === 0 ? "九天" : null,
        })),
        chief: {
          star: "天辅",
          door: "生门",
          hidden_instrument: "戊",
          xun_palace: 1,
          hosted_xun_palace: 1,
          destination_palace: 1,
        },
        director: {
          door: "生门",
          xun_palace: 1,
          destination_palace: 1,
          hour_offset_in_xun: 0,
        },
        instruments_wonders: {
          six_instruments: ["戊"],
          three_wonders: ["乙"],
          earth_plate: [],
          heaven_plate: [],
          hidden_jia: { xun: "甲子", instrument: "戊" },
        },
        xunkong: { xun: "甲子", branches: ["戌", "亥"], palaces: [6, 7] },
        horse: { hour_branch: "子", branch: "寅", palace: 8 },
        named_patterns: [
          {
            id: "QM-P13",
            name: "五不遇时",
            status: "predicate_matched_not_verdict",
            palace: null,
            identity_adjudication: {
              status: "adjudicated_pattern_identity",
              decision_scope: "qimen_named_pattern_identity",
              pattern_id: "QM-P13",
              pattern_name: "五不遇时",
              palace: null,
              hard_verdict: null,
              event_verdict: null,
              source_ref: {
                pack: "san-shi/qimen-dunjia-tongzhi",
                rule_id: "QM-P13",
                source_anchor: "references/books/san-shi/qimen-dunjia-tongzhi/rules.md#QM-P13",
                verification_status: "verified",
                binding_digest: "addc36958a2efaf63b6ceac219a8afe49ea4b26e5bcb5d32e404c35d59d70302",
              },
              unresolved_checks: [
                "格局强弱、制化与并见关系",
                "事项用神及宫位关系",
                "事件成败、吉凶与应期",
              ],
            },
          },
        ],
      }}
    />,
  );

  expect(screen.getByText("天辅、天禽")).toBeVisible();
  expect(screen.getByText("格局身份已裁定（未断吉凶）")).toBeVisible();
  expect(screen.getByText("全局")).toBeVisible();
  expect(screen.getByText("QM-P13 · san-shi/qimen-dunjia-tongzhi")).toBeVisible();
  expect(screen.queryByText("第null宫")).toBeNull();
});

it("renders relationship ViewModels as traceable cross-chart facts", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "bazi-relationship/v1",
        subjects: [
          { subject_ref: "profile-version:a", profile_version_id: "a", label: "甲方" },
          { subject_ref: "profile-version:b", profile_version_id: "b", label: "乙方" },
        ],
        relationship_type: "romantic",
        signals: [
          {
            dimension_id: "relationship",
            subject_refs: ["profile-version:a", "profile-version:b"],
            signal_id: "bazi.cross_branch.liu_chong.year.year",
            display_text: "甲方年支「子」与乙方年支「午」构成六冲（跨盘结构事实）。",
            fact_refs: [
              "fact:a/calculated/bazi/four_pillars",
              "fact:b/calculated/bazi/four_pillars",
            ],
          },
        ],
      }}
    />,
  );

  expect(screen.getAllByText("甲方")).toHaveLength(2);
  expect(screen.getByText("情侣")).toBeVisible();
  expect(screen.queryByText("romantic")).toBeNull();
  expect(screen.getByText(/构成六冲/)).toBeVisible();
  expect(screen.getByText("双方命盘计算事实")).toBeVisible();
  expect(screen.queryByText(/fact:a\/calculated\/bazi\/four_pillars/)).toBeNull();
  expect(screen.getByText(/没有把结构事实转换成匹配分数/)).toBeVisible();
});

it("renders Runtime Ziwei core facts without adding browser-side judgments", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "ziwei-chart/v1",
        subject_ref: "profile-version:fixture",
        life_palace_id: "0",
        body_palace_id: "1",
        palaces: Array.from({ length: 12 }, (_, index) => ({
          palace_id: String(index),
          label: index === 0 ? "命宫" : `宫${index}`,
          heavenly_stem: "甲",
          earthly_branch: "子",
          major_stars: index === 0 ? ["紫微"] : [],
          minor_stars: [],
          adjective_stars: [],
        })),
        time_layers: [],
        core_facts: {
          five_elements_class: "水二局",
          source_conditioned_patterns: [{
            rule_id: "ziwei/taiwei-fu#TR-01",
            local_rule_id: "TR-01",
            title: "至玄至微",
            source_pack: "ziwei/taiwei-fu",
            source_anchor: "rules.md#L9-L16",
            status: "predicate_matched_not_verdict",
            fact_paths: ["fact:/chart_facts/output/palaces/0/name"],
            predicate_audit: ["/output/palaces:descendant_eq:命宫"],
          }],
          ming_shen: { body_star: "天相", ming_branch: "子", shen_branch: "寅", soul_star: "贪狼" },
          major_limit_direction: { direction: "reverse", gender: "male", year_polarity: "yang", year_stem: "甲" },
          major_limit_starting_age: 2,
          major_limit_sequence: [],
          major_limits: [],
          transformations: [{ star: "廉贞", transformation: "禄", palace: "福德", palace_branch: "卯", scope: "natal" }],
          star_facts: [],
        },
      }}
    />,
  );

  expect(screen.getByText("水二局")).toBeVisible();
  expect(screen.getByText("紫微")).toBeVisible();
  expect(screen.getByRole("region", { name: "四化" })).toHaveTextContent("廉贞");
  expect(screen.queryByText("本命四化事实")).not.toBeInTheDocument();
  expect(screen.queryByText("TR-01 · 至玄至微")).not.toBeInTheDocument();
  expect(screen.queryByText(/不在浏览器追加判断/)).not.toBeInTheDocument();
  expect(screen.queryByText(/吉凶|大吉|大凶/)).not.toBeInTheDocument();
});

it("renders ZiweiPalaceBoard for ziwei-chart/v1 and fail-closes missing core_facts modules", () => {
  const branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"] as const;
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "ziwei-chart/v1",
        subject_ref: "profile-version:fixture",
        life_palace_id: "0",
        body_palace_id: "1",
        palaces: branches.map((branch, index) => ({
          palace_id: String(index),
          label: index === 0 ? "命宫" : `宫${index}`,
          heavenly_stem: "甲",
          earthly_branch: branch,
          major_stars: index === 0 ? ["紫微"] : [],
          minor_stars: [],
          adjective_stars: [],
        })),
        time_layers: [],
        core_facts: null,
      }}
    />,
  );

  expect(screen.getByRole("grid", { name: "十二宫环盘" })).toBeVisible();
  expect(screen.getAllByText("紫微").length).toBeGreaterThan(0);
  expect(screen.getAllByText("命宫").length).toBeGreaterThan(0);
  expect(screen.queryByRole("region", { name: "口径" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "四化" })).not.toBeInTheDocument();
  expect(screen.queryByText("测试期未开放")).toBeVisible();
  expect(screen.queryByText(/¥/)).not.toBeInTheDocument();
});

it("renders Runtime Qizheng core facts and keeps absent aspects absent", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "qizheng-chart/v1",
        subject_ref: "profile-version:fixture",
        planets: [{ planet_id: "太阳", sign_id: "金牛", house_id: "1", longitude: 39.3 }],
        houses: Array.from({ length: 12 }, (_, index) => ({
          house_id: String(index + 1),
          sign_id: "白羊",
          cusp_longitude: index * 30,
        })),
        aspects: [],
        time_layers: [],
        core_facts: {
          source_conditioned_patterns: [{
            rule_id: "xingming/guotian-jing#GR-01-01",
            local_rule_id: "GR-01-01",
            title: "起八字法",
            source_pack: "xingming/guotian-jing",
            source_anchor: "normalized#L31",
            status: "predicate_matched_not_verdict",
            fact_paths: ["fact:/chart_facts/calendar_normalization/ganzhi/year"],
            predicate_audit: ["/calendar_normalization/ganzhi/year:nonempty:()"],
          }],
          classical_bodies: [{
            body_id: "Sun",
            classical_name: "太阳",
            longitude: 39.3,
            latitude_degrees: 0.1,
            degree_in_zodiac_sign: 9.3,
            house_id: "1",
            house_degree: 2.5,
            motion_state: "direct",
            fact_status: "calculated_not_interpreted",
            point_kind: "observed_ephemeris_body",
            observed_body: true,
            source_dependency_id: "xingming.ephemeris.seven-luminaries",
            trace: { engine: "astronomy-engine" },
          }, {
            body_id: "紫炁",
            classical_name: "紫炁",
            longitude: 284.58,
            latitude_degrees: 0,
            degree_in_zodiac_sign: 14.58,
            house_id: "1",
            house_degree: 4.58,
            motion_state: "direct",
            fact_status: "calculated_not_interpreted",
            point_kind: "classical_mean_pseudo_point",
            observed_body: false,
            source_dependency_id: "xingming.four-residuals.numeric-profiles",
            trace: {
              profile: "xingxue-dated-mean-ziqi-v1",
              calibration_path: "references/matrices/xingming-ziqi-calibration-v1.yaml",
            },
          }],
          ming_shen: {
            ming_degree: 46.6,
            shen_degree: 226.6,
            separation_degrees: 180,
            local_apparent_sidereal_degrees: 112,
            profile: "synthetic",
            fact_status: "calculated_not_interpreted",
          },
          major_limits: [{ sequence: 1, house: "命宫", age_start_years: 0, age_end_years: 15, start_degree: 46.6, end_degree: 76.6, status: "calculated_limit_span_not_verdict" }],
          transformations: [{ sequence: 1, transformation: "天禄", label: "天禄", classical_body: "火星", body: "Mars", year_stem: "甲", status: "calculated_assignment_not_verdict" }],
        },
      }}
    />,
  );

  expect(screen.getByText("命度 / 身度")).toBeVisible();
  expect(screen.getByText("星体计算事实")).toBeVisible();
  expect(screen.getByText("xingming.ephemeris.seven-luminaries")).toBeVisible();
  expect(screen.getByText("四余算法来源事实")).toBeVisible();
  expect(screen.getByText("xingxue-dated-mean-ziqi-v1")).toBeVisible();
  expect(screen.getByText("十干变换事实")).toBeVisible();
  expect(screen.getByText("GR-01-01 · 起八字法")).toBeVisible();
  expect(screen.getByText(/未返回相位时，页面不自行补算/)).toBeVisible();
});

it("renders time-check event evidence without turning an unmatched row into a verdict", () => {
  const branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"];
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "time-check-view/v1",
        subject_ref: "profile-version:fixture",
        candidate_count: 12,
        candidates: branches.map((hour_branch, index) => ({
          candidate_id: `hour-${hour_branch}`,
          hour_branch,
          local_civil_datetime: `2000-10-18T${String(index * 2).padStart(2, "0")}:00:00+08:00`,
          within_known_time_range: index === 2,
          bazi_chart_digest: null,
          four_pillars: { hour: `甲${hour_branch}` },
          day_master: { stem: "甲" },
          calendar_normalization: { normalized_datetime: "2000-10-18T00:00:00+08:00" },
        })),
        known_time_range: { start: "04:00", end: "05:59" },
        time_basis_policy: "local_apparent_solar-v1",
        known_event_count: 3,
        event_input_status: "structured_valid",
        candidate_rankings: branches.map((hour_branch, index) => ({
          candidate_id: `hour-${hour_branch}`,
          hour_branch,
          eligible: index === 2,
          evidence_score: index === 2 ? 3 : 0,
          matched_event_ids: index === 2 ? ["开工"] : [],
          elimination_reasons: index === 2 ? [] : ["outside_known_time_range"],
          event_evidence: index === 2
            ? [
                {
                  event_id: "开工",
                  matched: true,
                  evidence_score: 3,
                  relations: [{
                    natal_position: "day",
                    natal_branch: "午",
                    event_branch: "未",
                    relation_type: "六合",
                  }],
                  event_year_ten_god: "正官",
                  reasons: ["positive_branch_relation", "domain_ten_god_role"],
                },
                {
                  event_id: "搬家",
                  matched: false,
                  evidence_score: 0,
                  relations: [],
                  event_year_ten_god: null,
                  reasons: [],
                },
              ]
            : [],
          rank: index + 1,
        })),
        event_matches: [],
        ranking_status: "candidate_evidence_ranked",
        event_matching_status: "structured_evidence",
        limitations: ["这里只展示候选证据，不形成古法定盘结论。"],
      }}
    />,
  );

  expect(screen.getByText("结构化事件证据明细")).toBeVisible();
  expect(screen.getByText("存在合、会或三合支关系；事件领域对应十神角色")).toBeVisible();
  expect(screen.getByText("无支持或反对信号")).toBeVisible();
  expect(screen.getByText("命中候选证据")).toBeVisible();
  expect(screen.getByText("未命中候选证据")).toBeVisible();
  expect(screen.getByText(/不形成古法定盘结论/)).toBeVisible();
});

it("renders internal Runtime provider ViewModels as bounded fact tables", () => {
  const { rerender } = render(
    <RuntimeChart
      viewModel={{
        schema_version: "luming-nayin-chart/v1",
        subject_ref: "profile-version:fixture",
        pillars: [
          { position: "year", stem: "甲", branch: "戌", nayin: "山头火" },
          { position: "month", stem: "戊", branch: "辰", nayin: "大林木" },
          { position: "day", stem: "丙", branch: "戌", nayin: "屋上土" },
          { position: "hour", stem: "辛", branch: "卯", nayin: "松柏木" },
        ],
        three_yuan_profiles: { year: { name: "上元" } },
        taiyuan: { ganzhi: "己巳" },
        relations: [{
          category: "lu",
          relation: "干禄",
          anchor: "year",
          anchor_pillar: "甲戌",
          status: "calculated_relation_not_verdict",
          target_branch: "寅",
          candidates: [],
          matched_positions: [],
          recension: null,
        }],
        source_conditioned_patterns: [{
          rule_id: "luming-nayin/li-xuzhong-mingshu#LX-01-17",
          local_rule_id: "LX-01-17",
          title: "庚辰（禄暗会）",
          source_pack: "luming-nayin/li-xuzhong-mingshu",
          source_anchor: "fulltext.md#L32",
          status: "predicate_matched_not_verdict",
          fact_paths: ["fact:/chart_facts/output/four_pillars/year"],
          predicate_audit: ["/four_pillars/year:eq:庚辰"],
          applicability_adjudication: {
            status: "adjudicated_rule_applicability",
            decision_scope: "luming_nayin_source_rule_applicability",
            rule_id: "luming-nayin/li-xuzhong-mingshu#LX-01-17",
            local_rule_id: "LX-01-17",
            rule_title: "庚辰（禄暗会）",
            evidence_role: "issue_specific_judgment_rule",
            hard_verdict: null,
            life_verdict: null,
            source_ref: {
              pack: "luming-nayin/li-xuzhong-mingshu",
              rule_id: "LX-01-17",
              source_anchor: "references/books/luming-nayin/li-xuzhong-mingshu/rules.md#LX-01-17",
              verification_status: "verified",
              binding_digest: "1".repeat(64),
            },
            unresolved_checks: ["多条规则并见尚未权衡"],
          },
        }],
      }}
    />,
  );

  expect(screen.getByText("禄命纳音四柱")).toBeVisible();
  expect(screen.getByText("山头火")).toBeVisible();
  expect(screen.getByText("已计算关系")).toBeVisible();
  expect(screen.getByText("古籍规则适用性裁定")).toBeVisible();
  expect(screen.getByText("LX-01-17 · 庚辰（禄暗会）")).toBeVisible();
  expect(screen.getByText("规则适用性已裁定（未形成命断）")).toBeVisible();
  expect(screen.queryByText("calculated_relation_not_verdict")).toBeNull();
  expect(screen.getByText(/不追加吉凶/)).toBeVisible();

  rerender(
    <RuntimeChart
      viewModel={{
        schema_version: "taiyi-chart/v1",
        subject_ref: "profile-version:fixture",
        calendar: {
          annual_boundary: "lunar_new_year_from_shared_calendar",
          lunar_year: 2026,
          year_ganzhi: "丙午",
        },
        epoch: {
          accumulated_year: 1938583,
          anchor_accumulated_year: 1937281,
          anchor_lunar_year_ce: 724,
          derived_ce_offset: 1936557,
          one_based: true,
          profile_id: "synthetic",
          source_anchor: "L67-L69",
        },
        cycle: {
          bureau: 55,
          governance: "理天",
          ji: 6,
          position_360: 343,
          year_in_ji: 43,
          year_in_zi_yuan: 55,
          zi_yuan: 5,
          zi_yuan_head: "壬子",
        },
        board: {
          heshen: "未",
          jishen: "申",
          shiji: "艮",
          taisui: "午",
          taiyi_position: "艮",
          tianmu_wenchang: { name: "武德", position: "申" },
        },
        host_guest: { host: { count: 16 }, guest: { count: 3 } },
        four_generals: { guest_assistant: 9, guest_major: 3, host_assistant: 8, host_major: 6 },
        long_cycle_deities: [{
          deity_id: "junji",
          accumulated_year: 286313,
          cycle_position: 113,
          epoch_profile: "synthetic",
          name: "君基",
          position: "丑",
          source_anchor: "L602-L604",
          status: "calculated_position_not_verdict",
        }],
        board_predicates: [{
          predicate_id: "TY-P01",
          name: "掩",
          predicate: "shiji_same_as_taiyi",
          fact_paths: ["/shiji", "/taiyi"],
          source_anchor: "fulltext.md L430",
          source_dependency_id: "taiyi.synthetic",
          status: "predicate_matched_not_verdict",
          identity_adjudication: {
            status: "adjudicated_pattern_identity",
            decision_scope: "taiyi_board_pattern_identity",
            pattern_id: "TY-P01",
            pattern_name: "掩",
            hard_verdict: null,
            event_verdict: null,
            source_ref: {
              pack: "san-shi/taiyi-shenshu",
              rule_id: "TY-P01",
              source_anchor: "references/books/san-shi/taiyi-shenshu/rules.md#TY-P01",
              verification_status: "verified",
              binding_digest: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            },
            unresolved_checks: [
              "并见格局、制化与主客关系",
              "宏观事项范围及盘面取用",
              "现实成败、吉凶与应期",
            ],
          },
        }],
        scope_contract: {
          declared_scope: "annual_macro_historical_board_facts",
          interpretation_policy: "calculated_facts_and_predicates_only_no_event_verdicts",
          supported_horizons: ["year"],
          supported_objects: ["macro_historical"],
          unsupported_scopes: ["personal_event"],
        },
      }}
    />,
  );

  expect(screen.getByText("太乙盘面事实")).toBeVisible();
  expect(screen.getByText("共享历法农历新年")).toBeVisible();
  expect(screen.getByText("个人事件范围")).toBeVisible();
  expect(screen.getByText("已计算位置")).toBeVisible();
  expect(screen.getByText("结构命题已匹配")).toBeVisible();
  expect(screen.getByText("格局身份已裁定（未断吉凶）")).toBeVisible();
  expect(screen.getByText("TY-P01 · san-shi/taiyi-shenshu")).toBeVisible();
  expect(screen.queryByText("calculated_position_not_verdict")).toBeNull();
  expect(screen.queryByText("predicate_matched_not_verdict")).toBeNull();

  rerender(
    <RuntimeChart
      viewModel={{
        schema_version: "selection-chart/v1",
        subject_ref: "event:fixture",
        event_profile: "business_opening_transaction",
        eligible_candidates: [{
          candidate_id: "2026-09-03",
          civil_date: "2026-09-03",
          best_candidate_time_id: "2026-09-03:寅:synthetic",
          eligibility: { eligible: true },
          rejection_reasons: [],
          ranking_components: { official_huang_day_first: true },
        }],
        eligible_date_time_candidates: ["2026-09-03:寅:synthetic"],
        eliminations: [],
        ranking: {
          component_order: ["hard_eligible_first"],
          eligible_candidate_ids: ["2026-09-03"],
          eligible_date_time_candidate_ids: ["2026-09-03:寅:synthetic"],
          folk_affects_rank: false,
          method: "explainable_lexicographic_v1",
          opaque_numeric_score: false,
          ordered_candidate_ids: ["2026-09-03"],
          ordered_date_time_candidate_ids: ["2026-09-03:寅:synthetic"],
        },
        lineage_policy: {
          folk: "folk",
          folk_priority: "comparison_only",
          merge_verdicts: false,
          official: "official",
          official_priority: "primary",
          preserve_disagreement: true,
        },
        no_valid_candidate: false,
        basis_projection: { candidate_limit_per_list: 12 },
        source_conditioned_patterns: [{
          rule_id: "selection/xingli-kaoyuan#KR-05",
          local_rule_id: "KR-05",
          title: "五虎遁与五鼠遁",
          source_pack: "selection/xingli-kaoyuan",
          source_anchor: "rules.md#L42-L49",
          status: "predicate_matched_not_verdict",
          fact_paths: ["fact:selection:fixture/calendar/ganzhi/year"],
          predicate_audit: ["/calendar/ganzhi/year:nonempty"],
        }],
      }}
    />,
  );

  expect(screen.getByText("营业或交易开启")).toBeVisible();
  expect(screen.getByText("2026-09-03")).toBeVisible();
  expect(screen.getByText(/不把排序结果包装/)).toBeVisible();
  expect(screen.getByText("KR-05 · 五虎遁与五鼠遁")).toBeVisible();

  rerender(
    <RuntimeChart
      viewModel={{
        schema_version: "fengshui-view/v1",
        subject_ref: "property:fixture",
        active_subprofiles: ["form", "liqi"],
        observation_provenance: { provider_performed_vision: false },
        compass: { status: "resolved", facing: { mountain: "午", trigram: "离", degrees: 180 } },
        building_chronology: { period_use: "not_required_for_bazhai" },
        layout_graph: { nodes: [], edges: [] },
        form: { status: "not_requested" },
        liqi: { status: "calculated_selected_school_facts_not_verdict" },
        active_source_rule_ids: ["internal-rule"],
        conflicts: [],
        uncertainties: [],
        critical_missing: [],
      }}
    />,
  );

  expect(screen.getByText("形势、理气")).toBeVisible();
  expect(screen.getByText("午 · 离")).toBeVisible();
  expect(screen.getByText("八宅模式不要求建筑年代")).toBeVisible();
  expect(screen.getByText("已解析")).toBeVisible();
  expect(screen.getByText("未请求")).toBeVisible();
  expect(screen.getByText("已计算选定流派资料")).toBeVisible();
  expect(screen.queryByText(/provider_performed_vision/)).toBeNull();
  expect(screen.queryByText("resolved")).toBeNull();
  expect(screen.queryByText("not_requested")).toBeNull();
  expect(screen.queryByText("calculated_selected_school_facts_not_verdict")).toBeNull();
  expect(screen.getByText(/没有图像识别或居住吉凶判断/)).toBeVisible();
});

it("renders Meihua source-adjudicated relation polarity without inventing an event verdict", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "meihua-chart/v1",
        subject_ref: "meihua:fixture",
        question: "这件事后续如何",
        casting_method: "time",
        primary_hexagram: { name: "风雷益", upper_trigram: "巽", lower_trigram: "震" },
        mutual_hexagram: { name: "山地剥", upper_trigram: "艮", lower_trigram: "坤" },
        changed_hexagram: { name: "风泽中孚", upper_trigram: "巽", lower_trigram: "兑" },
        moving_lines: [2],
        body_use: {
          body: { position: "upper", trigram: "巽", element: "木" },
          use: { position: "lower", trigram: "震", element: "木" },
          relation: "比和",
          status: "calculated_relation_not_verdict",
        },
        core_facts: {
          body_relation_facts: [],
          seasonal_strength: null,
          interpretation_status: "source_adjudicated_relations",
          interpretive_candidates: {
            schema_version: "mingli-meihua-interpretive-candidates-v1",
            status: "source_adjudicated_relations",
            hard_verdict: null,
            verification_status: "verified",
            relation_candidates: [{
              candidate_id: "meihua.primary_use.upper.same_element",
              source_plate: "primary_use",
              position: "upper",
              relation: "比和",
              relation_key: "same_element",
              actor: { position: "upper", trigram: "巽", element: "木" },
              body: { position: "upper", trigram: "巽", element: "木" },
              seasonal_state: "旺",
              rule_id: "MR-04-02",
              status: "relation_adjudicated_not_event_verdict",
              hard_verdict: null,
              verification_status: "verified",
              source_pack: "divination/meihua-yishu",
              source_anchor: "references/books/divination/meihua-yishu/rules.md#MR-04-02",
              source_dependency_id: "meihua.classical-adjudication.body-use-candidates",
              relation_adjudication: {
                status: "adjudicated_relation_polarity",
                decision_scope: "meihua_body_use_relation",
                relation_key: "same_element",
                source_polarity: "harmonious",
                hard_verdict: null,
                event_verdict: null,
                source_refs: [{
                  pack: "divination/meihua-yishu",
                  rule_id: "MR-04-02",
                  source_anchor: "references/fulltext/divination/meihua-yishu/fulltext.md#L875",
                  verification_status: "verified",
                  binding_digest: "202662eb4c023883aab61febf3de3d7d42137740f31d50ba1a7ada25149db50f",
                }],
                unresolved_checks: [
                  "具体问题中的体用取义、领域例外与外应",
                  "本卦、互卦、变卦关系的并见权重及月令旺衰",
                  "现实事件成败、吉凶程度与应期",
                ],
              },
            }],
            requires_classical_adjudication: false,
            requires_synthesis_adjudication: true,
            boundary: "关系极性已裁定，综合事件结论仍待裁决",
          },
        },
      }}
    />,
  );

  expect(screen.getByRole("heading", { name: "古籍极性" })).toBeVisible();
  expect(screen.getAllByText("比和").length).toBeGreaterThan(0);
  expect(screen.getByText("关系极性已裁定")).toBeVisible();
  expect(
    screen.getByText("以上是古籍已裁定的关系极性。这件事成不成、吉凶、应期，本页不断。"),
  ).toBeVisible();
  expect(screen.queryByText("以上为古籍已裁定的关系极性，事件成败不在本页判断")).toBeNull();
  expect(screen.queryByText("体用关系候选（非最终结论）")).toBeNull();
});

it("renders rhythm facts without importing the broader luming relation surface", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "rhythm-facts-view/v1",
        subject_ref: "profile-version:fixture",
        pillars: [
          { position: "year", stem: "甲", branch: "戌", nayin: "山头火" },
          { position: "month", stem: "戊", branch: "辰", nayin: "大林木" },
          { position: "day", stem: "丙", branch: "戌", nayin: "屋上土" },
          { position: "hour", stem: "辛", branch: "卯", nayin: "松柏木" },
        ],
        independent_lineage: "early-luming-nayin",
        fact_scope: "early_luming_natal_facts",
        interpretation_status: "facts_only",
        source_boundary: "只展示 Runtime 四柱纳音事实，不生成音色、频率、姓名学、性格或吉凶结论。",
      }}
    />,
  );

  expect(screen.getByText("本命音律四柱纳音事实")).toBeVisible();
  expect(screen.getByText("early-luming-nayin")).toBeVisible();
  expect(screen.getByText("松柏木")).toBeVisible();
  expect(screen.getByText(/不生成音色、频率/)).toBeVisible();
  expect(screen.queryByText("禄马贵结构事实")).toBeNull();
});

it("renders five-elements facts with explicit source gaps and no verdict", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "five-elements-facts-view/v1",
        subject_ref: "profile-version:fixture",
        day_master: { stem: "丙", element: "fire", polarity: "阳" },
        month_command: {
          branch: "辰",
          label: "辰月",
          main_qi: "戊",
          main_qi_element: "earth",
        },
        seasonal_profile: {
          season: "季春",
          month_qi: "土承木余气",
          temperature: "温",
          moisture: "湿",
        },
        tiaohou_markers: {
          temperature: "温",
          moisture: "湿",
          markers: ["温", "湿"],
          day_stem: "丙",
          month_branch: "辰",
          scope: "month-level climate anchors only",
        },
        element_inventory: {
          visible_stem_branch_counts: [
            { element: "wood", value: 2 },
            { element: "fire", value: 1 },
          ],
          hidden_stem_occurrence_counts: [{ element: "earth", value: 3 }],
          scope: "inventory only",
        },
        interpretive_candidates: {
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
              { element: "earth", value: 3 },
              { element: "metal", value: 0 },
              { element: "water", value: 0 },
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
            boundary: "只展示五行出现次数，不等于旺衰定论。",
          },
          structure: {
            status: "candidate_only",
            hard_verdict: null,
            month_main_qi: "戊",
            month_main_qi_ten_god: "食神",
            main_qi_visible: false,
            visible_positions: ["month"],
            boundary: "只展示月令主气与透干候选，不完成格局裁定。",
          },
          following_and_transformation: {
            status: "requires_classical_adjudication",
            hard_verdict: null,
            stem_combination_candidates: [],
            branch_formation_candidates: [
              { relation_type: "六合", positions: ["month", "hour"], branches: ["辰", "卯"] },
            ],
            boundary: "合化、从格仍需经典裁决。",
          },
          salience_signals: [
            {
              signal_id: "seasonal-anchor",
              status: "mechanical_candidate",
              hard_verdict: null,
              basis: { month_branch: "辰" },
              boundary: "显著信号不等于吉凶。",
            },
          ],
        },
        source_identity: {
          day_stem: "丙",
          month_branch: "辰",
          source_dependency_id: "bazi.seasonal-tiaohou.day-master-month",
          source_section_id: null,
          source_rule_id: null,
        },
        active_source_rule_ids: [],
        source_dependency_ids: ["bazi.seasonal-tiaohou.day-master-month"],
        source_status: "identity_only",
        source_gaps: ["当前 Runtime 只返回调候适用性身份，未返回逐条来源规则 ID。"],
        limitations: [
          "五行计数只表示盘面库存，不直接决定旺衰、喜忌或用神。",
          "调候标记只表示月令气候事实，不单独形成调候用神结论。",
          "强弱证据、结构候选与合冲信号只展示 Runtime 机械输出，不形成最终格局或吉凶结论。",
        ],
      }}
    />,
  );

  expect(screen.getByText("五行库存事实")).toBeVisible();
  expect(screen.getByText("只有日主×月令适用性身份")).toBeVisible();
  expect(screen.getByText("月令状态裁定与强弱 / 结构边界")).toBeVisible();
  expect(screen.getByText("月令状态裁定")).toBeVisible();
  expect(screen.getByText(/全局身强身弱与唯一用神仍未裁定/)).toBeVisible();
  expect(screen.getByText(/月令状态 休/)).toBeVisible();
  expect(screen.getByText(/同类 1 项；生扶 木 2 项/)).toBeVisible();
  expect(screen.getByText(/1 项机械候选/)).toBeVisible();
  expect(screen.getByText(/未返回逐条来源规则 ID/)).toBeVisible();
  expect(screen.getByText(/不直接决定旺衰/)).toBeVisible();
  expect(screen.queryByText("喜神")).toBeNull();
});

it("renders exact chart comparison facts without turning them into a score", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "chart-similarity-view/v1",
        left_subject_ref: "profile-version:left",
        right_subject_ref: "profile-version:right",
        basis: "bazi.four_pillars.exact",
        left_fact_ref: "fact:left/calculated/bazi/four_pillars",
        right_fact_ref: "fact:right/calculated/bazi/four_pillars",
        comparisons: [
          {
            position: "year",
            left: { position: "year", stem: "甲", branch: "子" },
            right: { position: "year", stem: "甲", branch: "子" },
            exact_match: true,
          },
          {
            position: "month",
            left: { position: "month", stem: "乙", branch: "丑" },
            right: { position: "month", stem: "乙", branch: "丑" },
            exact_match: true,
          },
          {
            position: "day",
            left: { position: "day", stem: "丙", branch: "寅" },
            right: { position: "day", stem: "丙", branch: "寅" },
            exact_match: true,
          },
          {
            position: "hour",
            left: { position: "hour", stem: "丁", branch: "卯" },
            right: { position: "hour", stem: "戊", branch: "辰" },
            exact_match: false,
          },
        ],
        exact_match: false,
        matched_positions: ["year", "month", "day"],
        differing_positions: ["hour"],
        limitations: [
          "只比较 Runtime 已计算的八字四柱原值，不比较出生资料、姓名或解释候选。",
          "本结果不表示缘分、合婚、性格相似度，也不生成百分比评分。",
        ],
      }}
    />,
  );

  expect(screen.getByText("八字四柱逐柱比较")).toBeVisible();
  expect(screen.getByText("年柱")).toBeVisible();
  expect(screen.getByText("丁卯")).toBeVisible();
  expect(screen.getByText("戊辰")).toBeVisible();
  expect(screen.getByText("不同")).toBeVisible();
  expect(screen.getByText(/不生成百分比评分/)).toBeVisible();
  expect(screen.queryByText(/相似度分数/)).toBeNull();
});

it("renders a bounded Daliuren timing candidate as a non-guaranteed date", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "daliuren-chart/v1",
        subject_ref: "liuren:timing-fixture",
        question: "这件事何时可能出现回应？",
        lessons: [
          { lesson_id: "1", upper: "酉", lower: "庚" },
          { lesson_id: "2", upper: "戌", lower: "酉" },
          { lesson_id: "3", upper: "子", lower: "申" },
          { lesson_id: "4", upper: "丑", lower: "子" },
        ],
        transmissions: [
          { stage: "initial", branch: "酉", general: "朱雀" },
          { stage: "middle", branch: "戌", general: "六合" },
          { stage: "final", branch: "亥", general: "勾陈" },
        ],
        core_facts: {
          day_hour: null,
          dimension_facts: null,
          earth_plate: null,
          heaven_plate: null,
          heavenly_generals: null,
          lesson_method: null,
          month_general: null,
          noble_person: null,
          plate_offset: null,
          structural_patterns: null,
          transmission_method: null,
          timing_candidates: [{
            id: "initial_group_upper_candidate",
            role: "event_response_candidate",
            anchor_earth_branch: "巳",
            branch: "酉",
            solar_date: "2026-08-21",
            day_ganzhi: "丁卯",
            days_after_cast: 7,
            source_pack: "san-shi/liuren-miben",
            source_rule: "LM-R21",
            candidate_not_guarantee: true,
          }],
          xunkong: null,
        },
      }}
    />,
  );

  expect(screen.getByRole("region", { name: "课传" })).toBeVisible();
  expect(screen.getByRole("button", { name: "初传 酉 朱雀" })).toBeVisible();
  expect(screen.getByText(/2026-08-21/)).toBeVisible();
  expect(screen.getByText("以下为古籍规则产生的候选日期，不是保证的应期")).toBeVisible();
  expect(screen.queryByText("有界应期候选")).not.toBeInTheDocument();
  expect(screen.queryByText("丁卯 · 酉")).not.toBeInTheDocument();
  expect(screen.queryByText("LM-R21 · san-shi/liuren-miben")).not.toBeInTheDocument();
  expect(screen.queryByText("候选日期，不是现实保证")).not.toBeInTheDocument();
});

it("renders DaliurenBoard for daliuren-chart/v1 and fail-closes missing timing_candidates", () => {
  render(
    <RuntimeChart
      viewModel={{
        schema_version: "daliuren-chart/v1",
        subject_ref: "liuren:timing-fixture",
        question: "这件事何时可能出现回应？",
        lessons: [
          { lesson_id: "1", upper: "酉", lower: "庚" },
          { lesson_id: "2", upper: "戌", lower: "酉" },
          { lesson_id: "3", upper: "子", lower: "申" },
          { lesson_id: "4", upper: "丑", lower: "子" },
        ],
        transmissions: [
          { stage: "initial", branch: "酉", general: "朱雀" },
          { stage: "middle", branch: "戌", general: "六合" },
          { stage: "final", branch: "亥", general: "勾陈" },
        ],
        core_facts: {
          day_hour: null,
          dimension_facts: null,
          earth_plate: null,
          heaven_plate: null,
          heavenly_generals: null,
          lesson_method: null,
          month_general: null,
          noble_person: null,
          plate_offset: null,
          structural_patterns: null,
          transmission_method: null,
          timing_candidates: null,
          xunkong: null,
        },
      }}
    />,
  );

  expect(screen.getByRole("region", { name: "课传" })).toBeVisible();
  expect(screen.getByRole("button", { name: "初传 酉 朱雀" })).toBeVisible();
  expect(screen.queryByText("2026-08-21")).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "应期" })).not.toBeInTheDocument();
  expect(screen.queryByText("有界应期候选")).not.toBeInTheDocument();
});
