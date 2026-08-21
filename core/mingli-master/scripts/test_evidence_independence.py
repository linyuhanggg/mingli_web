"""Tests for explicit source relationships without confidence arithmetic."""

from __future__ import annotations

import unittest

from evidence_independence import (
    independent_lineages,
    source_lineage,
    source_relationships,
)
from reading_engine.contracts import EvidenceNode


def node(rule_id: str, lineage: str) -> EvidenceNode:
    return EvidenceNode(
        rule_id=rule_id,
        source="fixture",
        anchor="fixture#L1-L1",
        applicability="fact:fixture",
        assertion="fixture",
        lineage=lineage,
        quote_hash="a" * 64,
    )


class EvidenceIndependenceTests(unittest.TestCase):
    def test_same_ziping_mainline_books_count_as_one_lineage(self) -> None:
        refs = [
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-01-03"},
            {"pack": "bazi/sanming-tonghui", "rule_id": "R-01-01"},
        ]
        self.assertEqual(independent_lineages(refs), {"bazi.ziping-mainline"})

    def test_distinct_commentarial_lineage_can_be_counted_separately(self) -> None:
        refs = [
            {"pack": "bazi/yuanhai-ziping", "rule_id": "YR-01-03"},
            {"pack": "bazi/ditiansui-chanwei", "rule_id": "DR-01-01"},
        ]
        self.assertEqual(
            independent_lineages(refs),
            {"bazi.ziping-mainline", "bazi.ditiansui-commentarial"},
        )

    def test_relationships_keep_derived_parallel_independent_and_conflict_explicit(self) -> None:
        supporting = (
            node("same-a", "bazi.ziping-mainline"),
            node("same-b", "bazi.ziping-mainline"),
            node("independent", "bazi.ditiansui-commentarial"),
            node("unknown", "unregistered:fixture"),
        )
        counters = (node("counter", "bazi.qiongtong-commentarial"),)

        relationships = source_relationships(supporting, counters)
        relations = {item.relation for item in relationships}

        self.assertEqual(
            relations,
            {"derived", "parallel", "independent", "conflict"},
        )
        self.assertFalse(any(hasattr(item, "confidence") for item in relationships))

    def test_unknown_pack_is_not_silently_treated_as_independent(self) -> None:
        with self.assertRaisesRegex(ValueError, "unregistered source pack"):
            source_lineage("bazi/not-a-real-pack")


if __name__ == "__main__":
    unittest.main()
