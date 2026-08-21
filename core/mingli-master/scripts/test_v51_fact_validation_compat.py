#!/usr/bin/env python3
"""Characterization tests pinning adapter_validate.validate_payload behavior.

These tests freeze the external compatibility envelope of the fact-validation
facade before and across the FactContract seam migration. They must pass on
the legacy implementation and continue to pass, byte-for-byte, after the bazi
validation moves behind the Provider-owned fact contract.
"""

from __future__ import annotations

import copy
import inspect
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import adapter_validate  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parents[1]
ADAPTER = SKILL_DIR / "scripts" / "bazi_fact_adapter.py"

_EXPECTED_RESULT_KEYS = {"ok", "system", "findings", "codes"}
_EXPECTED_FINDING_KEYS = {"level", "code", "message"}


def _pillar_payload(*pillars: str, gender: str | None = None) -> dict:
    args = [sys.executable, str(ADAPTER), "pillars", "--pillars", *pillars, "--source", "text"]
    if gender is not None:
        args.extend(["--gender", gender])
    completed = subprocess.run(
        args,
        cwd=SKILL_DIR,
        text=True,
        capture_output=True,
        check=True,
        timeout=60,
    )
    return json.loads(completed.stdout)


def _assert_envelope(testcase: unittest.TestCase, report: object) -> dict:
    testcase.assertIsInstance(report, dict)
    testcase.assertEqual(set(report), _EXPECTED_RESULT_KEYS)
    testcase.assertIsInstance(report["ok"], bool)
    testcase.assertIsInstance(report["system"], str)
    testcase.assertIsInstance(report["findings"], list)
    testcase.assertIsInstance(report["codes"], list)
    testcase.assertEqual(
        report["codes"], [item["code"] for item in report["findings"]]
    )
    for item in report["findings"]:
        testcase.assertEqual(set(item), _EXPECTED_FINDING_KEYS)
    return report


class ValidatePayloadEnvelopeTests(unittest.TestCase):
    """The facade return shape is the physical contract for every caller."""

    def test_public_signature_stays_byte_for_byte_compatible(self) -> None:
        signature = inspect.signature(adapter_validate.validate_payload)
        self.assertEqual(
            str(signature),
            "(system: 'str', payload: 'dict[str, Any]', *, evidence_bundle: "
            "'dict[str, Any] | None' = None) -> 'dict[str, Any]'",
        )

    def test_valid_bazi_payload_reports_no_findings(self) -> None:
        payload = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="male")
        report = adapter_validate.validate_payload("bazi", payload)
        _assert_envelope(self, report)
        self.assertTrue(report["ok"])
        self.assertEqual(report["system"], "bazi")
        self.assertEqual(report["findings"], [])

    def test_genderless_supplied_pillars_stay_clean(self) -> None:
        payload = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳")
        report = adapter_validate.validate_payload("bazi", payload)
        _assert_envelope(self, report)
        self.assertTrue(report["ok"])
        self.assertEqual(report["findings"], [])

    def test_unknown_system_is_frozen(self) -> None:
        report = adapter_validate.validate_payload("nonexistent", {})
        self.assertEqual(
            report,
            {
                "ok": False,
                "system": "nonexistent",
                "findings": [
                    {
                        "level": "error",
                        "code": "unknown_system",
                        "message": "Unknown system: nonexistent",
                    }
                ],
                "codes": ["unknown_system"],
            },
        )

    def test_system_alias_normalization_is_preserved(self) -> None:
        # canonical_system maps aliases; unmapped strings pass through and
        # fail as unknown systems rather than raising.
        report = adapter_validate.validate_payload("BAZI", {})
        _assert_envelope(self, report)
        self.assertFalse(report["ok"])
        self.assertEqual(report["system"], "BAZI")
        self.assertIn("unknown_system", report["codes"])
        aliased = adapter_validate.validate_payload("san-shi/liuren", {})
        self.assertEqual(aliased["system"], "liuren")

    def test_fabricated_partial_luck_timing_finding_is_frozen(self) -> None:
        payload = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="male")
        payload["output"]["luck_cycles"]["cycles"][0]["start_age_years"] = 3.0
        report = adapter_validate.validate_payload("bazi", payload)
        self.assertEqual(
            report["findings"],
            [
                {
                    "level": "error",
                    "code": "bazi_partial_luck_fabricated_timing",
                    "message": (
                        "A partial luck layer must not fabricate start ages,"
                        " calendar mappings, or timing"
                    ),
                }
            ],
        )

    def test_oracle_direction_flip_is_caught(self) -> None:
        payload = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="male")
        payload["output"]["luck_cycles"]["direction"] = "forward"
        report = adapter_validate.validate_payload("bazi", payload)
        self.assertFalse(report["ok"])
        self.assertEqual(report["codes"], ["bazi_partial_luck_recompute_mismatch"])


class ValidatePayloadHostileShapeTests(unittest.TestCase):
    """Any hostile payload must yield a lawful report, never an exception."""

    def setUp(self) -> None:
        self.base = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="male")

    # Frozen characterization: each hostile mutation must keep producing the
    # exact legacy report (codes and ok flag), never an exception.
    _FROZEN = {
        "status_dict": (False, ["bazi_partial_luck_invalid_input"]),
        "status_list": (False, ["bazi_partial_luck_invalid_input"]),
        "output_list": (
            False,
            [
                "missing_output:four_pillars",
                "missing_output:hidden_stems",
                "missing_output:ten_gods",
                "missing_output:nayin",
                "missing_output:twelve_growth_stages",
                "missing_output:xunkong",
                "missing_output:san_yuan",
                "missing_output:month_command",
                "missing_output:seasonal_profile",
                "missing_output:tiaohou_markers",
                "missing_output:interpretive_candidates",
                "missing_output:shensha_auxiliary",
            ],
        ),
        "adapter_list": (
            False,
            [
                "missing_adapter:name",
                "missing_adapter:version",
                "missing_adapter:rule_profile",
                "bazi_partial_luck_invalid_input",
            ],
        ),
        "calendar_list": (
            False,
            [
                "bazi_partial_luck_input_output_mismatch",
                "missing_calendar:status",
                "missing_calendar:ganzhi",
            ],
        ),
        # A truthy non-list trace currently produces no warning; frozen as-is.
        "trace_dict": (True, []),
        "bool_luck": (False, ["bazi_partial_luck_missing"]),
        "bool_sequence": (False, ["bazi_partial_luck_invalid_shape"]),
        "bool_pillars": (
            False,
            [
                "bazi_growth_stages_missing",
                "bazi_xunkong_missing",
                "bazi_san_yuan_missing",
                "bazi_partial_luck_input_output_mismatch",
            ],
        ),
    }

    @staticmethod
    def _apply(name: str, payload: dict) -> None:
        if name == "status_dict":
            payload["fact_layer_status"] = {"a": 1}
        elif name == "status_list":
            payload["fact_layer_status"] = ["x"]
        elif name == "output_list":
            payload["output"] = [1, 2]
        elif name == "adapter_list":
            payload["adapter"] = ["not", "dict"]
        elif name == "calendar_list":
            payload["calendar_normalization"] = ["bad"]
        elif name == "trace_dict":
            payload["trace"] = {"step": 1}
        elif name == "bool_luck":
            payload["output"]["luck_cycles"] = True
        elif name == "bool_sequence":
            payload["output"]["luck_cycles"]["cycles"][0]["sequence"] = True
        elif name == "bool_pillars":
            payload["output"]["four_pillars"] = False

    def test_hostile_shapes_match_the_frozen_legacy_report(self) -> None:
        for name, (expected_ok, expected_codes) in self._FROZEN.items():
            with self.subTest(case=name):
                payload = copy.deepcopy(self.base)
                self._apply(name, payload)
                report = adapter_validate.validate_payload("bazi", payload)
                _assert_envelope(self, report)
                self.assertEqual(report["ok"], expected_ok)
                self.assertEqual(report["codes"], expected_codes)

    def test_empty_payload_still_reports_missing_fields(self) -> None:
        report = adapter_validate.validate_payload("bazi", {})
        _assert_envelope(self, report)
        self.assertFalse(report["ok"])
        self.assertIn("missing_top_level:adapter", report["codes"])
        self.assertIn("missing_output:four_pillars", report["codes"])
        self.assertIn("missing_calendar:ganzhi", report["codes"])


class ValidatePayloadEquivalenceHarnessTests(unittest.TestCase):
    """A reusable harness for before/after migration equivalence checks."""

    CASES = [
        ("supplied_male", ("乙酉", "辛巳", "丙午", "癸巳"), "male"),
        ("supplied_female", ("乙酉", "辛巳", "丙午", "癸巳"), "female"),
        ("supplied_genderless", ("乙酉", "辛巳", "丙午", "癸巳"), None),
        ("boundary_wrap", ("癸亥", "癸亥", "甲子", "甲子"), "female"),
    ]

    @classmethod
    def frozen_reports(cls) -> dict[str, dict]:
        reports = {}
        for name, pillars, gender in cls.CASES:
            payload = _pillar_payload(*pillars, gender=gender)
            reports[name] = adapter_validate.validate_payload("bazi", payload)
        return reports

    def test_reports_are_stable_across_repeated_calls(self) -> None:
        first = self.frozen_reports()
        second = self.frozen_reports()
        self.assertEqual(first, second)
        for name, report in first.items():
            with self.subTest(case=name):
                self.assertTrue(report["ok"], report)
                self.assertEqual(report["findings"], [])


if __name__ == "__main__":
    unittest.main()
