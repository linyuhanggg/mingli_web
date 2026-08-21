#!/usr/bin/env python3
"""Task 7N live-provider replay contract for early Luming/Nayin."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import yaml

import audit_luming_provider
from reading_engine.providers import PROVIDER_CAPABILITIES, LumingProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "luming-v51.yaml"
REQUIRED_BOUNDARIES = {
    "solar_term_boundary",
    "day_rollover",
    "leap_month",
    "timezone_boundary",
}


class LumingProviderReplayAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit_luming_provider.audit_luming_provider()

    def test_every_route_owned_case_is_a_qualifying_double_provider_replay(self) -> None:
        report = self.report
        counts = report["counts"]

        self.assertTrue(
            {
                "route_owned_cases",
                "qualifying_cases",
                "provider_calculations",
                "determinism_checks",
                "adapter_validation_checks",
                "source_binding_checks",
            }
            <= set(counts),
            counts,
        )
        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["status"], "pass")
        self.assertGreaterEqual(counts["route_owned_cases"], 30)
        self.assertEqual(counts["qualifying_cases"], counts["route_owned_cases"])
        self.assertEqual(
            counts["provider_calculations"],
            2 * counts["route_owned_cases"],
        )
        self.assertEqual(counts["determinism_checks"], counts["route_owned_cases"])
        self.assertEqual(
            counts["adapter_validation_checks"],
            2 * counts["route_owned_cases"],
        )
        self.assertEqual(
            counts["source_binding_checks"],
            2 * counts["route_owned_cases"],
        )
        self.assertEqual(report["findings"], [])

    def test_provider_identity_sources_boundaries_and_fixture_hash_are_release_bound(self) -> None:
        report = self.report

        self.assertTrue(
            {
                "provider",
                "fixture",
                "fixture_sha256",
                "boundary_categories",
                "algorithm_sources",
            }
            <= set(report),
            report,
        )
        self.assertEqual(
            report["provider"],
            {
                "class": "reading_engine.providers.LumingProvider",
                "provider_id": "mingli-master.luming-nayin.v1",
                "provider_version": "1.2.0",
                "capability_mode": "calculation",
            },
        )
        self.assertEqual(
            report["fixture_sha256"],
            hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            report["fixture"]["sha256"],
            report["fixture_sha256"],
        )
        self.assertTrue(REQUIRED_BOUNDARIES <= set(report["boundary_categories"]))
        self.assertTrue(report["algorithm_sources"]["ok"], report)
        self.assertTrue(
            report["algorithm_sources"]["research_sources_verified"],
            report,
        )
        self.assertEqual(
            report["algorithm_sources"]["dependency_ids"],
            [
                "luming.nayin.sixty-jiazi-table",
                "luming.three-yuan-and-taiyuan",
                "luming.relations.lu-ma-gui",
                "luming.source-conditioned-patterns",
            ],
        )

    def test_audit_source_contains_real_provider_calculation_not_only_helpers(self) -> None:
        source = Path(audit_luming_provider.__file__).read_text(encoding="utf-8")

        self.assertIn("LumingProvider", source)
        self.assertIn("provider.calculate", source)

    def test_mutated_fixture_or_oracle_fails_closed(self) -> None:
        payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(payload)
        mutated["nayin_cycle"][0][1] = "大海水"
        mutated["calendar_cases"][0]["expected_pillars"][0] = "甲子"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "luming-mutated.yaml"
            path.write_text(
                yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_luming_provider.audit_luming_provider(fixture_path=path)

        self.assertFalse(report["provider_ready"])
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            {"fixture_sha256", "fixture"} <= set(report),
            report,
        )
        self.assertTrue(
            {"qualifying_cases", "route_owned_cases"} <= set(report["counts"]),
            report,
        )
        self.assertNotEqual(report["fixture_sha256"], report["fixture"]["expected_sha256"])
        self.assertTrue(
            any("fixture sha256 mismatch" in item for item in report["findings"]),
            report,
        )
        self.assertLess(
            report["counts"]["qualifying_cases"],
            report["counts"]["route_owned_cases"],
        )

    def test_non_calculation_capability_cannot_report_provider_ready(self) -> None:
        unavailable = replace(PROVIDER_CAPABILITIES["luming-nayin"], mode="unavailable")
        with patch.dict(
            PROVIDER_CAPABILITIES,
            {"luming-nayin": unavailable},
        ):
            report = audit_luming_provider.audit_luming_provider()

        self.assertFalse(report["provider_ready"], report)
        self.assertIn(
            "Luming provider capability mode is not calculation",
            report["findings"],
        )


if __name__ == "__main__":
    unittest.main()
