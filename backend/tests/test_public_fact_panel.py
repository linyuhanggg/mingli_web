from __future__ import annotations

from app.readings.public_fact_panel import (
    is_sensitive_public_fact,
    project_public_fact_panel,
)
from app.readings.runtime_contracts import ReadingBrief


def _brief_with_facts(facts: list[dict[str, object]]) -> ReadingBrief:
    return ReadingBrief.from_dict(
        {
            "question": "事业上最该先抓住哪条主线？",
            "vocabulary": [],
            "facts": facts,
            "evidence": [],
            "findings": [],
            "claim_scopes": [
                {
                    "subject_ref": "profile-version:test",
                    "dimension_id": "career",
                    "allowed_kind_ids": ["kind.tendency"],
                    "certainty_ceiling_id": "certainty.tendency",
                    "fact_refs": [facts[0]["ref"]] if facts else [],
                    "evidence_refs": [],
                }
            ],
            "limits": [
                {
                    "kind_id": "limit:traditional",
                    "public_text": "本解读仅供传统文化参考，不构成现实决策保证。",
                    "scope_refs": ["profile-version:test"],
                    "detail_ids": [],
                }
            ],
            "prior_answer": None,
            "request_view": {
                "subject_refs": ["profile-version:test"],
                "capability_ids": ["bazi"],
                "object_id": "natal",
                "dimension_ids": ["career"],
                "horizon": {"kind_id": "life", "start": None, "end": None},
            },
        }
    )


def test_input_birth_datetime_fact_is_sensitive() -> None:
    fact = {
        "ref": "fact:profile-version:test/input/birth_datetime",
        "subject_ref": "profile-version:test",
        "kind_id": "kind.structure",
        "value": "1994-04-30T05:55:00+08:00",
        "display_text": "出生时间：1994-04-30T05:55:00+08:00",
    }
    assert is_sensitive_public_fact(fact) is True


def test_every_raw_input_fact_is_sensitive() -> None:
    for field_id, value in (
        ("location", "上海市"),
        ("timezone", "Asia/Shanghai"),
        ("gender", "female"),
        ("time_basis_policy", "civil_time"),
        ("zi_hour_policy", "midnight_rollover"),
        ("future_private_field", "private-by-default"),
    ):
        fact = {
            "ref": f"fact:profile-version:test/input/{field_id}",
            "subject_ref": "profile-version:test",
            "kind_id": "kind.structure",
            "value": value,
            "display_text": f"原始输入：{value}",
        }
        assert is_sensitive_public_fact(fact) is True


def test_public_chart_facts_remain() -> None:
    fact = {
        "ref": "fact:profile-version:test/chart/day_master",
        "subject_ref": "profile-version:test",
        "kind_id": "kind.structure",
        "value": {"stem": "甲"},
        "display_text": "日主：甲",
    }
    assert is_sensitive_public_fact(fact) is False


def test_project_public_fact_panel_strips_birth_input_and_keeps_chart() -> None:
    brief = _brief_with_facts(
        [
            {
                "ref": "fact:profile-version:test/input/birth_datetime",
                "subject_ref": "profile-version:test",
                "kind_id": "kind.structure",
                "value": "1994-04-30T05:55:00+08:00",
                "display_text": "出生时间：1994-04-30T05:55:00+08:00",
            },
            {
                "ref": "fact:career-structure",
                "subject_ref": "profile-version:test",
                "kind_id": "kind.structure",
                "value": {"fixture": "stable"},
                "display_text": "当前结构更支持持续积累。",
            },
        ]
    )
    panel = project_public_fact_panel(brief)
    assert panel is not None
    assert len(panel["facts"]) == 1
    assert panel["facts"][0]["display_text"] == "当前结构更支持持续积累。"
    dumped = str(panel)
    assert "1994-04-30" not in dumped
    for fact in panel["facts"]:
        assert "input/birth_datetime" not in str(fact.get("ref", ""))
    for scope in panel["claim_scopes"]:
        for ref in scope.get("fact_refs", []):
            assert "birth_datetime" not in str(ref)


def test_project_public_fact_panel_removes_all_input_refs_from_dependencies() -> None:
    raw_location_ref = "fact:profile-version:test/input/location"
    chart_ref = "fact:profile-version:test/chart/day_master"
    payload = {
        "facts": [
            {
                "ref": raw_location_ref,
                "subject_ref": "profile-version:test",
                "kind_id": "kind.structure",
                "value": "上海市",
                "display_text": "出生地点：上海市",
            },
            {
                "ref": chart_ref,
                "subject_ref": "profile-version:test",
                "kind_id": "kind.structure",
                "value": {"stem": "甲"},
                "display_text": "日主：甲",
            },
        ],
        "evidence": [
            {
                "ref": "evidence:test",
                "supports_fact_refs": [raw_location_ref, chart_ref],
            }
        ],
        "findings": [
            {
                "ref": "finding:test",
                "fact_refs": [raw_location_ref, chart_ref],
            }
        ],
        "claim_scopes": [
            {
                "subject_ref": "profile-version:test",
                "dimension_id": "career",
                "fact_refs": [raw_location_ref, chart_ref],
            }
        ],
    }

    panel = project_public_fact_panel(payload)

    assert panel is not None
    assert [fact["ref"] for fact in panel["facts"]] == [chart_ref]
    assert panel["evidence"][0]["supports_fact_refs"] == [chart_ref]
    assert panel["findings"][0]["fact_refs"] == [chart_ref]
    assert panel["claim_scopes"][0]["fact_refs"] == [chart_ref]
    assert raw_location_ref not in str(panel)


def test_project_public_fact_panel_none() -> None:
    assert project_public_fact_panel(None) is None
