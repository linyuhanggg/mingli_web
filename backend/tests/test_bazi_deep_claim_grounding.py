from __future__ import annotations

from app.readings.candidate_reference_closer import close_candidate_references
from app.readings.narrative_contracts import NarrativeCandidate
from app.readings.narrative_guard import NarrativeGuard
from app.readings.output_contracts import BAZI_DEEP_V1, PREVIEW_V1
from app.readings.runtime_contracts import ReadingBrief

FACT_TEXT = "当前结构更支持持续积累。"
FINDING_TEXT = "月令季节状态已经确定；这不等于整盘身强身弱。"
LIMIT_TEXT = "本解读仅供传统文化参考，不构成现实决策保证。"


def _brief() -> ReadingBrief:
    return ReadingBrief.from_dict(
        {
            "question": "事业上最该先抓住哪条主线？",
            "vocabulary": [],
            "facts": [
                {
                    "ref": "fact:career-structure",
                    "subject_ref": "profile-version:test",
                    "kind_id": "kind.structure",
                    "value": {"fixture": "runtime"},
                    "display_text": FACT_TEXT,
                }
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
                }
            ],
            "findings": [
                {
                    "ref": "finding:career-main",
                    "subject_ref": "profile-version:test",
                    "dimension_ids": ["career"],
                    "kind_id": "kind.tendency",
                    "data": {"runtime_candidate": True},
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
                }
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
    )


def _candidate(text: str | tuple[str, str, str]) -> NarrativeCandidate:
    texts = (
        text
        if isinstance(text, tuple)
        else tuple(
            [text]
            + [item for item in (FACT_TEXT, FINDING_TEXT, LIMIT_TEXT) if item != text][
                :2
            ]
        )
    )
    return NarrativeCandidate.from_dict(
        {
            "schema_version": "mingli-narrative-candidate-v1",
            "blocks": [
                {
                    "block_id": f"b{index}",
                    "block_type": "claim",
                    "text": block_text,
                    "subject_ref": "profile-version:test",
                    "dimension_id": "career",
                    "claim_kind_id": "kind.tendency",
                    "certainty_id": "certainty.tendency",
                    # Runtime findings are the source of these dependencies;
                    # the closer adds them before Guard runs, as production does.
                    "fact_refs": [],
                    "finding_refs": ["finding:career-main"],
                    "evidence_refs": [],
                    "limit_kind_ids": [],
                }
                for index, block_text in enumerate(texts, start=1)
            ],
        }
    )


def _closed_candidate(text: str) -> NarrativeCandidate:
    brief = _brief()
    return close_candidate_references(_candidate(text), brief)


def test_bazi_deep_rejects_unrelated_hard_claim_with_legal_refs() -> None:
    brief = _brief()
    candidate = _closed_candidate("这是一句与当前 Runtime 事实无关的硬断。")

    result = NarrativeGuard().validate(candidate, brief, BAZI_DEEP_V1)

    assert result.passed is False
    assert result.errors == ("bazi_deep_text_not_grounded",)


def test_bazi_deep_accepts_runtime_finding_when_text_is_an_enumerated_fact() -> None:
    brief = _brief()
    candidate = _closed_candidate(FACT_TEXT)

    result = NarrativeGuard().validate(candidate, brief, BAZI_DEEP_V1)

    assert result.passed is True
    assert result.errors == ()
    assert candidate.blocks[0].fact_refs == ("fact:career-structure",)
    assert candidate.blocks[0].finding_refs == ("finding:career-main",)


def test_bazi_deep_accepts_exact_runtime_public_claim_unit() -> None:
    brief = _brief()
    candidate = _closed_candidate(
        FINDING_TEXT
    )

    result = NarrativeGuard().validate(candidate, brief, BAZI_DEEP_V1)

    assert result.passed is True
    assert result.errors == ()
    assert candidate.blocks[0].finding_refs == ("finding:career-main",)


def test_preview_keeps_reference_closure_without_bazi_deep_grounding() -> None:
    brief = _brief()
    candidate = _closed_candidate("这是一句与当前 Runtime 事实无关的硬断。")

    result = NarrativeGuard().validate(candidate, brief, PREVIEW_V1)

    assert result.passed is True
    assert result.errors == ()


def test_bazi_deep_does_not_treat_opaque_finding_data_as_public_prose() -> None:
    brief = _brief()
    candidate = _closed_candidate("runtime_candidate=True，因此今年必然成功。")

    result = NarrativeGuard().validate(candidate, brief, BAZI_DEEP_V1)

    assert result.passed is False
    assert "bazi_deep_text_not_grounded" in result.errors


def test_bazi_deep_exact_copy_does_not_accept_extra_text() -> None:
    brief = _brief()
    candidate = _closed_candidate("当前结构更支持持续积累。 但这不是 Runtime 文案。")

    result = NarrativeGuard().validate(candidate, brief, BAZI_DEEP_V1)

    assert result.passed is False
    assert "bazi_deep_text_not_grounded" in result.errors


def test_bazi_deep_rejects_repeating_one_source_to_fill_three_blocks() -> None:
    brief = _brief()
    candidate = _closed_candidate((FINDING_TEXT, FINDING_TEXT, FINDING_TEXT))

    result = NarrativeGuard().validate(candidate, brief, BAZI_DEEP_V1)

    assert result.passed is False
    assert result.errors == ("bazi_deep_duplicate_source",)


def test_bazi_deep_finding_must_keep_exact_evidence_contract() -> None:
    for mutation in ("shared_turn", "no_evidence", "legacy_evidence", "wrong_support"):
        payload = _brief().to_dict()
        finding = payload["findings"][0]
        evidence = payload["evidence"][0]
        if mutation == "shared_turn":
            finding["support_mode"] = "shared_turn"
        elif mutation == "no_evidence":
            finding["evidence_refs"] = []
        elif mutation == "legacy_evidence":
            for key in (
                "evidence_ref",
                "rule_id",
                "verification_status",
                "verbatim_excerpt",
                "verbatim_citations",
            ):
                evidence.pop(key)
        else:
            evidence["supports_fact_refs"] = ["fact:not-the-finding-source"]
        brief = ReadingBrief.from_dict(payload)
        candidate = _closed_candidate(FINDING_TEXT)

        result = NarrativeGuard().validate(candidate, brief, BAZI_DEEP_V1)

        assert result.passed is False, mutation
        assert "bazi_deep_text_not_grounded" in result.errors
