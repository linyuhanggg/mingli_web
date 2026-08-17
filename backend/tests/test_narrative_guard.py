from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
from typing import Any

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "narrative"
FACT_TEXT = "当前结构更支持持续积累。"
FINDING_TEXT = "月令季节状态已经确定；整盘身强身弱仍未裁定。"
LIMIT_TEXT = "本解读仅供传统文化参考，不构成现实决策保证。"


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
                "display_text": FACT_TEXT,
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
                "evidence_ref": "evidence:classic-1",
                "rule_id": "bazi/test#R-01",
                "source_title": "测试古籍",
                "locator": "测试卷",
                "excerpt": "只用于合同测试的短摘录。",
                "verification_status": "verified_exact",
                "verbatim_excerpt": "只用于合同测试的短摘录。",
                "verbatim_citations": [
                    {
                        "source_title": "测试古籍",
                        "locator": "测试卷",
                        "verbatim_excerpt": "只用于合同测试的短摘录。",
                        "verification_status": "verified_exact",
                    }
                ],
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
                "public_text": FINDING_TEXT,
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
                "public_text": LIMIT_TEXT,
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


def bazi_deep_candidate(
    text: str,
    *,
    include_limit_ref: bool = True,
) -> dict[str, Any]:
    candidate = load_candidate()
    texts = tuple(
        [text]
        + [item for item in (FACT_TEXT, FINDING_TEXT, LIMIT_TEXT) if item != text][
            :2
        ]
    )
    blocks: list[dict[str, Any]] = []
    for index, block_text in enumerate(texts):
        block = copy.deepcopy(candidate["blocks"][0])
        block["block_id"] = f"b{index + 1}"
        block["text"] = block_text
        if not include_limit_ref and index == 0:
            block["limit_kind_ids"] = []
            block["finding_refs"] = []
        blocks.append(block)
    candidate["blocks"] = blocks
    return candidate


def test_candidate_refs_close_over_the_current_brief() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    guard = guard_module.NarrativeGuard()
    candidate = load_candidate()
    original = copy.deepcopy(candidate)

    result = guard.validate(candidate, build_brief(), output_contract="preview-v1")

    assert result.passed is True
    assert result.errors == ()
    assert candidate == original


def test_relationship_scope_allows_explicit_cross_subject_source_facts() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    payload = brief_payload()
    payload["facts"].append(
        {
            "ref": "fact:relationship-other-subject",
            "subject_ref": "profile-version:other",
            "kind_id": "kind.structure",
            "value": {"fixture": "other-subject"},
            "display_text": "另一主体的跨盘结构事实。",
        }
    )
    payload["claim_scopes"][1]["fact_refs"].append(
        "fact:relationship-other-subject"
    )
    candidate = load_candidate()
    candidate["blocks"][0].update(
        dimension_id="relationship",
        finding_refs=[],
        fact_refs=[
            "fact:relationship-structure",
            "fact:relationship-other-subject",
        ],
        evidence_refs=["evidence:classic-other"],
    )

    output_contracts = importlib.import_module("app.readings.output_contracts")
    result = guard_module.NarrativeGuard().validate(
        candidate,
        build_brief(payload),
        output_contract=output_contracts.output_contract_for_dimensions(
            ("relationship",)
        ),
    )

    assert result.passed is True
    assert result.errors == ()


def test_frozen_invalid_reference_fixture_is_rejected() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    result = guard_module.NarrativeGuard().validate(
        load_candidate("invalid-reference-candidate.json"),
        build_brief(),
        output_contract="preview-v1",
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
        output_contract="preview-v1",
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
        output_contract="preview-v1",
    )

    assert "scope_mismatch" in result.errors


def test_required_output_dimensions_and_limits_must_be_covered() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    candidate = load_candidate()
    # preview-v1 no longer hard-requires a limit id, because real runtime briefs
    # may emit an empty limits array; still require the contract dimension.
    candidate["blocks"][0]["dimension_id"] = "relationship"

    result = guard_module.NarrativeGuard().validate(
        candidate,
        build_brief(),
        output_contract="preview-v1",
    )

    assert "required_dimension_missing" in result.errors


def test_guard_proves_reference_closure_not_general_semantic_entailment() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    candidate = load_candidate()
    candidate["blocks"][0]["text"] = "这句话自然语言质量仍需黄金样例和人工评测。"

    result = guard_module.NarrativeGuard().validate(
        candidate,
        build_brief(),
        output_contract="preview-v1",
    )

    assert result.passed is True


def test_bazi_deep_rejects_unrelated_text_even_when_refs_are_legal() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")

    result = guard_module.NarrativeGuard().validate(
        bazi_deep_candidate("这是一句与当前事实无关的硬断。"),
        build_brief(),
        output_contract="bazi-deep-output-v1",
    )

    assert result.passed is False
    assert result.errors == ("bazi_deep_text_not_grounded",)


def test_bazi_deep_accepts_text_exactly_equal_to_a_referenced_fact() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")

    result = guard_module.NarrativeGuard().validate(
        bazi_deep_candidate(FACT_TEXT),
        build_brief(),
        output_contract="bazi-deep-output-v1",
    )

    assert result.passed is True
    assert result.errors == ()


@pytest.mark.parametrize(
    "text",
    [
        "另一条仅供闭合测试的事实。",
        "只用于合同测试的短摘录。",
    ],
)
def test_bazi_deep_rejects_unreferenced_fact_or_evidence_text(text: str) -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")

    result = guard_module.NarrativeGuard().validate(
        bazi_deep_candidate(text),
        build_brief(),
        output_contract="bazi-deep-output-v1",
    )

    assert result.passed is False
    assert result.errors == ("bazi_deep_text_not_grounded",)


def test_bazi_deep_accepts_limit_text_only_when_block_references_that_limit() -> None:
    guard_module = importlib.import_module("app.readings.narrative_guard")
    text = LIMIT_TEXT

    referenced = guard_module.NarrativeGuard().validate(
        bazi_deep_candidate(text),
        build_brief(),
        output_contract="bazi-deep-output-v1",
    )
    unreferenced = guard_module.NarrativeGuard().validate(
        bazi_deep_candidate(text, include_limit_ref=False),
        build_brief(),
        output_contract="bazi-deep-output-v1",
    )

    assert referenced.passed is True
    assert unreferenced.passed is False
    assert "bazi_deep_text_not_grounded" in unreferenced.errors
