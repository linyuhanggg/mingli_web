"""Task 7C regressions for complete deterministic Ziwei fact layers."""

from __future__ import annotations

import copy
import json
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import yaml

import adapter_validate
import ziwei_fact_adapter


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "ziwei-v51.yaml"
TRANSFORMATION_ORDER = ("禄", "权", "科", "忌")


def _facts(case: dict) -> dict:
    source = case["input"]
    return ziwei_fact_adapter.build_from_birth(
        source["datetime"],
        timezone_name="Asia/Shanghai",
        location="上海",
        gender=source["gender"],
        zi_hour_policy=source.get("zi_hour_policy", "midnight"),
    )


def _render_transformations(rows: list[dict]) -> list[str]:
    return [
        f"{row['star']}{row['transformation']}@{row['palace']}"
        for row in rows
    ]


def _resign_forged_payload(facts: dict, mutate) -> dict:
    """Tamper with a copy, then refresh its generator-owned payload digest."""

    forged = copy.deepcopy(facts)
    mutate(forged["output"]["source_conditioned_patterns"])
    forged["natal_fact_digest"] = ziwei_fact_adapter.natal_fact_digest(forged)
    return forged


class ZiweiV51CompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        cls.cases = cls.fixture["cases"]

    def test_fixture_contract_has_thirty_two_boundary_cases(self) -> None:
        self.assertEqual(self.fixture["schema_version"], "mingli-ziwei-fixtures-v51")
        self.assertGreaterEqual(len(self.cases), 30)
        self.assertEqual(len({case["id"] for case in self.cases}), len(self.cases))
        categories = Counter(case["category"] for case in self.cases)
        self.assertGreaterEqual(categories["known_chart"], 8)
        self.assertGreaterEqual(categories["leap_month"], 6)
        self.assertGreaterEqual(categories["zi_hour"], 6)
        self.assertGreaterEqual(categories["direction"], 4)
        self.assertGreaterEqual(categories["limit_boundary"], 4)
        self.assertGreaterEqual(categories["temporal_transformations"], 4)

    def test_source_conditioned_patterns_are_exact_identities_without_verdicts(self) -> None:
        facts = _facts(next(case for case in self.cases if case["category"] == "known_chart"))
        patterns = facts["output"]["source_conditioned_patterns"]

        self.assertEqual(
            {pattern["rule_id"] for pattern in patterns},
            {
                "ziwei/taiwei-fu#TR-01",
                "ziwei/ziwei-doushu-quanshu#ZW-M01",
            },
        )
        self.assertTrue(
            all(
                pattern["status"] == "predicate_matched_not_verdict"
                and pattern["source_dependency_id"]
                == "ziwei.source-conditioned-patterns"
                for pattern in patterns
            )
        )
        self.assertTrue(all("verdict" not in pattern for pattern in patterns))
        validation = adapter_validate.validate_payload("ziwei", facts)
        self.assertTrue(validation["ok"], validation)

    def test_resigned_source_pattern_identity_and_source_forgery_fails_closed(
        self,
    ) -> None:
        facts = _facts(
            next(case for case in self.cases if case["category"] == "known_chart")
        )
        for field, forged_value in (
            ("rule_id", "ziwei/taiwei-fu#TR-FORGED"),
            ("local_rule_id", "TR-FORGED"),
            ("title", "TR-FORGED rewritten title"),
            ("source_pack", "ziwei/forged-pack"),
            ("source_anchor", "rules.md#FORGED"),
        ):
            with self.subTest(field=field):
                forged = _resign_forged_payload(
                    facts,
                    lambda patterns, field=field, forged_value=forged_value: (
                        patterns[0].__setitem__(field, forged_value)
                    ),
                )
                validation = adapter_validate.validate_payload("ziwei", forged)
                self.assertFalse(validation["ok"], validation)
                self.assertIn(
                    "ziwei_source_pattern_binding_invalid",
                    validation["codes"],
                )

    def test_resigned_source_pattern_fact_paths_and_audit_forgery_fails_closed(
        self,
    ) -> None:
        facts = _facts(
            next(case for case in self.cases if case["category"] == "known_chart")
        )

        def forge_fact_path(patterns: list[dict]) -> None:
            patterns[0]["fact_paths"][0] = "fact:/chart_facts/output/forged"

        def forge_predicate_audit(patterns: list[dict]) -> None:
            patterns[0]["predicate_audit"][0] = (
                "/output/palaces:descendant_eq:伪造宫"
            )

        for label, mutate in (
            ("fact_paths", forge_fact_path),
            ("predicate_audit", forge_predicate_audit),
        ):
            with self.subTest(field=label):
                forged = _resign_forged_payload(facts, mutate)
                validation = adapter_validate.validate_payload("ziwei", forged)
                self.assertFalse(validation["ok"], validation)
                self.assertIn(
                    "ziwei_source_pattern_binding_invalid",
                    validation["codes"],
                )

    def test_source_pattern_contract_exception_becomes_a_finding(self) -> None:
        facts = _facts(
            next(case for case in self.cases if case["category"] == "known_chart")
        )
        with mock.patch(
            "fact_contracts.ziwei.evidence_rules.production_evidence_rules",
            side_effect=RuntimeError("fixture evidence index failure"),
        ):
            validation = adapter_validate.validate_payload("ziwei", facts)
        self.assertFalse(validation["ok"], validation)
        self.assertIn("fact_contract_error", validation["codes"])

    def test_known_charts_emit_independent_natal_fact_layers(self) -> None:
        for case in (item for item in self.cases if item["category"] == "known_chart"):
            with self.subTest(case=case["id"]):
                facts = _facts(case)
                expected = case["expected"]
                lunar = facts["calendar_normalization"]["lunar_date"]
                self.assertEqual(
                    [lunar["month"], lunar["day"], lunar["is_leap_month"]],
                    expected["lunar"],
                )
                ming_shen = facts["output"]["ming_shen"]
                self.assertEqual(
                    [ming_shen["ming_branch"], ming_shen["shen_branch"]],
                    expected["ming_shen"],
                )
                self.assertEqual(
                    facts["output"]["five_elements_class"],
                    expected["five_elements_class"],
                )
                layer = facts["output"]["transformation_layers"]["natal"]
                self.assertEqual(
                    [item["transformation"] for item in layer],
                    list(TRANSFORMATION_ORDER),
                )
                self.assertEqual(_render_transformations(layer), expected["transformations"])
                self.assertEqual(facts["output"]["interpretation_status"], "facts_only")
                self.assertEqual(len(facts["output"]["palaces"]), 12)
                self.assertTrue(facts["natal_fact_digest"])
                validation = adapter_validate.validate_payload("ziwei", facts)
                self.assertTrue(validation["ok"], validation)

    def test_leap_month_cases_use_the_declared_fix_leap_profile(self) -> None:
        for case in (item for item in self.cases if item["category"] == "leap_month"):
            with self.subTest(case=case["id"]):
                facts = _facts(case)
                lunar = facts["calendar_normalization"]["lunar_date"]
                self.assertEqual(
                    [lunar["month"], lunar["day"], lunar["is_leap_month"]],
                    case["expected"]["lunar"],
                )
                ming_shen = facts["output"]["ming_shen"]
                self.assertEqual(
                    [ming_shen["ming_branch"], ming_shen["shen_branch"]],
                    case["expected"]["ming_shen"],
                )
                self.assertTrue(facts["adapter"]["engine_contract"]["fix_leap"])

    def test_zi_hour_policy_is_consumed_by_the_engine_input(self) -> None:
        for case in (item for item in self.cases if item["category"] == "zi_hour"):
            with self.subTest(case=case["id"]):
                facts = _facts(case)
                expected = case["expected"]
                normalized = facts["input"]["normalized_input"]
                self.assertEqual(normalized["ziwei_engine_input"]["time_index"], expected["time_index"])
                self.assertEqual(facts["output"]["solar_date"], expected["engine_solar_date"])
                self.assertEqual(facts["output"]["chinese_date"].split()[2], expected["day_pillar"])
                self.assertEqual(facts["output"]["time"], expected["time"])
                ming_shen = facts["output"]["ming_shen"]
                self.assertEqual(
                    [ming_shen["ming_branch"], ming_shen["shen_branch"]],
                    expected["ming_shen"],
                )

    def test_gender_and_lunar_year_polarity_determine_limit_direction(self) -> None:
        for case in (item for item in self.cases if item["category"] == "direction"):
            with self.subTest(case=case["id"]):
                facts = _facts(case)
                expected = case["expected"]
                direction = facts["output"]["major_limit_direction"]
                self.assertEqual(direction["year_stem"], expected["year_stem"])
                self.assertEqual(direction["year_polarity"], expected["year_polarity"])
                self.assertEqual(direction["direction"], expected["direction"])
                ordered = sorted(facts["output"]["major_limits"], key=lambda row: row["sequence"])
                self.assertEqual([row["palace"] for row in ordered[:3]], expected["first_palaces"])

    def test_major_limit_boundaries_are_exact_target_facts(self) -> None:
        for case in (item for item in self.cases if item["category"] == "limit_boundary"):
            with self.subTest(case=case["id"]):
                facts = _facts(case)
                snapshot = ziwei_fact_adapter.build_target_fact_snapshot(
                    facts, case["input"]["target_date"]
                )
                actual = snapshot["major_limit"]
                expected = case["expected"]
                self.assertEqual(actual["index"], expected["index"])
                self.assertEqual(
                    actual["heavenlyStem"] + actual["earthlyBranch"],
                    expected["stem_branch"],
                )
                self.assertEqual(actual["active_natal_palace"]["name"], expected["natal_palace"])
                self.assertEqual(snapshot["boundary_profile"]["age_divide"], "normal/nominal-age")

    def test_each_requested_scope_locates_all_four_transformations(self) -> None:
        for case in (
            item for item in self.cases if item["category"] == "temporal_transformations"
        ):
            with self.subTest(case=case["id"]):
                facts = _facts(case)
                snapshot = ziwei_fact_adapter.build_target_fact_snapshot(
                    facts, case["input"]["target_date"]
                )
                for fixture_scope, output_scope in (
                    ("major", "major_limit"),
                    ("annual", "annual"),
                    ("monthly", "monthly"),
                ):
                    layer = snapshot["transformation_layers"][output_scope]
                    self.assertEqual(
                        [item["transformation"] for item in layer],
                        list(TRANSFORMATION_ORDER),
                    )
                    self.assertEqual(
                        _render_transformations(layer),
                        case["expected"][fixture_scope],
                    )
                    self.assertTrue(
                        all(item["palace_branch"] for item in layer),
                        layer,
                    )
                    self.assertTrue(
                        all(item["source_dependency_id"] for item in layer),
                        layer,
                    )

    def test_engine_contract_and_source_roles_are_machine_readable(self) -> None:
        facts = _facts(self.cases[0])
        contract = facts["adapter"]["engine_contract"]
        provenance = json.loads(
            (ziwei_fact_adapter.VENDOR / "PROVENANCE.json").read_text(encoding="utf-8")
        )
        self.assertEqual(contract["version"], "2.5.8")
        self.assertEqual(contract["config"], {
            "algorithm": "default",
            "yearDivide": "normal",
            "ageDivide": "normal",
            "dayDivide": "current",
            "horoscopeDivide": "normal",
        })
        self.assertEqual(contract["artifact_sha256"], provenance["vendored_sha256"])
        self.assertEqual(contract["license_sha256"], provenance["license_sha256"])
        roles = facts["source_lineage"]
        self.assertEqual(roles["calculation"][0]["pack"], "ziwei/ziwei-doushu-quanshu")
        self.assertEqual(roles["interpretation"][0]["pack"], "ziwei/taiwei-fu")
        self.assertEqual(
            roles["commentary_only"][0]["pack"],
            "ziwei/feixing-ziwei-doushu-yuanzhi",
        )

    def test_validator_fails_closed_on_direction_or_transformation_tampering(self) -> None:
        facts = _facts(self.cases[0])
        broken_direction = copy.deepcopy(facts)
        broken_direction["output"]["major_limit_direction"]["direction"] = "reverse"
        result = adapter_validate.validate_payload("ziwei", broken_direction)
        self.assertFalse(result["ok"])
        self.assertIn("ziwei_major_limit_direction_mismatch", result["codes"])

        broken_transformations = copy.deepcopy(facts)
        broken_transformations["output"]["transformation_layers"]["natal"].pop()
        result = adapter_validate.validate_payload("ziwei", broken_transformations)
        self.assertFalse(result["ok"])
        self.assertIn("ziwei_incomplete_natal_transformations", result["codes"])

    def test_same_input_repeats_the_same_natal_fact_digest(self) -> None:
        case = next(item for item in self.cases if item["id"] == "known-public-1970")
        first = _facts(case)
        second = _facts(case)
        self.assertEqual(first["natal_fact_digest"], second["natal_fact_digest"])
        self.assertEqual(first["output"], second["output"])

    def test_month_horizon_keeps_explicit_palace_star_and_transformation_facts(self) -> None:
        facts = _facts(next(item for item in self.cases if item["id"] == "direction-yang-male"))
        extension = ziwei_fact_adapter.build_horizon_fact_extensions(
            facts, horizon={"kind": "month", "start": "2026-07", "end": "2026-07"}
        )
        for segment in extension["monthly_layers"]["2026-07"]["segments"]:
            layer = segment["liu_yue"]
            self.assertEqual(len(layer["palace_assignments"]), 12)
            self.assertTrue(all("chart_palace" in row for row in layer["palace_assignments"]))
            self.assertTrue(all("palace" in row for row in layer["star_facts"]))
            self.assertEqual(len(segment["transformation_facts"]), 4)
        self.assertEqual(extension["interpretation_status"], "facts_only")
        validation = adapter_validate.validate_ziwei_extension(extension)
        self.assertTrue(validation["ok"], validation)

        broken = copy.deepcopy(extension)
        broken["monthly_layers"]["2026-07"]["segments"][0]["liu_yue"][
            "transformation_facts"
        ][0]["star"] = "不存在的星"
        validation = adapter_validate.validate_ziwei_extension(broken)
        self.assertFalse(validation["ok"])
        self.assertIn("ziwei_temporal_transformation_mismatch", validation["codes"])


if __name__ == "__main__":
    unittest.main()
