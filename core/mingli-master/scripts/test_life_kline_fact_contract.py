#!/usr/bin/env python3
"""Contract tests for the fail-closed life K-line Runtime facts."""

from __future__ import annotations

import copy
import json
import sys
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
    validate_life_kline_facts,
)


BASE_IDENTITY = {
    "subject_ref": "subject:synthetic-kline",
    "profile_version_id": "profile-version:synthetic-v1",
    "runtime_release": "mingli-master/5.1",
    "runtime_source_commit": "a" * 40,
    "runtime_manifest_digest": "b" * 64,
    "source_fact_digest": "c" * 64,
}


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


if __name__ == "__main__":
    unittest.main()
