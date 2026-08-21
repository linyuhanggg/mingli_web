"""Tests for source-bound v4 fact and evidence artifacts."""

from __future__ import annotations

import hashlib
import json
import unittest
from dataclasses import replace
from pathlib import Path

import reading_evidence_bundle
import reading_source_plan
from reading_engine.contracts import (
    CalculationResult,
    Judgment,
    PreparedReadingRecord,
    ReadingRequest,
)
from reading_engine.fact_index import build_fact_index
from reading_engine.providers import BaziProvider


ROOT = Path(__file__).resolve().parents[1]
READING_ID = "a" * 32


def calculation() -> CalculationResult:
    return CalculationResult.create(
        system="bazi",
        provider_id=BaziProvider.provider_id,
        provider_version=BaziProvider.provider_version,
        input_payload={"pillars": ["乙酉", "辛巳", "丙午", "癸巳"]},
        facts={
            "chart": {
                "four_lessons": ["乙酉", "辛巳", "丙午", "癸巳"],
                "day_master": "丙",
                "month_branch": "巳",
                "nested/key": {"tilde~key": True},
            }
        },
    )


def goal() -> dict:
    return {
        "requested_resolution": "比较当前事实可支持与不能支持的范围",
        "evidence_questions": ["月令和日主之间有哪些可核验规则"],
        "counter_evidence_questions": ["哪些规则构成反例或限制"],
        "source_packs": [
            "bazi/yuanhai-ziping",
            "bazi/sanming-tonghui",
            "bazi/ditiansui-chanwei",
        ],
        "comparison_packs": ["bazi/qiongtong-baojian"],
    }


def artifacts():
    current = calculation()
    current_goal = goal()
    plan = reading_source_plan.compile_source_plan(
        "bazi", current_goal, current.facts
    )
    index = build_fact_index(current, reading_id=READING_ID, version=1)
    bundle = reading_evidence_bundle.compile_evidence_bundle(
        current_goal,
        current.facts,
        plan,
        fact_index=index,
        reading_id=READING_ID,
        version=1,
    )
    return current, current_goal, plan, index, bundle


class ReadingEvidenceBundleTests(unittest.TestCase):
    def test_zero_score_fallback_requires_source_conditioned_methodology_rule(
        self,
    ) -> None:
        rules = {
            rule.rule_id: rule
            for rule in reading_evidence_bundle.production_evidence_rules()
        }
        methodology = rules["bazi/ditiansui-chanwei#DR-01-01"]
        judgment = rules["bazi/sanming-tonghui#R-02-04"]
        second_methodology = replace(
            methodology,
            rule_id="bazi/ditiansui-chanwei#DR-fixture",
            local_rule_id="DR-fixture",
            chapter="fixture chapter",
            title="fixture title",
            quote="fixture quote",
            topics=(),
        )
        methodology_candidate = (methodology, ("fact:/four_pillars",), ("matched",))
        judgment_candidate = (judgment, ("fact:/day_master",), ("matched",))
        second_candidate = (
            second_methodology,
            ("fact:/four_pillars",),
            ("matched",),
        )
        zero_score_terms = ["zzzz-selector-zero-token"]

        self.assertEqual(
            reading_evidence_bundle._rank_rules(
                [methodology_candidate],
                zero_score_terms,
                source_conditioned_rule_ids={methodology.rule_id},
            ),
            [methodology_candidate],
        )
        self.assertEqual(
            reading_evidence_bundle._rank_rules(
                [methodology_candidate],
                zero_score_terms,
                source_conditioned_rule_ids=set(),
            ),
            [],
        )
        self.assertEqual(
            reading_evidence_bundle._rank_rules(
                [(methodology, (), ("matched",))],
                zero_score_terms,
                source_conditioned_rule_ids={methodology.rule_id},
            ),
            [],
        )
        self.assertEqual(
            reading_evidence_bundle._rank_rules(
                [judgment_candidate],
                zero_score_terms,
                source_conditioned_rule_ids={judgment.rule_id},
            ),
            [],
        )
        self.assertEqual(
            reading_evidence_bundle._rank_rules(
                [methodology_candidate, second_candidate],
                zero_score_terms,
                source_conditioned_rule_ids={second_methodology.rule_id},
            ),
            [],
        )

    def test_fact_index_has_stable_json_pointer_ids_and_provider_provenance(self) -> None:
        current = calculation()

        first = build_fact_index(current, reading_id=READING_ID, version=1)
        second = build_fact_index(current, reading_id=READING_ID, version=1)

        self.assertEqual(first, second)
        by_path = {item.path: item for item in first}
        escaped = "/chart/nested~1key/tilde~0key"
        self.assertIn(escaped, by_path)
        self.assertEqual(by_path[escaped].fact_id, f"fact:{escaped}")
        self.assertEqual(by_path[escaped].provider_id, BaziProvider.provider_id)
        self.assertEqual(
            by_path[escaped].provider_version,
            BaziProvider.provider_version,
        )
        self.assertEqual(by_path[escaped].reading_id, READING_ID)

    def test_compile_rejects_fact_refs_from_a_forged_provider(self) -> None:
        current = calculation()
        current_goal = goal()
        plan = reading_source_plan.compile_source_plan(
            "bazi",
            current_goal,
            current.facts,
        )
        index = build_fact_index(current, reading_id=READING_ID, version=1)
        forged = tuple(replace(item, provider_id="forged.provider") for item in index)

        with self.assertRaisesRegex(ValueError, "provider identity"):
            reading_evidence_bundle.compile_evidence_bundle(
                current_goal,
                current.facts,
                plan,
                fact_index=forged,
                reading_id=READING_ID,
                version=1,
            )

    def test_goal_and_fact_index_drive_plan_without_raw_query_taxonomy(self) -> None:
        current, current_goal, plan, index, _ = artifacts()

        self.assertEqual(plan["evidence_questions"], current_goal["evidence_questions"])
        self.assertEqual(
            plan["counter_evidence_questions"],
            current_goal["counter_evidence_questions"],
        )
        self.assertEqual(set(plan["fact_ids"]), {item.fact_id for item in index})
        self.assertNotIn("query", plan)
        self.assertNotIn("question_type", plan)
        self.assertEqual(current.facts["chart"]["day_master"], "丙")

    def test_unbound_source_rules_stay_zero_with_structured_gaps(self) -> None:
        current = calculation()
        current_goal = goal()
        plan = reading_source_plan.compile_source_plan(
            "bazi", current_goal, current.facts
        )
        source_paths = {
            ROOT / source[key]
            for source in plan["sources"]
            for key in ("rule_file", "quote_index_file")
        }
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_paths
        }
        index = build_fact_index(current, reading_id=READING_ID, version=1)

        bundle = reading_evidence_bundle.compile_evidence_bundle(
            current_goal,
            current.facts,
            plan,
            fact_index=index,
            reading_id=READING_ID,
            version=1,
        )

        nodes = (*bundle.evidence, *bundle.counter_evidence)
        self.assertEqual(nodes, ())
        self.assertIn(
            "zero_applicable_evidence",
            {gap.reason for gap in bundle.source_gaps},
        )
        self.assertIn(
            "no_applicable_counter_evidence",
            {gap.reason for gap in bundle.source_gaps},
        )
        self.assertEqual(
            before,
            {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths},
        )

    def test_zero_applicable_sources_cannot_fabricate_cross_book_relationships(self) -> None:
        _, _, _, _, bundle = artifacts()
        relations = {item.relation for item in bundle.source_relationships}

        self.assertEqual(relations, set())
        self.assertNotIn("confidence", json.dumps(bundle.to_dict(), ensure_ascii=False))

    def test_real_bazi_provider_facts_bind_exact_qiongtong_evidence(self) -> None:
        provider = BaziProvider(ROOT)
        calculation = provider.calculate(
            ReadingRequest(
                query="三秋甲木怎样取调候",
                system="bazi",
                timezone="Asia/Shanghai",
                location="上海",
                chart_data={"pillars": ["甲子", "壬申", "甲辰", "庚午"]},
            )
        )
        current_goal = {
            "evidence_questions": ["三秋甲木怎样取调候"],
            "counter_evidence_questions": ["哪些条件会限制三秋甲木取用"],
            "source_packs": ["bazi/qiongtong-baojian"],
        }
        plan = reading_source_plan.compile_source_plan(
            "bazi",
            current_goal,
            calculation.facts,
        )
        index = build_fact_index(calculation, reading_id=READING_ID, version=1)

        bundle = reading_evidence_bundle.compile_evidence_bundle(
            current_goal,
            calculation.facts,
            plan,
            fact_index=index,
            reading_id=READING_ID,
            version=1,
        )

        self.assertTrue(bundle.evidence)
        self.assertTrue(all(node.fact_refs for node in bundle.evidence))
        self.assertIn(
            "bazi/qiongtong-baojian#QR-01-03",
            {node.rule_id for node in bundle.evidence},
        )
        self.assertTrue(
            any("三秋甲木" in node.assertion for node in bundle.evidence)
        )
        for node in (*bundle.evidence, *bundle.counter_evidence):
            path = ROOT / node.source_path
            self.assertTrue(path.is_file())
            self.assertEqual(
                node.source_sha256,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            self.assertTrue(node.anchor)

    def test_bazi_verified_methodology_evidence_survives_zero_bm25_score(
        self,
    ) -> None:
        provider = BaziProvider(ROOT)
        calculation = provider.calculate(
            ReadingRequest(
                query="验证八字核心盘面",
                system="bazi",
                timezone="Asia/Shanghai",
                location="合成测试地点",
                chart_data={"pillars": ["乙酉", "辛巳", "丙午", "癸巳"]},
            )
        )
        current_goal = {
            "evidence_questions": ["验证八字核心盘面"],
            "source_packs": ["bazi/ditiansui-chanwei"],
        }
        plan = reading_source_plan.compile_source_plan(
            "bazi",
            current_goal,
            calculation.facts,
        )
        index = build_fact_index(calculation, reading_id=READING_ID, version=1)

        bundle = reading_evidence_bundle.compile_evidence_bundle(
            current_goal,
            calculation.facts,
            plan,
            fact_index=index,
            reading_id=READING_ID,
            version=1,
        )

        self.assertEqual(
            [node.rule_id for node in bundle.evidence],
            ["bazi/ditiansui-chanwei#DR-01-01"],
        )
        self.assertEqual(len(bundle.evidence[0].exact_citations), 1)
        self.assertEqual(
            bundle.evidence[0].exact_citations[0]["verification_status"],
            "verified_exact",
        )

    def test_zero_score_methodology_fallback_never_populates_counter_pack(
        self,
    ) -> None:
        provider = BaziProvider(ROOT)
        calculation = provider.calculate(
            ReadingRequest(
                query="验证八字核心盘面",
                system="bazi",
                timezone="Asia/Shanghai",
                location="合成测试地点",
                chart_data={"pillars": ["乙酉", "辛巳", "丙午", "癸巳"]},
            )
        )
        current_goal = {
            "evidence_questions": ["验证八字核心盘面"],
            "source_packs": ["bazi/sanming-tonghui"],
            "comparison_packs": ["bazi/ditiansui-chanwei"],
        }
        plan = reading_source_plan.compile_source_plan(
            "bazi",
            current_goal,
            calculation.facts,
        )
        index = build_fact_index(calculation, reading_id=READING_ID, version=1)

        bundle = reading_evidence_bundle.compile_evidence_bundle(
            current_goal,
            calculation.facts,
            plan,
            fact_index=index,
            reading_id=READING_ID,
            version=1,
        )

        self.assertNotIn(
            "bazi/ditiansui-chanwei#DR-01-01",
            {node.rule_id for node in bundle.counter_evidence},
        )

    def test_bundle_is_deterministic_and_rejects_plan_from_another_goal(self) -> None:
        current, current_goal, plan, index, first = artifacts()
        second = reading_evidence_bundle.compile_evidence_bundle(
            current_goal,
            current.facts,
            plan,
            fact_index=index,
            reading_id=READING_ID,
            version=1,
        )
        self.assertEqual(first, second)

        changed_goal = {**current_goal, "evidence_questions": ["完全不同的问题"]}
        with self.assertRaisesRegex(ValueError, "source plan mismatch"):
            reading_evidence_bundle.compile_evidence_bundle(
                changed_goal,
                current.facts,
                plan,
                fact_index=index,
                reading_id=READING_ID,
                version=1,
            )

    def test_prepared_reading_exposes_calculation_fact_index_and_evidence_not_conclusions(self) -> None:
        current, _, _, _, bundle = artifacts()
        request = ReadingRequest(
            query="调用方自由问题",
            action="new",
            system="bazi",
            reading_id=READING_ID,
        )
        judgment = Judgment.create(
            system="bazi",
            calculation_digest=current.result_hash,
            evidence_digest=bundle.bundle_digest,
            basis_label="确定性事实",
            basis_text="",
            dimensions=(),
        )
        prepared = PreparedReadingRecord.create(
            reading_id=READING_ID,
            version=1,
            request=request,
            calculation=current,
            evidence=bundle,
            judgment=judgment,
            action="new",
        ).public_contract()

        self.assertEqual(prepared.calculation, current)
        self.assertEqual(
            {item.fact_id for item in prepared.fact_index},
            set(reading_source_plan.compile_source_plan("bazi", goal(), current.facts)["fact_ids"]),
        )
        self.assertEqual(prepared.evidence, bundle.evidence)
        self.assertEqual(prepared.source_relationships, bundle.source_relationships)
        self.assertEqual(prepared.dimensions, ())


if __name__ == "__main__":
    unittest.main()
