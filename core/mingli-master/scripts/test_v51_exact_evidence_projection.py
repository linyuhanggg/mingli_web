"""Focused G1 exact-citation projection contracts."""

from __future__ import annotations

import unittest

from reading_engine.brief import _verified_public_evidence
from reading_engine.evidence_rules import production_evidence_rules
from reading_evidence_bundle import _node


class ExactEvidenceProjectionTests(unittest.TestCase):
    def test_verified_bazi_rule_carries_every_bound_original(self) -> None:
        rule = next(
            item
            for item in production_evidence_rules()
            if item.rule_id == "bazi/qiongtong-baojian#QR-01-01"
        )
        node = _node(
            (rule, ("fact:/chart_facts/output/day_master",), ("probe",)),
            titles={rule.source_pack: rule.source_title},
            reading_id="reading-g1",
            version=1,
        )

        self.assertEqual(len(node.exact_citations), 3)
        for citation in node.exact_citations:
            self.assertEqual(citation["verification_status"], "verified_exact")
            self.assertTrue(citation["verbatim_excerpt"])
            self.assertEqual(citation["source_title"], rule.source_title)
            self.assertTrue(citation["locator"])
            self.assertEqual(citation["rule_id"], rule.rule_id)

        public = _verified_public_evidence(
            {
                "ref": f"evidence:bazi/{rule.rule_id}",
                "verification_status": "verified_exact",
                "verbatim_excerpt": node.exact_citations[0]["verbatim_excerpt"],
                "source_title": node.exact_citations[0]["source_title"],
                "locator": node.exact_citations[0]["locator"],
                "rule_id": rule.rule_id,
                "verbatim_citations": node.exact_citations,
                "supports_fact_refs": [],
            }
        )
        self.assertIsNotNone(public)
        assert public is not None
        self.assertEqual(public.evidence_ref, f"evidence:bazi/{rule.rule_id}")
        self.assertEqual(public.evidence_ref, public.ref)
        self.assertEqual(
            set(public.to_dict()),
            {
                "ref",
                "evidence_ref",
                "verification_status",
                "verbatim_excerpt",
                "source_title",
                "locator",
                "rule_id",
                "excerpt",
                "verbatim_citations",
                "supports_fact_refs",
            },
        )

    def test_public_projection_never_uses_rule_summary_as_original(self) -> None:
        item = _verified_public_evidence(
            {
                "ref": "evidence:bazi/rule-1",
                "verification_status": "verified_exact",
                "verbatim_excerpt": "真实逐字原文",
                "source_title": "古籍",
                "locator": "fulltext.md#L12",
                "rule_id": "bazi/rule-1",
                "excerpt": "规则摘要：不可冒充原文",
                "verbatim_citations": [
                    {
                        "source_title": "古籍",
                        "locator": "fulltext.md#L12",
                        "verbatim_excerpt": "真实逐字原文",
                        "verification_status": "verified_exact",
                    },
                    {
                        "source_title": "古籍",
                        "locator": "fulltext.md#L18",
                        "verbatim_excerpt": "第二条逐字原文",
                        "verification_status": "verified_exact",
                    },
                ],
                "supports_fact_refs": [],
            }
        )

        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.verbatim_excerpt, "真实逐字原文")
        self.assertEqual(item.excerpt, "真实逐字原文")
        self.assertEqual(item.evidence_ref, "evidence:bazi/rule-1")
        self.assertEqual(len(item.verbatim_citations), 2)
        self.assertEqual(item.to_dict()["evidence_ref"], item.ref)

        list_only = _verified_public_evidence(
            {
                "evidence_ref": "evidence:bazi/rule-2",
                "verification_status": "verified_exact",
                "rule_id": "bazi/rule-2",
                "verbatim_citations": item.verbatim_citations,
                "supports_fact_refs": [],
            }
        )
        self.assertIsNotNone(list_only)
        assert list_only is not None
        self.assertEqual(list_only.source_title, "古籍")
        self.assertEqual(list_only.locator, "fulltext.md#L12")
        self.assertEqual(list_only.verbatim_excerpt, "真实逐字原文")

    def test_unverified_or_incomplete_citations_fail_closed(self) -> None:
        base = {
            "ref": "evidence:bazi/rule-1",
            "source_title": "古籍",
            "locator": "fulltext.md#L12",
            "rule_id": "bazi/rule-1",
            "verbatim_excerpt": "真实逐字原文",
            "supports_fact_refs": [],
        }
        for mutation in (
            {"verification_status": "unverified"},
            {"verification_status": "verified_exact", "locator": ""},
            {"verification_status": "verified_exact", "verbatim_excerpt": ""},
            {"evidence_ref": "evidence:bazi/other-rule"},
        ):
            with self.subTest(mutation=mutation):
                candidate = {**base, **mutation}
                self.assertIsNone(_verified_public_evidence(candidate))


if __name__ == "__main__":
    unittest.main()
