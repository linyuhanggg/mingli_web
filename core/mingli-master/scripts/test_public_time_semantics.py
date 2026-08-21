"""Public-interface acceptance tests for the time-semantics rework.

Every test drives the real ``ReadingInterface.execute(command_from_dict(...))``
path. No test calls ``provider.calculate()`` or a private helper to stand in
for production acceptance. Algorithm consumption is proven by comparing
specific reading fields (Bazi hour pillar, Ziwei time_index / palace branch),
never by whole-object inequality or by echo fields (warnings, normalized
input, digest) that can change without the chart changing.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import (
    Describe,
    HorizonSelection,
    IntentSelection,
    Prepare,
    command_from_dict,
)
from runtime_python import runtime_command

ROOT = Path(__file__).resolve().parents[1]
VENV = Path(runtime_command()[0])

CROSS_HOUR_CIVIL = datetime(2000, 10, 18, 6, 52).isoformat()
COORDS = {
    "longitude": 119.11150,
    "latitude": 25.46096,
    "coordinate_source": "regression-fixture",
}


def _run(command_dict: dict, *, runtime_context=None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        interface = ReadingInterface(
            skill_root=ROOT,
            store_root=Path(tmp) / "s",
            runtime_context=runtime_context,
        )
        result = interface.execute(command_from_dict(command_dict))
    return result


def _prepare(
    query: str,
    system: str,
    obj: str,
    facts: dict,
    dims=("career",),
    horizon="life",
) -> dict:
    return Prepare(
        query=query,
        intent=IntentSelection(
            subject_refs=("current_user",),
            object_id=obj,
            dimension_ids=dims,
            horizon=HorizonSelection(kind_id=horizon),
            capability_id=system,
        ),
        facts={"current_user": facts},
    ).to_dict()


def _birth_facts(
    policy: str,
    accuracy: float | None = None,
    civil: str = CROSS_HOUR_CIVIL,
) -> dict:
    facts = {
        "birth_datetime": civil,
        "birth_datetime_or_four_pillars": civil,
        "datetime": civil,
        "timezone": "Asia/Shanghai",
        "location": "fixture",
        "gender": "male",
        "zi_hour_policy": "midnight",
        "time_basis_policy": policy,
        **COORDS,
    }
    if accuracy is not None:
        facts["coordinate_accuracy_meters"] = accuracy
    return facts


def _event_facts(
    policy: str,
    accuracy: float | None = None,
    civil: str = CROSS_HOUR_CIVIL,
) -> dict:
    meta = {"time_basis_policy": policy, **COORDS}
    if accuracy is not None:
        meta["coordinate_accuracy_meters"] = accuracy
    return {
        "event_datetime_or_reference_datetime": civil,
        "event_datetime": civil,
        "reference_datetime": civil,
        "timezone": "Asia/Shanghai",
        "location": "fixture",
        **meta,
    }


def _fact_value(brief: dict, provider_id: str, fact_id: str):
    """Resolve one exact public calculated fact, never a same-named nested key."""

    expected = f"fact:current_user/calculated/{provider_id}/{fact_id}"
    matches = [
        fact.get("value")
        for fact in brief.get("facts", [])
        if fact.get("ref") == expected
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"expected exactly one public fact {expected}, got {len(matches)}"
        )
    return matches[0]


def _liuyao_facts(policy: str, accuracy: float | None = None) -> dict:
    return {
        **_event_facts(policy, accuracy),
        "cast": [6, 7, 8, 9, 7, 8],
    }


def _meihua_facts(policy: str, accuracy: float | None = None) -> dict:
    return {
        **_event_facts(policy, accuracy),
        "casting_method": "time",
    }


class DescribeTimeSemanticsTests(unittest.TestCase):
    def test_every_capability_exposes_structured_time_semantics(self) -> None:
        result = _run(Describe().to_dict())
        self.assertEqual(result.kind, "described")
        for cap in result.capabilities:
            with self.subTest(provider=cap.id):
                ts = cap.time_semantics
                self.assertIsNotNone(ts, f"{cap.id} has no time_semantics")
                self.assertIn(ts.role_id, {"pillar_clock", "physical_instant", "civil_schedule", "not_applicable"})
                self.assertIn(ts.unsupported_behavior_id, {"need_input", "civil_only", "not_applicable"})
                if ts.role_id != "not_applicable":
                    self.assertIn(ts.default_policy_id, ts.supported_policy_ids)
        # not_applicable providers have empty supported set + no coordinate requirement
        for cap in result.capabilities:
            if cap.time_semantics.role_id == "not_applicable":
                self.assertEqual(cap.time_semantics.supported_policy_ids, ())
                self.assertEqual(cap.time_semantics.coordinate_required_policy_ids, ())

    def test_describe_round_trips_through_dict(self) -> None:
        result = _run(Describe().to_dict())
        cap = next(c for c in result.capabilities if c.id == "bazi")
        roundtrip = json.loads(json.dumps(cap.to_dict()))
        from reading_engine.interface_contracts import CapabilityView
        restored = CapabilityView.from_dict(roundtrip)
        self.assertEqual(restored.time_semantics, cap.time_semantics)


class ZiweiCrossHourApparentTests(unittest.TestCase):
    def test_ziwei_apparent_cross_hour_returns_prepared_and_moves_chart(self) -> None:
        civil = _run(_prepare("看紫微", "ziwei", "natal", _birth_facts("civil")))
        apparent = _run(_prepare("看紫微", "ziwei", "natal", _birth_facts("local_apparent_solar-v1")))
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        # time_index is the iztro hour index actually used for the cast.
        civil_index = _fact_value(civil.brief.to_dict(), "ziwei", "chart_convention")["time_index"]
        apparent_index = _fact_value(apparent.brief.to_dict(), "ziwei", "chart_convention")["time_index"]
        self.assertEqual(civil_index, 3)  # 卯
        self.assertEqual(apparent_index, 4)  # 辰
        # The palace layout must differ, not just the bound calendar digest.
        civil_ming = _fact_value(civil.brief.to_dict(), "ziwei", "ming_shen")["ming_branch"]
        apparent_ming = _fact_value(apparent.brief.to_dict(), "ziwei", "ming_shen")["ming_branch"]
        self.assertEqual(civil_ming, "未")
        self.assertEqual(apparent_ming, "午")
        self.assertNotEqual(civil_ming, apparent_ming)

    def test_ziwei_apparent_cross_date_uses_effective_date_and_hour(self) -> None:
        cross_date_civil = datetime(2000, 10, 18, 23, 55).isoformat()
        civil = _run(
            _prepare(
                "看紫微",
                "ziwei",
                "natal",
                _birth_facts("civil", civil=cross_date_civil),
            )
        )
        apparent = _run(
            _prepare(
                "看紫微",
                "ziwei",
                "natal",
                _birth_facts(
                    "local_apparent_solar-v1",
                    civil=cross_date_civil,
                ),
            )
        )
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        self.assertEqual(
            _fact_value(civil.brief.to_dict(), "ziwei", "solar_date"),
            "2000-10-18",
        )
        self.assertEqual(
            _fact_value(apparent.brief.to_dict(), "ziwei", "solar_date"),
            "2000-10-19",
        )
        self.assertEqual(
            _fact_value(civil.brief.to_dict(), "ziwei", "chart_convention")["time_index"],
            12,
        )
        self.assertEqual(
            _fact_value(apparent.brief.to_dict(), "ziwei", "chart_convention")["time_index"],
            0,
        )


class BaziCrossHourApparentTests(unittest.TestCase):
    def test_bazi_apparent_cross_hour_moves_hour_pillar(self) -> None:
        civil = _run(_prepare("看命", "bazi", "natal", _birth_facts("civil")))
        apparent = _run(_prepare("看命", "bazi", "natal", _birth_facts("local_apparent_solar-v1")))
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        civil_hour = _fact_value(civil.brief.to_dict(), "bazi", "four_pillars")["hour"]
        apparent_hour = _fact_value(apparent.brief.to_dict(), "bazi", "four_pillars")["hour"]
        # hour is the sexagenary hour pillar string, e.g. "丁卯" -> "戊辰".
        self.assertIsInstance(civil_hour, str)
        self.assertIsInstance(apparent_hour, str)
        self.assertEqual(civil_hour[1], "卯")
        self.assertEqual(apparent_hour[1], "辰")
        self.assertNotEqual(civil_hour, apparent_hour)


class LiurenCrossHourApparentTests(unittest.TestCase):
    def test_liuren_apparent_cross_hour_moves_day_hour_pillar(self) -> None:
        civil = _run(_prepare("合作能否成", "liuren", "concrete_event", _event_facts("civil"), dims=("outcome",), horizon="instant"))
        apparent = _run(_prepare("合作能否成", "liuren", "concrete_event", _event_facts("local_apparent_solar-v1"), dims=("outcome",), horizon="instant"))
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        # Liuren exposes the day/hour pillars as facts; the hour branch must move.
        civil_hour = _fact_value(civil.brief.to_dict(), "liuren", "day_hour")["hour"]
        apparent_hour = _fact_value(apparent.brief.to_dict(), "liuren", "day_hour")["hour"]
        self.assertNotEqual(civil_hour, apparent_hour)


class RemainingTimedProviderSemanticsTests(unittest.TestCase):
    def test_luming_apparent_cross_hour_moves_hour_pillar(self) -> None:
        civil = _run(_prepare("看命", "luming-nayin", "natal", _birth_facts("civil")))
        apparent = _run(
            _prepare(
                "看命",
                "luming-nayin",
                "natal",
                _birth_facts("local_apparent_solar-v1"),
            )
        )
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        self.assertNotEqual(
            _fact_value(civil.brief.to_dict(), "luming-nayin", "four_pillars")["hour"],
            _fact_value(apparent.brief.to_dict(), "luming-nayin", "four_pillars")["hour"],
        )

    def test_xingming_keeps_physical_instant_and_positions_invariant(self) -> None:
        civil = _run(_prepare("看星盘", "xingming", "natal", _birth_facts("civil")))
        apparent = _run(
            _prepare(
                "看星盘",
                "xingming",
                "natal",
                _birth_facts("local_apparent_solar-v1"),
            )
        )
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        civil_ephemeris = _fact_value(civil.brief.to_dict(), "xingming", "ephemeris")
        apparent_ephemeris = _fact_value(apparent.brief.to_dict(), "xingming", "ephemeris")
        self.assertEqual(civil_ephemeris["instant_utc"], apparent_ephemeris["instant_utc"])

        def physical_positions(result) -> list[tuple]:
            positions = _fact_value(result.brief.to_dict(), "xingming", "positions")
            return [
                (
                    item["body"],
                    item["longitude_degrees"],
                    item["latitude_degrees"],
                    item["house"],
                    item["degree_in_house"],
                )
                for item in positions
            ]

        self.assertEqual(physical_positions(civil), physical_positions(apparent))

    def test_liuyao_supplied_cast_is_not_recast_by_time_policy(self) -> None:
        civil = _run(
            _prepare(
                "看结果",
                "liuyao",
                "concrete_event",
                _liuyao_facts("civil"),
                dims=("outcome",),
                horizon="instant",
            )
        )
        apparent = _run(
            _prepare(
                "看结果",
                "liuyao",
                "concrete_event",
                _liuyao_facts("local_apparent_solar-v1"),
                dims=("outcome",),
                horizon="instant",
            )
        )
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        self.assertEqual(
            _fact_value(civil.brief.to_dict(), "liuyao", "casting"),
            _fact_value(apparent.brief.to_dict(), "liuyao", "casting"),
        )
        self.assertEqual(
            _fact_value(civil.brief.to_dict(), "liuyao", "primary_hexagram"),
            _fact_value(apparent.brief.to_dict(), "liuyao", "primary_hexagram"),
        )

    def test_meihua_time_cast_uses_corrected_hour(self) -> None:
        civil = _run(
            _prepare(
                "看结果",
                "meihua",
                "concrete_event",
                _meihua_facts("civil"),
                dims=("outcome",),
                horizon="instant",
            )
        )
        apparent = _run(
            _prepare(
                "看结果",
                "meihua",
                "concrete_event",
                _meihua_facts("local_apparent_solar-v1"),
                dims=("outcome",),
                horizon="instant",
            )
        )
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        self.assertNotEqual(
            _fact_value(civil.brief.to_dict(), "meihua", "calendar")["hour_ganzhi"],
            _fact_value(apparent.brief.to_dict(), "meihua", "calendar")["hour_ganzhi"],
        )
        self.assertNotEqual(
            _fact_value(civil.brief.to_dict(), "meihua", "primary_hexagram"),
            _fact_value(apparent.brief.to_dict(), "meihua", "primary_hexagram"),
        )

    def test_meihua_time_cast_uses_effective_lunar_date_after_midnight(self) -> None:
        cross_date = datetime(2000, 10, 18, 23, 55).isoformat()

        def facts(policy: str) -> dict:
            return {
                **_meihua_facts(policy),
                "event_datetime_or_reference_datetime": cross_date,
                "event_datetime": cross_date,
                "reference_datetime": cross_date,
            }

        civil = _run(
            _prepare(
                "看结果",
                "meihua",
                "concrete_event",
                facts("civil"),
                dims=("outcome",),
                horizon="instant",
            )
        )
        apparent = _run(
            _prepare(
                "看结果",
                "meihua",
                "concrete_event",
                facts("local_apparent_solar-v1"),
                dims=("outcome",),
                horizon="instant",
            )
        )
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        civil_cast = _fact_value(civil.brief.to_dict(), "meihua", "casting")
        apparent_cast = _fact_value(
            apparent.brief.to_dict(), "meihua", "casting"
        )
        self.assertEqual(civil_cast["inputs"]["hour_branch_number"], 1)
        self.assertEqual(apparent_cast["inputs"]["hour_branch_number"], 1)
        self.assertEqual(civil_cast["inputs"]["lunar_day"], 21)
        self.assertEqual(apparent_cast["inputs"]["lunar_day"], 22)
        self.assertNotEqual(
            _fact_value(civil.brief.to_dict(), "meihua", "primary_hexagram"),
            _fact_value(apparent.brief.to_dict(), "meihua", "primary_hexagram"),
        )

    def test_qimen_apparent_cross_hour_moves_board(self) -> None:
        civil = _run(
            _prepare("看结果", "qimen", "concrete_event", _event_facts("civil"), dims=("outcome",), horizon="instant")
        )
        apparent = _run(
            _prepare("看结果", "qimen", "concrete_event", _event_facts("local_apparent_solar-v1"), dims=("outcome",), horizon="instant")
        )
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        self.assertNotEqual(
            _fact_value(civil.brief.to_dict(), "qimen", "calendar_pillars")["hour"],
            _fact_value(apparent.brief.to_dict(), "qimen", "calendar_pillars")["hour"],
        )
        self.assertNotEqual(
            _fact_value(civil.brief.to_dict(), "qimen", "board_digest"),
            _fact_value(apparent.brief.to_dict(), "qimen", "board_digest"),
        )

    def test_taiyi_annual_board_is_invariant_within_the_same_year(self) -> None:
        civil = _run(
            _prepare("看年势", "taiyi", "macro_historical", _event_facts("civil"), dims=("outcome",), horizon="year")
        )
        apparent = _run(
            _prepare("看年势", "taiyi", "macro_historical", _event_facts("local_apparent_solar-v1"), dims=("outcome",), horizon="year")
        )
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        self.assertEqual(
            _fact_value(civil.brief.to_dict(), "taiyi", "board_digest"),
            _fact_value(apparent.brief.to_dict(), "taiyi", "board_digest"),
        )


class FortuneInlineProfileTests(unittest.TestCase):
    def _fortune_facts(self, policy: str) -> dict:
        return {
            "birth_datetime": CROSS_HOUR_CIVIL,
            "datetime": CROSS_HOUR_CIVIL,
            "timezone": "Asia/Shanghai",
            "location": "fixture",
            "gender": "male",
            "zi_hour_policy": "midnight",
            "time_basis_policy": policy,
            "reference_datetime": "2026-07-31T12:00:00",
            **COORDS,
        }

    def test_inline_facts_and_profile_produce_one_brief(self) -> None:
        from reading_engine.runtime_context import build_runtime_context

        profile = self._fortune_facts("local_apparent_solar-v1")
        inline = _run(_prepare("本周运势", "fortune", "near_time_personal", profile, dims=("outcome",), horizon="week"))
        context = build_runtime_context(
            default_timezone_name="Asia/Shanghai",
            subject_profiles={"current_user": profile},
        )
        profile_cmd = _prepare("本周运势", "fortune", "near_time_personal", {}, dims=("outcome",), horizon="week")
        profile_result = _run(profile_cmd, runtime_context=context)
        self.assertEqual(inline.kind, "prepared", inline)
        self.assertEqual(profile_result.kind, "prepared", profile_result)
        self.assertEqual(
            json.dumps(inline.brief.to_dict(), ensure_ascii=False, sort_keys=True),
            json.dumps(profile_result.brief.to_dict(), ensure_ascii=False, sort_keys=True),
        )

    def test_fortune_natal_hour_pillar_differs_civil_vs_apparent(self) -> None:
        civil = _run(_prepare("本周运势", "fortune", "near_time_personal", self._fortune_facts("civil"), dims=("outcome",), horizon="week"))
        apparent = _run(_prepare("本周运势", "fortune", "near_time_personal", self._fortune_facts("local_apparent_solar-v1"), dims=("outcome",), horizon="week"))
        self.assertEqual(civil.kind, "prepared", civil)
        self.assertEqual(apparent.kind, "prepared", apparent)
        civil_hour = _fact_value(civil.brief.to_dict(), "fortune", "natal_pillars")["hour"]
        apparent_hour = _fact_value(apparent.brief.to_dict(), "fortune", "natal_pillars")["hour"]
        self.assertNotEqual(civil_hour, apparent_hour)


class SelectionUnsupportedPolicyTests(unittest.TestCase):
    def test_selection_apparent_returns_unsupported_not_need_input(self) -> None:
        facts = {
            "time_basis_policy": "local_apparent_solar-v1",
            "timezone": "Asia/Shanghai",
            "location": "fixture",
            "event_profile": {"kind": "moving"},
            "requested_actions": ["moving"],
            "date_range": {"start": "2026-08-01", "end": "2026-08-31"},
        }
        result = _run(_prepare("择日", "selection", "calendar_choice", facts, dims=("timing",), horizon="month"))
        self.assertEqual(result.kind, "stopped")
        self.assertEqual(result.reason, "unsupported")
        self.assertIsNone(result.input_request)


class MissingCoordinatePublicTests(unittest.TestCase):
    def test_all_coordinate_aware_providers_return_labeled_need_input(self) -> None:
        fortune_facts = {
            **_birth_facts("local_apparent_solar-v1"),
            "reference_datetime": "2026-07-31T12:00:00",
        }
        cases = (
            ("bazi", "natal", _birth_facts("local_apparent_solar-v1"), ("career",), "life"),
            ("ziwei", "natal", _birth_facts("local_apparent_solar-v1"), ("career",), "life"),
            ("luming-nayin", "natal", _birth_facts("local_apparent_solar-v1"), ("career",), "life"),
            ("xingming", "natal", _birth_facts("local_apparent_solar-v1"), ("career",), "life"),
            ("liuren", "concrete_event", _event_facts("local_apparent_solar-v1"), ("outcome",), "instant"),
            ("liuyao", "concrete_event", _liuyao_facts("local_apparent_solar-v1"), ("outcome",), "instant"),
            ("meihua", "concrete_event", _meihua_facts("local_apparent_solar-v1"), ("outcome",), "instant"),
            ("qimen", "concrete_event", _event_facts("local_apparent_solar-v1"), ("outcome",), "instant"),
            ("taiyi", "macro_historical", _event_facts("local_apparent_solar-v1"), ("outcome",), "year"),
            ("fortune", "near_time_personal", fortune_facts, ("outcome",), "week"),
        )
        for system, obj, facts, dims, horizon in cases:
            without_coordinates = dict(facts)
            for field in ("longitude", "latitude", "coordinate_source"):
                without_coordinates.pop(field, None)
            with self.subTest(system=system):
                result = _run(
                    _prepare(
                        "看结果",
                        system,
                        obj,
                        without_coordinates,
                        dims=dims,
                        horizon=horizon,
                    )
                )
                self.assertEqual(result.kind, "stopped", result)
                self.assertEqual(result.reason, "need_input")
                self.assertTrue(result.public_copy.strip())
                requested = {
                    field.id
                    for requirement in result.input_request.requirements
                    for field in requirement.any_of
                }
                self.assertTrue(
                    {"longitude", "latitude", "coordinate_source"}
                    <= requested
                )


class CoordinateAccuracyTests(unittest.TestCase):
    def test_illegal_accuracy_is_rejected(self) -> None:
        for bad in (float("inf"), -5.0, float("nan")):
            with self.subTest(bad=bad):
                result = _run(_prepare("看命", "bazi", "natal", _birth_facts("local_apparent_solar-v1", accuracy=bad)))
                self.assertEqual(result.kind, "stopped")
                self.assertNotEqual(result.kind, "prepared")

    def test_large_accuracy_surfaces_unresolved_boundary(self) -> None:
        # A 100 km coordinate uncertainty pushes the cross-hour apparent chart
        # into the uncertainty budget; the brief must surface an unresolved
        # time boundary instead of asserting a certain hour branch.
        result = _run(_prepare("看命", "bazi", "natal", _birth_facts("local_apparent_solar-v1", accuracy=100000.0)))
        self.assertEqual(result.kind, "prepared", result)
        limits = result.brief.to_dict().get("limits", [])
        limit_kinds = [limit.get("kind_id") for limit in limits]
        self.assertIn("limit.unresolved_time_boundary", limit_kinds)

    def test_every_timed_provider_routes_accuracy_to_a_public_boundary(self) -> None:
        """All ten coordinate-aware providers retain one uncertainty signal."""

        fortune_facts = {
            **_birth_facts("local_apparent_solar-v1", accuracy=100_000.0),
            "reference_datetime": "2026-07-31T12:00:00",
        }
        cases = (
            ("bazi", "natal", _birth_facts("local_apparent_solar-v1", 100_000.0), ("career",), "life"),
            ("ziwei", "natal", _birth_facts("local_apparent_solar-v1", 100_000.0), ("career",), "life"),
            ("luming-nayin", "natal", _birth_facts("local_apparent_solar-v1", 100_000.0), ("career",), "life"),
            ("xingming", "natal", _birth_facts("local_apparent_solar-v1", 100_000.0), ("career",), "life"),
            ("liuren", "concrete_event", _event_facts("local_apparent_solar-v1", 100_000.0), ("outcome",), "instant"),
            ("liuyao", "concrete_event", _liuyao_facts("local_apparent_solar-v1", 100_000.0), ("outcome",), "instant"),
            ("meihua", "concrete_event", _meihua_facts("local_apparent_solar-v1", 100_000.0), ("outcome",), "instant"),
            ("qimen", "concrete_event", _event_facts("local_apparent_solar-v1", 100_000.0), ("outcome",), "instant"),
            ("taiyi", "macro_historical", _event_facts("local_apparent_solar-v1", 100_000.0), ("outcome",), "year"),
            ("fortune", "near_time_personal", fortune_facts, ("outcome",), "week"),
        )
        for system, obj, facts, dims, horizon in cases:
            with self.subTest(system=system):
                result = _run(
                    _prepare(
                        "看命盘",
                        system,
                        obj,
                        facts,
                        dims=dims,
                        horizon=horizon,
                    )
                )
                self.assertEqual(result.kind, "prepared", result)
                brief = result.brief.to_dict()
                limits = [
                    limit
                    for limit in brief.get("limits", [])
                    if limit.get("kind_id") == "limit.unresolved_time_boundary"
                ]
                self.assertEqual(
                    len(limits),
                    1,
                    f"{system} dropped coordinate_accuracy_meters",
                )
                term = next(
                    item
                    for item in brief.get("vocabulary", [])
                    if item.get("id") == "limit.unresolved_time_boundary"
                )
                self.assertNotEqual(term["label"], term["id"])
                self.assertEqual(limits[0]["public_text"], term["label"])


class NotApplicableProvidersTests(unittest.TestCase):
    def test_physiognomy_and_fengshui_declare_not_applicable(self) -> None:
        result = _run(Describe().to_dict())
        for pid in ("physiognomy", "fengshui"):
            cap = next(c for c in result.capabilities if c.id == pid)
            self.assertEqual(cap.time_semantics.role_id, "not_applicable")
            self.assertEqual(cap.time_semantics.coordinate_required_policy_ids, ())


class CrossHostIsomorphismTests(unittest.TestCase):
    def test_in_process_and_cli_describe_are_identical(self) -> None:
        direct = _run(Describe().to_dict())
        env = {**os.environ, "MINGLI_PYTHON": str(VENV), "PYTHONDONTWRITEBYTECODE": "1"}
        completed = subprocess.run(
            [*runtime_command(), str(ROOT / "scripts/adapters/json_cli.py")],
            input=json.dumps(Describe().to_dict()),
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        cli = json.loads(completed.stdout)
        self.assertEqual(direct.to_dict(), cli)

    def test_apparent_solar_prepare_is_identical_in_process_and_cli(self) -> None:
        command = _prepare(
            "看命",
            "bazi",
            "natal",
            _birth_facts("local_apparent_solar-v1"),
        )
        direct = _run(command)
        self.assertEqual(direct.kind, "prepared", direct)
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                **os.environ,
                "MINGLI_PYTHON": str(VENV),
                "MINGLI_STORE_ROOT": str(Path(tmp) / "cli-store"),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            completed = subprocess.run(
                [*runtime_command(), str(ROOT / "scripts/adapters/json_cli.py")],
                input=json.dumps(command),
                capture_output=True,
                text=True,
                env=env,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        cli = json.loads(completed.stdout)
        self.assertEqual(cli["kind"], "prepared", cli)
        self.assertEqual(direct.brief.to_dict(), cli["brief"])


if __name__ == "__main__":
    unittest.main()
