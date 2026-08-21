"""Bazi paid-reading claim units stay deterministic and source-bound."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import (
    HorizonSelection,
    IntentSelection,
    Prepare,
    Prepared,
)


ROOT = Path(__file__).resolve().parents[1]


class BaziPublicClaimUnitTests(unittest.TestCase):
    def _prepare(
        self,
        pillars: list[str],
    ) -> Prepared:
        with tempfile.TemporaryDirectory() as temporary:
            result = ReadingInterface(
                skill_root=ROOT,
                store_root=Path(temporary),
            ).execute(
                Prepare(
                    query="请围绕事业主线生成八字结构化深读。",
                    intent=IntentSelection(
                        subject_refs=("subject:test",),
                        object_id="natal",
                        dimension_ids=("career",),
                        horizon=HorizonSelection(kind_id="life"),
                        capability_id="bazi",
                    ),
                    facts={
                        "subject:test": {
                            "birth_datetime_or_four_pillars": pillars,
                            "gender": "male",
                        }
                    },
                )
            )
        self.assertIsInstance(result, Prepared, result)
        return result

    def _public_claims(self, result: Prepared) -> tuple:
        return tuple(
            finding
            for finding in result.brief.findings
            if finding.public_text is not None
        )

    def _assert_exact_claim_shape(self, result: Prepared, claims: tuple) -> None:
        evidence = {item.ref: item for item in result.brief.evidence}
        facts = {item.ref for item in result.brief.facts}
        for finding in claims:
            self.assertEqual(finding.support_mode, "exact")
            self.assertEqual(finding.dimension_ids, ("career",))
            self.assertTrue(finding.fact_refs)
            self.assertTrue(set(finding.fact_refs) <= facts)
            self.assertEqual(len(finding.evidence_refs), 1)
            self.assertEqual(finding.limit_kind_ids, ())
            cited = evidence[finding.evidence_refs[0]]
            self.assertEqual(cited.verification_status, "verified_exact")
            self.assertTrue(cited.verbatim_citations)
            self.assertTrue(cited.supports_fact_refs)
            self.assertTrue(
                set(cited.supports_fact_refs) <= set(finding.fact_refs)
            )
            self.assertIn("未裁定", finding.public_text)
            self.assertEqual(
                finding.to_dict()["public_text"],
                finding.public_text,
            )
            self.assertIsNone(finding.data.get("hard_verdict"))
            self.assertNotIn("偏强", finding.public_text)
            self.assertNotIn("偏弱", finding.public_text)

    def test_bazi_prepare_emits_four_exact_public_claim_units(self) -> None:
        result = self._prepare(["乙酉", "辛巳", "丙午", "癸巳"])
        claims = self._public_claims(result)
        self.assertEqual(len(claims), 4, result.brief.to_dict())
        self.assertEqual(
            {finding.data["claim_unit_id"] for finding in claims},
            {
                "bazi.month-order-state-v1",
                "bazi.day-master-root-support-v1",
                "bazi.ziping-pattern-entry-v1",
                "bazi.tiaohou-priority-v1",
            },
        )
        self._assert_exact_claim_shape(result, claims)

        root = next(
            finding
            for finding in claims
            if finding.data["claim_unit_id"]
            == "bazi.day-master-root-support-v1"
        )
        self.assertEqual(
            root.public_text,
            (
                "日主五行火，月令主气五行为火，月令对日主为“旺”（当令同气生扶）；"
                "同党出现7处，印星木出现1处，五行计数为木1、火7、土3、金5、水1，"
                "同党根气在月、日、时支，透干生扶1、克泄2；"
                "这只是根气与月令生扶、克泄证据，整盘身强身弱仍未裁定，"
                "用神与吉凶仍未裁定。"
            ),
        )
        self.assertEqual(
            root.evidence_refs,
            ("evidence:bazi/bazi/sanming-tonghui#R-02-04",),
        )

    def test_root_support_unit_fail_closes_when_transformation_is_in_play(
        self,
    ) -> None:
        # 甲己合土 and 辰月土令: 化神当令 is mechanically in play.
        result = self._prepare(["己酉", "戊辰", "甲子", "乙亥"])
        claims = self._public_claims(result)
        ids = {finding.data["claim_unit_id"] for finding in claims}
        self.assertNotIn("bazi.day-master-root-support-v1", ids, result.brief.to_dict())
        self.assertEqual(
            ids,
            {
                "bazi.month-order-state-v1",
                "bazi.ziping-pattern-entry-v1",
                "bazi.tiaohou-priority-v1",
            },
        )
        self._assert_exact_claim_shape(result, claims)


if __name__ == "__main__":
    unittest.main()
