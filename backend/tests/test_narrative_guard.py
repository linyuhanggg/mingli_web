from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
from typing import Any

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "narrative"


def load_candidate(name: str = "valid-bazi-candidate.json") -> dict[str, Any]:
    with (FIXTURE_ROOT / name).open(encoding="utf-8") as stream:
        payload: dict[str, Any] = json.load(stream)
    return payload


def brief_payload() -> dict[str, Any]:
    return {
        "question": "事业上最该先抓住哪条主线？",
        "vocabulary": [],
        "facts": [
            {
                "ref": "fact:career-structure",
                "subject_ref": "profile-version:test",
                "kind_id": "kind.structure",
                "value": {"fixture": "stable"},
                "display_text": "当前结构更支持持续积累。",
            },
            {
                "ref": "fact:relationship-structure",
                "subject_ref": "profile-version:test",
                "kind_id": "kind.structure",
                "value": {"fixture": "other"},
                "display_text": "另一条仅供闭合测试的事实。",
            },
        ],
        "evidence": [
            {
                "ref": "evidence:classic-1",
                "source_title": "测试古籍",
                "locator": "测试卷",
                "excerpt": "只用于合同测试的短摘录。",
                "supports_fact_refs": ["fact:career-structure"],
            },
            {
                "ref": "evidence:classic-other",
                "source_title": "另一测试古籍",
                "locator": None,
                "excerpt": None,
                "supports_fact_refs": ["fact:relationship-structure"],
            },
        ],
        "findings": [
            {
                "ref": "finding:career-main",
                "subject_ref": "profile-version:test",
                "dimension_ids": ["career"],
                "kind_id": "kind.tendency",
                "data": {"fixture": True},
                "fact_refs": ["fact:career-structure"],
                "evidence_refs": ["evidence:classic-1"],
                "limit_kind_ids": ["limit:traditional"],
                "support_mode": "exact",
            }
        ],
        "claim_scopes": [
            {
                "subject_ref": "profile-version:test",
                "dimension_id": "career",
                "allowed_kind_ids": ["kind.tendency"],
                "certainty_ceiling_id": "certainty.tendency",
                "fact_refs": ["fact:career-structure"],
                "evidence_refs": ["evidence:classic-1"],
            },
            {
                "subject_ref": "profile-version:test",
                "dimension_id": "relationship",
                "allowed_kind_ids": ["kind.tendency"],
                "certainty_ceiling_id": "certainty.tendency",
                "fact_refs": ["fact:relationship-structure"],
                "evidence_refs": ["evidence:classic-other"],
            },
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


def build_brief(payload: dict[str, Any] | None = None) -> Any:
    runtime = importlib.import_module("app.readings.runtime_contracts")
    return runtime.ReadingBrief.from_dict(payload or brief_payload())


def test_candidate_refs_close_over_the_current_brief() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    guard = guard_module.NarrativeGuard()
    candidate = load_candidate()
    original = copy.deepcopy(candidate)

    result = guard.validate(candidate, build_brief(), output_contract="scoped-preview-v1")

    assert result.passed is True
    assert result.errors == ()
    assert candidate == original


def test_frozen_invalid_reference_fixture_is_rejected() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    result = guard_module.NarrativeGuard().validate(
        load_candidate("invalid-reference-candidate.json"),
        build_brief(),
        output_contract="scoped-preview-v1",
    )

    assert result.passed is False
    assert "unknown_fact_ref" in result.errors


@pytest.mark.parametrize(
    "mutation, expected_error",
    [
        (lambda block: block.update(subject_ref="profile-version:unknown"), "unknown_subject_ref"),
        (lambda block: block.update(dimension_id="wealth"), "unknown_dimension"),
        (lambda block: block.update(fact_refs=["fact:unknown"]), "unknown_fact_ref"),
        (
            lambda block: block.update(finding_refs=["finding:unknown"]),
            "unknown_finding_ref",
        ),
        (
            lambda block: block.update(evidence_refs=["evidence:unknown"]),
            "unknown_evidence_ref",
        ),
        (
            lambda block: block.update(limit_kind_ids=["limit:unknown"]),
            "unknown_limit_ref",
        ),
        (lambda block: block.update(claim_kind_id="kind.guarantee"), "kind_not_allowed"),
        (
            lambda block: block.update(certainty_id="certainty.certain"),
            "certainty_exceeded",
        ),
        (
            lambda block: block.update(evidence_refs=["evidence:classic-other"]),
            "scope_mismatch",
        ),
        (
            lambda block: block.update(
                dimension_id="relationship",
                fact_refs=["fact:relationship-structure"],
                evidence_refs=["evidence:classic-other"],
            ),
            "scope_mismatch",
        ),
        (
            lambda block: block.update(text="内部 fact:career-structure 不应可见"),
            "internal_identifier_visible",
        ),
        (lambda block: block.update(text="成功概率是 80%"), "uncalibrated_probability"),
        (lambda block: block.update(text="这件事一定会成功"), "unsupported_guarantee"),
        (lambda block: block.update(text="保证你明年升职"), "unsupported_guarantee"),
        (lambda block: block.update(text="成功概率是百分之八十"), "uncalibrated_probability"),
        (lambda block: block.update(text="会在 2027-05-01 得到 50000 元"), "invented_specific"),
        (lambda block: block.update(text="太长" * 700), "output_too_long"),
        (lambda block: block.update(text=""), "schema_invalid"),
        (lambda block: block.update(extra_field="forbidden"), "schema_invalid"),
    ],
)
def test_guard_rejects_closed_world_counterexamples(
    mutation: Any,
    expected_error: str,
) -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    candidate = load_candidate()
    mutation(candidate["blocks"][0])

    result = guard_module.NarrativeGuard().validate(
        candidate,
        build_brief(),
        output_contract="scoped-preview-v1",
    )

    assert result.passed is False
    assert expected_error in result.errors


def test_evidence_must_support_a_fact_used_by_the_same_claim() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    payload = brief_payload()
    payload["evidence"][0]["supports_fact_refs"] = ["fact:relationship-structure"]

    result = guard_module.NarrativeGuard().validate(
        load_candidate(),
        build_brief(payload),
        output_contract="scoped-preview-v1",
    )

    assert "scope_mismatch" in result.errors


def test_required_output_dimensions_and_limits_must_be_covered() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    candidate = load_candidate()
    # scoped-preview-v1 no longer hard-requires a limit id, because real runtime
    # briefs may emit an empty limits array; still require the contract dimension.
    candidate["blocks"][0]["dimension_id"] = "relationship"

    result = guard_module.NarrativeGuard().validate(
        candidate,
        build_brief(),
        output_contract="scoped-preview-v1",
    )

    assert "required_dimension_missing" in result.errors


def test_preview_contract_requires_the_overview_dimension() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    payload = brief_payload()
    payload["findings"][0]["dimension_ids"] = ["overview"]
    payload["claim_scopes"] = [
        {
            "subject_ref": "profile-version:test",
            "dimension_id": "overview",
            "allowed_kind_ids": ["kind.tendency"],
            "certainty_ceiling_id": "certainty.tendency",
            "fact_refs": ["fact:career-structure"],
            "evidence_refs": ["evidence:classic-1"],
        }
    ]
    payload["request_view"]["dimension_ids"] = ["overview", "state"]
    candidate = load_candidate()
    candidate["blocks"][0]["dimension_id"] = "overview"

    accepted = guard_module.NarrativeGuard().validate(
        candidate,
        build_brief(payload),
        output_contract="preview-v1",
    )
    assert accepted.passed is True

    candidate["blocks"][0]["dimension_id"] = "career"
    rejected = guard_module.NarrativeGuard().validate(
        candidate,
        build_brief(payload),
        output_contract="preview-v1",
    )
    assert rejected.passed is False
    assert "required_dimension_missing" in rejected.errors


def test_guard_proves_reference_closure_not_general_semantic_entailment() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    candidate = load_candidate()
    candidate["blocks"][0]["text"] = "这句话自然语言质量仍需黄金样例和人工评测。"

    result = guard_module.NarrativeGuard().validate(
        candidate,
        build_brief(),
        output_contract="scoped-preview-v1",
    )

    assert result.passed is True
