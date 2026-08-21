#!/usr/bin/env python3
"""Task 7N regressions for the dedicated Bazi provider audit."""

from __future__ import annotations

import unittest
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import yaml

import bazi_fact_adapter as bazi
import audit_bazi_provider as audit
import build_evidence_index
import generate_classical_evidence_bindings
from reading_engine.contracts import CalculationResult
from reading_engine.evidence_rules import EvidenceRule


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "audit_bazi_provider.py"


def _birth() -> dict:
    facts, conflict = bazi.build_from_birth(
        "2000-10-18T06:45:00",
        timezone_name="Asia/Shanghai",
        location="上海",
        gender="male",
        expected_pillars=None,
        zi_hour_policy="midnight",
    )
    if conflict:
        raise AssertionError("fixed Bazi audit birth unexpectedly conflicts")
    return facts


def _fresh_evidence_rules() -> tuple[EvidenceRule, ...]:
    records = build_evidence_index.compile_evidence_rules(
        root=ROOT, enforce_classical_bindings=False
    )
    bindings = generate_classical_evidence_bindings.load_committed()["bindings"]
    for record in records:
        binding = bindings.get(record["rule_id"])
        signature = build_evidence_index.canonical_predicate_signature(
            record["required_fact_predicates"], record["excluded_fact_predicates"]
        )
        record_digest = build_evidence_index.canonical_rule_record_digest(record)
        if binding is None:
            record.update(
                runtime_active=False,
                classical_binding_status="inactive_unscoped",
                applicability_signature=signature,
                rule_record_digest=record_digest,
                classical_binding_digest="",
                classical_sources=[],
            )
        else:
            record.update(
                runtime_active=binding["verification_status"] == "verified",
                classical_binding_status=binding["verification_status"],
                applicability_signature=signature,
                rule_record_digest=record_digest,
                classical_binding_digest=binding["binding_digest"],
                classical_sources=binding["classical_sources"],
            )
    return tuple(EvidenceRule.from_dict(record) for record in records)


def _representative_calculation() -> CalculationResult:
    return CalculationResult.create(
        system="bazi",
        provider_id="fixture.bazi",
        provider_version="4.1",
        input_payload={"fixture": "qiongtong-audit"},
        facts={
            "chart_facts": {
                "output": {
                    "day_master": {"stem": "甲"},
                    "month_command": {"branch": "寅"},
                }
            }
        },
    )


class BaziAuditBootstrapTests(unittest.TestCase):
    def test_dedicated_audit_module_exists(self) -> None:
        self.assertTrue(AUDIT.is_file())

    def test_dedicated_audit_exposes_fail_closed_entrypoint(self) -> None:
        self.assertTrue(callable(getattr(audit, "audit_bazi_provider", None)))


class BaziQiongtongApplicabilityAuditTests(unittest.TestCase):
    def test_separates_structural_coverage_from_verified_fixture_coverage(self) -> None:
        findings: list[str] = []
        with mock.patch(
            "audit_bazi_provider.production_evidence_rules",
            return_value=_fresh_evidence_rules(),
        ):
            report, complete = audit._source_applicability(
                _representative_calculation(), findings
            )

        self.assertTrue(complete, findings)
        self.assertEqual(report["structural_tiaohou_chapters"], 40)
        self.assertEqual(report["runtime_verified_tiaohou_chapters"], 18)
        self.assertEqual(report["fixture_required_tiaohou_chapters"], 17)
        self.assertEqual(report["fixture_covered_tiaohou_chapters"], 17)
        self.assertNotIn(
            "bazi/qiongtong-baojian#QTB-M01",
            report["runtime_verified_tiaohou_rule_ids"],
        )
        self.assertEqual(findings, [])

    def test_methodology_rule_cannot_replace_a_missing_fixture_chapter(self) -> None:
        missing_rule_id = "bazi/qiongtong-baojian#QR-03-07"
        rules = tuple(
            replace(
                rule,
                runtime_active=False,
                classical_binding_status="inactive_unverified",
            )
            if rule.rule_id == missing_rule_id
            else rule
            for rule in _fresh_evidence_rules()
        )
        findings: list[str] = []
        with mock.patch(
            "audit_bazi_provider.production_evidence_rules",
            return_value=rules,
        ):
            report, complete = audit._source_applicability(
                _representative_calculation(), findings
            )

        self.assertFalse(complete)
        self.assertEqual(report["fixture_covered_tiaohou_chapters"], 16)
        self.assertIn(
            "Bazi verified Qiongtong chapters do not cover every route fixture context",
            findings,
        )
        self.assertIn(
            "bazi/qiongtong-baojian#QTB-M01",
            {
                rule.rule_id
                for rule in rules
                if rule.runtime_active and rule.evidence_role == "methodology_rule"
            },
        )


class BaziProviderAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit.audit_bazi_provider()

    def test_live_audit_is_ready_only_after_all_checks_pass(self) -> None:
        self.assertTrue(self.report["provider_ready"], self.report["findings"])
        self.assertEqual(self.report["status"], "pass")
        self.assertEqual(self.report["findings"], [])
        self.assertTrue(all(self.report["checks"].values()))

    def test_audit_counts_route_owned_provider_cases_and_boundaries(self) -> None:
        counts = self.report["counts"]

        self.assertEqual(counts["fixture_cases"], 34)
        self.assertEqual(counts["fixture_oracle_cases"], 34)
        self.assertEqual(counts["qualifying_provider_cases"], 30)
        self.assertEqual(counts["route_owned_cases"], 30)
        self.assertEqual(counts["provider_calculation_pairs"], 34)
        self.assertEqual(counts["provider_extension_pairs"], 15)
        self.assertEqual(counts["determinism_pairs"], 49)
        self.assertEqual(counts["declared_horizons_executed"], 4)
        self.assertEqual(counts["boundary_categories"], 6)
        self.assertEqual(counts["microsecond_boundaries"], 8)
        self.assertGreaterEqual(counts["algorithm_dependencies"], 5)
        self.assertGreaterEqual(counts["source_applicable_rules"], 40)
        self.assertGreater(counts["source_unbound_rules"], 0)

    def test_audit_binds_versions_provenance_and_fixture_hash(self) -> None:
        runtime = self.report["runtime"]
        fixture = self.report["fixture"]

        self.assertEqual(runtime["provider_class"], "BaziProvider")
        self.assertEqual(runtime["provider_id"], "mingli-master.bazi.v7")
        self.assertTrue(runtime["provider_version"])
        self.assertEqual(runtime["adapter_version"], "1.3.0")
        self.assertTrue(runtime["calendar_algorithm_version"])
        self.assertEqual(
            fixture["sha256"],
            "f5e7e1f5460ef1faf1b2d64dcc5b97cbfca8adeca03945aa9c59f2fb25bf13a4",
        )
        self.assertTrue(self.report["source_applicability"]["unbound_fail_closed"])

    def test_missing_route_fixtures_fail_closed(self) -> None:
        payload = yaml.safe_load(audit.FIXTURE.read_text(encoding="utf-8"))
        payload["cases"] = []
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "bazi-fixtures.yaml"
            fixture.write_text(
                yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit.audit_bazi_provider(fixture_path=fixture)

        self.assertFalse(report["provider_ready"])
        self.assertTrue(
            any("fixture sha256 mismatch" in item for item in report["findings"])
        )
        self.assertTrue(
            any("at least 30" in item for item in report["findings"])
        )


class BaziBoundaryPrecisionTests(unittest.TestCase):
    def test_luck_cycle_overlap_preserves_microsecond_boundary(self) -> None:
        point = datetime.fromisoformat("2007-07-09T18:28:52.600800+08:00")
        result = bazi._extension_active_luck_cycle_interval(
            point,
            point + timedelta(microseconds=1),
            _birth(),
            transition_status="transition_period",
        )

        cycle = result["cycles"][0]
        self.assertEqual(
            cycle["cycle_start_datetime"],
            point.isoformat(timespec="microseconds"),
        )
        self.assertEqual(
            cycle["overlap_start_inclusive"],
            point.isoformat(timespec="microseconds"),
        )
        self.assertEqual(
            cycle["overlap_end_exclusive"],
            (point + timedelta(microseconds=1)).isoformat(
                timespec="microseconds"
            ),
        )


if __name__ == "__main__":
    unittest.main()
