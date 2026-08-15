from __future__ import annotations

from typing import Any

from app.charts.contracts import (
    BaziRelationshipV1,
    QizhengRelationshipV1,
    ZiweiRelationshipV1,
)
from app.charts.projectors import project_runtime_view_model


def relationship_brief(
    capabilities: list[str],
    *,
    relationship_type: str = "romantic",
    relationship_signals: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    subjects = ["profile-version:a", "profile-version:b"]
    facts: list[dict[str, object]] = [
        {
            "ref": "fact:relationship/calculated/relationship_signals",
            "subject_ref": "relationship",
            "kind_id": "kind.relationship.signals",
            "value": relationship_signals or [],
            "display_text": "跨盘结构事实",
        },
        {
            "ref": "fact:input/relationship/four_pillars",
            "subject_ref": subjects[0],
            "kind_id": "kind.fact",
            "value": {"year": "甲子"},
            "display_text": "输入事实，不得作为关系依据",
        },
    ]
    source_refs: set[str] = set()
    for item in relationship_signals or []:
        raw_refs = item.get("fact_refs")
        if not isinstance(raw_refs, (list, tuple)):
            continue
        source_refs.update(
            ref
            for ref in raw_refs
            if isinstance(ref, str) and "/input/" not in ref
        )
    facts.extend(
        {
            "ref": ref,
            "subject_ref": ref.split("/calculated/", 1)[0].removeprefix("fact:"),
            "kind_id": "kind.fact",
            "value": {"source": "runtime"},
            "display_text": "Runtime 计算事实",
        }
        for ref in sorted(source_refs)
    )
    return {
        "facts": facts,
        "request_view": {
            "subject_refs": subjects,
            "subject_labels": ["甲方", "乙方"],
            "capability_ids": capabilities,
            "relationship_type": relationship_type,
        },
    }


def signal(
    signal_id: str,
    display_text: str,
    capability: str,
    *,
    fact_refs: list[str] | None = None,
) -> dict[str, object]:
    return {
        "dimension_id": "relationship",
        "subject_refs": ["profile-version:a", "profile-version:b"],
        "signal_id": signal_id,
        "display_text": display_text,
        "fact_refs": fact_refs
        or [
            f"fact:profile-version:a/calculated/{capability}/chart",
            f"fact:profile-version:b/calculated/{capability}/chart",
        ],
    }


def test_bazi_relationship_projects_runtime_cross_chart_facts() -> None:
    payload = relationship_brief(
        ["bazi"],
        relationship_signals=[
            signal(
                "bazi.cross_branch.liu_chong.year.year",
                "甲方年支「子」与乙方年支「午」构成六冲（跨盘结构事实）。",
                "bazi",
            ),
            signal(
                "bazi.cross_stem.wu_he.year.month",
                "甲方年干「甲」与乙方月干「己」构成天干五合（跨盘结构事实）。",
                "bazi",
            ),
        ],
    )

    view_model = project_runtime_view_model(payload, product_id="bazi-relationship")

    assert isinstance(view_model, BaziRelationshipV1)
    assert view_model.subjects[0].profile_version_id == "a"
    assert view_model.subjects[1].profile_version_id == "b"
    assert any("六冲" in item.display_text for item in view_model.signals)
    assert any("天干五合" in item.display_text for item in view_model.signals)
    assert all("fact:input" not in ref for item in view_model.signals for ref in item.fact_refs)


def test_ziwei_relationship_projects_runtime_palace_facts_without_recomputing() -> None:
    payload = relationship_brief(
        ["ziwei"],
        relationship_signals=[
            signal(
                "ziwei.cross_palace.liu_chong.命宫",
                "甲方命宫与乙方命宫构成六冲（紫微跨盘结构事实）。",
                "ziwei",
            )
        ],
    )

    view_model = project_runtime_view_model(payload, product_id="ziwei-relationship")

    assert isinstance(view_model, ZiweiRelationshipV1)
    assert len(view_model.signals) == 1
    assert "命宫" in view_model.signals[0].display_text


def test_qizheng_relationship_projects_runtime_aspect_facts() -> None:
    payload = relationship_brief(
        ["xingming"],
        relationship_signals=[
            signal(
                "qizheng.cross_aspect.conjunction.太阳.太阳",
                "甲方太阳与乙方太阳形成合相，容许度 7.0°（七政跨盘结构筛查事实）。",
                "xingming",
            ),
            signal(
                "qizheng.cross_aspect.square.太阳.太阴",
                "甲方太阳与乙方太阴形成刑相，容许度 0.0°（七政跨盘结构筛查事实）。",
                "xingming",
            ),
        ],
    )

    view_model = project_runtime_view_model(payload, product_id="qizheng-relationship")

    assert isinstance(view_model, QizhengRelationshipV1)
    assert {item.signal_id for item in view_model.signals} == {
        "qizheng.cross_aspect.conjunction.太阳.太阳",
        "qizheng.cross_aspect.square.太阳.太阴",
    }


def test_relationship_projector_rejects_missing_native_facts_or_input_only_facts() -> None:
    missing = relationship_brief(["bazi"])
    assert project_runtime_view_model(missing, product_id="bazi-relationship") is None

    input_only = relationship_brief(
        ["bazi"],
        relationship_signals=[
            signal(
                "bazi.cross_branch.liu_chong.year.year",
                "不应发布",
                "bazi",
                fact_refs=["fact:profile-version:a/input/birth_datetime"],
            )
        ],
    )
    assert project_runtime_view_model(input_only, product_id="bazi-relationship") is None


def test_relationship_projector_rejects_unknown_fact_references() -> None:
    payload = relationship_brief(
        ["bazi"],
        relationship_signals=[
            signal(
                "bazi.cross_branch.liu_chong.year.year",
                "不应发布",
                "bazi",
            )
        ],
    )
    facts = payload["facts"]
    assert isinstance(facts, list)
    signals = facts[0]["value"]
    assert isinstance(signals, list)
    signals[0]["fact_refs"] = [
        "fact:profile-version:a/calculated/bazi/not-present",
    ]

    assert project_runtime_view_model(payload, product_id="bazi-relationship") is None


def test_relationship_dispatch_rejects_single_subject_or_wrong_capability() -> None:
    payload: dict[str, Any] = relationship_brief(
        ["bazi"],
        relationship_signals=[signal("x", "x", "bazi")],
    )
    payload["request_view"] = {
        "subject_refs": ["profile-version:a"],
        "capability_ids": ["bazi"],
        "relationship_type": "romantic",
    }
    assert project_runtime_view_model(payload, product_id="bazi-relationship") is None
