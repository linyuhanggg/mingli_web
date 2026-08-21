"""Task 7N fail-closed audit tests for the live Ziwei provider."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import yaml

from reading_engine.contracts import ReadingRequest
from reading_engine.providers import ZiweiProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "ziwei-v51.yaml"
AUDIT = ROOT / "scripts" / "audit_ziwei_provider.py"

if AUDIT.is_file():
    import audit_ziwei_provider
else:  # RED state: the dedicated audit must be implemented after this test.
    audit_ziwei_provider = None


class ZiweiProviderFixtureContractTests(unittest.TestCase):
    def test_dedicated_audit_script_exists(self) -> None:
        self.assertTrue(AUDIT.is_file(), "Task 7N requires audit_ziwei_provider.py")

    def test_route_owned_fixture_declares_provider_and_independent_1970_oracle(self) -> None:
        payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        contract = payload.get("provider_contract")
        self.assertIsInstance(contract, dict, "fixture must declare provider_contract")
        assert isinstance(contract, dict)
        self.assertEqual(contract["system"], "ziwei")
        self.assertEqual(
            contract["provider_class"],
            "reading_engine.providers.ZiweiProvider",
        )
        self.assertEqual(contract["provider_id"], "mingli-master.ziwei.iztro")
        self.assertEqual(contract["provider_version"], "1.2.0+iztro-2.5.8")
        self.assertEqual(contract["minimum_fixture_cases"], 30)
        self.assertEqual(contract["timezone"], "Asia/Shanghai")
        self.assertEqual(contract["location"], "上海")
        self.assertEqual(
            contract["algorithm_dependency_ids"],
            [
                "ziwei.iztro.natal-palaces-stars-transformations",
                "ziwei.iztro.decadal-year-month-horoscope",
                "ziwei.iztro.leap-hour-major-limit-conventions",
                "ziwei.source-conditioned-patterns",
            ],
        )

        cases = list(payload["cases"])
        self.assertGreaterEqual(len(cases), contract["minimum_fixture_cases"])
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        categories = Counter(case["category"] for case in cases)
        self.assertEqual(
            set(contract["required_boundary_categories"]),
            {
                "known_chart",
                "leap_month",
                "zi_hour",
                "direction",
                "limit_boundary",
                "temporal_transformations",
            },
        )
        self.assertTrue(
            all(categories[category] > 0 for category in contract["required_boundary_categories"])
        )

        benchmark = next(case for case in cases if case["id"] == "known-public-1970")
        self.assertEqual(benchmark["input"].get("timezone"), "Asia/Shanghai")
        self.assertEqual(benchmark["input"].get("location"), "北京，中国")
        self.assertEqual(
            benchmark["oracle"],
            {
                "kind": "fixed_independent_public_benchmark",
                "source_dependency_id": "ziwei.iztro.natal-palaces-stars-transformations",
                "source_path": "references/matrices/algorithm-source-dependencies.yaml",
                "source_anchor": "ziwei-public-benchmark-1970-07-22",
                "independence": "expected chart facts are stored outside ZiweiProvider and are never generated during audit",
            },
        )
        self.assertEqual(benchmark["expected"]["ganzhi"], ["庚戌", "癸未", "癸卯", "庚申"])
        self.assertEqual(
            benchmark["expected"]["first_palace"],
            {
                "name": "田宅",
                "earthly_branch": "寅",
                "major_stars": [
                    {"name": "太阳", "brightness": "旺", "mutagen": "禄"},
                    {"name": "巨门", "brightness": "庙", "mutagen": ""},
                ],
            },
        )


@unittest.skipUnless(AUDIT.is_file(), "dedicated audit is still in the RED state")
class ZiweiProviderAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert audit_ziwei_provider is not None
        cls.report = audit_ziwei_provider.audit_ziwei_provider()

    def test_audit_uses_the_live_provider_and_passes_every_route_owned_case(self) -> None:
        report = self.report
        self.assertEqual(report["schema_version"], "mingli-ziwei-provider-audit-v1")
        self.assertEqual(report["system"], "ziwei")
        self.assertEqual(report["status"], "pass", report["findings"])
        self.assertTrue(report["provider_ready"], report["findings"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(
            report["provider"],
            {
                "class": "reading_engine.providers.ZiweiProvider",
                "provider_id": "mingli-master.ziwei.iztro",
                "provider_version": "1.2.0+iztro-2.5.8",
                "capability_mode": "calculation",
            },
        )
        counts = report["counts"]
        self.assertEqual(counts["fixture_cases"], 32)
        self.assertEqual(counts["provider_calculation_runs"], 64)
        self.assertEqual(counts["calculation_determinism_pairs"], 32)
        self.assertEqual(counts["temporal_fixture_extension_cases"], 8)
        self.assertEqual(counts["declared_horizon_probe_cases"], 2)
        self.assertEqual(counts["extension_cases"], 10)
        self.assertEqual(counts["provider_extension_runs"], 20)
        self.assertEqual(counts["extension_determinism_pairs"], 10)
        self.assertEqual(counts["algorithm_dependencies"], 4)
        self.assertEqual(counts["independent_oracles"], 1)
        self.assertEqual(
            counts["fixtures_by_category"],
            {
                "known_chart": 8,
                "leap_month": 6,
                "zi_hour": 6,
                "direction": 4,
                "limit_boundary": 4,
                "temporal_transformations": 4,
            },
        )
        self.assertEqual(
            report["fixture_sha256"], hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        )

    def test_independent_1970_oracle_reaches_exact_palace_and_stars(self) -> None:
        check = self.report["independent_oracle_checks"]["known-public-1970"]
        self.assertTrue(check["passed"], check)
        self.assertEqual(check["ganzhi"], ["庚戌", "癸未", "癸卯", "庚申"])
        self.assertEqual(check["palace"], ["田宅", "寅"])
        self.assertEqual(
            check["major_stars"],
            [["太阳", "旺", "禄"], ["巨门", "庙", ""]],
        )
        self.assertEqual(
            check["source_dependency_id"],
            "ziwei.iztro.natal-palaces-stars-transformations",
        )

    def test_algorithm_sources_versions_and_boundary_coverage_are_audited(self) -> None:
        source_report = self.report["algorithm_sources"]
        self.assertTrue(source_report["ok"], source_report)
        self.assertTrue(source_report["research_sources_verified"], source_report)
        self.assertEqual(
            source_report["dependency_ids"],
            [
                "ziwei.iztro.natal-palaces-stars-transformations",
                "ziwei.iztro.decadal-year-month-horoscope",
                "ziwei.iztro.leap-hour-major-limit-conventions",
                "ziwei.source-conditioned-patterns",
            ],
        )
        self.assertEqual(
            self.report["boundary_coverage"],
            {
                "known_chart": True,
                "leap_month": True,
                "zi_hour": True,
                "direction": True,
                "limit_boundary": True,
                "temporal_transformations": True,
            },
        )
        self.assertEqual(
            self.report["declared_horizon_coverage"],
            {"life": True, "month": True, "year": True},
        )
        self.assertTrue(self.report["source_dependency_bindings_complete"])

    def test_month_extension_binds_target_date_and_rejects_out_of_range_target(self) -> None:
        provider = ZiweiProvider(ROOT)
        base = provider.calculate(
            ReadingRequest(
                query="紫微目标日绑定核验",
                system="ziwei",
                timezone="Asia/Shanghai",
                location="上海",
                birth_data={
                    "datetime": "1990-06-15T10:00:00",
                    "timezone": "Asia/Shanghai",
                    "location": "上海",
                    "gender": "male",
                    "zi_hour_policy": "midnight",
                },
            )
        )

        bound = provider.extend(
            base,
            ("timing",),
            {
                "kind": "month",
                "start": "2025-01",
                "end": "2025-01",
                "target_date": "2025-01-28",
            },
        )
        assert bound.fact_extension is not None
        self.assertEqual(bound.fact_extension.status, "complete")
        self.assertEqual(
            bound.fact_extension.facts["calendar_coverage"][
                "requested_target_date"
            ],
            "2025-01-28",
        )

        out_of_range = provider.extend(
            base,
            ("timing",),
            {
                "kind": "month",
                "start": "2025-01",
                "end": "2025-01",
                "target_date": "2025-02-01",
            },
        )
        assert out_of_range.fact_extension is not None
        self.assertEqual(out_of_range.fact_extension.status, "unsupported")

    def test_audit_cannot_bypass_calculate_or_extend_through_adapter_helpers(self) -> None:
        source = AUDIT.read_text(encoding="utf-8")
        self.assertIn("ZiweiProvider", source)
        self.assertIn("provider.calculate", source)
        self.assertIn("provider.extend", source)
        self.assertNotIn("ziwei_fact_adapter.build_from_birth", source)
        self.assertNotIn("ziwei_fact_adapter.build_target_fact_snapshot", source)

    def test_tampered_or_incomplete_fixture_fails_closed(self) -> None:
        assert audit_ziwei_provider is not None
        payload = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(payload)
        mutated["provider_contract"]["provider_version"] = "tampered-version"
        mutated["cases"] = mutated["cases"][:29]
        benchmark = next(
            case for case in mutated["cases"] if case["id"] == "known-public-1970"
        )
        benchmark["expected"]["first_palace"]["name"] = "命宫"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ziwei-mutated.yaml"
            path.write_text(
                yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_ziwei_provider.audit_ziwei_provider(fixture_path=path)
        self.assertFalse(report["provider_ready"])
        self.assertEqual(report["status"], "fail")
        self.assertIn("provider contract version mismatch", report["findings"])
        self.assertIn("fewer than 30 route-owned fixtures", report["findings"])
        self.assertIn(
            "fixture mismatch: known-public-1970:first_palace",
            report["findings"],
        )


if __name__ == "__main__":
    unittest.main()
