from __future__ import annotations

from app.readings.candidate_reference_closer import close_candidate_references
from app.readings.narrative_contracts import NarrativeCandidate
from app.readings.narrative_guard import NarrativeGuard
from app.readings.output_contracts import PREVIEW_V1
from app.readings.runtime_contracts import ReadingBrief


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
                    "value": {"fixture": "stable"},
                    "display_text": "当前结构更支持持续积累。",
                },
                {
                    "ref": "fact:day-master",
                    "subject_ref": "profile-version:test",
                    "kind_id": "kind.structure",
                    "value": {"fixture": "day"},
                    "display_text": "日主测试。",
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
                    "ref": "evidence:classic-day",
                    "source_title": "日主古籍",
                    "locator": None,
                    "excerpt": None,
                    "supports_fact_refs": ["fact:day-master"],
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
                    "allowed_kind_ids": ["kind.tendency", "kind.fact"],
                    "certainty_ceiling_id": "certainty.tendency",
                    "fact_refs": ["fact:career-structure", "fact:day-master"],
                    "evidence_refs": ["evidence:classic-1", "evidence:classic-day"],
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


def test_close_candidate_pulls_finding_and_evidence_dependencies() -> None:
    open_candidate = NarrativeCandidate.from_dict(
        {
            "schema_version": "mingli-narrative-candidate-v1",
            "blocks": [
                {
                    "block_id": "b1",
                    "block_type": "claim",
                    "text": "事业主线更适合先抓住可持续积累。",
                    "subject_ref": "profile-version:test",
                    "dimension_id": "career",
                    "claim_kind_id": "kind.tendency",
                    "certainty_id": "certainty.tendency",
                    "fact_refs": ["fact:day-master"],
                    "finding_refs": ["finding:career-main"],
                    "evidence_refs": ["evidence:classic-day"],
                    "limit_kind_ids": [],
                }
            ],
        }
    )
    brief = _brief()
    guard = NarrativeGuard()
    before = guard.validate(open_candidate, brief, PREVIEW_V1)
    assert before.passed is False
    assert "scope_mismatch" in before.errors

    closed = close_candidate_references(open_candidate, brief)
    after = guard.validate(closed, brief, PREVIEW_V1)
    assert after.passed is True, after.errors
    block = closed.blocks[0]
    assert "fact:career-structure" in block.fact_refs
    assert "evidence:classic-1" in block.evidence_refs
    assert "limit:traditional" in block.limit_kind_ids


def test_close_candidate_drops_out_of_scope_refs() -> None:
    candidate = NarrativeCandidate.from_dict(
        {
            "schema_version": "mingli-narrative-candidate-v1",
            "blocks": [
                {
                    "block_id": "b1",
                    "block_type": "claim",
                    "text": "事业主线更适合先抓住可持续积累。",
                    "subject_ref": "profile-version:test",
                    "dimension_id": "career",
                    "claim_kind_id": "kind.tendency",
                    "certainty_id": "certainty.tendency",
                    "fact_refs": ["fact:career-structure", "fact:not-in-brief"],
                    "finding_refs": [],
                    "evidence_refs": ["evidence:classic-1", "evidence:ghost"],
                    "limit_kind_ids": ["limit:ghost"],
                }
            ],
        }
    )
    closed = close_candidate_references(candidate, _brief())
    block = closed.blocks[0]
    assert block.fact_refs == ("fact:career-structure",)
    assert block.evidence_refs == ("evidence:classic-1",)
    assert block.limit_kind_ids == ()
    assert NarrativeGuard().validate(closed, _brief(), PREVIEW_V1).passed is True
