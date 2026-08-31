from __future__ import annotations

from app.charts.projectors import project_runtime_view_model
from app.readings.presentation.contracts import ReadingDocumentV1
from app.readings.runtime_contracts import ReadingBrief
from app.readings.service import _project_presented_document


def _minimal_bazi_brief(subject_ref: str = "profile-version:test") -> ReadingBrief:
    return ReadingBrief.from_dict(
        {
            "question": "查看本命四柱结构",
            "vocabulary": [],
            "facts": [
                {
                    "ref": f"fact:{subject_ref}/calculated/bazi/four_pillars",
                    "subject_ref": subject_ref,
                    "kind_id": "kind.fact",
                    "value": {
                        "year": "甲子",
                        "month": "乙丑",
                        "day": "丙寅",
                        "hour": "丁卯",
                    },
                    "display_text": "四柱已由 Runtime 计算。",
                }
            ],
            "evidence": [],
            "findings": [],
            "claim_scopes": [],
            "limits": [],
            "prior_answer": None,
            "request_view": {
                "subject_refs": [subject_ref],
                "capability_ids": ["bazi"],
                "object_id": "natal",
                "dimension_ids": ["overview"],
                "horizon": {"kind_id": "life", "start": None, "end": None},
            },
        }
    )


def _document_payload(
    *,
    subject_ref: str,
    view_model: object,
    product_version: str,
    presentation_contract_version: str,
    claims: list[dict[str, object]],
    evidence: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "document_id": "reading-version:test",
        "reading_version_id": "00000000-0000-0000-0000-000000000001",
        "accepted_copy_ref": "accepted-copy:test",
        "product_version": product_version,
        "presentation_contract_version": presentation_contract_version,
        "view_model": view_model.model_dump(mode="json"),
        "answer_summary": claims[0]["text"] if claims else "占位",
        "subject_summaries": [{"subject_ref": subject_ref, "label": "本人"}],
        "themes": [{"theme_id": "career", "label": "事业"}],
        "claims": claims,
        "evidence": evidence,
        "boundaries": [],
        "actions": {
            "correction": {"enabled": True},
            "follow_up": {"enabled": False},
            "export": {"enabled": True},
            "share": {"enabled": True},
        },
        "versions": {
            "runtime_release": "mingli-runtime/test",
            "view_model_schema": view_model.schema_version,
        },
    }


def _claim(
    *,
    claim_id: str,
    text: str,
    subject_ref: str,
    fact_refs: list[str],
    evidence_refs: list[str] | None = None,
) -> dict[str, object]:
    return {
        "claim_id": claim_id,
        "section_id": "overview",
        "text": text,
        "subject_ref": subject_ref,
        "dimension_id": "career",
        "claim_kind_id": "kind.tendency",
        "certainty_id": "certainty.tendency",
        "fact_refs": fact_refs,
        "finding_refs": [],
        "evidence_refs": evidence_refs or [],
        "limit_refs": [],
        "verification": {"enabled": True},
    }


def test_project_presented_document_keeps_empty_support_evidence() -> None:
    subject_ref = "profile-version:test"
    public_fact_ref = f"fact:{subject_ref}/calculated/bazi/four_pillars"
    removed_fact_ref = f"fact:{subject_ref}/calculated/bazi/unknown_engine_dump"
    view_model = project_runtime_view_model(
        _minimal_bazi_brief(subject_ref).to_dict(),
        product_id="bazi",
    )
    assert view_model is not None
    document = ReadingDocumentV1.model_validate(
        _document_payload(
            subject_ref=subject_ref,
            view_model=view_model,
            product_version="bazi-reading/test",
            presentation_contract_version="bazi-presentation/test",
            claims=[
                _claim(
                    claim_id="claim:public",
                    text="公开结论",
                    subject_ref=subject_ref,
                    fact_refs=[public_fact_ref],
                    evidence_refs=["evidence:public-only"],
                )
            ],
            evidence=[
                {
                    "evidence_ref": "evidence:mixed-must-drop",
                    "title": "MIXED-EVIDENCE-MUST-DROP",
                    "supports_fact_refs": [public_fact_ref, removed_fact_ref],
                },
                {
                    "evidence_ref": "evidence:empty-dependency",
                    "title": "EMPTY-DEPENDENCY-EVIDENCE-MUST-KEEP",
                    "supports_fact_refs": [],
                },
                {
                    "evidence_ref": "evidence:public-only",
                    "title": "公开依据",
                    "supports_fact_refs": [public_fact_ref],
                },
            ],
        )
    )

    projected = _project_presented_document(
        document,
        view_model=view_model,
        public_fact_refs=frozenset({public_fact_ref}),
    )

    assert projected is not None
    assert [item.evidence_ref for item in projected.evidence] == [
        "evidence:empty-dependency",
        "evidence:public-only",
    ]
    assert "EMPTY-DEPENDENCY-EVIDENCE-MUST-KEEP" in {
        item.title for item in projected.evidence
    }
    assert "MIXED-EVIDENCE-MUST-DROP" not in {
        item.title for item in projected.evidence
    }
    assert [claim.claim_id for claim in projected.claims] == ["claim:public"]
    assert projected.actions.share.enabled is True
    assert projected.actions.export.enabled is True


def test_project_presented_document_fail_closes_when_sole_claim_is_culled() -> None:
    subject_ref = "profile-version:test"
    public_fact_ref = f"fact:{subject_ref}/calculated/bazi/four_pillars"
    removed_fact_ref = f"fact:{subject_ref}/calculated/bazi/unknown_engine_dump"
    view_model = project_runtime_view_model(
        _minimal_bazi_brief(subject_ref).to_dict(),
        product_id="bazi",
    )
    assert view_model is not None
    document = ReadingDocumentV1.model_validate(
        _document_payload(
            subject_ref=subject_ref,
            view_model=view_model,
            product_version="bazi-reading/test",
            presentation_contract_version="bazi-presentation/test",
            claims=[
                _claim(
                    claim_id="claim:unsupported-only",
                    text="SOLE-CLAIM-MUST-DROP",
                    subject_ref=subject_ref,
                    fact_refs=[removed_fact_ref],
                )
            ],
            evidence=[
                {
                    "evidence_ref": "evidence:empty-dependency",
                    "title": "EMPTY-DEPENDENCY-EVIDENCE-MUST-KEEP",
                    "supports_fact_refs": [],
                }
            ],
        )
    )

    projected = _project_presented_document(
        document,
        view_model=view_model,
        public_fact_refs=frozenset({public_fact_ref}),
    )

    assert projected is None


def test_project_presented_document_fail_closes_when_deep_claims_fall_below_minimum() -> None:
    subject_ref = "profile-version:test"
    public_fact_ref = f"fact:{subject_ref}/calculated/bazi/four_pillars"
    removed_fact_ref = f"fact:{subject_ref}/calculated/bazi/unknown_engine_dump"
    view_model = project_runtime_view_model(
        _minimal_bazi_brief(subject_ref).to_dict(),
        product_id="bazi",
    )
    assert view_model is not None
    document = ReadingDocumentV1.model_validate(
        _document_payload(
            subject_ref=subject_ref,
            view_model=view_model,
            product_version="bazi-deep-reading/v1",
            presentation_contract_version="bazi-deep-presentation/v1",
            claims=[
                _claim(
                    claim_id="claim:keep-one",
                    text="深读结论一",
                    subject_ref=subject_ref,
                    fact_refs=[public_fact_ref],
                ),
                _claim(
                    claim_id="claim:keep-two",
                    text="深读结论二",
                    subject_ref=subject_ref,
                    fact_refs=[public_fact_ref],
                ),
                _claim(
                    claim_id="claim:drop",
                    text="DEEP-CLAIM-MUST-DROP",
                    subject_ref=subject_ref,
                    fact_refs=[removed_fact_ref],
                ),
            ],
            evidence=[],
        )
    )

    projected = _project_presented_document(
        document,
        view_model=view_model,
        public_fact_refs=frozenset({public_fact_ref}),
    )

    assert projected is None
