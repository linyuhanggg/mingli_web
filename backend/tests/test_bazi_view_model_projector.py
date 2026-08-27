from __future__ import annotations

import pytest
from app.charts.contracts import BaziCalendarNormalization, FortuneCalendarNormalization
from app.charts.projectors import (
    project_bazi_view_model,
    project_runtime_view_model,
)
from app.readings.runtime_contracts import ReadingBrief


def _brief(*, capability_id: str = "bazi") -> ReadingBrief:
    return ReadingBrief.from_dict(
        {
            "question": "查看本命四柱结构",
            "vocabulary": [],
            "facts": [
                {
                    "ref": "fact:profile-version:test/input/birth_datetime",
                    "subject_ref": "profile-version:test",
                    "kind_id": "kind.fact",
                    "value": "1994-04-30T05:55:00+08:00",
                    "display_text": "出生时间：1994-04-30T05:55:00+08:00",
                },
                {
                    "ref": "fact:profile-version:test/calculated/bazi/four_pillars",
                    "subject_ref": "profile-version:test",
                    "kind_id": "kind.fact",
                    "value": {
                        "year": "甲戌",
                        "month": "戊辰",
                        "day": "丙戌",
                        "hour": "辛卯",
                    },
                    "display_text": "四柱已由 Runtime 计算。",
                },
                {
                    "ref": "fact:profile-version:test/calculated/bazi/element_inventory",
                    "subject_ref": "profile-version:test",
                    "kind_id": "kind.fact",
                    "value": {
                        "visible_stem_branch_counts": {
                            "木": 2,
                            "火": 1,
                            "土": 4,
                            "金": 1,
                        }
                    },
                    "display_text": "五行可见干支计数已由 Runtime 计算。",
                },
            ],
            "evidence": [],
            "findings": [],
            "claim_scopes": [],
            "limits": [],
            "prior_answer": None,
            "request_view": {
                "subject_refs": ["profile-version:test"],
                "capability_ids": [capability_id],
                "object_id": "natal",
                "dimension_ids": ["overview"],
                "horizon": {"kind_id": "life", "start": None, "end": None},
            },
        }
    )


def _interpretive_candidates() -> dict[str, object]:
    return {
        "strength": {
            "status": "evidence_only",
            "hard_verdict": None,
            "day_element": "土",
            "month_command_element": "土",
            "seasonal_state": "旺",
            "seasonal_state_source_rule_id": "bazi/sanming-tonghui#R-02-04",
            "same_element_occurrences": 4,
            "resource_element": "火",
            "resource_occurrences": 2,
            "all_element_occurrences": {"木": 2, "火": 2, "土": 4, "金": 1, "水": 1},
            "month_order_adjudication": {
                "status": "adjudicated_month_order_state",
                "decision_scope": "bazi_month_order_seasonal_state",
                "day_master_element": "土",
                "month_command_element": "土",
                "seasonal_state": "旺",
                "whole_chart_strength_verdict": None,
                "useful_god_verdict": None,
                "source_ref": {
                    "pack": "bazi/sanming-tonghui",
                    "rule_id": "R-02-04",
                    "source_anchor": (
                        "references/books/bazi/sanming-tonghui/"
                        "rules.md#R-02-04"
                    ),
                    "verification_status": "verified",
                    "binding_digest": (
                        "77b387e17e65b50c7cbcdba3cc8ef5b1"
                        "70499c6d5c07461856b710d5aa50759e"
                    ),
                },
                "unresolved_checks": [
                    "全局根气、生扶、克泄与合化",
                    "从格、化气及旺极衰极的反向取用",
                    "整个日主强弱、唯一用神与现实吉凶应期",
                ],
            },
            "boundary": "只展示五行出现次数，不等于旺衰定论。",
        },
        "structure": {
            "status": "candidate_only",
            "hard_verdict": None,
            "month_main_qi": "戊",
            "month_main_qi_ten_god": "劫财",
            "main_qi_visible": False,
            "visible_positions": ["year"],
            "boundary": "只展示月令主气与透干候选，不完成格局裁定。",
        },
        "following_and_transformation": {
            "status": "requires_classical_adjudication",
            "hard_verdict": None,
            "stem_combination_candidates": [
                {
                    "with_position": "year-month",
                    "stems": ["甲", "己"],
                    "candidate_element": "土",
                    "status": "mechanical_candidate",
                }
            ],
            "branch_formation_candidates": [
                {
                    "type": "六合",
                    "positions": ["month", "hour"],
                    "branches": ["戌", "卯"],
                }
            ],
            "boundary": "合化、从格仍需经典裁决。",
        },
        "salience_signals": [
            {
                "signal_id": "seasonal-anchor",
                "status": "mechanical_candidate",
                "hard_verdict": None,
                "basis": {"month_branch": "戌"},
                "boundary": "显著信号不等于吉凶。",
            }
        ],
        "reasoning_tools": {
            "strength_evidence": {
                "schema_version": "mingli-bazi-reasoning-tool-v2",
                "tool_id": "bazi.tool.strength_evidence",
                "tool_kind": "disputed_rule_synthesis",
                "confidence_bucket": "medium",
                "confidence_ceiling": "medium",
                "visibility_class": "on_demand",
                "fact_refs": [{"path": "$.output.day_master", "value": {"element": "土"}}],
                "source_refs": [{"pack": "bazi/yuanhai-ziping", "rule_id": "YR-01-05"}],
                "output": {"status": "bounded_evidence_synthesis", "evidence_lean": "support_lean"},
                "caveats": ["不是旺衰硬断"],
                "tool_digest": "a" * 64,
            },
            "month_structure_candidate": {
                "schema_version": "mingli-bazi-reasoning-tool-v2",
                "tool_id": "bazi.tool.month_structure_candidate",
                "tool_kind": "rule_applicability",
                "confidence_bucket": "low",
                "confidence_ceiling": "medium",
                "visibility_class": "on_demand",
                "fact_refs": [{"path": "$.output.month_command", "value": {"main_qi": "戊"}}],
                "source_refs": [{"pack": "bazi/yuanhai-ziping", "rule_id": "YR-01-12"}],
                "output": {"status": "candidate_only"},
                "caveats": ["仍需经典裁决"],
                "tool_digest": "b" * 64,
            },
        },
    }


def _year_layer() -> dict[str, object]:
    shensha = {
        "status": "calculated_auxiliary_layer",
        "temporal_scope": "natal_plus_requested_transit",
        "precedence": "auxiliary_only",
        "evaluated_rules": [],
        "calculated_items": [],
        "cannot_override": ["transit_facts"],
        "boundary": "auxiliary only",
    }
    relation = {
        "type": "六破",
        "natal_position": "hour",
        "natal_branch": "卯",
        "transit_branch": "午",
    }
    structural = {
        "status": "mechanical_candidates_only",
        "transit_pillar": "丙午",
        "stem_ten_god": "正印",
        "branch_relations": [relation],
        "hard_verdict": None,
    }
    segment = {
        "start_inclusive": "2026-01-01T00:00:00+08:00",
        "end_exclusive": "2026-02-04T04:01:51+08:00",
        "ganzhi": "乙巳",
        "stem_ten_god": "七杀",
        "branch_hidden_ten_gods": [{"stem": "丙", "ten_god": "正印"}],
        "branch_relations": [],
        "seasonal_effect": {"status": "not_inferred_from_non_month_pillar"},
        "tiaohou_effect": {"status": "not_inferred_from_non_month_pillar"},
        "structural_changes": {
            "status": "mechanical_candidates_only",
            "transit_pillar": "乙巳",
            "stem_ten_god": "七杀",
            "branch_relations": [],
            "hard_verdict": None,
        },
        "seasonal_tiaohou_delta": {
            "status": "not_inferred_from_non_month_pillar"
        },
        "shensha_auxiliary": shensha,
    }
    return {
        "2026": {
            "year": 2026,
            "ganzhi": "丙午",
            "stem_ten_god": "正印",
            "branch_hidden_ten_gods": [{"stem": "丁", "ten_god": "偏印"}],
            "branch_relations": [relation],
            "structural_changes": structural,
            "shensha_auxiliary": shensha,
            "active_luck_cycle": {"status": "single_cycle"},
            "seasonal_effect": {"status": "calculated_exact_jie_segments"},
            "tiaohou_effect": {"status": "applicability_identity_by_exact_jie_segment"},
            "seasonal_tiaohou_delta": {"status": "calculated_exact_jie_segments"},
            "calendar_normalization": {
                "timezone": "Asia/Shanghai",
                "year_boundary": "立春",
                "boundary_datetime": "2026-02-04T04:01:51+08:00",
                "before_boundary_ganzhi": "乙巳",
                "after_boundary_ganzhi": "丙午",
            },
            "rule_trace": [
                {
                    "rule_id": "bazi.test.year",
                    "source_dependency_id": "bazi.test",
                    "operation": "test",
                }
            ],
            "ganzhi_segments": [segment, {**segment, "ganzhi": "丙午"}],
        }
    }


def _g3_calendar_normalization() -> dict[str, object]:
    return {
        "status": "calculated",
        "algorithm_version": "calendar-v53",
        "time_basis": {
            "policy": "local_apparent_solar-v1",
            "algorithm": {},
            "boundary": {},
        },
        "true_solar_time": {"status": "apparent_solar_applied"},
        "calendar_convention": {},
        "effective_datetime": "1985-03-01T23:33:00+08:00",
        "day_boundary": {
            "correction_crossed_date": True,
            "zi_policy_advanced_day_pillar": False,
        },
        "changed_pillars": ["day", "hour"],
        "solar_terms": {
            "previous": {
                "name": "雨水",
                "index": 2,
                "is_month_boundary_jie": False,
                "datetime": "1985-02-19T06:00:00+08:00",
                "instant_utc": "1985-02-18T22:00:00Z",
            },
            "next": {
                "name": "惊蛰",
                "index": 3,
                "is_month_boundary_jie": True,
                "datetime": "1985-03-05T17:00:00+08:00",
                "instant_utc": "1985-03-05T09:00:00Z",
            },
            "month_switch_policy": "exact_jie_instant",
        },
    }


def _brief_with_calendar(calendar: dict[str, object]) -> dict[str, object]:
    payload = _brief().to_dict()
    payload["facts"] = [
        *payload["facts"],
        {
            "ref": "fact:profile-version:test/calculated/bazi/calendar_normalization",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": calendar,
            "display_text": "历法与真太阳时已由 Runtime 计算。",
        },
    ]
    return payload


def test_projects_g3_bazi_calendar_facts_without_cross_contract_leakage() -> None:
    view_model = project_bazi_view_model(
        _brief_with_calendar(_g3_calendar_normalization())
    )

    assert view_model is not None
    assert view_model.core_facts is not None
    calendar = view_model.core_facts.calendar_normalization
    assert calendar is not None
    assert calendar.effective_datetime == "1985-03-01T23:33:00+08:00"
    assert calendar.day_boundary is not None
    assert calendar.day_boundary.correction_crossed_date is True
    assert calendar.day_boundary.zi_policy_advanced_day_pillar is False
    assert calendar.changed_pillars == ("day", "hour")
    assert calendar.solar_terms is not None
    assert calendar.solar_terms.previous is not None
    assert calendar.solar_terms.previous.name == "雨水"
    assert calendar.solar_terms.next is not None
    assert calendar.solar_terms.next.is_month_boundary_jie is True
    assert calendar.solar_terms.month_switch_policy == "exact_jie_instant"


def test_empty_changed_pillars_remains_present_and_distinct_from_missing() -> None:
    calendar = _g3_calendar_normalization()
    calendar["changed_pillars"] = []
    view_model = project_bazi_view_model(_brief_with_calendar(calendar))

    assert view_model is not None
    assert view_model.core_facts is not None
    normalized = view_model.core_facts.calendar_normalization
    assert normalized is not None
    assert normalized.changed_pillars == ()
    assert "changed_pillars" in normalized.model_dump(mode="json")


def test_missing_g3_bazi_calendar_fields_are_not_inferred_or_emitted() -> None:
    calendar = _g3_calendar_normalization()
    for field in (
        "effective_datetime",
        "day_boundary",
        "changed_pillars",
        "solar_terms",
    ):
        calendar.pop(field)
    view_model = project_bazi_view_model(_brief_with_calendar(calendar))

    assert view_model is not None
    assert view_model.core_facts is not None
    normalized = view_model.core_facts.calendar_normalization
    assert normalized is not None
    dumped = normalized.model_dump(mode="json")
    assert "effective_datetime" not in dumped
    assert "day_boundary" not in dumped
    assert "changed_pillars" not in dumped
    assert "solar_terms" not in dumped


def test_invalid_changed_pillar_is_rejected_by_bazi_contract_and_projector() -> None:
    calendar = _g3_calendar_normalization()
    calendar["changed_pillars"] = ["day", "week"]

    with pytest.raises(ValueError):
        BaziCalendarNormalization.model_validate(calendar)

    view_model = project_bazi_view_model(_brief_with_calendar(calendar))
    assert view_model is not None
    assert view_model.core_facts is not None
    assert view_model.core_facts.calendar_normalization is None


def test_g3_calendar_fields_are_additive_and_strict_in_fortune_contract() -> None:
    normalized = FortuneCalendarNormalization.model_validate(
        _g3_calendar_normalization()
    )
    assert normalized.effective_datetime == "1985-03-01T23:33:00+08:00"
    assert normalized.day_boundary is not None
    assert normalized.day_boundary.correction_crossed_date is True
    assert normalized.changed_pillars == ("day", "hour")
    assert normalized.solar_terms is not None
    assert normalized.solar_terms.next is not None
    assert normalized.solar_terms.next.name == "惊蛰"

    legacy = _g3_calendar_normalization()
    for field in (
        "effective_datetime",
        "day_boundary",
        "changed_pillars",
        "solar_terms",
    ):
        legacy.pop(field)
    legacy_dump = FortuneCalendarNormalization.model_validate(legacy).model_dump(
        mode="json"
    )
    assert "effective_datetime" not in legacy_dump
    assert "day_boundary" not in legacy_dump
    assert "changed_pillars" not in legacy_dump
    assert "solar_terms" not in legacy_dump

    invalid = _g3_calendar_normalization()
    solar_terms = invalid["solar_terms"]
    assert isinstance(solar_terms, dict)
    solar_terms["raw_runtime_payload"] = {}
    with pytest.raises(ValueError):
        FortuneCalendarNormalization.model_validate(invalid)


def test_projects_calculated_bazi_facts_into_versioned_chart() -> None:
    view_model = project_bazi_view_model(_brief())

    assert view_model is not None
    assert view_model.schema_version == "bazi-chart/v1"
    assert view_model.subject_ref == "profile-version:test"
    assert [(item.position, item.stem, item.branch) for item in view_model.pillars] == [
        ("year", "甲", "戌"),
        ("month", "戊", "辰"),
        ("day", "丙", "戌"),
        ("hour", "辛", "卯"),
    ]
    assert [(item.element, item.value) for item in view_model.element_balance] == [
        ("wood", 2.0),
        ("fire", 1.0),
        ("earth", 4.0),
        ("metal", 1.0),
    ]
    assert view_model.time_layers[0].available is True
    assert all(item.unavailable_reason for item in view_model.time_layers[1:])
    assert "1994-04-30" not in str(view_model.model_dump(mode="json"))


def test_projects_runtime_year_layer_and_marks_year_time_layer_available() -> None:
    payload = _brief().to_dict()
    payload["facts"] = [
        *payload["facts"],
        {
            "ref": "fact:profile-version:test/calculated/bazi/year_layers",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": _year_layer(),
            "display_text": "流年层已由 Runtime 计算。",
        },
    ]
    payload["request_view"]["horizon"] = {
        "kind_id": "year",
        "start": "2026",
        "end": "2026",
    }

    view_model = project_bazi_view_model(payload)

    assert view_model is not None
    assert view_model.time_layers[1].available is True
    assert view_model.core_facts is not None
    assert view_model.core_facts.year_layers is not None
    assert view_model.core_facts.year_layers[0].year == 2026
    assert view_model.core_facts.year_layers[0].ganzhi == "丙午"
    assert view_model.core_facts.year_layers[0].ganzhi_segments[1].ganzhi == "丙午"


def test_non_bazi_brief_does_not_get_projected_as_a_bazi_chart() -> None:
    assert project_bazi_view_model(_brief(capability_id="fortune")) is None


def test_projects_five_elements_facts_without_inventing_a_verdict() -> None:
    payload = _brief().to_dict()
    payload["facts"] = [
        *payload["facts"],
        {
            "ref": "fact:profile-version:test/calculated/bazi/day_master",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {"stem": "丙", "element": "火", "polarity": "阳"},
            "display_text": "日主已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/month_command",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "branch": "辰",
                "label": "辰月",
                "main_qi": "戊",
                "main_qi_element": "earth",
            },
            "display_text": "月令已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/seasonal_profile",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "season": "季春",
                "month_qi": "土承木余气",
                "temperature": "温",
                "moisture": "湿",
            },
            "display_text": "季节画像已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/tiaohou_markers",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "temperature": "温",
                "moisture": "湿",
                "markers": ["温", "湿"],
                "applicability_identity": {
                    "day_stem": "丙",
                    "month_branch": "辰",
                    "source_dependency_id": "bazi.seasonal-tiaohou.day-master-month",
                },
                "scope": "month-level climate anchors only",
            },
            "display_text": "调候标记已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/interpretive_candidates",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": _interpretive_candidates(),
            "display_text": "强弱证据与结构候选已由 Runtime 计算。",
        },
    ]

    view_model = project_runtime_view_model(payload, product_id="five-elements-facts")

    assert view_model is not None
    assert view_model.schema_version == "five-elements-facts-view/v1"
    assert view_model.source_status == "identity_only"
    assert view_model.source_dependency_ids == (
        "bazi.seasonal-tiaohou.day-master-month",
    )
    assert view_model.active_source_rule_ids == ()
    assert any("逐条来源规则 ID" in gap for gap in view_model.source_gaps)
    assert all(
        "旺衰" in limitation or "调候" in limitation or "强弱" in limitation
        for limitation in view_model.limitations
    )
    assert "用神" in " ".join(view_model.limitations)
    assert view_model.interpretive_candidates is not None
    assert view_model.interpretive_candidates.strength.same_element_occurrences == 4
    assert view_model.interpretive_candidates.strength.seasonal_state == "旺"
    assert (
        view_model.interpretive_candidates.strength.seasonal_state_source_rule_id
        == "bazi/sanming-tonghui#R-02-04"
    )
    assert view_model.interpretive_candidates.reasoning_tools is not None
    assert (
        view_model.interpretive_candidates.reasoning_tools["strength_evidence"]
        .output["evidence_lean"]
        == "support_lean"
    )
    assert view_model.interpretive_candidates.structure.main_qi_visible is False
    assert (
        view_model.interpretive_candidates.following_and_transformation
        .branch_formation_candidates[0]
        .relation_type
        == "六合"
    )


def test_five_elements_facts_projects_source_gap_when_runtime_fact_is_missing() -> None:
    view_model = project_runtime_view_model(
        _brief().to_dict(), product_id="five-elements-facts"
    )

    assert view_model is not None
    assert view_model.source_status == "unavailable"
    assert view_model.element_inventory is None
    assert view_model.source_gaps


def test_projects_runtime_bazi_core_facts_without_input_or_findings() -> None:
    payload = _brief().to_dict()
    payload["facts"] = [
        *payload["facts"],
        {
            "ref": "fact:profile-version:test/calculated/bazi/day_master",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {"stem": "丙", "element": "火", "polarity": "阳"},
            "display_text": "日主已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/hidden_stems",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "year": {"branch": "戌", "stems": ["戊", "辛", "丁"]},
                "month": {"branch": "辰", "stems": ["戊", "乙", "癸"]},
                "day": {"branch": "戌", "stems": ["戊", "辛", "丁"]},
                "hour": {"branch": "卯", "stems": ["乙"]},
            },
            "display_text": "藏干已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/ten_gods",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "heavenly_stems": {
                    "year": {"stem": "甲", "ten_god": "偏印"},
                    "month": {"stem": "戊", "ten_god": "食神"},
                    "day": {"stem": "丙", "ten_god": "日主"},
                    "hour": {"stem": "辛", "ten_god": "正财"},
                },
                "hidden_stems": {
                    "year": [{"stem": "戊", "ten_god": "食神"}],
                    "month": [{"stem": "乙", "ten_god": "正印"}],
                    "day": [{"stem": "丁", "ten_god": "劫财"}],
                    "hour": [{"stem": "乙", "ten_god": "正印"}],
                },
            },
            "display_text": "十神已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/nayin",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "year": "山头火",
                "month": "大林木",
                "day": "屋上土",
                "hour": "松柏木",
            },
            "display_text": "纳音已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/xunkong",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "day_pillar": "丙戌",
                "xun": "甲申",
                "branches": ["午", "未"],
                "source_dependency_id": "bazi.chart.xunkong-sexagenary-v1",
                "boundary": "按日柱所属旬计算旬空事实；不能单独推出吉凶、六亲或事件结论",
            },
            "display_text": "旬空已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/san_yuan",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "tai_yuan": "己未",
                "ming_gong": "甲戌",
                "shen_gong": "庚午",
                "source": "lunar-typescript-auxiliary",
                "source_dependency_id": "bazi.chart.san-yuan-lunar-typescript-v1",
                "boundary": "胎元、命宫、身宫位置事实；不能单独推出格局、旺衰、吉凶或事件结论",
            },
            "display_text": "胎元、命宫、身宫已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/month_command",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "branch": "辰",
                "label": "辰月",
                "main_qi": "戊",
                "main_qi_element": "earth",
            },
            "display_text": "月令已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/seasonal_profile",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "season": "季春",
                "month_qi": "土承木余气",
                "temperature": "温",
                "moisture": "湿",
            },
            "display_text": "季节画像已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/tiaohou_markers",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "temperature": "温",
                "moisture": "湿",
                "markers": ["温", "湿"],
                "applicability_identity": {"day_stem": "丙", "month_branch": "辰"},
                "scope": "month-level climate anchors only",
            },
            "display_text": "调候标记已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/branch_relations",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": [
                {
                    "type": "六合",
                    "positions": ["month", "hour"],
                    "branches": ["辰", "卯"],
                }
            ],
            "display_text": "地支关系已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/luck_cycles",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "status": "sequence_only",
                "direction": "forward",
                "direction_rule": "按年干阴阳与性别定顺逆",
                "cycles": [{"sequence": 1, "pillar": "己巳"}],
                "unavailable": ["start_age", "calendar_year_mapping"],
            },
            "display_text": "大运序列已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/calendar_normalization",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": {
                "algorithm_version": "sxtwl-2.0.7/exact-jie-boundary-v1.2",
                "calendar_convention": {
                    "day_rollover": "civil_midnight",
                    "hour_basis": "local_apparent_solar-v1",
                    "id": "east-asian-civil-jieqi-v1",
                    "month_boundary": "exact Jie instant",
                    "version": "1.0.2",
                    "year_boundary": "exact Li Chun instant",
                    "zi_hour_policy": "midnight",
                },
                "status": "calculated",
                "time_basis": {
                    "policy": "local_apparent_solar-v1",
                    "algorithm": {
                        "id": "astronomy-engine-apparent-solar-eot-v1",
                        "source": (
                            "astronomy-engine apparent solar hour angle; "
                            "equation_of_time = apparent_solar_time - mean_solar_time"
                        ),
                        "uncertainty_seconds": 30,
                        "version": "astronomy-engine-2.1.19",
                    },
                    "boundary": {
                        "correction_changes_hour_branch": False,
                        "distance_seconds": 3294,
                        "within_uncertainty": False,
                    },
                    "equation_of_time_seconds": 163,
                    "longitude_correction_seconds": -169,
                    "standard_meridian_degrees": 120.0,
                    "total_correction_seconds": -6,
                },
                "true_solar_time": {
                    "equation_of_time_seconds": 163,
                    "longitude_correction_seconds": -169,
                    "status": "apparent_solar_applied",
                    "policy": "local_apparent_solar-v1",
                    "total_correction_seconds": -6,
                },
            },
            "display_text": "历法与真太阳时已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/interpretive_candidates",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": _interpretive_candidates(),
            "display_text": "强弱证据与结构候选已由 Runtime 计算。",
        },
        {
            "ref": "fact:profile-version:test/calculated/bazi/source_conditioned_patterns",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": [
                {
                    "rule_id": "bazi/qiongtong-baojian#QR-02-01",
                    "local_rule_id": "QR-02-01",
                    "title": "QR-02-01 — 三春丙火",
                    "source_pack": "bazi/qiongtong-baojian",
                    "source_anchor": "fulltext.md L317-L382",
                    "status": "predicate_matched_not_verdict",
                    "fact_paths": [
                        "/chart_facts/output/day_master/stem",
                        "/chart_facts/output/month_command/branch",
                    ],
                    "predicate_audit": [
                        "stem:eq:丙",
                        "branch:eq:辰",
                    ],
                }
            ],
            "display_text": "已命中的经典来源条件已由 Runtime 计算，尚未形成裁决。",
        },
    ]
    payload["evidence"] = [
        {
            "ref": "evidence:bazi/bazi/qiongtong-baojian#QR-02-01",
            "evidence_ref": "evidence:bazi/bazi/qiongtong-baojian#QR-02-01",
            "rule_id": "bazi/qiongtong-baojian#QR-02-01",
            "source_title": "穷通宝鉴",
            "locator": "fulltext.md#L319",
            "excerpt": "正月用壬，庚辛为助。二月耑用壬水。三月土重晦光，取甲佐之为妙",
            "verification_status": "verified_exact",
            "verbatim_excerpt": (
                "正月用壬，庚辛为助。二月耑用壬水。"
                "三月土重晦光，取甲佐之为妙"
            ),
            "verbatim_citations": [
                {
                    "source_title": "穷通宝鉴",
                    "locator": "fulltext.md#L319",
                    "verbatim_excerpt": (
                        "正月用壬，庚辛为助。二月耑用壬水。"
                        "三月土重晦光，取甲佐之为妙"
                    ),
                    "verification_status": "verified_exact",
                }
            ],
            "supports_fact_refs": [
                "fact:profile-version:test/calculated/bazi/day_master",
                "fact:profile-version:test/calculated/bazi/month_command",
            ],
        }
    ]

    view_model = project_bazi_view_model(ReadingBrief.from_dict(payload))

    assert view_model is not None
    assert view_model.core_facts is not None
    assert view_model.core_facts.day_master is not None
    assert view_model.core_facts.day_master.stem == "丙"
    assert view_model.core_facts.hidden_stems is not None
    assert view_model.core_facts.hidden_stems[0].stems == ("戊", "辛", "丁")
    assert view_model.core_facts.ten_gods is not None
    assert view_model.core_facts.ten_gods.heavenly_stems[0].ten_god == "偏印"
    assert view_model.core_facts.nayin is not None
    assert view_model.core_facts.nayin[1].name == "大林木"
    assert view_model.core_facts.xunkong is not None
    assert view_model.core_facts.xunkong.branches == ("午", "未")
    assert view_model.core_facts.san_yuan is not None
    assert view_model.core_facts.san_yuan.tai_yuan == "己未"
    assert view_model.core_facts.san_yuan.ming_gong == "甲戌"
    assert view_model.core_facts.san_yuan.shen_gong == "庚午"
    assert view_model.core_facts.month_command is not None
    assert view_model.core_facts.month_command.main_qi == "戊"
    assert view_model.core_facts.tiaohou_markers is not None
    assert view_model.core_facts.branch_relations is not None
    assert view_model.core_facts.branch_relations[0].relation_type == "六合"
    assert view_model.core_facts.luck_cycles is not None
    assert view_model.core_facts.luck_cycles.status == "sequence_only"
    assert view_model.core_facts.calendar_normalization is not None
    assert (
        view_model.core_facts.calendar_normalization.true_solar_time.status
        == "apparent_solar_applied"
    )
    assert view_model.core_facts.calendar_normalization.time_basis.policy == (
        "local_apparent_solar-v1"
    )
    assert (
        view_model.core_facts.calendar_normalization.time_basis.longitude_correction_seconds
        == -169
    )
    assert (
        view_model.core_facts.calendar_normalization.time_basis.equation_of_time_seconds
        == 163
    )
    assert (
        view_model.core_facts.calendar_normalization.time_basis.boundary.within_uncertainty
        is False
    )
    assert (
        view_model.core_facts.calendar_normalization.calendar_convention.zi_hour_policy
        == "midnight"
    )
    assert view_model.core_facts.interpretive_candidates is not None
    assert view_model.core_facts.interpretive_candidates.strength.day_element == "earth"
    assert view_model.core_facts.interpretive_candidates.reasoning_tools is not None
    assert set(view_model.core_facts.interpretive_candidates.reasoning_tools) == {
        "strength_evidence",
        "month_structure_candidate",
    }
    assert [
        item.local_rule_id
        for item in view_model.core_facts.source_conditioned_patterns
    ] == ["QR-02-01"]
    assert (
        view_model.core_facts.source_conditioned_patterns[0].status
        == "predicate_matched_not_verdict"
    )
    evidence_by_ref = {item["ref"]: item for item in payload["evidence"]}
    assert view_model.core_facts.source_conditioned_patterns[0].evidence_ref is not None
    assert (
        view_model.core_facts.source_conditioned_patterns[0].evidence_ref
        in evidence_by_ref
    )
    assert all(
        pattern.evidence_ref in evidence_by_ref
        for pattern in view_model.core_facts.source_conditioned_patterns
        if pattern.evidence_ref is not None
    )
    assert "source_title" not in view_model.core_facts.source_conditioned_patterns[0].model_dump()
    assert "excerpt" not in view_model.core_facts.source_conditioned_patterns[0].model_dump()
    assert "1994-04-30" not in str(view_model.model_dump(mode="json"))


def test_bazi_source_pattern_does_not_invent_an_evidence_reference() -> None:
    payload = _brief().to_dict()
    payload["facts"] = [
        *payload["facts"],
        {
            "ref": "fact:profile-version:test/calculated/bazi/source_conditioned_patterns",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": [
                {
                    "rule_id": "bazi/missing-source#R-01",
                    "local_rule_id": "R-01",
                    "title": "无公开 evidence 的 Runtime 条件",
                    "source_pack": "bazi/missing-source",
                    "source_anchor": "rules.md#R-01",
                    "status": "predicate_matched_not_verdict",
                    "fact_paths": ["/chart_facts/output/day_master/stem"],
                    "predicate_audit": ["/day_master/stem:nonempty:()"],
                }
            ],
            "display_text": "Runtime 条件命中，未形成裁决。",
        },
    ]

    view_model = project_bazi_view_model(ReadingBrief.from_dict(payload))

    assert view_model is not None
    assert view_model.core_facts is not None
    pattern = view_model.core_facts.source_conditioned_patterns[0]
    assert pattern.evidence_ref is None
    assert "evidence_ref" not in pattern.model_dump()
