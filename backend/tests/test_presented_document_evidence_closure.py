from __future__ import annotations

from app.charts.projectors import project_runtime_view_model
from app.readings.presentation.contracts import ReadingDocumentV1
from app.readings.presentation.fact_panel import project_presented_fact_panel
from app.readings.runtime_contracts import ReadingBrief
from app.readings.service import (
    _presented_public_facts,
    _project_presented_document,
)


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


def _deep_bazi_brief(subject_ref: str = "profile-version:test") -> ReadingBrief:
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
                },
                {
                    "ref": f"fact:{subject_ref}/calculated/bazi/day_master",
                    "subject_ref": subject_ref,
                    "kind_id": "kind.fact",
                    "value": {"stem": "丙", "element": "火", "polarity": "阳"},
                    "display_text": "日主已由 Runtime 计算。",
                },
                {
                    "ref": f"fact:{subject_ref}/calculated/bazi/xunkong",
                    "subject_ref": subject_ref,
                    "kind_id": "kind.fact",
                    "value": {
                        "day_pillar": "丙寅",
                        "xun": "甲子",
                        "branches": ["戌", "亥"],
                        "source_dependency_id": "bazi.chart.xunkong-sexagenary-v1",
                        "boundary": "只表示旬空位置事实。",
                    },
                    "display_text": "旬空已由 Runtime 计算。",
                },
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


def _project(
    document: ReadingDocumentV1,
    *,
    brief: ReadingBrief,
    view_model: object,
) -> ReadingDocumentV1 | None:
    panel = project_presented_fact_panel(brief, view_model=view_model)
    assert panel is not None
    return _project_presented_document(
        document,
        view_model=view_model,
        public_facts=_presented_public_facts(panel),
    )


def test_project_presented_document_keeps_empty_support_evidence() -> None:
    subject_ref = "profile-version:test"
    public_fact_ref = f"fact:{subject_ref}/calculated/bazi/four_pillars"
    removed_fact_ref = f"fact:{subject_ref}/calculated/bazi/unknown_engine_dump"
    brief = _minimal_bazi_brief(subject_ref)
    view_model = project_runtime_view_model(
        brief.to_dict(),
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

    projected = _project(document, brief=brief, view_model=view_model)

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
    removed_fact_ref = f"fact:{subject_ref}/calculated/bazi/unknown_engine_dump"
    brief = _minimal_bazi_brief(subject_ref)
    view_model = project_runtime_view_model(
        brief.to_dict(),
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

    projected = _project(document, brief=brief, view_model=view_model)

    assert projected is None


def test_project_presented_document_fail_closes_when_deep_claims_fall_below_minimum() -> None:
    subject_ref = "profile-version:test"
    public_fact_ref = f"fact:{subject_ref}/calculated/bazi/four_pillars"
    removed_fact_ref = f"fact:{subject_ref}/calculated/bazi/unknown_engine_dump"
    brief = _minimal_bazi_brief(subject_ref)
    view_model = project_runtime_view_model(
        brief.to_dict(),
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

    projected = _project(document, brief=brief, view_model=view_model)

    assert projected is None


def test_project_presented_document_rebuilds_bazi_deep_claims_to_final_fact_text() -> None:
    subject_ref = "profile-version:test"
    brief = _deep_bazi_brief(subject_ref)
    view_model = project_runtime_view_model(brief.to_dict(), product_id="bazi")
    assert view_model is not None
    panel = project_presented_fact_panel(brief, view_model=view_model)
    assert panel is not None
    public_facts = _presented_public_facts(panel)
    four_pillars = f"fact:{subject_ref}/calculated/bazi/four_pillars"
    day_master = f"fact:{subject_ref}/calculated/bazi/day_master"
    xunkong = f"fact:{subject_ref}/calculated/bazi/xunkong"
    assert public_facts[four_pillars] == "四柱：年柱甲子、月柱乙丑、日柱丙寅、时柱丁卯。"
    assert public_facts[day_master] == "日主：丙火（阳）。"
    assert public_facts[xunkong] == "旬空：日柱丙寅 · 甲子旬 · 旬空戌/亥。"
    stale = "已由 Runtime 计算。"
    document = ReadingDocumentV1.model_validate(
        _document_payload(
            subject_ref=subject_ref,
            view_model=view_model,
            product_version="bazi-deep-reading/v1",
            presentation_contract_version="bazi-deep-presentation/v1",
            claims=[
                _claim(
                    claim_id="claim:four-pillars",
                    text=f"四柱{stale}",
                    subject_ref=subject_ref,
                    fact_refs=[four_pillars],
                ),
                _claim(
                    claim_id="claim:day-master",
                    text=f"日主{stale}",
                    subject_ref=subject_ref,
                    fact_refs=[day_master],
                ),
                _claim(
                    claim_id="claim:xunkong",
                    text=f"旬空{stale}",
                    subject_ref=subject_ref,
                    fact_refs=[xunkong],
                ),
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
        public_facts=public_facts,
    )

    assert projected is not None
    assert [claim.text for claim in projected.claims] == [
        public_facts[four_pillars],
        public_facts[day_master],
        public_facts[xunkong],
    ]
    assert projected.answer_summary == public_facts[four_pillars]
    assert "已由 Runtime 计算。" not in projected.answer_summary
    assert all("已由 Runtime 计算。" not in claim.text for claim in projected.claims)
    assert [item.evidence_ref for item in projected.evidence] == [
        "evidence:empty-dependency"
    ]
    assert projected.actions.share.enabled is True
    assert projected.actions.export.enabled is True
    assert projected.presentation_contract_version == "bazi-deep-presentation/v1"
