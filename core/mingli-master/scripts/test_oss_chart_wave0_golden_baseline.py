#!/usr/bin/env python3
"""Validate and replay the legal Wave 0 Bazi/Ziwei golden baseline.

The checked-in expected values are generated only from the accepted local
Runtime adapters.  Candidate OSS engine output is deliberately not an oracle.
Use ``--refresh-baseline`` only when a reviewed Runtime release intentionally
changes the canonical facts.
"""

from __future__ import annotations

import argparse
import copy
import json
import platform
import subprocess
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
CORE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = CORE_ROOT.parents[1]
FIXTURE_ROOT = CORE_ROOT / "references" / "fixtures" / "oss-chart-wave0"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
BASELINE_COMMIT = "fdfbee2ead72145e1c67daad6eba7f63cf4b60e6"
BASELINE_TREE = "e36435068294f9501cc06eb882fd3ddbffa01542"
CASE_SCHEMA = "mingli-oss-chart-golden-case-v1"
MANIFEST_SCHEMA = "mingli-oss-chart-golden-manifest-v1"
SOURCE_TYPE = "accepted_runtime_replay"
FORBIDDEN_RAW_KEYS = {
    "candidate_oss_output",
    "engine_raw",
    "engine_raw_json",
    "iztro_raw",
    "oss_raw",
    "raw_engine_output",
    "third_party_raw",
}
SENSITIVE_INPUT_KEYS = {
    "account",
    "api_key",
    "email",
    "name",
    "real_name",
    "secret",
    "token",
}

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bazi_fact_adapter  # noqa: E402
import ziwei_fact_adapter  # noqa: E402


@dataclass(frozen=True)
class CaseDefinition:
    case_id: str
    system: str
    category: str
    kwargs: Mapping[str, Any]

    @property
    def filename(self) -> str:
        return f"{self.case_id}.json"


def _birth_kwargs(
    civil_datetime: str,
    *,
    location: str,
    gender: str,
    timezone_name: str = "Asia/Shanghai",
    zi_hour_policy: str = "midnight",
    time_basis_policy: str = "civil",
    longitude: float | None = None,
    latitude: float | None = None,
    coordinate_source: str | None = None,
) -> dict[str, Any]:
    return {
        "civil_datetime": civil_datetime,
        "timezone_name": timezone_name,
        "location": location,
        "gender": gender,
        "zi_hour_policy": zi_hour_policy,
        "time_basis_policy": time_basis_policy,
        "longitude": longitude,
        "latitude": latitude,
        "coordinate_source": coordinate_source,
    }


CASES = (
    CaseDefinition(
        "bazi-normal-civil",
        "bazi",
        "normal",
        _birth_kwargs(
            "2000-10-18T06:45:00",
            location="synthetic:shanghai-normal",
            gender="male",
        ),
    ),
    CaseDefinition(
        "bazi-lichun-before",
        "bazi",
        "solar_term_boundary",
        _birth_kwargs(
            "2024-02-04T16:26:52+08:00",
            location="synthetic:shanghai-lichun-before",
            gender="female",
        ),
    ),
    CaseDefinition(
        "bazi-lichun-after",
        "bazi",
        "solar_term_boundary",
        _birth_kwargs(
            "2024-02-04T16:26:54+08:00",
            location="synthetic:shanghai-lichun-after",
            gender="female",
        ),
    ),
    CaseDefinition(
        "bazi-late-zi-midnight",
        "bazi",
        "zi_hour_boundary",
        _birth_kwargs(
            "2024-01-01T23:30:00",
            location="synthetic:shanghai-late-zi-midnight",
            gender="male",
        ),
    ),
    CaseDefinition(
        "bazi-late-zi-next-day",
        "bazi",
        "zi_hour_boundary",
        _birth_kwargs(
            "2024-01-01T23:30:00",
            location="synthetic:shanghai-late-zi-next-day",
            gender="male",
            zi_hour_policy="late-zi-next-day",
        ),
    ),
    CaseDefinition(
        "bazi-historical-shanghai-dst",
        "bazi",
        "historical_dst",
        _birth_kwargs(
            "1945-08-15T12:00:00",
            location="synthetic:shanghai-1945-dst",
            gender="female",
        ),
    ),
    CaseDefinition(
        "bazi-apparent-solar-hour-cross",
        "bazi",
        "true_solar_time",
        _birth_kwargs(
            "2000-10-18T06:52:00",
            location="synthetic:apparent-solar-hour-cross",
            gender="male",
            time_basis_policy="local_apparent_solar-v1",
            longitude=119.1115,
            latitude=25.46096,
            coordinate_source="synthetic-fixture",
        ),
    ),
    CaseDefinition(
        "ziwei-normal-civil",
        "ziwei",
        "normal",
        _birth_kwargs(
            "1970-07-22T15:00:00+08:00",
            location="synthetic:beijing-public-benchmark",
            gender="male",
        ),
    ),
    CaseDefinition(
        "ziwei-leap-month-first-day",
        "ziwei",
        "lunar_leap_month",
        _birth_kwargs(
            "2023-03-22T10:00:00",
            location="synthetic:shanghai-leap-month",
            gender="female",
        ),
    ),
    CaseDefinition(
        "ziwei-late-zi-midnight",
        "ziwei",
        "zi_hour_boundary",
        _birth_kwargs(
            "2024-01-15T23:00:00",
            location="synthetic:shanghai-ziwei-midnight",
            gender="male",
        ),
    ),
    CaseDefinition(
        "ziwei-late-zi-next-day",
        "ziwei",
        "zi_hour_boundary",
        _birth_kwargs(
            "2024-01-15T23:00:00",
            location="synthetic:shanghai-ziwei-next-day",
            gender="male",
            zi_hour_policy="late-zi-next-day",
        ),
    ),
    CaseDefinition(
        "ziwei-apparent-solar-hour-cross",
        "ziwei",
        "true_solar_time",
        _birth_kwargs(
            "2000-10-18T06:52:00",
            location="synthetic:ziwei-apparent-solar-hour-cross",
            gender="female",
            time_basis_policy="local_apparent_solar-v1",
            longitude=119.1115,
            latitude=25.46096,
            coordinate_source="synthetic-fixture",
        ),
    ),
)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _stable_facts(payload: Mapping[str, Any]) -> dict[str, Any]:
    stable = copy.deepcopy(dict(payload))
    adapter = stable.get("adapter")
    if isinstance(adapter, dict):
        adapter.pop("generated_at", None)
    return stable


def _replay(definition: CaseDefinition) -> dict[str, Any]:
    kwargs = dict(definition.kwargs)
    if definition.system == "bazi":
        payload, conflict = bazi_fact_adapter.build_from_birth(
            expected_pillars=None,
            question_contract={"domains": [], "gender": kwargs["gender"]},
            **kwargs,
        )
        if conflict:
            raise AssertionError(f"unexpected Bazi conflict for {definition.case_id}")
    elif definition.system == "ziwei":
        payload = ziwei_fact_adapter.build_from_birth(**kwargs)
    else:
        raise AssertionError(f"unsupported system: {definition.system}")
    return _stable_facts(payload)


def _runtime_identity(system: str, facts: Mapping[str, Any]) -> dict[str, Any]:
    adapter = facts["adapter"]
    convention = facts["calendar_normalization"]["calendar_convention"]
    if system == "bazi":
        engine_id = "sxtwl"
        engine_version = convention["engine_version"]
    else:
        engine_contract = adapter["engine_contract"]
        engine_id = engine_contract["name"]
        engine_version = engine_contract["version"]
    return {
        "adapter_id": adapter["name"],
        "adapter_version": adapter["version"],
        "engine_id": engine_id,
        "engine_version": engine_version,
        "policy_profile": adapter["rule_profile"],
        "time_basis": facts["calendar_normalization"]["time_basis"]["policy"],
    }


def _source_refs(system: str) -> list[str]:
    refs = [
        f"scripts/{system}_fact_adapter.py",
        f"scripts/test_{system}_fact_adapter.py",
        "scripts/reading_engine/calendar_core.py",
    ]
    if system == "ziwei":
        refs.append("references/fixtures/ziwei-v51.yaml")
    return refs


def _build_case(definition: CaseDefinition) -> dict[str, Any]:
    facts = _replay(definition)
    case = {
        "schema_version": CASE_SCHEMA,
        "case_id": definition.case_id,
        "system": definition.system,
        "category": definition.category,
        "input": dict(definition.kwargs),
        "expected_canonical_facts": facts,
        "provenance": {
            "source_type": SOURCE_TYPE,
            "source_refs": _source_refs(definition.system),
            "baseline_commit": BASELINE_COMMIT,
            "baseline_tree": BASELINE_TREE,
            "runtime": _runtime_identity(definition.system, facts),
            "expected_schema_version": facts["schema_version"],
            "candidate_oss_role": "future_differential_actual_only_never_expected",
        },
    }
    return case


def _assert_refresh_source_matches_baseline() -> None:
    recorded_tree = subprocess.run(
        ["git", "rev-parse", f"{BASELINE_COMMIT}^{{tree}}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if recorded_tree != BASELINE_TREE:
        raise RuntimeError("BASELINE_TREE does not match BASELINE_COMMIT")
    source_paths = [
        "core/mingli-master/scripts/bazi_fact_adapter.py",
        "core/mingli-master/scripts/ziwei_fact_adapter.py",
        "core/mingli-master/scripts/ziwei_runtime.js",
        "core/mingli-master/scripts/reading_engine/calendar_core.py",
        "core/mingli-master/vendor/iztro-2.5.8",
    ]
    source_diff = subprocess.run(
        ["git", "diff", "--quiet", BASELINE_COMMIT, "--", *source_paths],
        cwd=REPO_ROOT,
        check=False,
    )
    if source_diff.returncode != 0:
        raise RuntimeError(
            "accepted Runtime sources differ from BASELINE_COMMIT; update the "
            "reviewed baseline ref before refreshing expected facts"
        )


def refresh_baseline() -> None:
    _assert_refresh_source_matches_baseline()
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    entries = []
    for definition in CASES:
        case = _build_case(definition)
        path = FIXTURE_ROOT / definition.filename
        path.write_text(
            json.dumps(case, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        entries.append(
            {
                "case_id": definition.case_id,
                "system": definition.system,
                "category": definition.category,
                "path": definition.filename,
            }
        )
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "baseline_commit": BASELINE_COMMIT,
        "baseline_tree": BASELINE_TREE,
        "source_policy": {
            "allowed_expected_source_types": [SOURCE_TYPE],
            "candidate_oss_output_role": "differential_actual_only",
            "pii_policy": "synthetic_inputs_only",
        },
        "case_count": len(entries),
        "cases": entries,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_cases() -> list[dict[str, Any]]:
    manifest = _load_manifest()
    return [
        json.loads((FIXTURE_ROOT / entry["path"]).read_text(encoding="utf-8"))
        for entry in manifest["cases"]
    ]


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key
            for child in value.values()
            for key in _walk_keys(child)
        }
    if isinstance(value, list):
        return {key for child in value for key in _walk_keys(child)}
    return set()


class GoldenBaselineTests(unittest.TestCase):
    def test_manifest_schema_and_case_uniqueness(self) -> None:
        manifest = _load_manifest()
        self.assertEqual(manifest["schema_version"], MANIFEST_SCHEMA)
        self.assertEqual(manifest["baseline_commit"], BASELINE_COMMIT)
        self.assertEqual(manifest["baseline_tree"], BASELINE_TREE)
        self.assertNotIn("content_sha256", manifest)
        self.assertEqual(manifest["case_count"], len(CASES))
        ids = [entry["case_id"] for entry in manifest["cases"]]
        paths = [entry["path"] for entry in manifest["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(paths), len(set(paths)))
        expected_files = {definition.filename for definition in CASES}
        self.assertEqual(set(paths), expected_files)
        for entry, case in zip(manifest["cases"], _load_cases()):
            with self.subTest(case=entry["case_id"]):
                self.assertNotIn("content_sha256", entry)
                self.assertEqual(case["schema_version"], CASE_SCHEMA)
                self.assertEqual(case["case_id"], entry["case_id"])
                self.assertNotIn("content_sha256", case)

    def test_required_system_and_boundary_coverage(self) -> None:
        cases = _load_cases()
        by_system = {system: [] for system in ("bazi", "ziwei")}
        for case in cases:
            by_system[case["system"]].append(case["category"])
        self.assertIn("normal", by_system["bazi"])
        self.assertIn("normal", by_system["ziwei"])
        self.assertIn("solar_term_boundary", by_system["bazi"])
        self.assertIn("historical_dst", by_system["bazi"])
        self.assertIn("lunar_leap_month", by_system["ziwei"])
        for system in ("bazi", "ziwei"):
            self.assertIn("zi_hour_boundary", by_system[system])
            self.assertIn("true_solar_time", by_system[system])

    def test_provenance_is_complete_and_never_uses_candidate_oss_as_expected(self) -> None:
        for case in _load_cases():
            with self.subTest(case=case["case_id"]):
                provenance = case["provenance"]
                runtime = provenance["runtime"]
                self.assertEqual(provenance["source_type"], SOURCE_TYPE)
                self.assertEqual(provenance["baseline_commit"], BASELINE_COMMIT)
                self.assertEqual(provenance["baseline_tree"], BASELINE_TREE)
                self.assertTrue(provenance["source_refs"])
                self.assertEqual(
                    provenance["candidate_oss_role"],
                    "future_differential_actual_only_never_expected",
                )
                for field in (
                    "adapter_id",
                    "adapter_version",
                    "engine_id",
                    "engine_version",
                    "policy_profile",
                    "time_basis",
                ):
                    self.assertIsInstance(runtime[field], str)
                    self.assertTrue(runtime[field])
                self.assertEqual(
                    provenance["expected_schema_version"],
                    case["expected_canonical_facts"]["schema_version"],
                )

    def test_inputs_are_synthetic_and_third_party_raw_containers_do_not_cross(self) -> None:
        for case in _load_cases():
            with self.subTest(case=case["case_id"]):
                input_payload = case["input"]
                self.assertTrue(input_payload["location"].startswith("synthetic:"))
                self.assertTrue(SENSITIVE_INPUT_KEYS.isdisjoint(input_payload))
                serialized = _canonical_bytes(input_payload).decode("utf-8")
                self.assertNotIn("@", serialized)
                self.assertNotRegex(serialized, r"(?i)(bearer\s+|sk-[a-z0-9]{16,})")
                all_keys = _walk_keys(case["expected_canonical_facts"])
                self.assertTrue(FORBIDDEN_RAW_KEYS.isdisjoint(all_keys))

    def test_every_case_replays_twice_to_the_exact_canonical_facts(self) -> None:
        fixtures = {case["case_id"]: case for case in _load_cases()}
        for definition in CASES:
            expected = fixtures[definition.case_id]["expected_canonical_facts"]
            with self.subTest(case=definition.case_id):
                first = _replay(definition)
                second = _replay(definition)
                self.assertEqual(first, expected)
                self.assertEqual(second, expected)
                self.assertEqual(_canonical_bytes(first), _canonical_bytes(second))


def _run_tests(verbosity: int = 2) -> unittest.result.TestResult:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GoldenBaselineTests)
    return unittest.TextTestRunner(verbosity=verbosity).run(suite)


def _write_evidence(path: Path, result: unittest.result.TestResult) -> None:
    manifest = _load_manifest()
    path.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": "mingli-oss-chart-golden-replay-receipt-v1",
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "baseline_commit": BASELINE_COMMIT,
        "baseline_tree": BASELINE_TREE,
        "manifest_schema_version": manifest["schema_version"],
        "case_schema_version": CASE_SCHEMA,
        "provenance_source_type": SOURCE_TYPE,
        "case_count": manifest["case_count"],
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "runtime": {
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "bazi_adapter_version": bazi_fact_adapter.VERSION,
            "ziwei_adapter_version": ziwei_fact_adapter.ADAPTER_VERSION,
            "ziwei_engine_version": ziwei_fact_adapter.IZTRO_VERSION,
        },
    }
    (path / "replay-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-baseline",
        action="store_true",
        help="Regenerate expected facts from the accepted Runtime adapters.",
    )
    parser.add_argument(
        "--write-evidence",
        type=Path,
        help="Write a machine-readable replay receipt after the focused tests.",
    )
    args = parser.parse_args()
    if args.refresh_baseline:
        refresh_baseline()
    result = _run_tests()
    if args.write_evidence:
        _write_evidence(args.write_evidence, result)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
