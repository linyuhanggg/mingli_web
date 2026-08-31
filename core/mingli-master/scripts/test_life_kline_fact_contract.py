#!/usr/bin/env python3
"""Contract tests for the fail-closed life K-line Runtime facts."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reading_engine.life_kline import (  # noqa: E402
    CANDLE_UNAVAILABLE_REASON,
    CHANGE_UNAVAILABLE_REASON,
    GAP_ID,
    LifeKlineContractError,
    SCHEMA_VERSION,
    STATUS,
    VALUE_AXIS_UNAVAILABLE_REASON,
    build_unavailable_life_kline_facts,
    load_runtime_release_identity,
    validate_life_kline_facts,
)
import release_deploy  # noqa: E402


BASE_IDENTITY = {
    "subject_ref": "subject:synthetic-kline",
    "profile_version_id": "profile-version:synthetic-v1",
    "runtime_release": "mingli-master/5.1",
    "runtime_source_commit": "a" * 40,
    "runtime_manifest_digest": "b" * 64,
    "source_fact_digest": "c" * 64,
}

CORE_ROOT = SCRIPT_DIR.parent


def _build(**changes: str) -> dict[str, Any]:
    return build_unavailable_life_kline_facts(
        **{**BASE_IDENTITY, **changes},
    )


def _all_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(key)
            keys.update(_all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_all_keys(child))
    return keys


class LifeKlineUnavailableContractTests(unittest.TestCase):
    def test_contract_is_explicitly_unavailable_without_series_values(self) -> None:
        payload = _build()

        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["status"], STATUS)
        self.assertEqual(payload["series"], [])
        self.assertEqual(
            payload["value_axis"]["unavailable_reason"],
            VALUE_AXIS_UNAVAILABLE_REASON,
        )
        self.assertEqual(
            payload["candles"]["unavailable_reason"],
            CANDLE_UNAVAILABLE_REASON,
        )
        self.assertEqual(
            payload["change"]["unavailable_reason"],
            CHANGE_UNAVAILABLE_REASON,
        )
        self.assertFalse(payload["value_axis"]["available"])
        self.assertFalse(payload["candles"]["available"])
        self.assertFalse(payload["change"]["available"])

        forbidden = {"score", "open", "high", "low", "close", "direction", "delta"}
        self.assertEqual(_all_keys(payload) & forbidden, set())

    def test_candidate_axes_are_temporal_keys_not_numeric_measures(self) -> None:
        axes = _build()["candidate_time_axes"]

        self.assertEqual(
            [item["kind"] for item in axes],
            ["major_luck", "gregorian_year", "gregorian_month", "civil_day"],
        )
        self.assertTrue(all(item["role"] == "temporal_key_only" for item in axes))
        self.assertTrue(all(item["series_ready"] is False for item in axes))

    def test_algorithm_gap_is_machine_readable_and_not_user_resolvable(self) -> None:
        gap = _build()["algorithm_gap"]

        self.assertEqual(gap["gap_id"], GAP_ID)
        self.assertFalse(gap["user_input_can_resolve"])
        self.assertEqual(
            gap["missing_inputs"],
            [
                "versioned_comparable_measure_definition",
                "calibration_and_validation_corpus",
            ],
        )
        self.assertIn("cross_period_comparability", gap["missing_semantics"])
        self.assertIn(
            "open_and_close_sampling_points",
            gap["missing_semantics"],
        )
        self.assertIn(
            "meta.reading_document_version",
            gap["required_versioned_fields"],
        )
        self.assertIn(
            "meta.source_fact_digest",
            gap["required_versioned_fields"],
        )
        self.assertIn(
            "derive_direction_and_delta_only_from_authoritative_close_values",
            gap["minimum_implementation_slice"],
        )

    def test_same_identity_is_byte_for_byte_deterministic(self) -> None:
        first = _build()
        second = _build()

        self.assertEqual(first, second)
        self.assertEqual(
            json.dumps(first, ensure_ascii=False, sort_keys=True),
            json.dumps(second, ensure_ascii=False, sort_keys=True),
        )
        self.assertEqual(
            first["identity"]["cache_identity"],
            second["identity"]["cache_identity"],
        )

    def test_cache_identity_binds_profile_runtime_and_source_facts(self) -> None:
        baseline = _build()["identity"]["cache_identity"]
        variants = (
            _build(profile_version_id="profile-version:synthetic-v2"),
            _build(runtime_release="mingli-master/5.1-repacked"),
            _build(runtime_source_commit="d" * 40),
            _build(runtime_manifest_digest="e" * 64),
            _build(source_fact_digest="f" * 64),
        )

        self.assertTrue(
            all(item["identity"]["cache_identity"] != baseline for item in variants)
        )

    def test_exact_payload_validates(self) -> None:
        validate_life_kline_facts(_build())

    def test_ohlc_injection_is_rejected(self) -> None:
        payload = _build()
        payload["series"] = [
            {
                "t": "2026",
                "open": 50,
                "high": 60,
                "low": 40,
                "close": 55,
            }
        ]

        with self.assertRaises(LifeKlineContractError):
            validate_life_kline_facts(payload)

    def test_direction_or_delta_injection_is_rejected(self) -> None:
        for field, value in (("direction", "up"), ("delta", 1)):
            payload = _build()
            payload["change"][field] = value
            with self.subTest(field=field), self.assertRaises(
                LifeKlineContractError
            ):
                validate_life_kline_facts(payload)

    def test_identity_or_gap_tampering_is_rejected(self) -> None:
        mutations = (
            lambda value: value["identity"].__setitem__("cache_identity", "0" * 64),
            lambda value: value["algorithm_gap"]["missing_semantics"].clear(),
            lambda value: value.__setitem__("extra", "host-default"),
        )
        for mutation in mutations:
            payload = copy.deepcopy(_build())
            mutation(payload)
            with self.subTest(mutation=mutation), self.assertRaises(
                LifeKlineContractError
            ):
                validate_life_kline_facts(payload)

    def test_invalid_opaque_or_version_identity_fails_closed(self) -> None:
        invalid = (
            {"profile_version_id": ""},
            {"subject_ref": "contains whitespace"},
            {"runtime_source_commit": "not-a-commit"},
            {"runtime_manifest_digest": "0" * 63},
            {"source_fact_digest": "G" * 64},
        )
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(
                LifeKlineContractError
            ):
                _build(**changes)


class LifeKlineReleaseIdentityTests(unittest.TestCase):
    def _release_root(self, temporary: str) -> tuple[Path, bytes, bytes]:
        root = Path(temporary)
        version_path = root / "release" / "version.json"
        version_path.parent.mkdir(parents=True)
        version_bytes = b'{"name":"mingli-master","version":"5.1"}\n'
        version_path.write_bytes(version_bytes)
        manifest_bytes = (
            json.dumps(
                {
                    "schema_version": 3,
                    "release": "mingli-master-portable-core",
                    "source_commit": "d" * 40,
                    "files": {
                        "release/version.json": hashlib.sha256(
                            version_bytes
                        ).hexdigest()
                    },
                    "modes": {"release/version.json": 420},
                },
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        (root / ".mingli-release-manifest.json").write_bytes(manifest_bytes)
        return root, version_bytes, manifest_bytes

    def test_identity_is_derived_from_exact_bound_release_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _version_bytes, manifest_bytes = self._release_root(temporary)

            identity = load_runtime_release_identity(root)

            self.assertEqual(identity["runtime_release"], "mingli-master/5.1")
            self.assertEqual(identity["runtime_source_commit"], "d" * 40)
            self.assertEqual(
                identity["runtime_manifest_digest"],
                hashlib.sha256(manifest_bytes).hexdigest(),
            )

    def test_missing_or_unbound_release_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _version_bytes, _manifest_bytes = self._release_root(temporary)
            (root / "release" / "version.json").write_text(
                '{"name":"mingli-master","version":"host-default"}\n',
                encoding="utf-8",
            )
            with self.assertRaises(LifeKlineContractError):
                load_runtime_release_identity(root)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "release").mkdir()
            (root / "release" / "version.json").write_text(
                '{"name":"mingli-master","version":"5.1"}\n',
                encoding="utf-8",
            )
            with self.assertRaises(LifeKlineContractError):
                load_runtime_release_identity(root)


class LifeKlinePortableAdapterIntegrationTests(unittest.TestCase):
    def test_prepare_exposes_exact_gap_and_ignores_host_fabrication(self) -> None:
        subject_ref = "profile-version:synthetic-kline"
        source_commit = "d" * 40
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            installed = root / "installed"
            home = root / "home"
            shutil.copytree(
                CORE_ROOT,
                source,
                ignore=shutil.ignore_patterns(".git", "__pycache__"),
            )
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "add", "."], check=True)
            selected = release_deploy.tracked_release_files(source)
            manifest = release_deploy.build_manifest(
                source,
                selected,
                source_commit,
            )
            release_deploy.sync_destination(
                source,
                installed,
                manifest,
                apply=True,
            )
            runtime_python = os.environ.get("MINGLI_PYTHON") or sys.executable
            adapter_command = [
                runtime_python,
                "-I",
                "-B",
                str(installed / "scripts/adapters/json_cli.py"),
            ]
            environment = {
                "HOME": str(home),
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONDONTWRITEBYTECODE": "1",
            }

            def execute_adapter(payload: dict[str, Any]) -> dict[str, Any]:
                completed = subprocess.run(
                    adapter_command,
                    input=json.dumps(payload, ensure_ascii=False),
                    capture_output=True,
                    text=True,
                    cwd=str(installed),
                    env=environment,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

            described = execute_adapter({"kind": "describe"})
            bazi = next(
                capability
                for capability in described["capabilities"]
                if capability["id"] == "bazi"
            )
            self.assertIn(
                "life_kline",
                {item["id"] for item in bazi["objects"]},
            )

            command = {
                "kind": "prepare",
                "query": "读取人生 K 线当前事实状态。",
                "intent": {
                    "subject_refs": [subject_ref],
                    "object_id": "life_kline",
                    "dimension_ids": ["overview"],
                    "horizon": {"kind_id": "life"},
                    "capability_id": "bazi",
                    "comparisons": [],
                },
                "facts": {
                    subject_ref: {
                        "birth_datetime_or_four_pillars": [
                            "乙酉",
                            "辛巳",
                            "丙午",
                            "癸巳",
                        ],
                        "life_kline": {
                            "status": "ready",
                            "series": [
                                {
                                    "open": 40,
                                    "high": 60,
                                    "low": 30,
                                    "close": 55,
                                    "direction": "up",
                                    "delta": 15,
                                }
                            ],
                        },
                        "host_default": 50,
                    }
                },
            }
            result = execute_adapter(command)
            self.assertEqual(result["kind"], "prepared", result)
            matching = [
                fact
                for fact in result["brief"]["facts"]
                if fact["ref"]
                == f"fact:{subject_ref}/calculated/bazi/life_kline"
            ]
            self.assertEqual(len(matching), 1, result["brief"]["facts"])
            payload = matching[0]["value"]

            validate_life_kline_facts(payload)
            self.assertEqual(payload["status"], STATUS)
            self.assertEqual(payload["series"], [])
            self.assertFalse(payload["algorithm_gap"]["user_input_can_resolve"])
            self.assertEqual(payload["identity"]["subject_ref"], subject_ref)
            self.assertEqual(
                payload["identity"]["profile_version_id"],
                subject_ref,
            )
            self.assertEqual(
                payload["identity"]["runtime_source_commit"],
                source_commit,
            )
            forbidden = {
                "score",
                "open",
                "high",
                "low",
                "close",
                "direction",
                "delta",
                "host_default",
            }
            self.assertEqual(_all_keys(payload) & forbidden, set())
            self.assertNotIn("host_default", json.dumps(result, sort_keys=True))

            natal_command = copy.deepcopy(command)
            natal_command["intent"]["object_id"] = "natal"
            natal = execute_adapter(natal_command)
            self.assertEqual(natal["kind"], "prepared", natal)
            self.assertFalse(
                any(
                    fact["ref"].endswith("/calculated/bazi/life_kline")
                    for fact in natal["brief"]["facts"]
                )
            )


if __name__ == "__main__":
    unittest.main()
