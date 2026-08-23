#!/usr/bin/env python3
"""Golden and negative tests for the public Daliuren Runtime contract."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_liuren_structural_patterns
import liuren_calc
import liuren_fact_adapter
from reading_engine import liuren_contract
from reading_engine.liuren_contract import (
    LiurenRuntimeContractError,
    SCHEMA_VERSION,
    build_source_conditioned_patterns,
    validate_runtime_core_facts,
)


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "references" / "fixtures" / "liuren-runtime-core-facts-v1.json"
HORIZON = {"kind": "day", "start": "2026-07-10", "end": "2026-07-31"}


def _facts() -> dict:
    return liuren_fact_adapter.build_from_datetime(
        "2026-07-10T14:00:00",
        timezone_name="Asia/Shanghai",
        location="上海",
        question="脱敏契约样例",
    )


def _contract(
    dimensions: tuple[str, ...] = ("relationship", "timing"),
) -> dict:
    result = liuren_calc.extend_liuren_facts(
        _facts(),
        requested_dimensions=dimensions,
        horizon=HORIZON,
        target_relative="父母",
    )
    return result["runtime_core_facts"]


class LiurenRuntimeContractTests(unittest.TestCase):
    def test_golden_public_projection(self) -> None:
        expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
        self.assertEqual(_contract(), expected)

    def test_shape_and_order_are_stable(self) -> None:
        contract = _contract(("career", "outcome", "current_state"))

        self.assertEqual(contract["schema_version"], SCHEMA_VERSION)
        self.assertEqual(
            list(contract),
            [
                "schema_version",
                "day_hour",
                "earth_plate",
                "heaven_plate",
                "heavenly_generals",
                "month_general",
                "noble_person",
                "lesson_method",
                "four_lessons",
                "three_transmissions",
                "plate_offset",
                "xunkong",
                "structural_patterns",
                "source_conditioned_patterns",
                "dimension_facts",
            ],
        )
        self.assertEqual(contract["earth_plate"], list("子丑寅卯辰巳午未申酉戌亥"))
        self.assertEqual(
            [row["lesson"] for row in contract["four_lessons"]],
            [1, 2, 3, 4],
        )
        self.assertEqual(
            [row["stage"] for row in contract["three_transmissions"]],
            ["initial", "middle", "final"],
        )
        self.assertEqual(
            list(contract["dimension_facts"]),
            ["career", "outcome", "current_state"],
        )
        self.assertEqual(
            [
                row["canonical_dimension"]
                for row in contract["dimension_facts"].values()
            ],
            ["work", "outcome", "state"],
        )

    def test_timing_candidates_distinguish_omitted_from_empty(self) -> None:
        without_timing = _contract(("relationship",))
        self.assertNotIn("timing_candidates", without_timing)

        with_unbounded_timing = liuren_calc.extend_liuren_facts(
            _facts(),
            requested_dimensions=("timing",),
            horizon={"kind": "instant"},
            target_relative=None,
        )["runtime_core_facts"]
        self.assertIn("timing_candidates", with_unbounded_timing)
        self.assertEqual(with_unbounded_timing["timing_candidates"], [])
        self.assertIsNone(
            with_unbounded_timing["dimension_facts"]["timing"]["candidate_date"]
        )

    def test_unknown_internal_adapter_keys_are_not_published(self) -> None:
        facts = _facts()
        facts["output"]["future_internal_trace"] = {"opaque": True}
        contract = liuren_calc.extend_liuren_facts(
            facts,
            requested_dimensions=("relationship",),
            horizon=HORIZON,
            target_relative=None,
        )["runtime_core_facts"]

        self.assertNotIn("future_internal_trace", contract)
        validate_runtime_core_facts(contract)

    def test_missing_required_key_is_rejected(self) -> None:
        contract = _contract()
        del contract["month_general"]

        with self.assertRaisesRegex(
            LiurenRuntimeContractError, "missing required keys: month_general"
        ):
            validate_runtime_core_facts(contract)

    def test_unknown_keys_are_rejected_at_fixed_layers(self) -> None:
        mutations = []

        top = _contract()
        top["unknown"] = True
        mutations.append(top)

        method = _contract()
        method["lesson_method"]["direct_candidates"] = []
        mutations.append(method)

        dimension = _contract()
        dimension["dimension_facts"]["relationship"]["verdict"] = "invented"
        mutations.append(dimension)

        source = _contract()
        source_ref = source["dimension_facts"]["relationship"]["rule_evidence"][
            "matched"
        ][0]["source_refs"][0]
        source_ref["url"] = "not-in-v1"
        mutations.append(source)

        for mutation in mutations:
            with self.subTest(keys=list(mutation)):
                with self.assertRaisesRegex(
                    LiurenRuntimeContractError, "contains unknown keys"
                ):
                    validate_runtime_core_facts(mutation)

    def test_every_rule_source_has_a_stable_anchor(self) -> None:
        contract = _contract(
            ("outcome", "relationship", "timing", "state", "work", "money", "location")
        )
        for dimension, row in contract["dimension_facts"].items():
            evidence = row["rule_evidence"]
            self.assertIsNone(evidence["hard_verdict"], dimension)
            self.assertTrue(evidence["requires_school_adjudication"], dimension)
            for group in ("matched", "scope_boundaries", "not_evaluated"):
                for record in evidence[group]:
                    for source_ref in record["source_refs"]:
                        self.assertTrue(source_ref["source_anchor"], (dimension, record))

    def test_source_conditioned_patterns_are_anchored_and_not_verdicts(self) -> None:
        facts = liuren_fact_adapter.build_from_chart(
            day_ganzhi="癸丑",
            hour_ganzhi="戊午",
            month_general="午",
            question="脱敏来源样例",
            location="fixture",
        )
        contract = liuren_calc.extend_liuren_facts(
            facts,
            requested_dimensions=("relationship",),
            horizon=HORIZON,
            target_relative=None,
        )["runtime_core_facts"]

        self.assertEqual(
            [row["title"] for row in contract["source_conditioned_patterns"]],
            ["伏吟", "八专日"],
        )
        for row in contract["source_conditioned_patterns"]:
            self.assertEqual(row["status"], "predicate_matched_not_verdict")
            self.assertTrue(row["source_anchor"].startswith("fulltext.md#L"))
            self.assertNotIn("verdict", row)
            self.assertNotIn("hard_verdict", row)
            self.assertTrue(row["fact_paths"])
            self.assertTrue(row["predicate_audit"])

    def test_unmapped_or_unverifiable_patterns_fail_closed(self) -> None:
        output = copy.deepcopy(_facts()["output"])
        output["structural_patterns"] = ["伏吟", "合成未收录课体"]
        rows = build_source_conditioned_patterns(output)
        self.assertEqual([row["title"] for row in rows], ["伏吟"])

        catalog = copy.deepcopy(liuren_contract._structural_pattern_catalog())
        catalog["伏吟"]["source_anchor"] = ""
        with patch.object(
            liuren_contract,
            "_structural_pattern_catalog",
            return_value=catalog,
        ):
            self.assertEqual(build_source_conditioned_patterns(output), [])

    def test_two_lesson_incomplete_pattern_does_not_reuse_three_lesson_anchor(self) -> None:
        facts = liuren_fact_adapter.build_from_chart(
            day_ganzhi="癸丑",
            hour_ganzhi="戊午",
            month_general="午",
            question="脱敏来源边界",
            location="fixture",
        )
        output = facts["output"]
        self.assertIn("四课不备", output["structural_patterns"])
        self.assertNotIn(
            "四课不备",
            [row["title"] for row in build_source_conditioned_patterns(output)],
        )

    def test_structural_pattern_source_audit_closes_rule_quote_and_anchor(self) -> None:
        report = audit_liuren_structural_patterns.audit_liuren_structural_patterns()

        self.assertTrue(report["ready"], report)
        self.assertEqual(report["pattern_count"], 4)
        self.assertEqual(report["anchored_pattern_count"], 4)
        self.assertEqual(report["findings"], [])

    def test_missing_source_anchor_and_non_null_verdict_are_rejected(self) -> None:
        without_anchor = _contract()
        source_ref = without_anchor["dimension_facts"]["relationship"][
            "rule_evidence"
        ]["matched"][0]["source_refs"][0]
        del source_ref["source_anchor"]
        with self.assertRaisesRegex(
            LiurenRuntimeContractError, "missing required keys: source_anchor"
        ):
            validate_runtime_core_facts(without_anchor)

        with_verdict = _contract()
        with_verdict["dimension_facts"]["relationship"]["rule_evidence"][
            "hard_verdict"
        ] = "yes"
        with self.assertRaisesRegex(
            LiurenRuntimeContractError, "hard_verdict must be null"
        ):
            validate_runtime_core_facts(with_verdict)

        source_verdict = _contract()
        source_verdict["source_conditioned_patterns"][0]["verdict"] = "吉"
        with self.assertRaisesRegex(
            LiurenRuntimeContractError, "contains unknown keys: verdict"
        ):
            validate_runtime_core_facts(source_verdict)

        source_status = _contract()
        source_status["source_conditioned_patterns"][0]["status"] = "verdict"
        with self.assertRaisesRegex(
            LiurenRuntimeContractError,
            "status must be predicate_matched_not_verdict",
        ):
            validate_runtime_core_facts(source_status)

    def test_builder_returns_a_deep_copy(self) -> None:
        facts = _facts()
        extension = liuren_calc.extend_liuren_facts(
            facts,
            requested_dimensions=("relationship",),
            horizon=HORIZON,
            target_relative=None,
        )
        contract = extension["runtime_core_facts"]

        facts["output"]["earth_plate"][0] = "changed"
        extension["dimension_facts"]["relationship"]["status"] = "changed"
        self.assertEqual(contract["earth_plate"][0], "子")
        self.assertEqual(
            contract["dimension_facts"]["relationship"]["status"],
            "calculated_facts_not_verdict",
        )


if __name__ == "__main__":
    unittest.main()
