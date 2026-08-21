#!/usr/bin/env python3
"""Task 7N regressions for the dedicated Fortune provider audit."""

from __future__ import annotations

import copy
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import yaml

import audit_fortune_provider
from reading_engine.contracts import ReadingRequest
from reading_engine.providers import FortuneProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "references" / "fixtures" / "fortune-v51.yaml"


def _request(reference_datetime: str) -> ReadingRequest:
    return ReadingRequest(
        query="看这一天",
        action="new",
        system="fortune",
        birth_data={
            "birth_datetime": "2000-10-18T06:45:00",
            "timezone": "Asia/Shanghai",
            "location": "上海",
            "gender": "male",
        },
        reference_datetime=reference_datetime,
    )


class FortuneReferenceSemanticsTests(unittest.TestCase):
    def test_reference_instant_selects_the_post_jie_day_segment(self) -> None:
        calculation = FortuneProvider(ROOT).calculate(
            _request("2024-02-04T18:00:00+08:00")
        )
        chart = calculation.facts["chart_facts"]
        segment = chart["selected_bazi_day_segment"]
        selected_at = datetime.fromisoformat(chart["reference_selection"]["selected_at"])

        self.assertEqual(chart["reference_selection"]["basis"], "reference_datetime")
        self.assertLessEqual(datetime.fromisoformat(segment["start_inclusive"]), selected_at)
        self.assertLess(selected_at, datetime.fromisoformat(segment["end_exclusive"]))
        self.assertEqual(segment["active_transits"]["year"], "甲辰")
        self.assertEqual(segment["active_transits"]["month"], "丙寅")
        self.assertEqual(chart["transit_layers"]["year"]["pillar"], "甲辰")
        self.assertEqual(chart["transit_layers"]["month"]["pillar"], "丙寅")

    def test_provider_fails_closed_outside_its_declared_day_scope(self) -> None:
        provider = FortuneProvider(ROOT)
        with self.assertRaisesRegex(ValueError, "reference_datetime"):
            provider.calculate(ReadingRequest(
                query="看今天",
                action="new",
                system="fortune",
                birth_data=_request("2024-02-04T12:00:00+08:00").birth_data,
            ))

        calculation = provider.calculate(_request("2024-02-04T12:00:00+08:00"))
        valid = provider.extend(
            calculation,
            ("timing",),
            {"kind": "day", "start": "2024-02-04", "end": "2024-02-04"},
        )
        self.assertEqual(valid.fact_extension.status, "complete")
        invalid_horizons = (
            {"kind": "instant"},
            {"kind": "month", "start": "2024-02", "end": "2024-02"},
            {"kind": "day", "start": "2024-02-05", "end": "2024-02-05"},
            {
                "kind": "day",
                "start": "2024-02-04",
                "end": "2024-02-04",
                "silent_default": True,
            },
        )
        for horizon in invalid_horizons:
            with self.subTest(horizon=horizon):
                result = provider.extend(calculation, ("timing",), horizon)
                self.assertEqual(result.fact_extension.status, "unsupported")
                self.assertEqual(result.fact_extension.facts, {})

        undeclared = provider.extend(
            calculation,
            ("undeclared_dimension",),
            {"kind": "day", "start": "2024-02-04", "end": "2024-02-04"},
        )
        self.assertEqual(undeclared.fact_extension.status, "unsupported")
        self.assertEqual(undeclared.fact_extension.facts, {})


class FortuneFixtureContractTests(unittest.TestCase):
    def test_route_owned_fixture_has_readable_independent_oracles(self) -> None:
        fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        cases = list(fixture["cases"])

        self.assertEqual(
            fixture["schema_version"],
            "mingli-fortune-provider-fixtures-v1",
        )
        self.assertEqual(fixture["fixture_version"], "1.0.1")
        self.assertGreaterEqual(len(cases), 30)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertEqual(set(fixture["oracle_sources"]), {"hko-2024", "hko-2025", "hko-2026"})
        for source in fixture["oracle_sources"].values():
            self.assertEqual(
                source["role"],
                "government-published independent calendar oracle; not a Fortune interpretation oracle",
            )
            self.assertRegex(source["artifact_sha256"], r"^[0-9a-f]{64}$")
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertIn(case["source_id"], fixture["oracle_sources"])
                self.assertRegex(case["source_anchor"], r"^CSV row \d+$")
                self.assertEqual(
                    set(case["expected_lunar"]),
                    {"year", "month", "day", "is_leap_month"},
                )
                self.assertEqual(case["horizon"], {"kind": "day"})
        self.assertTrue(
            {
                "solar_term_boundary",
                "day_rollover",
                "lunar_new_year_boundary",
                "leap_day",
                "leap_month_boundary",
            }
            <= {case["category"] for case in cases}
        )

    def test_machine_audit_runs_every_real_provider_case_twice(self) -> None:
        report = audit_fortune_provider.audit_fortune_provider()

        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["status"], "pass")
        self.assertGreaterEqual(report["counts"]["qualifying_cases"], 30)
        self.assertEqual(
            report["counts"]["provider_calculations"],
            2 * report["counts"]["qualifying_cases"],
        )
        self.assertEqual(
            report["counts"]["provider_extensions"],
            2 * report["counts"]["qualifying_cases"],
        )
        self.assertEqual(report["counts"]["oracle_mismatches"], 0)
        self.assertEqual(report["counts"]["deterministic_mismatches"], 0)
        self.assertEqual(report["counts"]["extension_mismatches"], 0)
        self.assertEqual(report["counts"]["source_artifact_mismatches"], 0)
        self.assertEqual(report["counts"]["algorithm_dependencies"], 1)
        self.assertEqual(report["counts"]["algorithm_source_findings"], 0)
        self.assertGreaterEqual(report["counts"]["boundary_cases"], 8)
        self.assertEqual(report["provider"]["provider_id"], "mingli-master.fortune.v6")
        self.assertEqual(
            report["provider"]["provider_version"],
            "fortune-public-v6-mechanism-stack",
        )
        self.assertEqual(report["findings"], [])

    def test_machine_audit_rejects_a_mutated_or_duplicate_fixture(self) -> None:
        fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(fixture)
        mutated["cases"][0]["expected_lunar"]["day"] = 99
        mutated["cases"].append(copy.deepcopy(mutated["cases"][0]))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fortune-mutated.yaml"
            path.write_text(
                yaml.safe_dump(mutated, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            report = audit_fortune_provider.audit_fortune_provider(
                fixture_path=path
            )

        self.assertFalse(report["provider_ready"])
        self.assertIn("Fortune fixture artifact hash mismatch", report["findings"])
        self.assertIn("Fortune fixture case ids are not unique", report["findings"])

    def test_machine_audit_rejects_a_symlinked_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fortune-link.yaml"
            path.symlink_to(FIXTURE)
            report = audit_fortune_provider.audit_fortune_provider(
                fixture_path=path
            )

        self.assertFalse(report["provider_ready"])
        self.assertIn("Fortune fixture must not be a symlink", report["findings"])


if __name__ == "__main__":
    unittest.main()
