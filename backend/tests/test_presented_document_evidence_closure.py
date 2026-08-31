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
        {
            "document_id": "reading-version:test",
            "reading_version_id": "00000000-0000-0000-0000-000000000001",
            "accepted_copy_ref": "accepted-copy:test",
            "product_version": "bazi-reading/test",
            "presentation_contract_version": "bazi-presentation/test",
            "view_model": view_model.model_dump(mode="json"),
            "answer_summary": "公开结论",
            "subject_summaries": [{"subject_ref": subject_ref, "label": "本人"}],
            "themes": [{"theme_id": "career", "label": "事业"}],
            "claims": [],
            "evidence": [
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
    )

    projected = _project_presented_document(
        document,
        view_model=view_model,
        public_fact_refs=frozenset({public_fact_ref}),
    )

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
