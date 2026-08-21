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

    def _claim_by_id(self, claims: tuple, claim_unit_id: str):
        return next(
            finding
            for finding in claims
            if finding.data["claim_unit_id"] == claim_unit_id
        )

    def test_bazi_prepare_emits_seven_exact_public_claim_units(self) -> None:
        result = self._prepare(["乙酉", "辛巳", "丙午", "癸巳"])
        claims = self._public_claims(result)
        self.assertEqual(len(claims), 7, result.brief.to_dict())
        self.assertEqual(
            {finding.data["claim_unit_id"] for finding in claims},
            {
                "bazi.month-order-state-v1",
                "bazi.day-master-root-support-v1",
                "bazi.ziping-pattern-entry-v1",
                "bazi.tiaohou-priority-v1",
                "bazi.pillar-roles-v1",
                "bazi.three-yuan-structure-v1",
                "bazi.element-flow-inventory-v1",
            },
        )
        self._assert_exact_claim_shape(result, claims)

        root = self._claim_by_id(claims, "bazi.day-master-root-support-v1")
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

        pillar_roles = self._claim_by_id(claims, "bazi.pillar-roles-v1")
        self.assertEqual(
            pillar_roles.public_text,
            (
                "四柱以日干丙为主：年柱乙酉为本，月柱辛巳为提纲，时柱癸巳为辅佐；"
                "这只是四柱判读次序的定位，格局、旺衰与吉凶仍未裁定。"
            ),
        )
        self.assertEqual(
            pillar_roles.evidence_refs,
            ("evidence:bazi/bazi/yuanhai-ziping#YR-M01",),
        )

        three_yuan = self._claim_by_id(claims, "bazi.three-yuan-structure-v1")
        self.assertEqual(
            three_yuan.public_text,
            (
                "四柱天干乙、辛、丙、癸为天元；地支酉、巳、午、巳为地元；"
                "支中所藏（年酉藏辛，月巳藏丙庚戊，日午藏丁己，时巳藏丙庚戊）"
                "为人元；这只是干支藏三元的结构陈列，格局与吉凶仍未裁定。"
            ),
        )
        self.assertEqual(
            three_yuan.evidence_refs,
            ("evidence:bazi/bazi/ditiansui-chanwei#DR-01-01",),
        )

        element_flow = self._claim_by_id(
            claims, "bazi.element-flow-inventory-v1"
        )
        self.assertEqual(
            element_flow.public_text,
            (
                "盘中五行（含支藏）出现次数为木1、火7、土3、金5、水1；"
                "五行顺则相生、逆则相克，日主五行为火，生火者为木；"
                "这只是五行计数与生克次序的陈列，整盘旺衰、喜忌与吉凶仍未裁定。"
            ),
        )
        self.assertEqual(
            element_flow.evidence_refs,
            ("evidence:bazi/bazi/sanming-tonghui#R-01-02",),
        )

    def test_root_support_unit_fail_closes_when_transformation_is_in_play(
        self,
    ) -> None:
        # 甲己合土 and 辰月土令: 化神当令 is mechanically in play.  The
        # structural units keep rendering: pillar roles, the three-yuan
        # layout, and the element inventory stay valid chart facts even
        # when a transformation regime blocks the root-support synthesis.
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
                "bazi.pillar-roles-v1",
                "bazi.three-yuan-structure-v1",
                "bazi.element-flow-inventory-v1",
            },
        )
        self._assert_exact_claim_shape(result, claims)


if __name__ == "__main__":
    unittest.main()
