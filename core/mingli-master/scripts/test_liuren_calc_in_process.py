#!/usr/bin/env python3
"""Regression tests for the in-process Da Liu Ren Provider adapter seam."""

from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import liuren_calc  # noqa: E402
import liuren_fact_adapter  # noqa: E402


def _args() -> argparse.Namespace:
    return argparse.Namespace(
        timezone="Asia/Shanghai",
        location="合成测试地点",
        guiren_profile="official-corrected",
        day_night_profile="civil-double-hour",
        zi_hour_policy="midnight",
        biezhe_profile="daliuren-daquan-body-branch",
        longitude=121.0,
        latitude=31.0,
        coordinate_source="synthetic-fixture",
        coordinate_accuracy_meters=10.0,
        time_basis_policy="civil",
    )


class LiurenInProcessAdapterTests(unittest.TestCase):
    def test_real_adapter_keeps_the_previous_json_boundary_shape(self) -> None:
        args = _args()
        question = "请排出这件事的大六壬课盘。"
        civil_datetime = "2026-08-14T10:00:00+08:00"
        expected = liuren_fact_adapter.build_from_datetime(
            civil_datetime,
            timezone_name=args.timezone,
            location=args.location,
            question=question,
            guiren_profile=args.guiren_profile,
            day_night_profile=args.day_night_profile,
            zi_hour_policy=args.zi_hour_policy,
            biezhe_profile=args.biezhe_profile,
            longitude=args.longitude,
            latitude=args.latitude,
            coordinate_source=args.coordinate_source,
            coordinate_accuracy_meters=args.coordinate_accuracy_meters,
            time_basis_policy=args.time_basis_policy,
        )
        expected = json.loads(
            json.dumps(expected, ensure_ascii=False, sort_keys=True)
        )

        self.assertEqual(
            liuren_calc._run_adapter(
                ROOT,
                args,
                question,
                civil_datetime,
            ),
            expected,
        )

    def test_cast_arguments_are_forwarded_without_semantic_rewrite(self) -> None:
        args = _args()
        build = mock.Mock(
            return_value={
                "z_tuple": ("甲子",),
                "a_mapping": {"ok": True},
            }
        )
        question = "原始问题"
        civil_datetime = "2026-08-14T10:00:00+08:00"

        with mock.patch.object(
            liuren_calc.liuren_fact_adapter,
            "build_from_datetime",
            build,
        ):
            result = liuren_calc._run_adapter(
                ROOT,
                args,
                question,
                civil_datetime,
            )

        self.assertEqual(list(result), ["a_mapping", "z_tuple"])
        self.assertEqual(result["z_tuple"], ["甲子"])
        build.assert_called_once_with(
            civil_datetime,
            timezone_name=args.timezone,
            location=args.location,
            question=question,
            guiren_profile=args.guiren_profile,
            day_night_profile=args.day_night_profile,
            zi_hour_policy=args.zi_hour_policy,
            biezhe_profile=args.biezhe_profile,
            longitude=args.longitude,
            latitude=args.latitude,
            coordinate_source=args.coordinate_source,
            coordinate_accuracy_meters=args.coordinate_accuracy_meters,
            time_basis_policy=args.time_basis_policy,
        )

    def test_adapter_error_remains_fail_closed(self) -> None:
        args = _args()
        with mock.patch.object(
            liuren_calc.liuren_fact_adapter,
            "build_from_datetime",
            side_effect=ValueError("invalid month-general profile"),
        ), self.assertRaisesRegex(
            RuntimeError,
            "invalid month-general profile",
        ):
            liuren_calc._run_adapter(
                ROOT,
                args,
                "原始问题",
                "2026-08-14T10:00:00+08:00",
            )

    def test_adapter_from_another_runtime_remains_fail_closed(self) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            "does not belong to this Runtime",
        ):
            liuren_calc._run_adapter(
                ROOT / "different-runtime",
                _args(),
                "原始问题",
                "2026-08-14T10:00:00+08:00",
            )


if __name__ == "__main__":
    unittest.main()
