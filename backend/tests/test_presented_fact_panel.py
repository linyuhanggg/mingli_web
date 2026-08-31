from __future__ import annotations

from typing import Any

from app.charts.projectors import project_runtime_view_model
from app.readings.presentation.access_policy import ACTIVE_CONTENT_ACCESS_POLICY
from app.readings.presentation.fact_panel import (
    project_presented_fact_panel,
    project_presented_view_model,
)
from app.readings.runtime_contracts import ReadingBrief


def _brief(capability_id: str, facts: list[dict[str, Any]]) -> ReadingBrief:
    subject_ref = "profile-version:ming-83"
    return ReadingBrief.from_dict(
        {
            "question": "验证公开事实的人化投影",
            "vocabulary": [],
            "facts": facts,
            "evidence": [
                {
                    "ref": "evidence:unknown",
                    "source_title": "测试依据",
                    "locator": "测试卷",
                    "excerpt": "仅用于合同测试。",
                    "supports_fact_refs": [
                        f"fact:{subject_ref}/calculated/{capability_id}/unknown_engine_dump"
                    ],
                }
            ],
            "findings": [
                {
                    "ref": "finding:unknown",
                    "subject_ref": subject_ref,
                    "dimension_ids": ["career"],
                    "kind_id": "kind.tendency",
                    "data": {"fixture": True},
                    "fact_refs": [
                        f"fact:{subject_ref}/calculated/{capability_id}/unknown_engine_dump"
                    ],
                    "evidence_refs": ["evidence:unknown"],
                    "limit_kind_ids": [],
                    "support_mode": "exact",
                }
            ],
            "claim_scopes": [
                {
                    "subject_ref": subject_ref,
                    "dimension_id": "career",
                    "allowed_kind_ids": ["kind.tendency"],
                    "certainty_ceiling_id": "certainty.tendency",
                    "fact_refs": [
                        f"fact:{subject_ref}/calculated/{capability_id}/unknown_engine_dump"
                    ],
                    "evidence_refs": ["evidence:unknown"],
                }
            ],
            "limits": [],
            "prior_answer": None,
            "request_view": {
                "subject_refs": [subject_ref],
                "capability_ids": [capability_id],
                "object_id": "natal",
                "dimension_ids": ["career"],
                "horizon": {"kind_id": "life", "start": None, "end": None},
            },
        }
    )


def _fact(capability_id: str, field_id: str, value: object) -> dict[str, Any]:
    return {
        "ref": (
            f"fact:profile-version:ming-83/calculated/{capability_id}/{field_id}"
        ),
        "subject_ref": "profile-version:ming-83",
        "kind_id": "kind.fact",
        "value": value,
        "display_text": (
            '{"schema_version":"engine-internal/v1","field":"'
            f"{field_id}" + '"}'
        ),
    }


def _calendar_normalization() -> dict[str, object]:
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
    }


def _texts(panel: dict[str, Any]) -> dict[str, str]:
    return {
        str(item["ref"]).rsplit("/", 1)[-1]: str(item["display_text"])
        for item in panel["facts"]
    }


def test_bazi_public_facts_use_named_view_model_text_and_fail_closed() -> None:
    brief = _brief(
        "bazi",
        [
            _fact(
                "bazi",
                "four_pillars",
                {"year": "甲戌", "month": "戊辰", "day": "丙戌", "hour": "辛卯"},
            ),
            _fact(
                "bazi",
                "day_master",
                {"stem": "丙", "element": "火", "polarity": "阳"},
            ),
            _fact(
                "bazi",
                "xunkong",
                {
                    "day_pillar": "丙戌",
                    "xun": "甲申",
                    "branches": ["午", "未"],
                    "source_dependency_id": "bazi.chart.xunkong-v1",
                    "boundary": "只表示旬空位置事实。",
                },
            ),
            _fact("bazi", "month_layers", {"unsupported": True}),
            _fact("bazi", "unknown_engine_dump", {"engine": "bazi-core"}),
        ],
    )
    view_model = project_runtime_view_model(brief.to_dict(), product_id="bazi")
    assert view_model is not None
    panel = project_presented_fact_panel(
        brief,
        view_model=view_model,
    )

    assert panel is not None
    assert _texts(panel) == {
        "four_pillars": "四柱：年柱甲戌、月柱戊辰、日柱丙戌、时柱辛卯。",
        "day_master": "日主：丙火（阳）。",
        "xunkong": "旬空：日柱丙戌 · 甲申旬 · 旬空午/未。",
    }
    serialized = str(panel)
    assert "{" not in "".join(_texts(panel).values())
    assert "schema_version" not in serialized
    assert "unknown_engine_dump" not in serialized
    assert "month_layers" not in serialized
    assert panel["claim_scopes"] == []
    assert panel["findings"] == []
    assert panel["evidence"] == []
    assert "fixture" not in serialized
    assert "仅用于合同测试。" not in serialized


def test_bazi_calendar_distinguishes_missing_empty_and_changed_pillars() -> None:
    projected: dict[str, dict[str, str]] = {}
    for case, changed_pillars in (
        ("missing", None),
        ("empty", []),
        ("changed", ["day", "hour"]),
    ):
        calendar = _calendar_normalization()
        if changed_pillars is not None:
            calendar["changed_pillars"] = changed_pillars
        brief = _brief(
            "bazi",
            [
                _fact(
                    "bazi",
                    "four_pillars",
                    {
                        "year": "甲戌",
                        "month": "戊辰",
                        "day": "丙戌",
                        "hour": "辛卯",
                    },
                ),
                _fact("bazi", "calendar_normalization", calendar),
            ],
        )
        view_model = project_runtime_view_model(brief.to_dict(), product_id="bazi")

        assert view_model is not None
        panel = project_presented_fact_panel(brief, view_model=view_model)
        assert panel is not None
        projected[case] = _texts(panel)

    assert "calendar_normalization" not in projected["missing"]
    assert projected["empty"]["calendar_normalization"] == (
        "时间口径：已完成历法与时间归一；四柱未因校正变更。"
    )
    assert projected["changed"]["calendar_normalization"] == (
        "时间口径：已完成历法与时间归一；日柱、时柱。"
    )


def test_bazi_year_layers_render_each_exact_ganzhi_segment() -> None:
    from test_bazi_view_model_projector import _year_layer

    year_layers = _year_layer()
    layer = year_layers["2026"]
    assert isinstance(layer, dict)
    segments = layer["ganzhi_segments"]
    assert isinstance(segments, list)
    second = segments[1]
    assert isinstance(second, dict)
    segments[1] = {
        **second,
        "start_inclusive": "2026-02-04T04:01:51+08:00",
        "end_exclusive": "2027-01-01T00:00:00+08:00",
        "ganzhi": "丙午",
        "stem_ten_god": "正印",
    }
    brief = _brief(
        "bazi",
        [
            _fact(
                "bazi",
                "four_pillars",
                {"year": "甲戌", "month": "戊辰", "day": "丙戌", "hour": "辛卯"},
            ),
            _fact("bazi", "year_layers", year_layers),
        ],
    )
    view_model = project_runtime_view_model(brief.to_dict(), product_id="bazi")

    assert view_model is not None
    panel = project_presented_fact_panel(brief, view_model=view_model)

    assert panel is not None
    assert _texts(panel)["year_layers"] == (
        "流年：2026年："
        "乙巳（区间自2026-01-01T00:00:00+08:00（含）"
        "至2026-02-04T04:01:51+08:00（不含），天干十神七杀）；"
        "丙午（区间自2026-02-04T04:01:51+08:00（含）"
        "至2027-01-01T00:00:00+08:00（不含），天干十神正印）。"
    )


def test_ziwei_public_facts_use_named_view_model_text_and_fail_closed() -> None:
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
    brief = _brief(
        "ziwei",
        [
            _fact("ziwei", "palaces", palaces),
            _fact("ziwei", "five_elements_class", "水二局"),
            _fact(
                "ziwei",
                "ming_shen",
                {
                    "body_star": "天相",
                    "ming_branch": "子",
                    "shen_branch": "寅",
                    "soul_star": "贪狼",
                },
            ),
            _fact("ziwei", "monthly_layers", {"unsupported": True}),
            _fact("ziwei", "unknown_engine_dump", {"engine": "ziwei-core"}),
        ],
    )
    view_model = project_runtime_view_model(brief.to_dict(), product_id="ziwei")
    assert view_model is not None
    panel = project_presented_fact_panel(
        brief,
        view_model=view_model,
    )

    assert panel is not None
    texts = _texts(panel)
    assert texts["palaces"].startswith("十二宫：命宫（甲子）主星紫微；")
    assert texts["five_elements_class"] == "五行局：水二局。"
    assert texts["ming_shen"] == "命身信息：命主贪狼、身主天相，命宫子、身宫寅。"
    assert "{" not in "".join(texts.values())
    assert "schema_version" not in str(panel)
    assert "unknown_engine_dump" not in str(panel)
    assert "monthly_layers" not in str(panel)


def test_ziwei_half_open_intervals_are_explicit_in_presented_text() -> None:
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
    brief = _brief(
        "ziwei",
        [
            _fact("ziwei", "palaces", palaces),
            _fact(
                "ziwei",
                "active_major_limit_segments",
                [
                    {
                        "start_inclusive": "2026-01-01",
                        "end_exclusive": "2026-07-01",
                        "major_limit": {"index": 1},
                    },
                    {
                        "start_inclusive": "2026-07-01",
                        "end_exclusive": "2027-01-01",
                        "major_limit": {"index": 2},
                    },
                ],
            ),
            _fact(
                "ziwei",
                "calendar_coverage",
                {
                    "start_inclusive": "2026-01-01",
                    "end_exclusive": "2027-01-01",
                    "requested_target_date": "2026-06-01",
                },
            ),
            _fact(
                "ziwei",
                "annual_layers",
                {
                    "2026": {
                        "year": 2026,
                        "coverage_start": "2026-02-17",
                        "coverage_end_exclusive": "2027-02-06",
                        "liu_nian": {"year": 2026},
                        "segments": [{"start_inclusive": "2026-02-17"}],
                        "representative_scope": "year:2026",
                    }
                },
            ),
        ],
    )
    view_model = project_runtime_view_model(brief.to_dict(), product_id="ziwei")

    assert view_model is not None
    panel = project_presented_fact_panel(brief, view_model=view_model)

    assert panel is not None
    texts = _texts(panel)
    assert texts["active_major_limit_segments"] == (
        "当前大限区间：自2026-01-01（含）至2026-07-01（不含）、"
        "自2026-07-01（含）至2027-01-01（不含）。"
    )
    assert texts["calendar_coverage"] == (
        "历法覆盖：自2026-01-01（含）至2027-01-01（不含）"
        " · 目标日2026-06-01。"
    )
    assert texts["annual_layers"] == (
        "流年：2026年（区间自2026-02-17（含）至2027-02-06（不含））。"
    )


def test_supported_time_layer_values_are_visible_without_billing_state() -> None:
    bazi_brief = _brief(
        "bazi",
        [
            _fact(
                "bazi",
                "four_pillars",
                {"year": "甲戌", "month": "戊辰", "day": "丙戌", "hour": "辛卯"},
            ),
            _fact(
                "bazi",
                "month_layers",
                {
                    "2032-01": {
                        "year": 2032,
                        "month": 1,
                        "ganzhi_segments": [{"ganzhi": "壬子"}],
                        "structural_changes": {"status": "fixture"},
                        "seasonal_tiaohou_delta": {"status": "fixture"},
                        "shensha_auxiliary": {"status": "fixture"},
                        "active_luck_cycle": {"status": "fixture"},
                        "calendar_normalization": {"status": "fixture"},
                        "rule_trace": [{"rule_id": "bazi.test.month"}],
                    }
                },
            ),
        ],
    )
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
    ziwei_brief = _brief(
        "ziwei",
        [
            _fact("ziwei", "palaces", palaces),
            _fact(
                "ziwei",
                "monthly_layers",
                {
                    "2032-01": {
                        "year": 2032,
                        "month": 1,
                        "liu_yue": {"palace": "命宫"},
                        "segments": [{"start": "2032-01-01"}],
                        "representative_scope": "month",
                    }
                },
            ),
        ],
    )
    bazi = project_runtime_view_model(bazi_brief.to_dict(), product_id="bazi")
    ziwei = project_runtime_view_model(ziwei_brief.to_dict(), product_id="ziwei")
    assert bazi is not None
    assert ziwei is not None
    assert bazi.core_facts is not None
    assert bazi.core_facts.month_layers is not None
    assert ziwei.core_facts is not None
    assert ziwei.core_facts.monthly_layers is not None

    presented_bazi = project_presented_view_model(bazi)
    presented_ziwei = project_presented_view_model(ziwei)

    assert presented_bazi.core_facts is not None
    assert presented_bazi.core_facts.month_layers is not None
    assert presented_ziwei.core_facts is not None
    assert presented_ziwei.core_facts.monthly_layers is not None

    bazi_panel = project_presented_fact_panel(bazi_brief, view_model=bazi)
    ziwei_panel = project_presented_fact_panel(ziwei_brief, view_model=ziwei)

    assert bazi_panel is not None
    assert ziwei_panel is not None
    assert _texts(bazi_panel)["month_layers"] == "流月：2032-01·壬子。"
    assert _texts(ziwei_panel)["monthly_layers"] == "流月：2032年1月。"


def test_active_content_access_policy_defaults_all_supported_content_to_readable() -> None:
    assert ACTIVE_CONTENT_ACCESS_POLICY.phase == "development_free_all_supported"
    assert ACTIVE_CONTENT_ACCESS_POLICY.legacy_time_layer_resolution == "granted"
