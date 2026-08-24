#!/usr/bin/env python3
"""Golden and negative tests for the public Daliuren Runtime contract."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import liuren_calc
import liuren_fact_adapter
from reading_engine.liuren_contract import (
    LiurenRuntimeContractError,
    SCHEMA_VERSION,
    build_runtime_core_facts,
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


def _all_dimension_extension() -> tuple[dict, dict]:
    facts = _facts()
    extension = liuren_calc.extend_liuren_facts(
        facts,
        requested_dimensions=(
            "outcome",
            "timing",
            "state",
            "location",
            "relationship",
            "work",
            "money",
        ),
        horizon=HORIZON,
        target_relative="妻财",
    )
    return facts, extension


def _fixed_dimension_payloads(dimension_facts: dict) -> list[tuple[str, dict, str]]:
    return [
        (
            "outcome.subject_object_relation",
            dimension_facts["outcome"]["subject_object_relation"],
            "subject",
        ),
        (
            "outcome.transmissions_to_day[]",
            dimension_facts["outcome"]["transmissions_to_day"][0],
            "stage",
        ),
        (
            "outcome.initial_final_relation",
            dimension_facts["outcome"]["initial_final_relation"],
            "subject",
        ),
        (
            "outcome.stage_flow[]",
            dimension_facts["outcome"]["stage_flow"][0],
            "from_stage",
        ),
        (
            "timing.candidate_branch",
            dimension_facts["timing"]["candidate_branch"],
            "branch",
        ),
        (
            "timing.candidate_date",
            dimension_facts["timing"]["candidate_date"],
            "id",
        ),
        (
            "state.stage_status[]",
            dimension_facts["state"]["stage_status"][0],
            "stage",
        ),
        (
            "state.general_landing_correspondences[]",
            dimension_facts["state"]["general_landing_correspondences"][0],
            "stage",
        ),
        (
            "location.stage_branch_directions[]",
            dimension_facts["location"]["stage_branch_directions"][0],
            "stage",
        ),
        (
            "relationship.six_relative_stages[]",
            dimension_facts["relationship"]["six_relative_stages"][0],
            "stage",
        ),
        (
            "work.target_strength[]",
            dimension_facts["work"]["target_strength"][0],
            "stage",
        ),
        (
            "work.target_general_modifier[]",
            dimension_facts["work"]["target_general_modifier"][0],
            "stage",
        ),
        (
            "money.wealth_stage_strength[]",
            dimension_facts["money"]["wealth_stage_strength"][0],
            "stage",
        ),
        (
            "money.wealth_void_status[]",
            dimension_facts["money"]["wealth_void_status"][0],
            "stage",
        ),
        (
            "money.wealth_general_modifier[]",
            dimension_facts["money"]["wealth_general_modifier"][0],
            "stage",
        ),
    ]


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
            with_unbounded_timing["dimension_facts"]["timing"]["candidate_branch"]
        )
        self.assertIsNone(
            with_unbounded_timing["dimension_facts"]["timing"]["candidate_date"]
        )

    def test_timing_candidate_helper_keys_are_not_published(self) -> None:
        facts, extension = _all_dimension_extension()
        timing_candidates = copy.deepcopy(extension["timing"]["candidates"])
        self.assertTrue(timing_candidates)
        expected = copy.deepcopy(timing_candidates)
        timing_candidates[0]["future_internal_trace"] = {"opaque": True}

        contract = build_runtime_core_facts(
            facts["output"],
            extension["dimension_facts"],
            timing_candidates=timing_candidates,
        )

        self.assertEqual(contract["timing_candidates"], expected)
        self.assertNotIn("future_internal_trace", contract["timing_candidates"][0])
        validate_runtime_core_facts(contract)

    def test_timing_candidate_public_payloads_fail_closed(self) -> None:
        contract = _contract(("timing",))
        self.assertTrue(contract["timing_candidates"])

        missing = copy.deepcopy(contract)
        del missing["timing_candidates"][0]["id"]
        with self.assertRaisesRegex(
            LiurenRuntimeContractError, "missing required keys: id"
        ):
            validate_runtime_core_facts(missing)

        unknown = copy.deepcopy(contract)
        unknown["timing_candidates"][0]["future_public_field"] = True
        with self.assertRaisesRegex(
            LiurenRuntimeContractError, "contains unknown keys: future_public_field"
        ):
            validate_runtime_core_facts(unknown)

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

    def test_unknown_nested_adapter_keys_are_not_published(self) -> None:
        facts = _facts()
        output = facts["output"]
        adapter_objects = (
            output["day_hour"],
            output["heaven_plate"][0],
            output["heavenly_generals"][0],
            output["month_general"],
            output["noble_person"],
            output["transmission_method"],
            output["four_lessons"][0],
            output["three_transmissions"][0],
            output["xunkong"],
        )
        for row in adapter_objects:
            row["future_internal_trace"] = {"opaque": True}

        contract = liuren_calc.extend_liuren_facts(
            facts,
            requested_dimensions=("relationship",),
            horizon=HORIZON,
            target_relative=None,
        )["runtime_core_facts"]
        published_objects = (
            contract["day_hour"],
            contract["heaven_plate"][0],
            contract["heavenly_generals"][0],
            contract["month_general"],
            contract["noble_person"],
            contract["lesson_method"],
            contract["four_lessons"][0],
            contract["three_transmissions"][0],
            contract["xunkong"],
        )

        for row in published_objects:
            self.assertNotIn("future_internal_trace", row)
        validate_runtime_core_facts(contract)

    def test_unknown_dimension_helper_keys_are_not_published(self) -> None:
        facts, extension = _all_dimension_extension()
        dimension_facts = extension["dimension_facts"]
        for row in dimension_facts.values():
            row["future_internal_trace"] = {"opaque": True}
        for _, payload, _ in _fixed_dimension_payloads(dimension_facts):
            payload["future_internal_trace"] = {"opaque": True}

        contract = build_runtime_core_facts(
            facts["output"],
            dimension_facts,
            timing_candidates=extension["timing"]["candidates"],
        )

        for row in contract["dimension_facts"].values():
            self.assertNotIn("future_internal_trace", row)
        for label, payload, _ in _fixed_dimension_payloads(
            contract["dimension_facts"]
        ):
            with self.subTest(label=label):
                self.assertNotIn("future_internal_trace", payload)
        validate_runtime_core_facts(contract)

    def test_rule_evidence_helper_keys_are_not_published_recursively(self) -> None:
        facts, extension = _all_dimension_extension()
        evidence = extension["dimension_facts"]["outcome"]["rule_evidence"]
        matched = evidence["matched"][0]
        matched_source = matched["source_refs"][0]
        not_evaluated = evidence["not_evaluated"][0]
        not_evaluated_source = not_evaluated["source_refs"][0]

        projected_layers = (
            evidence,
            matched,
            matched_source,
            not_evaluated,
            not_evaluated_source,
        )
        for layer in projected_layers:
            layer["future_internal_trace"] = {"opaque": True}
        matched["observation"]["future_observation_detail"] = {"opaque": True}

        contract = build_runtime_core_facts(
            facts["output"],
            extension["dimension_facts"],
            timing_candidates=extension["timing"]["candidates"],
        )

        projected = contract["dimension_facts"]["outcome"]["rule_evidence"]
        projected_matched = projected["matched"][0]
        projected_not_evaluated = projected["not_evaluated"][0]
        for layer in (
            projected,
            projected_matched,
            projected_matched["source_refs"][0],
            projected_not_evaluated,
            projected_not_evaluated["source_refs"][0],
        ):
            self.assertNotIn("future_internal_trace", layer)
        self.assertEqual(
            projected_matched["observation"]["future_observation_detail"],
            {"opaque": True},
        )
        validate_runtime_core_facts(contract)

    def test_rule_evidence_public_payloads_fail_closed_recursively(self) -> None:
        for label in (
            "evidence",
            "matched",
            "matched_source",
            "not_evaluated",
            "not_evaluated_source",
        ):
            with self.subTest(label=label):
                contract = _contract(("outcome",))
                evidence = contract["dimension_facts"]["outcome"]["rule_evidence"]
                matched = evidence["matched"][0]
                not_evaluated = evidence["not_evaluated"][0]
                layers = {
                    "evidence": evidence,
                    "matched": matched,
                    "matched_source": matched["source_refs"][0],
                    "not_evaluated": not_evaluated,
                    "not_evaluated_source": not_evaluated["source_refs"][0],
                }
                layers[label]["future_public_field"] = True

                with self.assertRaisesRegex(
                    LiurenRuntimeContractError,
                    "contains unknown keys: future_public_field",
                ):
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

    def test_nested_dimension_payloads_fail_closed_on_missing_or_unknown_keys(
        self,
    ) -> None:
        _, extension = _all_dimension_extension()
        contract = extension["runtime_core_facts"]

        for label, _, required_field in _fixed_dimension_payloads(
            contract["dimension_facts"]
        ):
            with self.subTest(label=label, mutation="missing"):
                mutation = copy.deepcopy(contract)
                payloads = {
                    name: payload
                    for name, payload, _ in _fixed_dimension_payloads(
                        mutation["dimension_facts"]
                    )
                }
                del payloads[label][required_field]
                with self.assertRaisesRegex(
                    LiurenRuntimeContractError, "missing required keys"
                ):
                    validate_runtime_core_facts(mutation)

            with self.subTest(label=label, mutation="unknown"):
                mutation = copy.deepcopy(contract)
                payloads = {
                    name: payload
                    for name, payload, _ in _fixed_dimension_payloads(
                        mutation["dimension_facts"]
                    )
                }
                payloads[label]["future_public_field"] = True
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
