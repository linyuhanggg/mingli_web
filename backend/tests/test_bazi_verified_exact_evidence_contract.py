from __future__ import annotations

from app.charts.projectors import project_bazi_view_model
from app.readings.runtime_contracts import ReadingBrief


def _verified_exact_brief_payload() -> dict[str, object]:
    evidence_ref = "evidence:bazi/bazi/qiongtong-baojian#QR-02-04"
    rule_id = "bazi/qiongtong-baojian#QR-02-04"
    return {
        "question": "查看本命四柱结构",
        "vocabulary": [],
        "facts": [],
        "evidence": [
            {
                "ref": evidence_ref,
                "evidence_ref": evidence_ref,
                "rule_id": rule_id,
                "source_title": "穷通宝鉴",
                "locator": "fulltext.md#L507",
                "excerpt": "十月丙火，木旺宜庚，水旺宜戊，火旺用壬，随宜酌用可也",
                "verification_status": "verified_exact",
                "verbatim_excerpt": "十月丙火，木旺宜庚，水旺宜戊，火旺用壬，随宜酌用可也",
                "verbatim_citations": [
                    {
                        "source_title": "穷通宝鉴",
                        "locator": "fulltext.md#L507",
                        "verbatim_excerpt": "十月丙火，木旺宜庚，水旺宜戊，火旺用壬，随宜酌用可也",
                        "verification_status": "verified_exact",
                    },
                    {
                        "source_title": "穷通宝鉴",
                        "locator": "fulltext.md#L518",
                        "verbatim_excerpt": "十一月丙火，冬至一阳生，弱中复强，壬水为最，戊土佐之",
                        "verification_status": "verified_exact",
                    },
                ],
                "supports_fact_refs": [],
            }
        ],
        "findings": [],
        "claim_scopes": [],
        "limits": [],
        "prior_answer": None,
        "request_view": {
            "subject_refs": ["profile-version:test"],
            "capability_ids": ["bazi"],
            "object_id": "natal",
            "dimension_ids": ["overview"],
            "horizon": {"kind_id": "life", "start": None, "end": None},
        },
    }


def _bazi_pattern_facts() -> list[dict[str, object]]:
    return [
        {
            "ref": "fact:profile-version:test/calculated/bazi/four_pillars",
            "subject_ref": "profile-version:test",
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
            "ref": (
                "fact:profile-version:test/calculated/bazi/"
                "source_conditioned_patterns"
            ),
            "subject_ref": "profile-version:test",
            "kind_id": "kind.fact",
            "value": [
                {
                    "rule_id": "bazi/qiongtong-baojian#QR-02-04",
                    "local_rule_id": "QR-02-04",
                    "title": "冬月丙火条件",
                    "source_pack": "bazi/qiongtong-baojian",
                    "source_anchor": "rules.md#QR-02-04",
                    "status": "predicate_matched_not_verdict",
                    "fact_paths": ["/day_master/stem"],
                    "predicate_audit": ["/day_master/stem:eq:丙"],
                }
            ],
            "display_text": "经典来源条件已命中，尚未形成裁决。",
        },
    ]


def test_reading_brief_accepts_verified_exact_multi_citation_evidence() -> None:
    brief = ReadingBrief.from_dict(_verified_exact_brief_payload())

    evidence = brief.to_dict()["evidence"][0]
    assert evidence["verification_status"] == "verified_exact"
    assert evidence["rule_id"] == "bazi/qiongtong-baojian#QR-02-04"
    assert [item["locator"] for item in evidence["verbatim_citations"]] == [
        "fulltext.md#L507",
        "fulltext.md#L518",
    ]


def test_bazi_pattern_does_not_link_legacy_summary_evidence() -> None:
    payload = _verified_exact_brief_payload()
    payload["facts"] = _bazi_pattern_facts()
    payload["evidence"] = [
        {
            "ref": "evidence:bazi/bazi/qiongtong-baojian#QR-02-04",
            "source_title": "穷通宝鉴",
            "locator": "rules.md#QR-02-04",
            "excerpt": "这是规则摘要，不是古籍逐字原文。",
            "supports_fact_refs": [],
        }
    ]

    view_model = project_bazi_view_model(ReadingBrief.from_dict(payload))

    assert view_model is not None
    assert view_model.core_facts is not None
    assert view_model.core_facts.source_conditioned_patterns[0].evidence_ref is None


def test_bazi_pattern_links_complete_verified_exact_evidence() -> None:
    payload = _verified_exact_brief_payload()
    payload["facts"] = _bazi_pattern_facts()

    view_model = project_bazi_view_model(ReadingBrief.from_dict(payload))

    assert view_model is not None
    assert view_model.core_facts is not None
    assert view_model.core_facts.source_conditioned_patterns[0].evidence_ref == (
        "evidence:bazi/bazi/qiongtong-baojian#QR-02-04"
    )


def test_bazi_pattern_rejects_conflicting_legacy_excerpt() -> None:
    payload = _verified_exact_brief_payload()
    payload["facts"] = _bazi_pattern_facts()
    evidence = dict(payload["evidence"][0])
    evidence["excerpt"] = "这是规则摘要，不是首条古籍原文。"
    payload["evidence"] = [evidence]

    view_model = project_bazi_view_model(ReadingBrief.from_dict(payload))

    assert view_model is not None
    assert view_model.core_facts is not None
    assert view_model.core_facts.source_conditioned_patterns[0].evidence_ref is None


def test_bazi_pattern_accepts_legacy_excerpt_when_it_matches_first_citation() -> None:
    payload = _verified_exact_brief_payload()
    payload["facts"] = _bazi_pattern_facts()
    evidence = dict(payload["evidence"][0])
    evidence["excerpt"] = evidence["verbatim_excerpt"]
    payload["evidence"] = [evidence]

    view_model = project_bazi_view_model(ReadingBrief.from_dict(payload))

    assert view_model is not None
    assert view_model.core_facts is not None
    assert view_model.core_facts.source_conditioned_patterns[0].evidence_ref == (
        "evidence:bazi/bazi/qiongtong-baojian#QR-02-04"
    )
