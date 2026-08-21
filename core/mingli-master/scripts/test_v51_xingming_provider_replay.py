#!/usr/bin/env python3
"""Task 7N live-provider replay contract for Xingming/Qizheng."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import yaml

import audit_xingming_provider
from reading_engine.providers import PROVIDER_CAPABILITIES, XingmingProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "xingming-v51.yaml"
REQUIRED_BOUNDARIES = {
    "reference_chart",
    "date_boundary",
    "location_boundary",
    "timezone_boundary",
}


class XingmingProviderReplayAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit_xingming_provider.audit_xingming_provider()

    def test_all_thirty_reference_charts_are_qualifying_double_provider_replays(self) -> None:
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
                "oracle_longitude_checks",
            }
            <= set(counts),
            counts,
        )
        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(counts["route_owned_cases"], 30)
        self.assertEqual(counts["qualifying_cases"], 30)
        self.assertEqual(counts["provider_calculations"], 60)
        self.assertEqual(counts["determinism_checks"], 30)
        self.assertEqual(counts["adapter_validation_checks"], 60)
        self.assertEqual(counts["source_binding_checks"], 60)
        self.assertEqual(counts["oracle_longitude_checks"], 210)
        self.assertEqual(report["findings"], [])

    def test_provider_identity_sources_boundaries_oracle_and_fixture_hash_are_bound(self) -> None:
        report = self.report

        self.assertTrue(
            {
                "provider",
                "fixture",
                "fixture_sha256",
                "boundary_categories",
                "oracle",
                "algorithm_sources",
            }
            <= set(report),
            report,
        )
        self.assertEqual(
            report["provider"],
            {
                "class": "reading_engine.providers.XingmingProvider",
                "provider_id": "mingli-master.xingming.v1",
                "provider_version": "1.1.0",
                "capability_mode": "calculation",
            },
        )
        self.assertEqual(
            report["fixture_sha256"],
            hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        )
        self.assertEqual(report["fixture"]["sha256"], report["fixture_sha256"])
        self.assertTrue(REQUIRED_BOUNDARIES <= set(report["boundary_categories"]))
        self.assertTrue(report["oracle"]["verified"], report)
        self.assertEqual(report["oracle"]["version"], "2.1.19")
        self.assertTrue(report["algorithm_sources"]["ok"], report)
        self.assertTrue(
            report["algorithm_sources"]["research_sources_verified"],
            report,
        )
        self.assertEqual(
            report["algorithm_sources"]["dependency_ids"],
            [
                "xingming.ephemeris.seven-luminaries",
                "xingming.houses.ming-shen-degrees",
                "xingming.houses.topocentric-ming-degree",
                "xingming.four-residuals.numeric-profiles",
                "xingming.transformations.ten-stem-table",
                "xingming.limits.dongwei-bailiu-table",
                "xingming.source-conditioned-patterns",
            ],
        )

    def test_audit_source_contains_real_provider_calculation_not_only_helpers(self) -> None:
        source = Path(audit_xingming_provider.__file__).read_text(encoding="utf-8")

        self.assertIn("XingmingProvider", source)
        self.assertIn("provider.calculate", source)

    def test_mutated_fixture_oracle_fails_closed_after_provider_execution(self) -> None:
        payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(payload)
        mutated["reference_charts"][0]["expected_longitudes"]["Sun"] += 1.0
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "xingming-mutated.yaml"
            path.write_text(
                yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_xingming_provider.audit_xingming_provider(
                fixture_path=path
            )

        self.assertFalse(report["provider_ready"])
        self.assertEqual(report["status"], "fail")
        self.assertTrue(
            {"fixture_sha256", "fixture"} <= set(report),
            report,
        )
        self.assertTrue(
            {"provider_calculations", "qualifying_cases"}
            <= set(report["counts"]),
            report,
        )
        self.assertNotEqual(report["fixture_sha256"], report["fixture"]["expected_sha256"])
        self.assertTrue(
            any("ephemeris oracle mismatch" in item for item in report["findings"]),
            report,
        )
        self.assertEqual(report["counts"]["provider_calculations"], 60)
        self.assertEqual(report["counts"]["qualifying_cases"], 29)

    def test_non_calculation_capability_cannot_report_provider_ready(self) -> None:
        unavailable = replace(PROVIDER_CAPABILITIES["xingming"], mode="unavailable")
        with patch.dict(
            PROVIDER_CAPABILITIES,
            {"xingming": unavailable},
        ):
            report = audit_xingming_provider.audit_xingming_provider()

        self.assertFalse(report["provider_ready"], report)
        self.assertIn(
            "Xingming provider capability mode is not calculation",
            report["findings"],
        )

    def test_unknown_oracle_body_is_a_structured_finding_not_key_error(self) -> None:
        payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(payload)
        expected = mutated["reference_charts"][0]["expected_longitudes"]
        expected["NotARealBody"] = expected.pop("Sun")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "xingming-unknown-body.yaml"
            path.write_text(
                yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_xingming_provider.audit_xingming_provider(
                fixture_path=path
            )

        self.assertFalse(report["provider_ready"], report)
        self.assertTrue(
            any("unknown oracle body" in item for item in report["findings"]),
            report,
        )


if __name__ == "__main__":
    unittest.main()
