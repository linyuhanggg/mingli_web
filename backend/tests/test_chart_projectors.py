from __future__ import annotations

from typing import Any

from app.charts.contracts import (
    CanwenViewV1,
    DaliurenChartV1,
    FengshuiViewV1,
    FiveElementsFactsViewV1,
    HecanViewV1,
    LiuyaoChartV1,
    LumingNayinChartV1,
    MeihuaChartV1,
    PhysiognomyViewV1,
    QimenChartV1,
    QizhengChartV1,
    RhythmFactsViewV1,
    SelectionChartV1,
    TaiyiChartV1,
    WenshiViewV1,
    ZiweiChartV1,
)
from app.charts.projectors import (
    project_canwen_view_model,
    project_daliuren_view_model,
    project_fengshui_view_model,
    project_hecan_view_model,
    project_liuyao_view_model,
    project_luming_nayin_view_model,
    project_meihua_view_model,
    project_physiognomy_view_model,
    project_qimen_view_model,
    project_qizheng_view_model,
    project_rhythm_facts_view_model,
    project_runtime_view_model,
    project_selection_view_model,
    project_taiyi_view_model,
    project_wenshi_view_model,
    project_ziwei_view_model,
)


def brief(capability_id: str, values: dict[str, Any]) -> dict[str, object]:
    facts = [
        {
            "ref": f"fact:calculated/{capability_id}/{field_id}",
            "subject_ref": "fixture:probe",
            "kind_id": "kind.fact",
            "value": value,
            "display_text": field_id,
        }
        for field_id, value in values.items()
    ]
    facts.append(
        {
            "ref": f"fact:input/{capability_id}/palaces",
            "subject_ref": "fixture:probe",
            "kind_id": "kind.fact",
            "value": {"must_not": "be read"},
            "display_text": "input",
        }
    )
    return {
        "question": "fixture question",
        "facts": facts,
        "request_view": {
            "subject_refs": ["fixture:probe"],
            "capability_ids": [capability_id],
        },
    }


def test_ziwei_projector_preserves_twelve_palaces_and_life_body_refs() -> None:
    palaces = [
        {
            "index": index,
            "name": "命宫" if index == 0 else f"宫{index}",
            "heavenlyStem": "甲",
            "earthlyBranch": "子",
            "majorStars": [{"name": "紫微"}] if index == 0 else [],
            "isBodyPalace": index == 1,
        }
        for index in range(12)
    ]

    view_model = project_ziwei_view_model(brief("ziwei", {"palaces": palaces}))

    assert isinstance(view_model, ZiweiChartV1)
    assert view_model.life_palace_id == "0"
    assert view_model.body_palace_id == "1"
    assert view_model.palaces[0].major_stars == ("紫微",)


def test_ziwei_projector_exposes_calculated_core_facts_without_input_material() -> None:
    palaces = [
        {
            "index": index,
            "name": "命宫" if index == 0 else f"宫{index}",
            "heavenlyStem": "甲",
            "earthlyBranch": "子",
            "majorStars": [{"name": "紫微"}] if index == 0 else [],
            "isBodyPalace": index == 1,
        }
        for index in range(12)
    ]
    view_model = project_ziwei_view_model(
        brief(
            "ziwei",
            {
                "palaces": palaces,
                "five_elements_class": "水二局",
                "ming_shen": {
                    "body_star": "天相",
                    "ming_branch": "子",
                    "shen_branch": "寅",
                    "soul_star": "贪狼",
                },
                "major_limit_direction": {
                    "direction": "reverse",
                    "gender": "male",
                    "year_polarity": "yang",
                    "year_stem": "甲",
                },
                "major_limit_starting_age": 2,
                "major_limit_sequence": [
                    {
                        "palace": "命宫",
                        "palace_index": 0,
                        "palace_branch": "子",
                        "range": [2, 11],
                        "sequence": 1,
                        "heavenlyStem": "甲",
                        "earthlyBranch": "子",
                        "direction": "reverse",
                    }
                ],
                "major_limits": [],
                "natal_transformation_facts": [
                    {
                        "star": "廉贞",
                        "transformation": "禄",
                        "palace": "福德",
                        "palace_branch": "卯",
                        "scope": "natal",
                    }
                ],
                "star_facts": [
                    {
                        "name": "紫微",
                        "type": "major",
                        "scope": "natal",
                        "brightness": "庙",
                        "palace": "命宫",
                        "palace_branch": "子",
                        "palace_index": 0,
                    }
                ],
            },
        )
    )

    assert isinstance(view_model, ZiweiChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.five_elements_class == "水二局"
    assert view_model.core_facts.major_limit_sequence is not None
    assert view_model.core_facts.major_limit_sequence[0].age_start == 2
    assert view_model.core_facts.transformations is not None
    assert view_model.core_facts.transformations[0].transformation == "禄"
    assert view_model.core_facts.star_facts is not None
    assert view_model.core_facts.star_facts[0].brightness == "庙"


def test_qizheng_projector_derives_only_display_coordinates_from_runtime_longitudes() -> None:
    positions = [
        {
            "body": "Sun",
            "classical_name": "太阳",
            "longitude": 39.3,
            "house_sequence": 12,
        },
        {
            "body": "Moon",
            "classical_name": "太阴",
            "longitude": 275.7,
            "house_sequence": 8,
        },
    ]
    houses = [
        {"sequence": index, "start_degree": (index - 1) * 30}
        for index in range(1, 13)
    ]

    view_model = project_qizheng_view_model(
        brief("xingming", {"positions": positions, "houses": houses})
    )

    assert isinstance(view_model, QizhengChartV1)
    assert [item.sign_id for item in view_model.planets] == ["金牛", "摩羯"]
    assert len(view_model.houses) == 12
    assert view_model.aspects == ()


def test_qizheng_projector_exposes_ephemeris_ming_shen_limits_and_transformations() -> None:
    positions = [
        {
            "body": "Sun",
            "classical_name": "太阳",
            "longitude_degrees": 39.3,
            "latitude_degrees": 0.1,
            "degree_in_zodiac_sign": 9.3,
            "house": "命宫",
            "house_sequence": 1,
            "degree_in_house": 2.5,
            "motion_state": "direct",
            "fact_status": "calculated_not_interpreted",
        }
    ]
    houses = [
        {"sequence": index, "start_degree": (index - 1) * 30}
        for index in range(1, 13)
    ]
    view_model = project_qizheng_view_model(
        brief(
            "xingming",
            {
                "positions": positions,
                "classical_bodies": positions,
                "houses": houses,
                "ming_shen": {
                    "ming_degree": 46.6,
                    "shen_degree": 226.6,
                    "longitude_degrees": 120.2,
                    "latitude_degrees": 25.0,
                    "separation_degrees": 180.0,
                    "local_apparent_sidereal_degrees": 112.0,
                    "profile": "topocentric-equal-house-mingshen-opposition-v1",
                    "fact_status": "calculated_not_interpreted",
                },
                "major_limits": [
                    {
                        "sequence": 1,
                        "house": "命宫",
                        "age_start_years": 0.0,
                        "age_end_years": 15.0,
                        "start_degree": 46.6,
                        "end_degree": 76.6,
                        "status": "calculated_limit_span_not_verdict",
                    }
                ],
                "transformations": [
                    {
                        "sequence": 1,
                        "transformation": "天禄",
                        "label": "天禄",
                        "classical_body": "火星",
                        "body": "火星",
                        "year_stem": "甲",
                        "status": "calculated_assignment_not_verdict",
                    }
                ],
            },
        )
    )

    assert isinstance(view_model, QizhengChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.classical_bodies is not None
    assert view_model.core_facts.classical_bodies[0].house_id == "1"
    assert view_model.core_facts.ming_shen is not None
    assert view_model.core_facts.ming_shen.separation_degrees == 180.0
    assert view_model.core_facts.major_limits is not None
    assert view_model.core_facts.major_limits[0].age_end_years == 15.0
    assert view_model.core_facts.transformations is not None
    assert view_model.core_facts.transformations[0].classical_body == "火星"


def test_liuyao_projector_maps_runtime_line_states_to_contract_values() -> None:
    lines = [
        {"line": 1, "state": "老阳", "moving": True},
        {"line": 2, "state": "少阳", "moving": False},
        {"line": 3, "state": "少阴", "moving": False},
        {"line": 4, "state": "老阴", "moving": True},
        {"line": 5, "state": "少阳", "moving": False},
        {"line": 6, "state": "少阴", "moving": False},
    ]
    values = {
        "primary_hexagram": {
            "name": "泽天夬",
            "upper_trigram": "兑",
            "lower_trigram": "乾",
        },
        "changed_hexagram": {
            "name": "天风姤",
            "upper_trigram": "乾",
            "lower_trigram": "巽",
        },
        "lines": lines,
        "line_facts": [{"line": 1, "six_relative": "妻财", "moving": True}],
        "najia": [{"branch": "子", "element": "水", "ganzhi": "甲子"}],
        "returning_relations": [{"source_line": 1, "relations": ["回头生"]}],
        "six_relatives": ["妻财"],
        "xunkong": {"day_ganzhi": "甲子", "void_branches": ["戌", "亥"]},
    }

    view_model = project_liuyao_view_model(brief("liuyao", values))

    assert isinstance(view_model, LiuyaoChartV1)
    assert [line.value for line in view_model.lines] == [9, 7, 8, 6, 7, 8]
    assert [line.moving for line in view_model.lines] == [True, False, False, True, False, False]
    assert view_model.core_facts is not None
    assert view_model.core_facts.six_relatives == ("妻财",)
    assert view_model.core_facts.line_facts == (
        {"line": 1, "six_relative": "妻财", "moving": True},
    )
    assert view_model.core_facts.returning_relations == (
        {"source_line": 1, "relations": ["回头生"]},
    )
    assert view_model.core_facts.xunkong == {
        "day_ganzhi": "甲子",
        "void_branches": ["戌", "亥"],
    }


def test_meihua_projector_maps_structural_plate_facts_without_verdicts() -> None:
    values = {
        "casting_method": "time",
        "primary_hexagram": {
            "name": "风雷益",
            "upper_trigram": "巽",
            "lower_trigram": "震",
        },
        "mutual_hexagram": {
            "name": "山地剥",
            "upper_trigram": "艮",
            "lower_trigram": "坤",
        },
        "changed_hexagram": {
            "name": "风泽中孚",
            "upper_trigram": "巽",
            "lower_trigram": "兑",
        },
        "moving_lines": [2],
        "body_use": {
            "body": {"position": "upper", "trigram": "巽", "element": "木"},
            "use": {"position": "lower", "trigram": "震", "element": "木"},
            "relation": "比和",
            "status": "calculated_relation_not_verdict",
        },
        "body_relation_facts": [
            {
                "body": {"position": "upper", "trigram": "巽", "element": "木"},
                "element": "木",
                "position": "primary_upper",
                "relation": "比和",
                "source_dependency_id": "meihua.fixture",
                "source_plate": "primary",
                "status": "calculated_relation_not_verdict",
                "trigram": "巽",
            }
        ],
        "seasonal_strength": {
            "body": {
                "month_branch": "辰",
                "season": "spring",
                "source_dependency_id": "meihua.fixture",
                "state": "旺",
                "status": "calculated_relation_not_verdict",
                "trigram": "巽",
            }
        },
    }

    view_model = project_meihua_view_model(brief("meihua", values))

    assert isinstance(view_model, MeihuaChartV1)
    assert view_model.primary_hexagram.name == "风雷益"
    assert view_model.mutual_hexagram is not None
    assert view_model.moving_lines == (2,)
    assert view_model.body_use.status == "calculated_relation_not_verdict"
    assert view_model.core_facts is not None
    assert view_model.core_facts.body_relation_facts is not None
    assert view_model.core_facts.body_relation_facts[0].source_plate == "primary"
    assert view_model.core_facts.seasonal_strength is not None
    assert view_model.core_facts.seasonal_strength["body"].state == "旺"


def test_luming_projector_maps_nayin_and_source_named_relations() -> None:
    view_model = project_luming_nayin_view_model(
        brief(
            "luming-nayin",
            {
                "pillars": {
                    "year": {"stem": "甲", "branch": "戌", "nayin": {"name": "山头火"}},
                    "month": {"stem": "戊", "branch": "辰", "nayin": {"name": "大林木"}},
                    "day": {"stem": "丙", "branch": "戌", "nayin": {"name": "屋上土"}},
                    "hour": {"stem": "辛", "branch": "卯", "nayin": {"name": "松柏木"}},
                },
                "three_yuan_profiles": {"year": {"name": "上元"}},
                "taiyuan": {"ganzhi": "己巳"},
                "relations": {
                    "lu": [
                        {
                            "anchor": "year",
                            "anchor_pillar": "甲戌",
                            "relation": "干禄",
                            "status": "calculated_relation_not_verdict",
                            "target_branch": "寅",
                            "matched_positions": [],
                        }
                    ],
                    "ma": [],
                    "gui": [],
                },
            },
        )
    )

    assert isinstance(view_model, LumingNayinChartV1)
    assert view_model.pillars[0].nayin == "山头火"
    assert view_model.relations[0].category == "lu"
    assert view_model.taiyuan == {"ganzhi": "己巳"}


def test_rhythm_projector_keeps_only_nayin_facts_and_uses_product_dispatch() -> None:
    values = {
        "pillars": {
            "year": {"stem": "甲", "branch": "戌", "nayin": {"name": "山头火"}},
            "month": {"stem": "戊", "branch": "辰", "nayin": {"name": "大林木"}},
            "day": {"stem": "丙", "branch": "戌", "nayin": {"name": "屋上土"}},
            "hour": {"stem": "辛", "branch": "卯", "nayin": {"name": "松柏木"}},
        },
        "independent_lineage": "early-luming-nayin",
        "fact_scope": "early_luming_natal_facts",
        "interpretation_status": "facts_only",
        "relations": {"lu": [], "ma": [], "gui": []},
    }

    view_model = project_rhythm_facts_view_model(brief("luming-nayin", values))
    dispatched = project_runtime_view_model(brief("luming-nayin", values), product_id="rhythm")

    assert isinstance(view_model, RhythmFactsViewV1)
    assert isinstance(dispatched, RhythmFactsViewV1)
    assert view_model.pillars[0].nayin == "山头火"
    assert view_model.independent_lineage == "early-luming-nayin"
    assert not hasattr(view_model, "relations")

    invalid = dict(values)
    invalid["interpretation_status"] = "interpreted"
    assert project_rhythm_facts_view_model(brief("luming-nayin", invalid)) is None


def test_taiyi_projector_keeps_annual_scope_and_predicates_typed() -> None:
    view_model = project_taiyi_view_model(
        brief(
            "taiyi",
            {
                "calendar": {
                    "annual_boundary": "lunar_new_year_from_shared_calendar",
                    "lunar_year": 2026,
                    "year_ganzhi": "丙午",
                },
                "epoch": {
                    "accumulated_year": 1938583,
                    "anchor_accumulated_year": 1937281,
                    "anchor_lunar_year_ce": 724,
                    "derived_ce_offset": 1936557,
                    "one_based": True,
                    "profile_id": "synthetic",
                    "source_anchor": "L67-L69",
                },
                "cycle": {
                    "bureau": 55,
                    "governance": "理天",
                    "ji": 6,
                    "position_360": 343,
                    "year_in_ji": 43,
                    "year_in_zi_yuan": 55,
                    "zi_yuan": 5,
                    "zi_yuan_head": "壬子",
                },
                "board": {
                    "heshen": "未",
                    "jishen": "申",
                    "shiji": "艮",
                    "taisui": "午",
                    "taiyi_position": "艮",
                    "tianmu_wenchang": {"name": "武德", "position": "申"},
                },
                "host_guest": {"host": {"count": 16}, "guest": {"count": 3}},
                "four_generals": {
                    "guest_assistant": 9,
                    "guest_major": 3,
                    "host_assistant": 8,
                    "host_major": 6,
                },
                "long_cycle_deities": {
                    "junji": {
                        "accumulated_year": 286313,
                        "cycle_position": 113,
                        "epoch_profile": "synthetic",
                        "name": "君基",
                        "position": "丑",
                        "source_anchor": "L602-L604",
                        "status": "calculated_position_not_verdict",
                    }
                },
                "board_predicates": [
                    {
                        "id": "TY-P01",
                        "name": "掩",
                        "predicate": "shiji_same_as_taiyi",
                        "fact_paths": ["/shiji", "/taiyi"],
                        "source_anchor": "fulltext.md L430",
                        "source_dependency_id": "taiyi.synthetic",
                        "status": "predicate_matched_not_verdict",
                    }
                ],
                "scope_contract": {
                    "declared_scope": "annual_macro_historical_board_facts",
                    "interpretation_policy": "facts_only",
                    "supported_horizons": ["year"],
                    "supported_objects": ["macro_historical"],
                    "unsupported_scopes": ["personal_event"],
                },
            },
        )
    )

    assert isinstance(view_model, TaiyiChartV1)
    assert view_model.calendar.year_ganzhi == "丙午"
    assert view_model.board_predicates[0].status == "predicate_matched_not_verdict"


def test_selection_projector_uses_bounded_public_basis_projection() -> None:
    view_model = project_selection_view_model(
        brief(
            "selection",
            {
                "event_profile": "business_opening_transaction",
                "eligible_candidates": [
                    {
                        "candidate_id": "2026-09-03",
                        "civil_date": "2026-09-03",
                        "best_candidate_time_id": "2026-09-03:寅:synthetic",
                        "eligibility": {"eligible": True},
                        "rejection_reasons": [],
                        "ranking_components": {"official_huang_day_first": True},
                    }
                ],
                "eligible_date_time_candidates": ["2026-09-03:寅:synthetic"],
                "eliminations": [],
                "ranking": {
                    "component_order": ["hard_eligible_first"],
                    "eligible_candidate_ids": ["2026-09-03"],
                    "eligible_date_time_candidate_ids": ["2026-09-03:寅:synthetic"],
                    "folk_affects_rank": False,
                    "method": "explainable_lexicographic_v1",
                    "opaque_numeric_score": False,
                    "ordered_candidate_ids": ["2026-09-03"],
                    "ordered_date_time_candidate_ids": ["2026-09-03:寅:synthetic"],
                },
                "lineage_policy": {
                    "folk": "folk",
                    "folk_priority": "comparison_only",
                    "merge_verdicts": False,
                    "official": "official",
                    "official_priority": "primary",
                    "preserve_disagreement": True,
                },
                "no_valid_candidate": False,
                "basis_projection": {"candidate_limit_per_list": 12},
            },
        )
    )

    assert isinstance(view_model, SelectionChartV1)
    assert view_model.eligible_candidates[0].civil_date == "2026-09-03"
    assert view_model.ranking.opaque_numeric_score is False


def test_fengshui_projector_preserves_observation_boundary() -> None:
    view_model = project_fengshui_view_model(
        brief(
            "fengshui",
            {
                "active_subprofiles": ["liqi"],
                "observation_provenance": {"provider_performed_vision": False},
                "compass": {"status": "resolved", "facing": {"mountain": "午"}},
                "building_chronology": {"period_use": "not_required_for_bazhai"},
                "layout_graph": {"nodes": [], "edges": []},
                "form": {"status": "not_requested"},
                "liqi": {"status": "calculated_selected_school_facts_not_verdict"},
                "active_source_rule_ids": ["fengshui/yangzhai-shishu#YZS-R007"],
                "conflicts": [],
                "uncertainties": [],
                "critical_missing": [],
            },
        )
    )

    assert isinstance(view_model, FengshuiViewV1)
    assert view_model.liqi["status"] == "calculated_selected_school_facts_not_verdict"
    assert view_model.observation_provenance["provider_performed_vision"] is False


def test_qimen_projector_keeps_center_palace_omissions_as_null() -> None:
    palaces = [
        {
            "palace": index,
            "earth_stem": "戊" if index == 5 else "甲",
            "heaven_stems": [] if index == 5 else ["乙"],
            "stars": [] if index == 5 else ["天辅"],
            "door": None if index == 5 else "生门",
            "deity": None if index == 5 else "九天",
        }
        for index in range(1, 10)
    ]

    view_model = project_qimen_view_model(
        brief(
            "qimen",
            {
                "ju": {"dun": "yang", "number": 3},
                "chief": {
                    "star": "天蓬",
                    "door": "休门",
                    "hidden_instrument": "戊",
                    "xun_palace": 1,
                    "hosted_xun_palace": 1,
                    "destination_palace": 2,
                },
                "director": {
                    "door": "休门",
                    "xun_palace": 1,
                    "destination_palace": 3,
                    "hour_offset_in_xun": 2,
                },
                "instruments_wonders": {
                    "six_instruments": ["戊"],
                    "three_wonders": ["乙"],
                    "earth_plate": [],
                    "heaven_plate": [],
                    "hidden_jia": {"xun": "甲子", "instrument": "戊"},
                },
                "xunkong": {"xun": "甲子", "branches": ["戌", "亥"], "palaces": [6, 7]},
                "horse": {"hour_branch": "子", "branch": "寅", "palace": 8},
                "named_patterns": [],
                "palaces": palaces,
            },
        )
    )

    assert isinstance(view_model, QimenChartV1)
    center = view_model.palaces[4]
    assert center.palace_id == "5"
    assert center.star is None
    assert center.door is None
    assert center.deity is None
    assert view_model.palaces[0].heaven_stems == ("乙",)
    assert view_model.chief.star == "天蓬"
    assert view_model.xunkong.palaces == (6, 7)


def test_daliuren_projector_maps_lessons_and_three_transmissions() -> None:
    values = {
        "four_lessons": [
            {"lesson": 1, "upper": "辰", "lower": "庚"},
            {"lesson": 2, "upper": "子", "lower": "辰"},
            {"lesson": 3, "upper": "辰", "lower": "申"},
            {"lesson": 4, "upper": "子", "lower": "辰"},
        ],
        "three_transmissions": [
            {"stage": "initial", "branch": "子", "heavenly_general": "青龙"},
            {"stage": "middle", "branch": "申", "heavenly_general": "腾蛇"},
            {"stage": "final", "branch": "辰", "heavenly_general": "玄武"},
        ],
        "day_hour": {"day": "甲子", "hour": "乙丑"},
        "earth_plate": ["子", "丑"],
        "structural_patterns": ["伏吟"],
        "timing_candidates": [
            {"id": "initial_group_upper_candidate", "candidate_not_guarantee": True}
        ],
        "xunkong": {"xun": "甲子", "branches": ["戌", "亥"]},
    }

    view_model = project_daliuren_view_model(brief("liuren", values))

    assert isinstance(view_model, DaliurenChartV1)
    assert [item.lesson_id for item in view_model.lessons] == ["1", "2", "3", "4"]
    assert [item.general for item in view_model.transmissions] == ["青龙", "腾蛇", "玄武"]
    assert view_model.core_facts is not None
    assert view_model.core_facts.earth_plate == ("子", "丑")
    assert view_model.core_facts.structural_patterns == ("伏吟",)
    assert view_model.core_facts.timing_candidates == (
        {"id": "initial_group_upper_candidate", "candidate_not_guarantee": True},
    )


def test_physiognomy_projector_maps_public_observations_and_ignores_private_input() -> None:
    payload = brief(
        "physiognomy",
        {
            "normalized_visible_observations": [
                {
                    "region": "forehead",
                    "feature_kind": "visible_morphology",
                    "descriptor": "region_visible",
                    "visibility": "full",
                    "uncertainty": 0.2,
                    "asset_id": "asset-private",
                    "source_ref": "source-private",
                }
            ]
        },
    )
    payload["facts"] = [
        *payload["facts"],
        {
            "ref": "fact:input/physiognomy/normalized_visible_observations",
            "subject_ref": "fixture:probe",
            "kind_id": "kind.fact",
            "value": [{"region": "must-not-be-read"}],
            "display_text": "input",
        },
    ]

    view_model = project_physiognomy_view_model(payload)

    assert isinstance(view_model, PhysiognomyViewV1)
    assert view_model.mode == "face"
    assert view_model.observations[0].region_id == "forehead"
    assert view_model.observations[0].confidence == 0.8
    assert "asset-private" not in view_model.observations[0].display_text


def test_runtime_dispatch_projects_physiognomy_view_model() -> None:
    view_model = project_runtime_view_model(
        brief(
            "physiognomy",
            {
                "normalized_visible_observations": [
                    {
                        "region": "forehead",
                        "feature_kind": "visible_morphology",
                        "descriptor": "region_visible",
                        "visibility": "full",
                        "uncertainty": 0.0,
                    }
                ]
            },
        )
    )

    assert isinstance(view_model, PhysiognomyViewV1)


def test_runtime_dispatch_projects_five_elements_facts_view_model() -> None:
    view_model = project_runtime_view_model(
        brief(
            "bazi",
            {
                "four_pillars": {
                    "year": "甲戌",
                    "month": "戊辰",
                    "day": "丙戌",
                    "hour": "辛卯",
                },
                "element_inventory": {
                    "visible_stem_branch_counts": {"木": 2, "火": 1, "土": 4, "金": 1},
                    "hidden_stem_occurrence_counts": {"木": 1, "火": 2, "土": 3, "金": 2, "水": 1},
                    "scope": "inventory only",
                },
                "seasonal_profile": {
                    "season": "季春",
                    "month_qi": "土承木余气",
                    "temperature": "温",
                    "moisture": "湿",
                },
                "tiaohou_markers": {
                    "temperature": "温",
                    "moisture": "湿",
                    "markers": ["温", "湿"],
                    "applicability_identity": {
                        "day_stem": "丙",
                        "month_branch": "辰",
                        "source_rule_id": "bazi/qiongtong-baojian#QR-02-01",
                    },
                    "scope": "month-level climate anchors only",
                },
            },
        ),
        product_id="five-elements-facts",
    )

    assert isinstance(view_model, FiveElementsFactsViewV1)
    assert view_model.source_status == "exact_rule_bound"
    assert view_model.active_source_rule_ids == ("bazi/qiongtong-baojian#QR-02-01",)


def test_runtime_dispatch_projects_internal_art_view_models() -> None:
    assert isinstance(
        project_runtime_view_model(
            brief(
                "fengshui",
                {
                    "active_subprofiles": [],
                    "observation_provenance": {},
                    "compass": {},
                    "building_chronology": {},
                    "layout_graph": {},
                    "form": {},
                    "liqi": {},
                    "active_source_rule_ids": [],
                    "conflicts": [],
                    "uncertainties": [],
                    "critical_missing": [],
                },
            )
        ),
        FengshuiViewV1,
    )


def test_canwen_projector_exposes_scope_alignment_and_missing_cross_art_scope() -> None:
    payload = {
        "question": "比较共同事实范围",
        "facts": [
            {
                "ref": "fact:profile/calculated/bazi/four_pillars",
                "subject_ref": "profile:fixture",
                "kind_id": "kind.fact",
                "value": {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": "丁卯"},
                "display_text": "four_pillars",
            },
            {
                "ref": "fact:profile/calculated/bazi/dimension_fact_scope",
                "subject_ref": "profile:fixture",
                "kind_id": "kind.fact",
                "value": {
                    "career": {
                        "scope": "calculated_natal_chart",
                        "base_calculation_digest": "a" * 64,
                    }
                },
                "display_text": "dimension_fact_scope",
            },
            {
                "ref": "fact:profile/calculated/ziwei/dimension_fact_scope",
                "subject_ref": "profile:fixture",
                "kind_id": "kind.fact",
                "value": {
                    "career": {
                        "scope": "calculated_natal_chart",
                        "base_calculation_digest": "b" * 64,
                    }
                },
                "display_text": "dimension_fact_scope",
            },
        ],
        "request_view": {
            "subject_refs": ["profile:fixture"],
            "capability_ids": ["bazi", "ziwei", "xingming"],
            "dimension_ids": ["career"],
        },
    }

    view_model = project_canwen_view_model(payload)

    assert isinstance(view_model, CanwenViewV1)
    assert view_model.selected_art_ids == ("bazi", "ziwei", "qizheng")
    dimension = view_model.dimensions[0]
    assert [signal.art_id for signal in dimension.signals] == ["bazi", "ziwei"]
    assert dimension.convergence == ()
    assert dimension.disagreements == ()
    assert dimension.missing_art_ids == ("qizheng",)
    assert project_runtime_view_model(payload) == view_model

    hecan = project_hecan_view_model(payload)
    assert isinstance(hecan, HecanViewV1)
    assert hecan.selected_art_ids == ("bazi", "ziwei", "qizheng")
    assert hecan.dimensions == view_model.dimensions
    assert project_runtime_view_model(payload, product_id="hecan") == hecan


def test_canwen_does_not_treat_provider_scope_names_as_art_disagreement() -> None:
    payload = {
        "question": "比较共同事实范围",
        "facts": [
            {
                "ref": "fact:profile/calculated/bazi/dimension_fact_scope",
                "subject_ref": "profile:fixture",
                "kind_id": "kind.fact",
                "value": {
                    "career": {
                        "scope": "calculated_natal_chart",
                        "base_calculation_digest": "a" * 64,
                    }
                },
                "display_text": "dimension_fact_scope",
            },
            {
                "ref": "fact:profile/calculated/ziwei/dimension_fact_scope",
                "subject_ref": "profile:fixture",
                "kind_id": "kind.fact",
                "value": {
                    "career": {
                        "scope": "calculated_natal_ziwei_chart",
                        "base_calculation_digest": "b" * 64,
                    }
                },
                "display_text": "dimension_fact_scope",
            },
            {
                "ref": "fact:profile/calculated/xingming/dimension_fact_scope",
                "subject_ref": "profile:fixture",
                "kind_id": "kind.fact",
                "value": {
                    "career": {
                        "scope": "calculated_natal_xingming_chart",
                        "base_calculation_digest": "c" * 64,
                    }
                },
                "display_text": "dimension_fact_scope",
            },
        ],
        "request_view": {
            "subject_refs": ["profile:fixture"],
            "capability_ids": ["bazi", "ziwei", "xingming"],
            "dimension_ids": ["career"],
        },
    }

    view_model = project_canwen_view_model(payload)

    assert isinstance(view_model, CanwenViewV1)
    dimension = view_model.dimensions[0]
    assert dimension.missing_art_ids == ()
    assert dimension.disagreements == ()
    assert dimension.convergence == (
        "所选术数的计算事实范围均已提供；尚未形成实质性互证结论。",
    )


def test_project_runtime_view_model_does_not_treat_wenshi_as_canwen() -> None:
    brief_payload = {
        "question": "这次合作能否推进？",
        "facts": [],
        "request_view": {
            "subject_refs": ["wenshi:synthetic"],
            "capability_ids": ["liuyao", "qimen", "liuren"],
            "dimension_ids": ["outcome"],
        },
    }

    view_model = project_runtime_view_model(brief_payload)
    assert isinstance(view_model, WenshiViewV1)
    assert view_model.dimensions[0].missing_art_ids == (
        "liuyao",
        "qimen",
        "daliuren",
    )


def test_wenshi_projector_exposes_three_art_structure_and_keeps_synthesis_empty() -> None:
    payload = {
        "question": "这次合作能否推进？",
        "facts": [
            {
                "ref": "fact:wenshi:synthetic/calculated/liuyao/relation_facts",
                "subject_ref": "wenshi:synthetic",
                "kind_id": "kind.liuyao-structure",
                "value": {"primary_hexagram": "fixture"},
                "display_text": "relation_facts",
            },
            {
                "ref": "fact:wenshi:synthetic/calculated/qimen/calculated_board_scope",
                "subject_ref": "wenshi:synthetic",
                "kind_id": "kind.qimen-structure",
                "value": {"scope": "fixture"},
                "display_text": "calculated_board_scope",
            },
            {
                "ref": "fact:wenshi:synthetic/calculated/liuren/dimension_facts",
                "subject_ref": "wenshi:synthetic",
                "kind_id": "kind.liuren-structure",
                "value": {"outcome": {"scope": "fixture"}},
                "display_text": "dimension_facts",
            },
        ],
        "request_view": {
            "subject_refs": ["wenshi:synthetic"],
            "capability_ids": ["liuyao", "qimen", "liuren"],
            "dimension_ids": ["outcome", "timing"],
        },
    }

    view_model = project_wenshi_view_model(payload)

    assert isinstance(view_model, WenshiViewV1)
    assert view_model.selected_art_ids == ("liuyao", "qimen", "daliuren")
    assert [signal.art_id for signal in view_model.dimensions[0].signals] == [
        "liuyao",
        "qimen",
        "daliuren",
    ]
    assert view_model.dimensions[0].convergence == ()
    assert view_model.dimensions[0].disagreements == ()
    assert view_model.dimensions[1].missing_art_ids == ("daliuren",)
    assert project_runtime_view_model(payload) == view_model


def test_runtime_dispatch_returns_none_for_a_capability_without_a_projector() -> None:
    assert project_runtime_view_model(brief("fortune", {"target_date": "fixture"})) is None
