from __future__ import annotations

import pytest
from app.charts.contracts import ChartSimilarityViewV1
from app.charts.projectors import project_chart_similarity_view_model
from app.charts.similarity import ChartSimilarityInputError, compare_bazi_four_pillars
from app.readings.request_compiler import (
    ConfirmedProfileVersion,
    RequestCompilationError,
    compile_chart_similarity_prepare,
)


def _pillars(*, hour: str = "丁卯") -> dict[str, str]:
    return {"year": "甲子", "month": "乙丑", "day": "丙寅", "hour": hour}


def _brief(left: dict[str, str], right: dict[str, str]) -> dict[str, object]:
    return {
        "facts": [
            {
                "ref": "fact:profile-a/calculated/bazi/four_pillars",
                "subject_ref": "profile-a",
                "kind_id": "kind.fact",
                "value": left,
                "display_text": "four_pillars",
            },
            {
                "ref": "fact:profile-b/calculated/bazi/four_pillars",
                "subject_ref": "profile-b",
                "kind_id": "kind.fact",
                "value": right,
                "display_text": "four_pillars",
            },
            {
                "ref": "fact:input/profile-a/birth_datetime",
                "subject_ref": "profile-a",
                "kind_id": "kind.fact",
                "value": "must not be read",
                "display_text": "input",
            },
        ],
        "request_view": {
            "subject_refs": ["profile-a", "profile-b"],
            "capability_ids": ["bazi"],
            "dimension_ids": ["state"],
        },
    }


def _profile(subject_ref: str) -> ConfirmedProfileVersion:
    return ConfirmedProfileVersion(
        subject_ref=subject_ref,
        birth_datetime="2000-01-01T05:10:00+08:00",
        birth_datetime_or_four_pillars="2000-01-01T05:10:00+08:00",
        timezone="Asia/Shanghai",
        location="福建省莆田市",
        gender="male",
        time_basis_policy="civil",
        zi_hour_policy="midnight",
        longitude=119.1,
        latitude=25.5,
        coordinate_source="fixture",
    )


def test_exact_four_pillar_comparison_has_no_score() -> None:
    result = compare_bazi_four_pillars(_pillars(), _pillars())

    assert result == (
        ("year", "甲子", "甲子", True),
        ("month", "乙丑", "乙丑", True),
        ("day", "丙寅", "丙寅", True),
        ("hour", "丁卯", "丁卯", True),
    )


def test_four_pillar_comparison_keeps_only_the_changed_position() -> None:
    result = compare_bazi_four_pillars(_pillars(), _pillars(hour="戊辰"))

    assert [item[0] for item in result if not item[3]] == ["hour"]


def test_four_pillar_comparison_rejects_incomplete_calculated_facts() -> None:
    with pytest.raises(ChartSimilarityInputError, match="month"):
        compare_bazi_four_pillars(
            {"year": "甲子", "month": "乙", "day": "丙寅", "hour": "丁卯"},
            _pillars(),
        )


def test_chart_similarity_projector_uses_calculated_refs_for_two_subjects() -> None:
    view = project_chart_similarity_view_model(_brief(_pillars(), _pillars(hour="戊辰")))

    assert isinstance(view, ChartSimilarityViewV1)
    assert view.basis == "bazi.four_pillars.exact"
    assert view.exact_match is False
    assert view.matched_positions == ("year", "month", "day")
    assert view.differing_positions == ("hour",)
    assert view.left_fact_ref.endswith("/calculated/bazi/four_pillars")
    assert view.right_fact_ref.endswith("/calculated/bazi/four_pillars")


def test_chart_similarity_projector_does_not_fall_back_to_input_facts() -> None:
    payload = _brief(_pillars(), _pillars())
    payload["facts"] = [
        item
        for item in payload["facts"]  # type: ignore[index]
        if "/calculated/" not in item["ref"]  # type: ignore[index]
    ]

    assert project_chart_similarity_view_model(payload) is None


def test_chart_similarity_compiler_binds_two_profiles_to_one_bazi_route() -> None:
    prepare = compile_chart_similarity_prepare(
        action="chart_similarity_preview",
        query="比较两份已确认命盘的八字四柱事实。",
        profiles=(_profile("profile-a"), _profile("profile-b")),
        dimension_ids=("state",),
    )

    assert prepare.intent["capability_id"] == "bazi"
    assert prepare.intent["subject_refs"] == ("profile-a", "profile-b")
    assert set(prepare.facts) == {"profile-a", "profile-b"}


def test_chart_similarity_compiler_rejects_non_state_dimensions() -> None:
    with pytest.raises(RequestCompilationError, match="outside the product allowlist"):
        compile_chart_similarity_prepare(
            action="chart_similarity_preview",
            query="比较",
            profiles=(_profile("profile-a"), _profile("profile-b")),
            dimension_ids=("career",),
        )
