from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from app.charts.contracts import (
    CanwenViewV1,
    DaliurenChartV1,
    FengshuiViewV1,
    FiveElementsFactsViewV1,
    FortuneFactsViewV1,
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
    project_fortune_view_model,
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
from jsonschema import Draft202012Validator


def test_fortune_projector_preserves_runtime_facts_without_verdict() -> None:
    view_model = project_fortune_view_model(
        brief(
            "fortune",
            {
                "natal_pillars": {
                    "year": "甲戌",
                    "month": "戊辰",
                    "day": "丙戌",
                    "hour": "辛卯",
                },
                "day_master": {"stem": "丙", "element": "fire", "polarity": "阳"},
                "month_command": {
                    "branch": "辰",
                    "label": "辰月",
                    "main_qi": "戊",
                    "main_qi_element": "earth",
                },
                "active_luck_cycle": "乙丑",
                "target_day": "2026-08-14",
                "target_period": {
                    "kind": "day",
                    "start": "2026-08-14",
                    "end": "2026-08-14",
                },
                "available_periods": ["2026-08-14"],
                "period_markers": [
                    {
                        "date": "2026-08-14",
                        "day_pillar": "甲子",
                        "day_role": "日运",
                        "active_luck_cycle": "乙丑",
                        "primary_mechanism_ids": ["fortune.day_pillar"],
                        "decisive_mechanism_ids": [],
                        "relations": [],
                        "specific_event_policy": "事实标记，不推出具体事件",
                        "unresolved_boundaries": [],
                    }
                ],
                "calendar_normalization": {
                    "status": "calculated",
                    "algorithm_version": "fixture-v1",
                    "time_basis": {
                        "policy": "local_apparent_solar-v1",
                        "total_correction_seconds": 1182.0,
                        "algorithm": {},
                        "boundary": {"correction_changes_hour_branch": False},
                    },
                    "true_solar_time": {
                        "status": "apparent_solar_applied",
                        "policy": "local_apparent_solar-v1",
                        "total_correction_seconds": 1182.0,
                    },
                    "calendar_convention": {"hour_basis": "true_solar"},
                    "effective_datetime": "1994-04-30T05:54:54+08:00",
                    "day_boundary": {
                        "correction_crossed_date": False,
                        "zi_policy_advanced_day_pillar": False,
                    },
                    "changed_pillars": [],
                    "solar_terms": {
                        "previous": {
                            "name": "谷雨",
                            "index": 8,
                            "is_month_boundary_jie": False,
                            "datetime": "1994-04-20T15:36:00+08:00",
                            "instant_utc": "1994-04-20T07:36:00+00:00",
                        },
                        "next": {
                            "name": "立夏",
                            "index": 9,
                            "is_month_boundary_jie": True,
                            "datetime": "1994-05-06T01:54:05+08:00",
                            "instant_utc": "1994-05-05T17:54:05+00:00",
                        },
                        "month_switch_policy": "exact Jie instant",
                    },
                },
            },
        )
    )

    assert isinstance(view_model, FortuneFactsViewV1)
    assert view_model.schema_version == "fortune-facts-view/v1"
    assert view_model.natal_pillars["day"] == "丙戌"
    assert view_model.day_master.element == "fire"
    assert view_model.period_markers[0].primary_mechanism_ids == ("fortune.day_pillar",)
    assert view_model.period_markers[0].specific_event_policy == "事实标记，不推出具体事件"
    normalization = view_model.calendar_normalization
    assert normalization.effective_datetime == "1994-04-30T05:54:54+08:00"
    assert normalization.day_boundary is not None
    assert normalization.day_boundary.correction_crossed_date is False
    assert normalization.changed_pillars == ()
    assert normalization.solar_terms is not None
    assert normalization.solar_terms.previous is not None
    assert normalization.solar_terms.previous.name == "谷雨"
    assert normalization.solar_terms.next is not None
    assert normalization.solar_terms.next.is_month_boundary_jie is True
    assert normalization.solar_terms.month_switch_policy == "exact Jie instant"

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "schemas"
        / "views"
        / "fortune-facts-view-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    payload = view_model.model_dump(mode="json")
    validator = Draft202012Validator(schema)
    validator.validate(payload)
    payload["calendar_normalization"]["location"] = {"name": "private fixture"}
    assert not validator.is_valid(payload)


def test_fortune_projector_rejects_private_calendar_input_fields() -> None:
    values = {
        "natal_pillars": {
            "year": "甲戌",
            "month": "戊辰",
            "day": "丙戌",
            "hour": "辛卯",
        },
        "day_master": {"stem": "丙", "element": "fire", "polarity": "阳"},
        "month_command": {
            "branch": "辰",
            "label": "辰月",
            "main_qi": "戊",
            "main_qi_element": "earth",
        },
        "active_luck_cycle": "乙丑",
        "target_day": "2026-08-14",
        "target_period": {
            "kind": "day",
            "start": "2026-08-14",
            "end": "2026-08-14",
        },
        "available_periods": ["2026-08-14"],
        "period_markers": [
            {
                "date": "2026-08-14",
                "day_pillar": "甲子",
                "day_role": "日运",
                "active_luck_cycle": "乙丑",
                "primary_mechanism_ids": ["fortune.day_pillar"],
                "decisive_mechanism_ids": [],
                "relations": [],
                "specific_event_policy": "事实标记，不推出具体事件",
                "unresolved_boundaries": [],
            }
        ],
        "calendar_normalization": {
            "status": "calculated",
            "algorithm_version": "fixture-v1",
            "time_basis": {
                "policy": "local_apparent_solar-v1",
                "algorithm": {},
                "boundary": {},
            },
            "true_solar_time": {"status": "apparent_solar_applied"},
            "calendar_convention": {},
            "civil_datetime": "2000-01-01T00:00:00+08:00",
            "location": {"name": "private fixture"},
        },
    }

    assert project_fortune_view_model(brief("fortune", values)) is None


def test_fortune_projector_rejects_unknown_nested_calendar_fields() -> None:
    values = {
        "natal_pillars": {
            "year": "甲戌",
            "month": "戊辰",
            "day": "丙戌",
            "hour": "辛卯",
        },
        "day_master": {"stem": "丙", "element": "fire", "polarity": "阳"},
        "month_command": {
            "branch": "辰",
            "label": "辰月",
            "main_qi": "戊",
            "main_qi_element": "earth",
        },
        "active_luck_cycle": "乙丑",
        "target_day": "2026-08-14",
        "target_period": {
            "kind": "day",
            "start": "2026-08-14",
            "end": "2026-08-14",
        },
        "available_periods": ["2026-08-14"],
        "period_markers": [],
        "calendar_normalization": {
            "status": "calculated",
            "algorithm_version": "fixture-v1",
            "time_basis": {
                "policy": "local_apparent_solar-v1",
                "algorithm": {},
                "boundary": {},
            },
            "true_solar_time": {"status": "apparent_solar_applied"},
            "calendar_convention": {},
            "solar_terms": {
                "previous": None,
                "next": None,
                "month_switch_policy": "exact Jie instant",
                "raw_runtime_payload": {},
            },
        },
    }

    assert project_fortune_view_model(brief("fortune", values)) is None


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


def test_ziwei_projector_preserves_ordered_active_major_limit_segments() -> None:
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
    segments = [
        {
            "start_inclusive": "2025-01-01",
            "end_exclusive": "2025-01-29",
            "major_limit": {
                "index": 1,
                "palace_assignments": [{"temporal_palace": "福德"}],
                "star_facts": [{"name": "武曲", "brightness": "庙"}],
                "transformation_facts": [
                    {"star": "武曲", "transformation": "禄"}
                ],
            },
        },
        {
            "start_inclusive": "2025-01-29",
            "end_exclusive": "2026-01-01",
            "major_limit": {
                "index": 2,
                "palace_assignments": [{"temporal_palace": "田宅"}],
                "star_facts": [{"name": "太阳", "brightness": "旺"}],
                "transformation_facts": [
                    {"star": "太阳", "transformation": "禄"}
                ],
            },
        },
    ]

    view_model = project_ziwei_view_model(
        brief(
            "ziwei",
            {
                "palaces": palaces,
                "active_major_limit": segments[0]["major_limit"],
                "active_major_limit_segments": segments,
            },
        )
    )

    assert isinstance(view_model, ZiweiChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.active_major_limit_segments is not None
    serialized = view_model.model_dump(mode="json")["core_facts"]
    assert serialized["active_major_limit_segments"] == segments
    round_trip = ZiweiChartV1.model_validate(view_model.model_dump(mode="json"))
    assert round_trip.model_dump(mode="json")["core_facts"] == serialized


def test_ziwei_projector_preserves_calendar_coverage_across_segment_boundary() -> None:
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
    segments = [
        {
            "start_inclusive": "2025-01-01",
            "end_exclusive": "2025-01-29",
            "major_limit": {"index": 1},
        },
        {
            "start_inclusive": "2025-01-29",
            "end_exclusive": "2025-02-01",
            "major_limit": {"index": 2},
        },
    ]
    runtime_calendar_coverage = {
        "start_inclusive": "2025-01-01",
        "end_exclusive": "2025-02-01",
        "requested_target_date": "2025-01-29",
        "status": "exact_daily_boundary_detection",
        "horoscope_divide": "normal/lunar-new-year",
        "age_divide": "normal/nominal-age",
    }
    expected_calendar_coverage = {
        key: runtime_calendar_coverage[key]
        for key in ("start_inclusive", "end_exclusive", "requested_target_date")
    }

    view_model = project_ziwei_view_model(
        brief(
            "ziwei",
            {
                "palaces": palaces,
                "active_major_limit": segments[0]["major_limit"],
                "active_major_limit_segments": segments,
                "calendar_coverage": runtime_calendar_coverage,
            },
        )
    )

    assert isinstance(view_model, ZiweiChartV1)
    assert view_model.core_facts is not None
    serialized = view_model.model_dump(mode="json")["core_facts"]
    assert serialized["calendar_coverage"] == expected_calendar_coverage
    round_trip = ZiweiChartV1.model_validate_json(view_model.model_dump_json())
    assert round_trip.model_dump(mode="json")["core_facts"] == serialized


def test_ziwei_projector_omits_calendar_coverage_when_runtime_fact_is_absent() -> None:
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
        brief("ziwei", {"palaces": palaces, "active_major_limit": {"index": 1}})
    )

    assert isinstance(view_model, ZiweiChartV1)
    assert view_model.core_facts is not None
    serialized = view_model.model_dump(mode="json")["core_facts"]
    assert "calendar_coverage" not in serialized
    round_trip = ZiweiChartV1.model_validate_json(view_model.model_dump_json())
    assert "calendar_coverage" not in round_trip.model_dump(mode="json")["core_facts"]


@pytest.mark.parametrize(
    "calendar_coverage",
    [
        None,
        "not-an-object",
        {},
        {
            "end_exclusive": "2025-02-01",
            "requested_target_date": "2025-01-29",
        },
        {
            "start_inclusive": "2025-01-01",
            "requested_target_date": "2025-01-29",
        },
        {
            "start_inclusive": "2025-01-01",
            "end_exclusive": "2025-02-01",
        },
        {
            "start_inclusive": "2025-02-30",
            "end_exclusive": "2025-03-01",
            "requested_target_date": "2025-02-28",
        },
        {
            "start_inclusive": "2025-01-01",
            "end_exclusive": "2025-02-01",
            "requested_target_date": "2025-02-30",
        },
        {
            "start_inclusive": "20250101",
            "end_exclusive": "2025-02-01",
            "requested_target_date": "2025-01-29",
        },
        {
            "start_inclusive": "2025-02-01",
            "end_exclusive": "2025-02-01",
            "requested_target_date": "2025-02-01",
        },
        {
            "start_inclusive": "2025-02-02",
            "end_exclusive": "2025-02-01",
            "requested_target_date": "2025-02-01",
        },
        {
            "start_inclusive": "2025-01-02",
            "end_exclusive": "2025-02-01",
            "requested_target_date": "2025-01-01",
        },
        {
            "start_inclusive": "2025-01-01",
            "end_exclusive": "2025-02-01",
            "requested_target_date": "2025-02-01",
        },
    ],
    ids=(
        "null",
        "non-object",
        "missing-all-fields",
        "missing-start",
        "missing-end",
        "missing-target",
        "invalid-start",
        "invalid-target",
        "non-canonical-start",
        "empty-range",
        "reverse-range",
        "target-before-start",
        "target-at-exclusive-end",
    ),
)
def test_ziwei_projector_rejects_invalid_calendar_coverage(
    calendar_coverage: object,
) -> None:
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
                "active_major_limit": {"index": 1},
                "calendar_coverage": calendar_coverage,
            },
        )
    )

    assert isinstance(view_model, ZiweiChartV1)
    assert view_model.core_facts is None


def test_ziwei_projector_omits_segments_only_when_runtime_fact_is_absent() -> None:
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
                "active_major_limit": {"index": 1},
            },
        )
    )

    assert isinstance(view_model, ZiweiChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.active_major_limit == {"index": 1}
    serialized = view_model.model_dump(mode="json")["core_facts"]
    assert "active_major_limit_segments" not in serialized
    round_trip = ZiweiChartV1.model_validate(view_model.model_dump(mode="json"))
    assert "active_major_limit_segments" not in round_trip.model_dump(mode="json")[
        "core_facts"
    ]


@pytest.mark.parametrize(
    "segments",
    [
        None,
        [],
        [{}],
        [
            {
                "end_exclusive": "2025-01-29",
                "major_limit": {"index": 1},
            }
        ],
        [
            {
                "start_inclusive": "2025-01-01",
                "major_limit": {"index": 1},
            }
        ],
        [
            {
                "start_inclusive": "2025-01-29",
                "end_exclusive": "2025-01-29",
                "major_limit": {"index": 1},
            }
        ],
        [
            {
                "start_inclusive": "2025-01-30",
                "end_exclusive": "2025-01-29",
                "major_limit": {"index": 1},
            }
        ],
        [
            {
                "start_inclusive": "2025-02-30",
                "end_exclusive": "2025-03-01",
                "major_limit": {"index": 1},
            }
        ],
        [
            {
                "start_inclusive": "2025-01-01",
                "end_exclusive": "2025-01-29",
            }
        ],
        [
            {
                "start_inclusive": "2025-01-01",
                "end_exclusive": "2025-01-29",
                "major_limit": {},
            }
        ],
    ],
    ids=(
        "null-list",
        "empty-list",
        "empty-segment",
        "missing-start",
        "missing-end",
        "empty-range",
        "reverse-range",
        "invalid-date",
        "missing-major-limit",
        "empty-major-limit",
    ),
)
def test_ziwei_projector_rejects_invalid_active_major_limit_segments(
    segments: object,
) -> None:
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
                "active_major_limit": {"index": 1},
                "active_major_limit_segments": segments,
            },
        )
    )

    assert isinstance(view_model, ZiweiChartV1)
    assert view_model.core_facts is None


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
            "point_kind": "observed_ephemeris_body",
            "observed_body": True,
            "source_dependency_id": "xingming.ephemeris.seven-luminaries",
            "trace": {"engine": "astronomy-engine"},
        },
        {
            "body": "紫炁",
            "classical_name": "紫炁",
            "longitude_degrees": 284.58,
            "degree_in_zodiac_sign": 14.58,
            "house": "命宫",
            "house_sequence": 1,
            "degree_in_house": 4.58,
            "motion_state": "direct",
            "fact_status": "calculated_not_interpreted",
            "point_kind": "classical_mean_pseudo_point",
            "observed_body": False,
            "source_dependency_id": "xingming.four-residuals.numeric-profiles",
            "trace": {
                "profile": "xingxue-dated-mean-ziqi-v1",
                "calibration_path": "references/matrices/xingming-ziqi-calibration-v1.yaml",
            },
        },
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
                "ephemeris": {
                    "schema_version": "mingli-ephemeris-v1",
                    "instant_utc": "2000-01-01T00:00:00+00:00",
                    "observer": {
                        "longitude": 120.2,
                        "latitude": 25.0,
                        "coordinate_source": "private-fixture",
                    },
                    "engine": {
                        "name": "astronomy-engine",
                        "version": "2.1.19",
                        "license": "MIT",
                    },
                    "coordinate_convention": {
                        "frame": "geocentric_true_ecliptic_of_date",
                        "zodiac": "tropical",
                        "aberration": True,
                        "precession": "equinox_of_date_by_astronomy_engine",
                    },
                },
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
    assert view_model.core_facts.classical_bodies[0].point_kind == "observed_ephemeris_body"
    assert view_model.core_facts.classical_bodies[0].observed_body is True
    assert view_model.core_facts.classical_bodies[0].source_dependency_id == (
        "xingming.ephemeris.seven-luminaries"
    )
    assert view_model.core_facts.classical_bodies[0].trace == {"engine": "astronomy-engine"}
    assert view_model.core_facts.classical_bodies[1].classical_name == "紫炁"
    assert view_model.core_facts.classical_bodies[1].point_kind == "classical_mean_pseudo_point"
    assert view_model.core_facts.classical_bodies[1].observed_body is False
    assert view_model.core_facts.classical_bodies[1].trace is not None
    assert view_model.core_facts.classical_bodies[1].trace["profile"] == (
        "xingxue-dated-mean-ziqi-v1"
    )
    assert view_model.core_facts.ming_shen is not None
    assert view_model.core_facts.ming_shen.separation_degrees == 180.0
    assert "longitude_degrees" not in view_model.core_facts.ming_shen.model_dump()
    assert view_model.core_facts.ephemeris is not None
    assert "instant_utc" not in view_model.core_facts.ephemeris.model_dump()
    assert "observer" not in view_model.core_facts.ephemeris.model_dump()
    assert view_model.core_facts.major_limits is not None
    assert view_model.core_facts.major_limits[0].age_end_years == 15.0
    assert view_model.core_facts.transformations is not None
    assert view_model.core_facts.transformations[0].classical_body == "火星"

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "schemas"
        / "views"
        / "qizheng-chart-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


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
        "useful_spirit_selection": {
            "status": "evidence_bound",
            "reason": "school-dependent adjudication is outside deterministic calculation",
            "query_word_matching": False,
            "source_dependency_id": (
                "liuyao.relations.returning-and-useful-spirit-candidates"
            ),
            "chain_candidates": {"status": "candidate_only"},
            "strength_evidence": {
                "status": "candidate_only",
                "by_relative": {
                    "妻财": {
                        "status": "candidate_only",
                        "candidates": [
                            {
                                "source": "visible_line",
                                "line": 1,
                                "moving": True,
                                "xunkong": False,
                                "najia": {"element": "水"},
                                "month_day_strength": {"seasonal_state": "旺"},
                                "seasonal_adjudication": {
                                    "status": (
                                        "adjudicated_seasonal_strength_band"
                                    ),
                                    "decision_scope": (
                                        "liuyao_candidate_month_order_strength_band"
                                    ),
                                    "candidate_source": "visible_line",
                                    "line": 1,
                                    "line_element": "水",
                                    "month_element": "水",
                                    "seasonal_state": "旺",
                                    "strength_band": "旺相",
                                    "whole_candidate_strength_verdict": None,
                                    "outcome_verdict": None,
                                    "source_ref": {
                                        "pack": "divination/zengshan-buyi",
                                        "rule_id": "ZR-05-05",
                                        "source_anchor": (
                                            "references/books/divination/"
                                            "zengshan-buyi/rules.md#ZR-05-05"
                                        ),
                                        "verification_status": "verified",
                                        "binding_digest": "strength-binding-digest",
                                    },
                                    "unresolved_checks": ["日辰与空破动变"],
                                },
                                "signals": [
                                    {
                                        "signal": "seasonal_support",
                                        "value": "旺",
                                        "status": "candidate_signal",
                                    },
                                    {
                                        "signal": "moving_line",
                                        "value": True,
                                        "status": "candidate_signal",
                                    },
                                ],
                                "status": "candidate_only",
                                "hard_verdict": None,
                            }
                        ],
                        "hard_verdict": None,
                    }
                },
                "source_rules": [
                    {
                        "pack": "divination/zengshan-buyi",
                        "rule_id": "ZR-05-05",
                        "source_anchor": (
                            "references/books/divination/zengshan-buyi/"
                            "rules.md#ZR-05-05"
                        ),
                        "verification_status": "verified",
                        "binding_digest": "strength-binding-digest",
                        "role": "useful_spirit_month_order_strength_band",
                    }
                ],
                "fact_status": "calculated_relation_not_verdict",
                "hard_verdict": None,
                "requires_school_adjudication": True,
                "source_dependency_id": (
                    "liuyao.interpretation.useful-spirit-strength-evidence"
                ),
            },
            "role_adjudication": {
                "status": "adjudicated_question_role_set",
                "decision_scope": "finance_useful_spirit_role_set",
                "question_class": "finance",
                "primary_relative": "妻财",
                "supporting_relatives": ["子孙"],
                "obstacle_attention_relatives": ["兄弟", "官鬼", "父母"],
                "specific_line_selection": 1,
                "specific_line_adjudication": {
                    "status": "adjudicated_unique_visible_line",
                    "decision_scope": "finance_primary_relative_line_identity",
                    "primary_relative": "妻财",
                    "visible_candidate_count": 1,
                    "visible_candidate_lines": [1],
                    "moving_visible_candidate_count": 1,
                    "moving_visible_candidate_lines": [1],
                    "specific_line_selection": 1,
                    "derivation_basis": (
                        "verified_role_plus_runtime_unique_visible_candidate"
                    ),
                    "selection_source_ref": {
                        "pack": "divination/huangjin-ce",
                        "rule_id": "HJC-R009",
                        "source_anchor": (
                            "references/books/divination/huangjin-ce/"
                            "rules.md#HJC-R009"
                        ),
                        "verification_status": "verified",
                        "binding_digest": "test-binding-digest",
                    },
                    "hard_verdict": None,
                },
                "hard_verdict": None,
                "source_ref": {
                    "pack": "divination/huangjin-ce",
                    "rule_id": "HJC-R009",
                    "source_anchor": (
                        "references/books/divination/huangjin-ce/"
                        "rules.md#HJC-R009"
                    ),
                    "verification_status": "verified",
                    "binding_digest": "test-binding-digest",
                },
                "unresolved_checks": ["月日旺衰与空破冲合"],
            },
            "question_context": {
                "question_class": "finance",
                "classification_source": "explicit_structured_input",
            },
        },
        "xunkong": {"day_ganzhi": "甲子", "void_branches": ["戌", "亥"]},
        "source_conditioned_patterns": [
            {
                "rule_id": "divination/huozhu-lin#HZL-M001",
                "local_rule_id": "HZL-M001",
                "title": "HZL-M001 先看世应",
                "source_pack": "divination/huozhu-lin",
                "source_anchor": "divination/huozhu-lin rules.md#L5-L22",
                "status": "predicate_matched_not_verdict",
                "fact_paths": ["/chart_facts/output/shi_ying"],
                "predicate_audit": ["/shi_ying:exists:None"],
            }
        ],
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
    assert view_model.core_facts.useful_spirit_selection is not None
    assert (
        view_model.core_facts.useful_spirit_selection.role_adjudication
        .specific_line_adjudication.specific_line_selection
        == 1
    )
    assert [
        pattern.local_rule_id
        for pattern in view_model.core_facts.source_conditioned_patterns
    ] == ["HZL-M001"]
    assert view_model.core_facts.source_conditioned_patterns[0].status == (
        "predicate_matched_not_verdict"
    )
    schema = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "contracts/schemas/views/liuyao-chart-v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


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
        "interpretive_candidates": {
            "schema_version": "mingli-meihua-interpretive-candidates-v1",
            "status": "source_adjudicated_relations",
            "hard_verdict": None,
            "verification_status": "verified",
            "relation_candidates": [
                {
                    "candidate_id": "meihua.primary_use.upper.same_element",
                    "source_plate": "primary_use",
                    "position": "upper",
                    "relation": "比和",
                    "relation_key": "same_element",
                    "actor": {
                        "position": "upper",
                        "trigram": "巽",
                        "element": "木",
                    },
                    "body": {
                        "position": "upper",
                        "trigram": "巽",
                        "element": "木",
                    },
                    "seasonal_state": "旺",
                    "rule_id": "MR-04-02",
                    "status": "relation_adjudicated_not_event_verdict",
                    "hard_verdict": None,
                    "verification_status": "verified",
                    "source_pack": "divination/meihua-yishu",
                    "source_anchor": "references/books/divination/meihua-yishu/rules.md#MR-04-02",
                    "source_dependency_id": "meihua.classical-adjudication.body-use-candidates",
                    "relation_adjudication": {
                        "status": "adjudicated_relation_polarity",
                        "decision_scope": "meihua_body_use_relation",
                        "relation_key": "same_element",
                        "source_polarity": "harmonious",
                        "hard_verdict": None,
                        "event_verdict": None,
                        "source_refs": [
                            {
                                "pack": "divination/meihua-yishu",
                                "rule_id": "MR-04-02",
                                "source_anchor": (
                                    "references/fulltext/divination/"
                                    "meihua-yishu/fulltext.md#L875"
                                ),
                                "verification_status": "verified",
                                "binding_digest": (
                                    "202662eb4c023883aab61febf3de3d7d"
                                    "42137740f31d50ba1a7ada25149db50f"
                                ),
                            }
                        ],
                        "unresolved_checks": [
                            "具体问题中的体用取义、领域例外与外应",
                            "本卦、互卦、变卦关系的并见权重及月令旺衰",
                            "现实事件成败、吉凶程度与应期",
                        ],
                    },
                }
            ],
            "requires_classical_adjudication": False,
            "requires_synthesis_adjudication": True,
            "boundary": "关系极性已裁定，综合事件结论仍待裁决",
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
    assert view_model.core_facts.interpretive_candidates is not None
    assert (
        view_model.core_facts.interpretive_candidates.relation_candidates[0].rule_id
        == "MR-04-02"
    )
    relation_adjudication = (
        view_model.core_facts.interpretive_candidates.relation_candidates[
            0
        ].relation_adjudication
    )
    assert relation_adjudication.source_polarity == "harmonious"
    assert relation_adjudication.event_verdict is None
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "schemas"
        / "views"
        / "meihua-chart-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


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
                "source_conditioned_patterns": [
                    {
                        "rule_id": "luming-nayin/li-xuzhong-mingshu#LX-01-17",
                        "local_rule_id": "LX-01-17",
                        "title": "庚辰（禄暗会）",
                        "source_pack": "luming-nayin/li-xuzhong-mingshu",
                        "source_anchor": "fulltext.md#L32",
                        "status": "predicate_matched_not_verdict",
                        "fact_paths": [
                            "fact:/chart_facts/output/four_pillars/year"
                        ],
                        "predicate_audit": ["/four_pillars/year:eq:庚辰"],
                        "applicability_adjudication": {
                            "status": "adjudicated_rule_applicability",
                            "decision_scope": (
                                "luming_nayin_source_rule_applicability"
                            ),
                            "rule_id": (
                                "luming-nayin/li-xuzhong-mingshu#LX-01-17"
                            ),
                            "local_rule_id": "LX-01-17",
                            "rule_title": "庚辰（禄暗会）",
                            "evidence_role": "issue_specific_judgment_rule",
                            "hard_verdict": None,
                            "life_verdict": None,
                            "source_ref": {
                                "pack": "luming-nayin/li-xuzhong-mingshu",
                                "rule_id": "LX-01-17",
                                "source_anchor": (
                                    "references/books/luming-nayin/"
                                    "li-xuzhong-mingshu/rules.md#LX-01-17"
                                ),
                                "verification_status": "verified",
                                "binding_digest": "1" * 64,
                            },
                            "unresolved_checks": ["多条规则并见尚未权衡"],
                        },
                    }
                ],
            },
        )
    )

    assert isinstance(view_model, LumingNayinChartV1)
    assert view_model.pillars[0].nayin == "山头火"
    assert view_model.relations[0].category == "lu"
    assert view_model.taiyuan == {"ganzhi": "己巳"}
    assert view_model.source_conditioned_patterns[0].local_rule_id == "LX-01-17"
    adjudication = view_model.source_conditioned_patterns[
        0
    ].applicability_adjudication
    assert adjudication.status == "adjudicated_rule_applicability"
    assert adjudication.life_verdict is None
    assert adjudication.source_ref.verification_status == "verified"
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "schemas"
        / "views"
        / "luming-nayin-chart-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


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
                        "identity_adjudication": {
                            "status": "adjudicated_pattern_identity",
                            "decision_scope": "taiyi_board_pattern_identity",
                            "pattern_id": "TY-P01",
                            "pattern_name": "掩",
                            "hard_verdict": None,
                            "event_verdict": None,
                            "source_ref": {
                                "pack": "san-shi/taiyi-shenshu",
                                "rule_id": "TY-P01",
                                "source_anchor": (
                                    "references/books/san-shi/taiyi-shenshu/"
                                    "rules.md#TY-P01"
                                ),
                                "verification_status": "verified",
                                "binding_digest": "a" * 64,
                            },
                            "unresolved_checks": [
                                "并见格局、制化与主客关系",
                                "宏观事项范围及盘面取用",
                                "现实成败、吉凶与应期",
                            ],
                        },
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
    adjudication = view_model.board_predicates[0].identity_adjudication
    assert adjudication.status == "adjudicated_pattern_identity"
    assert adjudication.source_ref.rule_id == "TY-P01"
    assert adjudication.hard_verdict is None
    assert adjudication.event_verdict is None
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "schemas"
        / "views"
        / "taiyi-chart-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


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
                "eligible_date_time_candidates": [
                    {"candidate_time_id": "2026-09-03:寅:synthetic"}
                ],
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
                "basis_projection": {
                    "candidate_limit_per_list": 12,
                    "complete_counts": {"source_conditioned_patterns": 1},
                    "full_facts_remain_in_calculation_record": True,
                },
                "source_conditioned_patterns": [
                    {
                        "rule_id": "selection/xingli-kaoyuan#KR-05",
                        "local_rule_id": "KR-05",
                        "title": "五虎遁与五鼠遁",
                        "source_pack": "selection/xingli-kaoyuan",
                        "source_anchor": "rules.md#L42-L49",
                        "status": "predicate_matched_not_verdict",
                        "fact_paths": ["fact:selection:fixture/calendar/ganzhi/year"],
                        "predicate_audit": ["/calendar/ganzhi/year:nonempty"],
                    }
                ],
            },
        )
    )

    assert isinstance(view_model, SelectionChartV1)
    assert view_model.eligible_candidates[0].civil_date == "2026-09-03"
    assert view_model.ranking.opaque_numeric_score is False
    assert [item.local_rule_id for item in view_model.source_conditioned_patterns] == [
        "KR-05"
    ]
    assert view_model.basis_projection["complete_counts"] == {
        "source_conditioned_patterns": 1
    }


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
                "source_conditioned_patterns": [
                    {
                        "rule_id": "fengshui/yangzhai-shishu#YZS-R007",
                        "local_rule_id": "YZS-R007",
                        "title": "宅门起例",
                        "source_pack": "fengshui/yangzhai-shishu",
                        "source_anchor": "rules.md#YZS-R007",
                        "status": "predicate_matched_not_verdict",
                        "fact_paths": [
                            "/chart_facts/output/active_source_rule_ids/0"
                        ],
                        "predicate_audit": [
                            "/active_source_rule_ids:descendant_eq:fengshui/yangzhai-shishu#YZS-R007"
                        ],
                    }
                ],
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
            "stars": (
                []
                if index == 5
                else ["天辅", "天禽"]
                if index == 1
                else ["天辅"]
            ),
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
                "named_patterns": [
                    {
                        "id": "QM-P13",
                        "name": "五不遇时",
                        "status": "predicate_matched_not_verdict",
                        "identity_adjudication": {
                            "status": "adjudicated_pattern_identity",
                            "decision_scope": "qimen_named_pattern_identity",
                            "pattern_id": "QM-P13",
                            "pattern_name": "五不遇时",
                            "palace": None,
                            "hard_verdict": None,
                            "event_verdict": None,
                            "source_ref": {
                                "pack": "san-shi/qimen-dunjia-tongzhi",
                                "rule_id": "QM-P13",
                                "source_anchor": (
                                    "references/books/san-shi/"
                                    "qimen-dunjia-tongzhi/rules.md#QM-P13"
                                ),
                                "verification_status": "verified",
                                "binding_digest": (
                                    "addc36958a2efaf63b6ceac219a8afe49ea4b26e5bcb5d32e404c35d59d70302"
                                ),
                            },
                            "unresolved_checks": [
                                "格局强弱、制化与并见关系",
                                "事项用神及宫位关系",
                                "事件成败、吉凶与应期",
                            ],
                        },
                    }
                ],
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
    assert view_model.palaces[0].stars == ("天辅", "天禽")
    assert view_model.chief.star == "天蓬"
    assert view_model.xunkong.palaces == (6, 7)
    assert view_model.named_patterns[0].palace is None
    assert view_model.named_patterns[0].identity_adjudication.status == (
        "adjudicated_pattern_identity"
    )
    assert view_model.named_patterns[0].identity_adjudication.event_verdict is None

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "schemas"
        / "views"
        / "qimen-chart-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


def test_daliuren_projector_maps_lessons_and_three_transmissions() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "liuren-runtime-core-facts-v1.json"
    )
    runtime_core_facts = json.loads(fixture_path.read_text(encoding="utf-8"))
    values = {"runtime_core_facts": runtime_core_facts}

    view_model = project_daliuren_view_model(brief("liuren", values))

    assert isinstance(view_model, DaliurenChartV1)
    assert [item.lesson_id for item in view_model.lessons] == ["1", "2", "3", "4"]
    assert [item.general for item in view_model.transmissions] == ["勾陈", "天后", "青龙"]
    assert view_model.core_facts is not None
    assert view_model.core_facts.day_hour is not None
    assert view_model.core_facts.day_hour.day == "乙酉"
    assert view_model.core_facts.structural_patterns == ("伏吟", "四课不备")
    assert view_model.core_facts.timing_candidates is not None
    assert view_model.core_facts.timing_candidates[0].solar_date == "2026-07-20"
    assert view_model.core_facts.timing_candidates[0].source_rule == "LM-R21"
    assert view_model.core_facts.timing_candidates[0].candidate_not_guarantee is True
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "schemas"
        / "views"
        / "daliuren-chart-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(view_model.model_dump(mode="json"))


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
            ],
            "missing_targets": [
                {
                    "region": "jaw",
                    "feature_kind": "visible_morphology",
                    "required": True,
                    "reason": "no_supplied_observation",
                }
            ],
            "uncertainties": [
                {
                    "region": "forehead",
                    "feature_kind": "visible_morphology",
                    "reason_codes": ["uncertainty_above_threshold"],
                }
            ],
            "observation_conflicts": [
                {
                    "region": "forehead",
                    "feature_kind": "visible_morphology",
                    "capture_scope": "caller_text_scoped",
                    "observation_count": 2,
                    "blocking": False,
                    "resolved": False,
                }
            ],
            "cross_capture_variations": [
                {
                    "region": "forehead",
                    "feature_kind": "visible_morphology",
                    "capture_count": 2,
                    "descriptor_count": 2,
                    "auto_equivalent": False,
                }
            ],
            "source_comparison": {
                "sources": [
                    {"title": "《麻衣神相》", "edition_caveat": "版本异文保留"}
                ],
                "disagreements_retained": True,
                "disagreements": [
                    {"sources": ["《麻衣神相》", "《神相全编》"], "summary": "术语不一致"}
                ],
                "forced_resolution": False,
            },
            "active_source_rule_ids": ["physiognomy/mayi-shenxiang#face.forehead"],
            "source_conditioned_patterns": [
                {
                    "rule_id": "physiognomy/liuzhuang-xiangfa#LZ-R01",
                    "local_rule_id": "LZ-R01",
                    "title": "额部可见观察条件",
                    "source_pack": "physiognomy/liuzhuang-xiangfa",
                    "source_anchor": "rules.md#L3-L6",
                    "status": "predicate_matched_not_verdict",
                    "fact_paths": ["fact:/chart_facts/fact_layer_status"],
                    "predicate_audit": [
                        "/fact_layer_status:eq:observation_driven_physiognomy_facts"
                    ],
                }
            ],
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
    assert view_model.missing_targets[0]["region"] == "jaw"
    assert view_model.uncertainties[0]["reason_codes"] == ["uncertainty_above_threshold"]
    assert view_model.conflicts[0]["blocking"] is False
    assert view_model.source_comparison.disagreements_retained is True
    assert view_model.source_comparison.disagreements[0]["summary"] == "术语不一致"
    assert view_model.active_source_rule_ids == ("physiognomy/mayi-shenxiang#face.forehead",)
    assert view_model.source_conditioned_patterns[0].local_rule_id == "LZ-R01"
    assert view_model.source_conditioned_patterns[0].status == "predicate_matched_not_verdict"


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


def test_canwen_projector_exposes_candidate_and_source_pattern_evidence() -> None:
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
                "ref": "fact:profile/calculated/bazi/interpretive_candidates",
                "subject_ref": "profile:fixture",
                "kind_id": "kind.fact",
                "value": {
                    "strength": {"status": "candidate_only"},
                    "structure": {"status": "candidate_only"},
                    "hard_verdict": None,
                },
                "display_text": "interpretive_candidates",
            },
            {
                "ref": "fact:profile/calculated/bazi/source_conditioned_patterns",
                "subject_ref": "profile:fixture",
                "kind_id": "kind.fact",
                "value": [
                    {
                        "local_rule_id": "DR-01-01",
                        "title": "八字来源谓词",
                        "status": "predicate_matched_not_verdict",
                    }
                ],
                "display_text": "source_conditioned_patterns",
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
                "ref": "fact:profile/calculated/ziwei/source_conditioned_patterns",
                "subject_ref": "profile:fixture",
                "kind_id": "kind.fact",
                "value": [
                    {
                        "local_rule_id": "ZW-M01",
                        "title": "紫微来源谓词",
                        "status": "predicate_matched_not_verdict",
                    }
                ],
                "display_text": "source_conditioned_patterns",
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
            {
                "ref": "fact:profile/calculated/xingming/source_conditioned_patterns",
                "subject_ref": "profile:fixture",
                "kind_id": "kind.fact",
                "value": [
                    {
                        "rule_id": "XR-M01",
                        "name": "星命来源谓词",
                        "status": "predicate_matched_not_verdict",
                    }
                ],
                "display_text": "source_conditioned_patterns",
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
    signal_ids = {signal.signal_id for signal in dimension.signals}
    assert {
        "bazi.dimension_scope",
        "bazi.career.candidate_scope.strength",
        "bazi.career.candidate_scope.structure",
        "bazi.career.source_pattern.DR-01-01",
        "ziwei.dimension_scope",
        "ziwei.career.source_pattern.ZW-M01",
        "qizheng.dimension_scope",
        "qizheng.career.source_pattern.XR-M01",
    } <= signal_ids
    evidence_signals = tuple(
        signal
        for signal in dimension.signals
        if "candidate_scope" in signal.signal_id
        or "source_pattern" in signal.signal_id
    )
    assert evidence_signals
    assert all("不形成跨术结论" in signal.display_text for signal in evidence_signals)
    assert all(signal.fact_refs for signal in evidence_signals)
    assert dimension.missing_art_ids == ()
    assert dimension.disagreements == ()
    assert dimension.convergence == (
        "所选术数的计算事实范围均已提供；尚未形成实质性互证结论。",
    )


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
                "value": {
                    "outcome": {
                        "scope": "fixture",
                        "rule_evidence": {
                            "status": "matched_evidence",
                            "hard_verdict": None,
                            "requires_school_adjudication": True,
                            "matched": [
                                {
                                    "rule_key": "subject_object_relation",
                                    "rule_id": "LR-17",
                                    "status": "matched",
                                    "source_refs": [
                                        {
                                            "pack": "san-shi/liuren-zhiyin",
                                            "rule_id": "LR-17",
                                            "quote_id": "LZ-Q054",
                                        }
                                    ],
                                    "fact_paths": [
                                        "dimension_facts.outcome.subject_object_relation"
                                    ],
                                }
                            ],
                        },
                    }
                },
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
        "daliuren",
    ]
    assert view_model.dimensions[0].signals[-1].signal_id == (
        "daliuren.outcome.rule_evidence.subject_object_relation"
    )
    assert view_model.dimensions[0].signals[-1].fact_refs == (
        "fact:wenshi:synthetic/calculated/liuren/dimension_facts",
    )
    assert view_model.dimensions[0].convergence == ()
    assert view_model.dimensions[0].disagreements == ()
    assert view_model.dimensions[1].missing_art_ids == ("daliuren",)
    assert project_runtime_view_model(payload) == view_model


def test_wenshi_projector_exposes_liuyao_candidates_and_qimen_predicates() -> None:
    payload = {
        "question": "验证六爻候选和奇门来源谓词是否进入合参信号",
        "facts": [
            {
                "ref": "fact:wenshi:evidence/calculated/liuyao/relation_facts",
                "subject_ref": "wenshi:evidence",
                "kind_id": "kind.liuyao-structure",
                "value": [],
                "display_text": "relation_facts",
            },
            {
                "ref": "fact:wenshi:evidence/calculated/liuyao/source_conditioned_patterns",
                "subject_ref": "wenshi:evidence",
                "kind_id": "kind.liuyao-patterns",
                "value": [
                    {
                        "local_rule_id": "HJC-M001",
                        "title": "六爻来源谓词",
                        "status": "predicate_matched_not_verdict",
                    }
                ],
                "display_text": "source_conditioned_patterns",
            },
            {
                "ref": "fact:wenshi:evidence/calculated/liuyao/useful_spirit_candidates",
                "subject_ref": "wenshi:evidence",
                "kind_id": "kind.liuyao-candidates",
                "value": {
                    "兄弟": [{"line": 1}],
                    "官鬼": [{"line": 2}, {"line": 5}],
                    "妻财": [],
                },
                "display_text": "useful_spirit_candidates",
            },
            {
                "ref": "fact:wenshi:evidence/calculated/liuyao/useful_spirit_selection",
                "subject_ref": "wenshi:evidence",
                "kind_id": "kind.liuyao-selection",
                "value": {
                    "status": "evidence_bound",
                    "hard_verdict": None,
                    "source_dependency_id": (
                        "liuyao.relations.returning-and-useful-spirit-candidates"
                    ),
                    "chain_candidates": {
                        "status": "candidate_only",
                        "chains": [{"candidates": ["用神", "原神"]}],
                    },
                    "strength_evidence": {
                        "status": "candidate_only",
                        "by_relative": {"官鬼": []},
                    },
                    "role_adjudication": {
                        "status": "adjudicated_question_role_set",
                        "decision_scope": "finance_useful_spirit_role_set",
                        "question_class": "finance",
                        "primary_relative": "妻财",
                        "supporting_relatives": ["子孙"],
                        "obstacle_attention_relatives": ["兄弟", "官鬼", "父母"],
                        "specific_line_selection": 4,
                        "specific_line_adjudication": {
                            "status": "adjudicated_unique_visible_line",
                            "decision_scope": (
                                "finance_primary_relative_line_identity"
                            ),
                            "primary_relative": "妻财",
                            "visible_candidate_count": 1,
                            "visible_candidate_lines": [4],
                            "moving_visible_candidate_count": 1,
                            "moving_visible_candidate_lines": [4],
                            "specific_line_selection": 4,
                            "derivation_basis": (
                                "verified_role_plus_runtime_unique_visible_candidate"
                            ),
                            "selection_source_ref": {
                                "pack": "divination/huangjin-ce",
                                "rule_id": "HJC-R009",
                                "verification_status": "verified",
                            },
                            "hard_verdict": None,
                        },
                        "hard_verdict": None,
                        "source_ref": {
                            "pack": "divination/huangjin-ce",
                            "rule_id": "HJC-R009",
                            "verification_status": "verified",
                        },
                    },
                },
                "display_text": "useful_spirit_selection",
            },
            {
                "ref": "fact:wenshi:evidence/calculated/qimen/calculated_board_scope",
                "subject_ref": "wenshi:evidence",
                "kind_id": "kind.qimen-structure",
                "value": {"scope": "fixture"},
                "display_text": "calculated_board_scope",
            },
            {
                "ref": "fact:wenshi:evidence/calculated/qimen/named_patterns",
                "subject_ref": "wenshi:evidence",
                "kind_id": "kind.qimen-patterns",
                "value": [
                    {
                        "id": "QM-P16",
                        "name": "三奇入墓",
                        "status": "predicate_matched_not_verdict",
                        "palace": 3,
                        "identity_adjudication": {
                            "status": "adjudicated_pattern_identity",
                            "decision_scope": "qimen_named_pattern_identity",
                            "pattern_id": "QM-P16",
                            "pattern_name": "三奇入墓",
                            "palace": 3,
                            "hard_verdict": None,
                            "event_verdict": None,
                            "source_ref": {
                                "rule_id": "QM-P16",
                                "verification_status": "verified",
                            },
                        },
                    },
                    {
                        "id": "QM-P17",
                        "name": "六仪击刑",
                        "status": "predicate_matched_not_verdict",
                        "palace": 8,
                        "identity_adjudication": {
                            "status": "adjudicated_pattern_identity",
                            "decision_scope": "qimen_named_pattern_identity",
                            "pattern_id": "QM-P17",
                            "pattern_name": "六仪击刑",
                            "palace": 8,
                            "hard_verdict": None,
                            "event_verdict": None,
                            "source_ref": {
                                "rule_id": "QM-P17",
                                "verification_status": "verified",
                            },
                        },
                    },
                ],
                "display_text": "named_patterns",
            },
        ],
        "request_view": {
            "subject_refs": ["wenshi:evidence"],
            "capability_ids": ["liuyao", "qimen", "liuren"],
            "dimension_ids": ["outcome"],
        },
    }

    view_model = project_wenshi_view_model(payload)

    assert isinstance(view_model, WenshiViewV1)
    signals = view_model.dimensions[0].signals
    assert {
        signal.signal_id for signal in signals
    } == {
        "liuyao.outcome.structure",
        "liuyao.outcome.source_pattern.HJC-M001",
        "liuyao.outcome.useful_spirit_candidates.兄弟",
        "liuyao.outcome.useful_spirit_candidates.官鬼",
        "liuyao.outcome.useful_spirit_selection.chain_candidates",
        "liuyao.outcome.useful_spirit_selection.role_adjudication",
        "liuyao.outcome.useful_spirit_selection.strength_evidence",
        "qimen.outcome.structure",
        "qimen.outcome.named_pattern.QM-P16",
        "qimen.outcome.named_pattern.QM-P17",
    }
    assert all(
        "不形成问事合参结论" in signal.display_text
        for signal in signals
        if "useful_spirit_candidates" in signal.signal_id
        or "useful_spirit_selection" in signal.signal_id
        or "named_pattern" in signal.signal_id
    )
    role_signal = next(
        signal
        for signal in signals
        if signal.signal_id.endswith("role_adjudication")
    )
    assert "妻财为主、子孙为辅" in role_signal.display_text
    assert "盘内唯一可见妻财为第4爻" in role_signal.display_text
    qimen_signals = [
        signal for signal in signals if ".named_pattern." in signal.signal_id
    ]
    assert all("格局身份" in signal.display_text for signal in qimen_signals)
    assert view_model.dimensions[0].convergence == ()
    assert view_model.dimensions[0].disagreements == ()


def test_wenshi_projector_exposes_liuren_timing_candidate_evidence() -> None:
    payload = {
        "question": "验证大六壬应期候选证据是否进入问事合参",
        "facts": [
            {
                "ref": "fact:wenshi:timing/calculated/liuyao/relation_facts",
                "subject_ref": "wenshi:timing",
                "kind_id": "kind.liuyao-structure",
                "value": [],
                "display_text": "relation_facts",
            },
            {
                "ref": "fact:wenshi:timing/calculated/qimen/calculated_board_scope",
                "subject_ref": "wenshi:timing",
                "kind_id": "kind.qimen-structure",
                "value": {"scope": "fixture"},
                "display_text": "calculated_board_scope",
            },
            {
                "ref": "fact:wenshi:timing/calculated/liuren/dimension_facts",
                "subject_ref": "wenshi:timing",
                "kind_id": "kind.liuren-structure",
                "value": {
                    "timing": {
                        "status": "calculated_facts_not_verdict",
                        "relative_speed": "relatively_faster",
                        "candidate_branch": "酉",
                        "candidate_date": "2026-08-21",
                    }
                },
                "display_text": "dimension_facts",
            },
        ],
        "request_view": {
            "subject_refs": ["wenshi:timing"],
            "capability_ids": ["liuyao", "qimen", "liuren"],
            "dimension_ids": ["timing"],
        },
    }

    view_model = project_wenshi_view_model(payload)

    assert isinstance(view_model, WenshiViewV1)
    signals = view_model.dimensions[0].signals
    assert "daliuren.timing.timing_candidate_evidence" in {
        signal.signal_id for signal in signals
    }
    timing_signal = next(
        signal
        for signal in signals
        if signal.signal_id == "daliuren.timing.timing_candidate_evidence"
    )
    assert timing_signal.fact_refs == (
        "fact:wenshi:timing/calculated/liuren/dimension_facts",
    )
    assert "不形成问事合参结论" in timing_signal.display_text
    assert view_model.dimensions[0].missing_art_ids == ()


def test_runtime_dispatch_returns_none_for_a_capability_without_a_projector() -> None:
    assert project_runtime_view_model(brief("fortune", {"target_date": "fixture"})) is None


def test_liuyao_projector_keeps_v51_core_facts_without_complete_useful_spirit() -> None:
    view_model = project_liuyao_view_model(
        brief(
            "liuyao",
            {
                "primary_hexagram": {
                    "name": "乾为天",
                    "upper_trigram": "乾",
                    "lower_trigram": "乾",
                },
                "lines": [
                    {"line": 1, "state": "老阳"},
                    {"line": 2, "state": "少阳"},
                    {"line": 3, "state": "少阴"},
                    {"line": 4, "state": "老阴"},
                    {"line": 5, "state": "少阳"},
                    {"line": 6, "state": "少阴"},
                ],
                "najia": [{"line": 1, "ganzhi": "甲子"}],
                "useful_spirit_selection": {
                    "status": "evidence_bound",
                    "reason": (
                        "school-dependent adjudication is outside deterministic calculation"
                    ),
                    "query_word_matching": False,
                    "source_dependency_id": (
                        "liuyao.relations.returning-and-useful-spirit-candidates"
                    ),
                },
            },
        )
    )

    assert isinstance(view_model, LiuyaoChartV1)
    assert view_model.core_facts is not None
    assert view_model.core_facts.najia == ({"line": 1, "ganzhi": "甲子"},)
    assert view_model.core_facts.useful_spirit_selection is None


def test_daliuren_projector_maps_v51_individual_facts_without_runtime_core_envelope() -> None:
    fixture_path = (
        Path(__file__).resolve().parent / "fixtures" / "liuren-runtime-core-facts-v1.json"
    )
    runtime_core_facts = json.loads(fixture_path.read_text(encoding="utf-8"))
    values = {
        field: value
        for field, value in runtime_core_facts.items()
        if field != "schema_version"
    }
    lesson_method = dict(values["lesson_method"])
    lesson_method["table_label"] = "八专"
    lesson_method["selection_trace"] = {"result": "八专"}
    values["lesson_method"] = lesson_method

    view_model = project_daliuren_view_model(brief("liuren", values))

    assert isinstance(view_model, DaliurenChartV1)
    assert [item.lesson_id for item in view_model.lessons] == ["1", "2", "3", "4"]
    assert view_model.core_facts is not None
    assert view_model.core_facts.day_hour is not None
    assert view_model.core_facts.day_hour.day == "乙酉"
    assert view_model.core_facts.heaven_plate is not None
    assert view_model.core_facts.lesson_method is not None
    assert view_model.core_facts.lesson_method.primary == values["lesson_method"]["primary"]
