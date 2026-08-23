#!/usr/bin/env python3
"""Task 7H regressions for the deterministic Daliuren provider."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from dataclasses import replace as dataclass_replace

import yaml

import audit_liuren_provider
import build_evidence_index
import liuren_calc
import liuren_fact_adapter
import reading_evidence_bundle
from reading_engine import calendar_core
from reading_engine.contracts import CalculationResult, FactRef, ReadingRequest
from reading_engine.providers import PROVIDER_CAPABILITIES
from reading_engine.evidence_rules import EvidenceRule, match_rule
from reading_engine.fact_index import build_fact_index
from reading_engine.providers import LiurenProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "liuren-v51.yaml"


def _fixture() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _transmissions(output: dict) -> str:
    return "".join(row["branch"] for row in output["three_transmissions"])


def _representative() -> dict:
    return liuren_fact_adapter.build_from_datetime(
        "2026-07-10T14:00:00",
        timezone_name="Asia/Shanghai",
        location="上海",
        question="fixture",
    )


class LiurenFixtureContractTests(unittest.TestCase):
    def test_shared_calendar_dependency_binds_month_general_source_table(self) -> None:
        manifest = yaml.safe_load(
            (
                ROOT
                / "references/matrices/algorithm-source-dependencies.yaml"
            ).read_text(encoding="utf-8")
        )
        dependency = next(
            item
            for item in manifest["providers"]["liuren"]["dependencies"]
            if item["id"] == "liuren.calendar.shared-sxtwl-four-pillars"
        )
        source_table_path = ROOT / "references/matrices/liuren-source-tables-v1.yaml"
        source_table_hash = hashlib.sha256(source_table_path.read_bytes()).hexdigest()

        self.assertEqual(
            dependency["source_artifact"],
            {
                "path": "references/matrices/liuren-source-tables-v1.yaml",
                "schema_version": "mingli-liuren-source-tables-v1",
                "sha256": source_table_hash,
            },
        )
        month_general_sources = [
            source
            for source in dependency["primary_sources"]
            if source["normalized_path"]
            == "references/fulltext/san-shi/liuren-miben/fulltext.md"
        ]
        self.assertEqual(len(month_general_sources), 1)
        self.assertEqual(month_general_sources[0]["anchor"], "L3529-L3539")
        self.assertIn(
            "雨水前日卯初刻，太陽入衛用登明亥。",
            month_general_sources[0]["exact_excerpt"],
        )

    def test_audit_reports_bound_shared_calendar_runtime_identity(self) -> None:
        report = audit_liuren_provider.audit_liuren_provider()

        self.assertEqual(
            report["calendar_identity"],
            {
                "dependency_id": "liuren.calendar.shared-sxtwl-four-pillars",
                "algorithm_version": calendar_core.ALGORITHM_VERSION,
                "convention_id": calendar_core.CONVENTION_ID,
                "convention_version": calendar_core.CONVENTION_VERSION,
                "engine": "sxtwl",
                "engine_version": "2.0.7",
                "zi_hour_policies": ["late-zi-next-day", "midnight"],
                "five_rat_known_answers": {
                    "midnight": {
                        "day": "戊寅",
                        "hour": "壬子",
                    },
                    "late-zi-next-day": {
                        "day": "己卯",
                        "hour": "甲子",
                    },
                },
            },
        )

    def test_audit_rejects_shared_calendar_runtime_version_drift(self) -> None:
        with patch.object(
            audit_liuren_provider.calendar_core,
            "ALGORITHM_VERSION",
            "sxtwl-drift",
        ):
            report = audit_liuren_provider.audit_liuren_provider()

        self.assertFalse(report["provider_ready"])
        self.assertIn(
            "Liuren shared calendar algorithm identity drift",
            report["findings"],
        )

    def test_audit_rejects_missing_live_shared_calendar_declaration(self) -> None:
        live = PROVIDER_CAPABILITIES["liuren"]
        without_calendar = dataclass_replace(
            live,
            algorithm_dependencies=tuple(
                dependency
                for dependency in live.algorithm_dependencies
                if dependency.id != "liuren.calendar.shared-sxtwl-four-pillars"
            ),
        )
        with patch.dict(PROVIDER_CAPABILITIES, {"liuren": without_calendar}):
            report = audit_liuren_provider.audit_liuren_provider()

        self.assertFalse(report["provider_ready"])
        self.assertIn(
            "Liuren live shared calendar dependency declaration missing",
            report["findings"],
        )

    def test_calendar_semantics_change_has_new_adapter_and_pipeline_versions(self) -> None:
        self.assertEqual(liuren_fact_adapter.VERSION, "2.0.1")
        self.assertEqual(
            LiurenProvider.provider_version,
            "mingli-liuren-pipeline-v6-runtime-contract",
        )

    def test_machine_readable_completeness_audit_passes_before_activation(self) -> None:
        report = audit_liuren_provider.audit_liuren_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertGreaterEqual(report["counts"]["classical_cases"], 39)
        self.assertEqual(report["counts"]["complete_source_plates"], 23)
        self.assertGreaterEqual(report["counts"]["calendar_boundaries"], 8)
        self.assertEqual(report["counts"]["primary_methods"], 10)
        self.assertGreaterEqual(report["counts"]["special_source_labels"], 10)
        self.assertEqual(report["counts"]["dimensions"], 7)
        self.assertEqual(report["counts"]["evidence_roles"], 4)
        self.assertEqual(report["counts"]["algorithm_dependencies"], 6)
        self.assertEqual(report["counts"]["imagery_exact_pairs"], 141)
        self.assertEqual(report["counts"]["imagery_missing_pairs"], 3)
        self.assertEqual(report["findings"], [])

    def test_audit_freezes_the_complete_source_plate_id_set(self) -> None:
        fixture = _fixture()
        target = next(
            case
            for case in fixture["classical_cases"]
            if case["id"] == "daquan-L6876"
        )
        del target["expected"]["four_lessons"]

        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            mutated = Path(temporary) / "liuren-missing-complete-plate.yaml"
            mutated.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_liuren_provider.audit_liuren_provider(
                fixture_path=mutated
            )

        self.assertFalse(report["provider_ready"])
        self.assertIn(
            "complete source plate id set mismatch",
            report["findings"],
        )

    def test_fixture_has_39_unique_source_anchored_cases_and_boundaries(self) -> None:
        fixture = _fixture()
        cases = fixture["classical_cases"]
        boundaries = fixture["calendar_boundaries"]
        categories = Counter(case["category"] for case in boundaries)

        self.assertEqual(len(cases), 39)
        self.assertEqual(len({case["id"] for case in cases}), 39)
        self.assertTrue(all(case["source_anchor"] for case in cases))
        self.assertGreaterEqual(sum("four_lessons" in case["expected"] for case in cases), 20)
        self.assertGreaterEqual(categories["solar_term_boundary"], 2)
        self.assertGreaterEqual(categories["day_rollover"], 2)
        self.assertGreaterEqual(categories["leap_month"], 1)
        self.assertGreaterEqual(categories["timezone_boundary"], 2)

    def test_all_classical_cases_reproduce_method_transmissions_and_complete_plates(self) -> None:
        for case in _fixture()["classical_cases"]:
            with self.subTest(case=case["id"]):
                supplied = case["input"]
                expected = case["expected"]
                output = liuren_fact_adapter.build_from_chart(
                    day_ganzhi=supplied["day"],
                    hour_ganzhi=supplied["hour"],
                    month_general=supplied["month_general"],
                    question="fixture",
                    location="fixture",
                )["output"]
                self.assertEqual(output["transmission_method"]["primary"], expected["primary_method"])
                self.assertEqual(_transmissions(output), expected["transmissions"])
                if expected.get("four_lessons"):
                    self.assertEqual(
                        [[row["upper"], row["lower"]] for row in output["four_lessons"]],
                        expected["four_lessons"],
                    )

    def test_audit_rejects_fixture_and_provider_sync_mutation_of_source_plate(self) -> None:
        fixture = _fixture()
        target = fixture["classical_cases"][0]
        target["expected"]["four_lessons"][0] = ["子", "子"]
        original_build = liuren_fact_adapter.build_from_chart

        def synchronized_provider(*args: object, **kwargs: object) -> dict:
            facts = original_build(*args, **kwargs)
            if (
                kwargs.get("day_ganzhi") == target["input"]["day"]
                and kwargs.get("hour_ganzhi") == target["input"]["hour"]
                and kwargs.get("month_general") == target["input"]["month_general"]
            ):
                facts = copy.deepcopy(facts)
                facts["output"]["four_lessons"][0]["upper"] = "子"
                facts["output"]["four_lessons"][0]["lower"] = "子"
            return facts

        with tempfile.TemporaryDirectory() as temporary:
            mutated = Path(temporary) / "liuren-mutated.yaml"
            mutated.write_text(
                yaml.safe_dump(fixture, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            with patch.object(
                audit_liuren_provider.liuren_fact_adapter,
                "build_from_chart",
                side_effect=synchronized_provider,
            ):
                report = audit_liuren_provider.audit_liuren_provider(
                    fixture_path=mutated
                )

        self.assertFalse(report["provider_ready"])
        source_findings = report["source_verification"].get("findings") or []
        self.assertTrue(
            "source-derived four-lessons mismatch: daquan-L6876"
            in source_findings
            or any(
                "live provider result differs from classical oracle" in finding
                for finding in report["findings"]
            ),
            report,
        )

    def test_source_label_variant_is_retained_without_overriding_calculation(self) -> None:
        case = next(case for case in _fixture()["classical_cases"] if case["id"] == "daquan-L7190")
        supplied = case["input"]
        source_table = yaml.safe_load(
            (
                ROOT
                / "references"
                / "matrices"
                / "liuren-source-tables-v1.yaml"
            ).read_text(encoding="utf-8")
        )
        variant = source_table["method_label_variants"][0]
        method = liuren_fact_adapter.build_from_chart(
            day_ganzhi=supplied["day"],
            hour_ganzhi=supplied["hour"],
            month_general=supplied["month_general"],
            question="fixture",
            location="fixture",
        )["output"]["transmission_method"]

        self.assertEqual(
            variant["input"],
            {"day": "乙卯", "hour_branch": "寅", "month_general": "子"},
        )
        self.assertEqual(method["primary"], "涉害")
        self.assertEqual(variant["transmissions"], "亥酉未")
        self.assertTrue(
            any(
                row["source_label"] == variant["source_label"]
                and row["source_anchor"] == variant["source_anchor"]
                and row["resolution"] == "calculated_transmissions_unchanged"
                for row in method["source_label_variants"]
            )
        )

    def test_audit_rejects_semantically_false_method_label_variant(self) -> None:
        source_table_path = (
            ROOT
            / "references"
            / "matrices"
            / "liuren-source-tables-v1.yaml"
        )
        source_table = yaml.safe_load(source_table_path.read_text(encoding="utf-8"))
        source_table["method_label_variants"][0]["calculated_label"] = "重审"

        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            mutated = Path(temporary) / "liuren-source-table-mutated.yaml"
            mutated.write_text(
                yaml.safe_dump(source_table, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            with patch.object(audit_liuren_provider, "SOURCE_TABLE", mutated):
                report = audit_liuren_provider.audit_liuren_provider()

        self.assertFalse(report["provider_ready"])
        self.assertIn(
            "method-label variant calculated label mismatch: daquan-L7190",
            report["findings"],
        )

    def test_calendar_boundaries_preserve_shared_calendar_facts(self) -> None:
        for case in _fixture()["calendar_boundaries"]:
            with self.subTest(case=case["id"]):
                facts = liuren_fact_adapter.build_from_datetime(
                    case["datetime"],
                    timezone_name=case["timezone"],
                    location="fixture",
                    question="fixture",
                    zi_hour_policy=case["zi_hour_policy"],
                )
                calendar = facts["calendar_normalization"]
                output = facts["output"]
                self.assertEqual(
                    [calendar["ganzhi"][key] for key in ("year", "month", "day", "hour")],
                    case["expected_pillars"],
                )
                self.assertEqual(output["day_hour"]["day"], case["expected_pillars"][2])
                self.assertEqual(output["day_hour"]["hour"], case["expected_pillars"][3])
                self.assertEqual(output["month_general"]["branch"], case["expected_general"])
                self.assertEqual(output["transmission_method"]["primary"], case["expected_method"])
                self.assertEqual(_transmissions(output), case["expected_transmissions"])

    def test_provider_consumes_the_explicit_zi_hour_policy(self) -> None:
        provider = LiurenProvider(ROOT)
        results = {}
        for policy in ("midnight", "late-zi-next-day"):
            results[policy] = provider.calculate(
                ReadingRequest(
                    query="子时边界",
                    action="new",
                    system="liuren",
                    event_datetime="2024-01-15T23:30:00",
                    timezone="Asia/Shanghai",
                    location="上海",
                    metadata={"zi_hour_policy": policy},
                )
            )

        self.assertEqual(
            results["midnight"].facts["chart_facts"]["output"]["day_hour"],
            {"day": "戊寅", "hour": "壬子"},
        )
        self.assertEqual(
            results["late-zi-next-day"].facts["chart_facts"]["output"][
                "day_hour"
            ],
            {"day": "己卯", "hour": "甲子"},
        )
        self.assertNotEqual(
            results["midnight"].input_hash,
            results["late-zi-next-day"].input_hash,
        )


class LiurenDimensionProjectionTests(unittest.TestCase):
    def test_every_dimension_has_distinct_whitelisted_calculated_facts(self) -> None:
        dimensions = ("outcome", "timing", "state", "location", "relationship", "work", "money")
        result = liuren_calc.extend_liuren_facts(
            _representative(),
            requested_dimensions=dimensions,
            horizon={"kind": "day", "start": "2026-07-10", "end": "2026-07-31"},
        )
        facts = result["dimension_facts"]

        self.assertEqual(set(facts), set(dimensions))
        self.assertTrue(all(row["status"] == "calculated_facts_not_verdict" for row in facts.values()))
        self.assertEqual(len({json.dumps(row, ensure_ascii=False, sort_keys=True) for row in facts.values()}), len(dimensions))
        self.assertEqual(
            set(facts["outcome"]),
            {"requested_dimension", "canonical_dimension", "status", "source_rule_ids", "rule_evidence", "subject_object_relation", "transmissions_to_day", "initial_final_relation", "stage_flow"},
        )
        self.assertEqual(
            set(facts["location"]),
            {"requested_dimension", "canonical_dimension", "status", "source_rule_ids", "rule_evidence", "stage_branch_directions"},
        )
        self.assertEqual(
            set(facts["money"]),
            {"requested_dimension", "canonical_dimension", "status", "source_rule_ids", "rule_evidence", "wealth_presence", "wealth_stage_strength", "wealth_void_status", "wealth_general_modifier"},
        )

    def test_aliases_project_the_same_fact_kind_without_natural_language_routing(self) -> None:
        result = liuren_calc.extend_liuren_facts(
            _representative(),
            requested_dimensions=("current_state", "location_direction", "career"),
            horizon={"kind": "instant"},
        )["dimension_facts"]

        self.assertEqual(result["current_state"]["canonical_dimension"], "state")
        self.assertEqual(result["location_direction"]["canonical_dimension"], "location")
        self.assertEqual(result["career"]["canonical_dimension"], "work")
        self.assertNotEqual(result["current_state"], result["location_direction"])
        with self.assertRaisesRegex(ValueError, "unsupported Liuren dimension"):
            liuren_calc.extend_liuren_facts(
                _representative(),
                requested_dimensions=("health_diagnosis",),
                horizon={"kind": "instant"},
            )

    def test_outcome_relations_are_directed_mechanical_facts_without_verdict(self) -> None:
        facts = liuren_calc.extend_liuren_facts(
            _representative(),
            requested_dimensions=("outcome",),
            horizon={"kind": "instant"},
        )["dimension_facts"]["outcome"]

        self.assertEqual(facts["subject_object_relation"]["subject"], "day_stem")
        self.assertEqual(facts["subject_object_relation"]["object"], "day_branch")
        self.assertEqual(len(facts["transmissions_to_day"]), 3)
        self.assertEqual(len(facts["stage_flow"]), 2)
        self.assertNotIn("verdict", facts)
        self.assertNotIn("conclusion", facts)

    def test_state_uses_exact_source_correspondence_but_not_activity_templates(self) -> None:
        state = liuren_calc.extend_liuren_facts(
            _representative(),
            requested_dimensions=("state",),
            horizon={"kind": "instant"},
        )["dimension_facts"]["state"]

        self.assertEqual(len(state["stage_status"]), 3)
        self.assertEqual(len(state["general_landing_correspondences"]), 3)
        for row in state["general_landing_correspondences"]:
            self.assertEqual(row["role"], "imagery_correspondence_not_observed_activity")
            self.assertTrue(row["source_text"])
            self.assertTrue(row["source_anchor"])
            self.assertNotIn("activity_candidates", row)
            self.assertNotIn("base_activity", row)

    def test_missing_exact_imagery_correspondence_stays_explicitly_missing(self) -> None:
        row = liuren_calc._general_landing_correspondences(
            [
                {
                    "stage": "initial",
                    "branch": "酉",
                    "heavenly_general": "天空",
                }
            ]
        )[0]

        self.assertEqual(row["status"], "no_exact_source_correspondence")
        self.assertEqual(row["landing_branch"], "酉")
        self.assertNotIn("source_text", row)
        self.assertNotIn("base_activity", row)

    def test_location_is_symbolic_direction_only_and_money_is_wife_wealth_only(self) -> None:
        facts = liuren_calc.extend_liuren_facts(
            _representative(),
            requested_dimensions=("location", "money"),
            horizon={"kind": "instant"},
        )["dimension_facts"]

        self.assertEqual(len(facts["location"]["stage_branch_directions"]), 3)
        self.assertTrue(
            all(row["scope"] == "symbolic_direction_candidate_only" for row in facts["location"]["stage_branch_directions"])
        )
        money = facts["money"]
        self.assertTrue(money["wealth_presence"])
        self.assertTrue(all(row["six_relative"] == "妻财" for row in money["wealth_stage_strength"]))
        self.assertTrue(all(row["six_relative"] == "妻财" for row in money["wealth_void_status"]))
        self.assertTrue(all(row["six_relative"] == "妻财" for row in money["wealth_general_modifier"]))

    def test_exact_timing_requires_calendar_rule_and_bounded_horizon(self) -> None:
        facts = _representative()
        bounded = liuren_calc.extend_liuren_facts(
            facts,
            requested_dimensions=("timing",),
            horizon={"kind": "day", "start": "2026-07-10", "end": "2026-07-31"},
        )
        candidates = bounded["timing"]["candidates"]
        self.assertTrue(candidates)
        self.assertTrue(all(row["source_rule"] == "LM-R21" for row in candidates))
        self.assertTrue(all(row["candidate_not_guarantee"] for row in candidates))

        no_horizon = liuren_calc.extend_liuren_facts(
            facts,
            requested_dimensions=("timing",),
            horizon={"kind": "instant"},
        )
        self.assertEqual(no_horizon["timing"]["candidates"], [])
        self.assertIsNone(no_horizon["timing"]["candidate_branch"])
        self.assertIsNone(no_horizon["dimension_facts"]["timing"]["candidate_date"])
        self.assertNotIn(
            "LM-R21",
            no_horizon["dimension_facts"]["timing"]["source_rule_ids"],
        )
        self.assertNotIn(
            "LM-R21",
            {row["rule_id"] for row in no_horizon["timing"]["rule_trace"]},
        )

        no_calendar = copy.deepcopy(facts)
        no_calendar["calendar_normalization"]["civil_datetime"] = "not_supplied"
        no_calendar_result = liuren_calc.extend_liuren_facts(
            no_calendar,
            requested_dimensions=("timing",),
            horizon={"kind": "day", "start": "2026-07-10", "end": "2026-07-31"},
        )
        self.assertEqual(no_calendar_result["timing"]["candidates"], [])
        self.assertEqual(no_calendar_result["timing"]["status"], "missing_calendar_precondition")
        self.assertIsNone(no_calendar_result["timing"]["candidate_branch"])
        self.assertNotIn(
            "LM-R21",
            no_calendar_result["dimension_facts"]["timing"]["source_rule_ids"],
        )

    def test_source_rules_activate_only_when_their_fact_conditions_hold(self) -> None:
        chart = liuren_fact_adapter.build_from_chart(
            day_ganzhi="甲寅",
            hour_ganzhi=liuren_fact_adapter.expected_hour_pillar("甲寅", "子"),
            month_general="子",
            question="fixture",
            location="fixture",
        )
        result = liuren_calc.extend_liuren_facts(
            chart,
            requested_dimensions=("outcome", "relationship", "work"),
            horizon={"kind": "instant"},
        )["dimension_facts"]

        self.assertEqual(
            result["outcome"]["subject_object_relation"]["relation"],
            "same_element",
        )
        self.assertNotIn("LR-17", result["outcome"]["source_rule_ids"])
        self.assertNotIn("LR-17", result["relationship"]["source_rule_ids"])
        self.assertNotIn("LM-R22", result["work"]["source_rule_ids"])


class LiurenEvidenceRoleTests(unittest.TestCase):
    def test_every_liuren_rule_has_exactly_one_of_four_evidence_roles(self) -> None:
        records = [row for row in build_evidence_index.compile_evidence_rules() if row["system"] == "liuren"]
        roles = {row.get("evidence_role") for row in records}

        self.assertEqual(
            roles,
            {"casting_rule", "imagery_correspondence", "issue_specific_judgment_rule", "timing_rule"},
        )
        self.assertTrue(all(row.get("evidence_role") for row in records))

    def test_loaded_evidence_rule_preserves_role_and_role_filter_uses_dimensions(self) -> None:
        payload = next(row for row in build_evidence_index.compile_evidence_rules() if row["system"] == "liuren")
        rule = EvidenceRule.from_dict(payload)
        self.assertEqual(rule.evidence_role, payload["evidence_role"])
        self.assertEqual(rule.to_dict()["evidence_role"], payload["evidence_role"])

        provider = LiurenProvider(ROOT)
        for dimensions, expected in (
            (
                ["timing"],
                {"casting_rule", "issue_specific_judgment_rule", "timing_rule"},
            ),
            (
                ["state", "location"],
                {
                    "casting_rule",
                    "issue_specific_judgment_rule",
                    "imagery_correspondence",
                },
            ),
            (
                ["outcome"],
                {"casting_rule", "issue_specific_judgment_rule"},
            ),
        ):
            route = provider.source_route(
                {"requested_dimensions": dimensions}, None
            )
            self.assertEqual(set(route["allowed_evidence_roles"]), expected)

    def test_dimension_rules_bind_to_matching_extension_facts_not_query_words(self) -> None:
        records = build_evidence_index.compile_evidence_rules()
        imagery_payload = next(
            row for row in records
            if row["rule_id"] == "san-shi/liuren-miben#LM-R01"
        )
        self.assertEqual(
            imagery_payload["required_fact_predicates"],
            [
                {
                    "path_suffix": "/general_landing_correspondences",
                    "operator": "same_record_fields",
                    "value": {
                        "source_pack": "san-shi/liuren-miben",
                        "status": "source_correspondence_matched",
                        "role": "imagery_correspondence_not_observed_activity",
                        "source_rule": "LM-R01",
                    },
                },
            ],
        )
        self.assertTrue(imagery_payload["runtime_active"])
        base = CalculationResult.create(
            system="liuren",
            provider_id="fixture.liuren",
            provider_version="4.1",
            input_payload={"fixture": "evidence-role"},
            facts={"chart_facts": _representative()},
        )
        provider = LiurenProvider(ROOT)
        state = provider.extend(base, ("state",), {"kind": "instant"})
        outcome = provider.extend(base, ("outcome",), {"kind": "instant"})
        rule = EvidenceRule.from_dict(imagery_payload)

        state_match = match_rule(
            rule,
            build_fact_index(state, reading_id="reading", version=1),
        )
        outcome_match = match_rule(
            rule,
            build_fact_index(outcome, reading_id="reading", version=1),
        )
        self.assertTrue(state_match[0])
        self.assertFalse(outcome_match[0])

        split_values = {
            "source_pack": "san-shi/liuren-miben",
            "status": "source_correspondence_matched",
            "role": "imagery_correspondence_not_observed_activity",
            "source_rule": "LM-R01",
        }
        cross_row_facts = tuple(
            FactRef(
                fact_id=f"forged:{index}",
                path=(
                    "/fact_extensions/facts/dimension_facts/state/"
                    f"general_landing_correspondences/{index}/{field}"
                ),
                value=value,
                provider_id=LiurenProvider.provider_id,
                provider_version=LiurenProvider.provider_version,
                reading_id="reading",
                version=1,
            )
            for index, (field, value) in enumerate(split_values.items())
        )
        self.assertFalse(match_rule(rule, cross_row_facts)[0])

    def test_inactive_conditional_rules_do_not_match_evidence(self) -> None:
        chart = liuren_fact_adapter.build_from_chart(
            day_ganzhi="甲寅",
            hour_ganzhi=liuren_fact_adapter.expected_hour_pillar("甲寅", "子"),
            month_general="子",
            question="fixture",
            location="fixture",
        )
        base = CalculationResult.create(
            system="liuren",
            provider_id="fixture.liuren",
            provider_version="4.1",
            input_payload={"fixture": "conditional-rule-activation"},
            facts={"chart_facts": chart},
        )
        provider = LiurenProvider(ROOT)
        outcome = provider.extend(base, ("outcome",), {"kind": "instant"})
        work = provider.extend(base, ("work",), {"kind": "instant"})
        records = build_evidence_index.compile_evidence_rules()

        for rule_id, calculation in (
            ("san-shi/liuren-zhiyin#LR-17", outcome),
            ("san-shi/liuren-miben#LM-R22", work),
        ):
            with self.subTest(rule_id=rule_id):
                payload = next(row for row in records if row["rule_id"] == rule_id)
                matched = match_rule(
                    EvidenceRule.from_dict(payload),
                    build_fact_index(calculation, reading_id="reading", version=1),
                )[0]
                self.assertFalse(matched)


if __name__ == "__main__":
    unittest.main()
