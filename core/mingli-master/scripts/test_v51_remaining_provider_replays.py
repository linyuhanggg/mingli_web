#!/usr/bin/env python3
"""Task 7N contracts for the six remaining live-provider replay audits."""

from __future__ import annotations

import copy
from concurrent.futures import ProcessPoolExecutor
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

import yaml

import audit_test_session
import audit_fengshui_provider
import audit_liuren_provider
import audit_physiognomy_provider
import audit_qimen_provider
import audit_selection_provider
import audit_taiyi_provider
from reading_engine.providers import (
    FengshuiProvider,
    LiurenProvider,
    PhysiognomyProvider,
    QimenProvider,
    SelectionProvider,
    TaiyiProvider,
)


ROOT = Path(__file__).resolve().parents[1]


Audit = Callable[..., dict[str, Any]]


ROUTES: dict[str, dict[str, Any]] = {
    "liuren": {
        "audit": audit_liuren_provider.audit_liuren_provider,
        "provider": LiurenProvider,
        "fixture": ROOT / "references/fixtures/liuren-v51.yaml",
        "minimum": 30,
    },
    "qimen": {
        "audit": audit_qimen_provider.audit_qimen_provider,
        "provider": QimenProvider,
        "fixture": ROOT / "references/fixtures/qimen-v51.yaml",
        "minimum": 30,
    },
    "taiyi": {
        "audit": audit_taiyi_provider.audit_taiyi_provider,
        "provider": TaiyiProvider,
        "fixture": ROOT / "references/fixtures/taiyi-v51.yaml",
        "minimum": 30,
    },
    "selection": {
        "audit": audit_selection_provider.audit_selection_provider,
        "provider": SelectionProvider,
        "fixture": ROOT / "references/fixtures/selection-v51.yaml",
        "minimum": 30,
    },
    "fengshui": {
        "audit": audit_fengshui_provider.audit_fengshui_provider,
        "provider": FengshuiProvider,
        "fixture": ROOT / "references/fixtures/fengshui-v51.yaml",
        "minimum": 20,
    },
    "physiognomy": {
        "audit": audit_physiognomy_provider.audit_physiognomy_provider,
        "provider": PhysiognomyProvider,
        "fixture": ROOT / "references/fixtures/physiognomy-v51.yaml",
        "minimum": 20,
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mutated_fixture(system: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    config = ROUTES[system]
    fixture_path = config["fixture"]
    payload = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    kwargs: dict[str, Any] = {}
    if system == "liuren":
        payload["classical_cases"][0]["expected"]["transmissions"] = "子子子"
    elif system == "qimen":
        fixture_path = ROOT / "references/fixtures/qimen-go-v51.yaml"
        payload = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
        payload["cases"][0]["chief_palace"] = 99
        kwargs["external_fixture_path"] = None
    elif system == "taiyi":
        payload["external_reference_cases"][0]["expected"]["taiyi"] = "__mutated__"
    elif system == "selection":
        payload["external_reference_cases"][0]["expected"]["jianchu"] = "__mutated__"
    elif system == "fengshui":
        payload["complete_observation_fixtures"][0]["expected"]["form_status"] = "partial"
    elif system == "physiognomy":
        payload["complete_cases"][0]["expected"]["active_observation_count"] = 99
    else:  # pragma: no cover - ROUTES is closed above.
        raise AssertionError(system)
    return fixture_path, payload, kwargs


def _audit_jobs(task_count: int) -> int:
    configured = os.environ.get("MINGLI_AUDIT_JOBS")
    if configured is None:
        jobs = 3
    else:
        try:
            jobs = int(configured)
        except ValueError as exc:
            raise ValueError("MINGLI_AUDIT_JOBS must be a positive integer") from exc
        if jobs < 1:
            raise ValueError("MINGLI_AUDIT_JOBS must be a positive integer")
    return max(1, min(jobs, max(1, task_count)))


def _parallel_audit_map(worker, items):
    tasks = tuple(items)
    jobs = _audit_jobs(len(tasks))
    if jobs == 1:
        return [worker(item) for item in tasks]
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        return list(executor.map(worker, tasks))


def _run_route_audit_pair(system: str):
    config = ROUTES[system]
    live_report = audit_test_session.load_report(system)
    if live_report is None:
        live_report = config["audit"]()
    with tempfile.TemporaryDirectory() as temporary:
        source_path, payload, kwargs = _mutated_fixture(system)
        copy_path = Path(temporary) / source_path.name
        copy_path.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        call_kwargs = copy.deepcopy(kwargs)
        if system == "qimen":
            call_kwargs["external_fixture_path"] = copy_path
        else:
            call_kwargs["fixture_path"] = copy_path
        mutated_report = config["audit"](**call_kwargs)
    return system, live_report, mutated_report


class RemainingProviderReplayAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        results = _parallel_audit_map(_run_route_audit_pair, ROUTES)
        cls.reports = {
            system: live_report
            for system, live_report, _mutated_report in results
        }
        cls.mutated_reports = {
            system: mutated_report
            for system, _live_report, mutated_report in results
        }

    def test_every_report_proves_live_provider_replay_and_determinism(self) -> None:
        for system, config in ROUTES.items():
            with self.subTest(system=system):
                report = self.reports[system]
                counts = report["counts"]
                provider = config["provider"]
                qualifying = counts["qualifying_cases"]
                route_owned = counts["route_owned_cases"]
                self.assertTrue(report["provider_ready"], report)
                self.assertGreaterEqual(qualifying, config["minimum"])
                self.assertGreaterEqual(route_owned, qualifying)
                self.assertGreaterEqual(
                    counts["provider_calculations"],
                    2 * route_owned,
                )
                self.assertGreaterEqual(
                    counts["determinism_checks"],
                    route_owned,
                )
                self.assertEqual(report["fixture_sha256"], _sha256(config["fixture"]))
                self.assertEqual(report["provider"]["provider_id"], provider.provider_id)
                self.assertEqual(
                    report["provider"]["provider_version"],
                    provider.provider_version,
                )
                self.assertTrue(report["boundary_categories"])

    def test_observation_routes_cover_complete_missing_conflict_quality_correction(self) -> None:
        required = {"complete", "missing", "conflict", "low_quality", "correction"}
        for system in ("fengshui", "physiognomy"):
            with self.subTest(system=system):
                report = self.reports[system]
                self.assertTrue(required <= set(report["boundary_categories"]), report)
                self.assertGreaterEqual(report["counts"]["qualifying_cases"], 20)
                self.assertEqual(report["counts"]["invented_observations"], 0)

    def test_liuren_calendar_boundaries_run_through_the_live_provider_twice(self) -> None:
        counts = self.reports["liuren"]["counts"]
        self.assertEqual(
            counts["boundary_provider_calculations"],
            2 * counts["calendar_boundaries"],
        )
        self.assertEqual(
            counts["boundary_provider_determinism_checks"],
            counts["calendar_boundaries"],
        )

    def test_calendar_boundaries_use_live_providers_for_remaining_routes(self) -> None:
        for system in ("qimen", "taiyi", "selection"):
            with self.subTest(system=system):
                counts = self.reports[system]["counts"]
                self.assertEqual(
                    counts["boundary_provider_calculations"],
                    2 * counts["boundary_case_count"],
                )
                self.assertEqual(
                    counts["boundary_provider_determinism_checks"],
                    counts["boundary_case_count"],
                )

    def test_mutated_qualifying_oracle_fails_closed(self) -> None:
        for system, report in self.mutated_reports.items():
            with self.subTest(system=system):
                self.assertFalse(report["provider_ready"], report)
                self.assertLess(
                    report["counts"]["qualifying_cases"],
                    report["counts"]["route_owned_cases"],
                    report,
                )


if __name__ == "__main__":
    unittest.main()
