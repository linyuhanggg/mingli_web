from __future__ import annotations

import copy
import unittest
from pathlib import Path

import bazi_fact_adapter
import adapter_validate
import liuren_fact_adapter
import ziwei_fact_adapter
from reading_engine.calendar_core import normalize_calendar


ROOT = Path(__file__).resolve().parents[1]


class CalendarCoreBoundaryTests(unittest.TestCase):
    def test_normalization_is_complete_and_digest_is_deterministic(self) -> None:
        arguments = {
            "civil_datetime": "1990-10-09T13:30:00",
            "timezone_name": "Asia/Shanghai",
            "location": "上海",
            "longitude": 121.4737,
            "latitude": 31.2304,
            "coordinate_source": "user_measurement",
            "zi_hour_policy": "midnight",
        }
        first = normalize_calendar(**arguments)
        second = normalize_calendar(**arguments)

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "mingli-calendar-normalization-v2")
        self.assertEqual(first["civil_datetime"], "1990-10-09T13:30:00+08:00")
        self.assertEqual(first["utc_datetime"], "1990-10-09T05:30:00+00:00")
        self.assertEqual(first["timezone"], "Asia/Shanghai")
        self.assertEqual(first["timezone_details"]["utc_offset_seconds"], 28800)
        self.assertEqual(first["location"]["name"], "上海")
        self.assertEqual(first["location"]["longitude"], 121.4737)
        self.assertEqual(first["location"]["latitude"], 31.2304)
        self.assertEqual(first["location"]["coordinate_source"], "user_measurement")
        self.assertEqual(first["calendar_convention"]["engine_version"], "2.0.7")
        self.assertEqual(first["calendar_convention"]["version"], "1.0.2")
        self.assertEqual(len(first["digest"]), 64)
        self.assertEqual(len(first["ganzhi"]), 4)
        self.assertIn("is_leap_month", first["lunar_date"])
        self.assertIn("exact_boundary", first["solar_terms"])

    def test_late_zi_day_rollover_is_explicit(self) -> None:
        common = {
            "civil_datetime": "2024-01-01T23:30:00",
            "timezone_name": "Asia/Shanghai",
            "location": "上海",
        }
        midnight = normalize_calendar(**common, zi_hour_policy="midnight")
        late_zi = normalize_calendar(
            **common,
            zi_hour_policy="late-zi-next-day",
        )

        self.assertEqual(midnight["civil_datetime"], late_zi["civil_datetime"])
        self.assertNotEqual(midnight["ganzhi"]["day"], late_zi["ganzhi"]["day"])
        self.assertEqual(
            midnight["calendar_convention"]["day_rollover"],
            "civil_midnight",
        )
        self.assertEqual(
            late_zi["calendar_convention"]["day_rollover"],
            "late_zi_advances_day_pillar",
        )

    def test_leap_month_state_is_not_flattened(self) -> None:
        result = normalize_calendar(
            "2023-03-22T12:00:00",
            timezone_name="Asia/Shanghai",
            location="上海",
        )

        self.assertEqual(
            result["lunar_date"],
            {"year": 2023, "month": 2, "day": 1, "is_leap_month": True},
        )

    def test_year_and_month_change_at_exact_li_chun_instant(self) -> None:
        before = normalize_calendar(
            "2024-02-04T16:26:52+08:00",
            timezone_name="Asia/Shanghai",
            location="上海",
        )
        after = normalize_calendar(
            "2024-02-04T16:26:54+08:00",
            timezone_name="Asia/Shanghai",
            location="上海",
        )

        self.assertEqual(before["ganzhi"]["year"], "癸卯")
        self.assertEqual(before["ganzhi"]["month"], "乙丑")
        self.assertEqual(after["ganzhi"]["year"], "甲辰")
        self.assertEqual(after["ganzhi"]["month"], "丙寅")
        self.assertEqual(before["solar_terms"]["next"]["name"], "立春")
        self.assertEqual(after["solar_terms"]["previous"]["name"], "立春")

    def test_historical_timezone_offset_is_preserved(self) -> None:
        result = normalize_calendar(
            "1945-08-15T12:00:00",
            timezone_name="Asia/Shanghai",
            location="上海",
        )

        self.assertEqual(result["civil_datetime"], "1945-08-15T12:00:00+09:00")
        self.assertEqual(result["utc_datetime"], "1945-08-15T03:00:00+00:00")
        self.assertEqual(result["timezone_offset_seconds"], 9 * 60 * 60)
        self.assertEqual(result["dst_offset_seconds"], 60 * 60)

    def test_nonexistent_dst_wall_time_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "nonexistent local time"):
            normalize_calendar(
                "2024-03-10T02:30:00",
                timezone_name="America/New_York",
                location="New York",
            )

    def test_locations_east_and_west_of_standard_meridian_are_explicit(self) -> None:
        common = {
            "civil_datetime": "2024-06-01T12:00:00",
            "timezone_name": "Asia/Shanghai",
            "latitude": 31.0,
            "coordinate_source": "surveyed",
            "time_basis_policy": "longitude_mean_solar-v1",
        }
        east = normalize_calendar(
            **common,
            location="east fixture",
            longitude=135.0,
        )
        west = normalize_calendar(
            **common,
            location="west fixture",
            longitude=105.0,
        )

        self.assertEqual(east["time_basis"]["standard_meridian_degrees"], 120.0)
        self.assertEqual(east["time_basis"]["longitude_correction_seconds"], 3600)
        self.assertEqual(west["time_basis"]["longitude_correction_seconds"], -3600)
        self.assertTrue(east["effective_datetime"].startswith("2024-06-01T13:00:00"))
        self.assertTrue(west["effective_datetime"].startswith("2024-06-01T11:00:00"))


class CalendarCoreProviderBindingTests(unittest.TestCase):
    def test_time_driven_adapters_share_one_calendar_digest(self) -> None:
        bazi, conflict = bazi_fact_adapter.build_from_birth(
            "1990-10-09T13:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            gender="male",
            expected_pillars=None,
            zi_hour_policy="midnight",
        )
        self.assertFalse(conflict)
        ziwei = ziwei_fact_adapter.build_from_birth(
            "1990-10-09T13:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            gender="male",
        )
        liuren = liuren_fact_adapter.build_from_datetime(
            "1990-10-09T13:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            question="fixture",
        )

        digests = {
            item["calendar_normalization"]["digest"]
            for item in (bazi, ziwei, liuren)
        }
        self.assertEqual(len(digests), 1)

    def test_time_driven_adapters_do_not_own_separate_sxtwl_logic(self) -> None:
        for relative in (
            "scripts/bazi_fact_adapter.py",
            "scripts/near_time_fortune_adapter.py",
            "scripts/liuren_fact_adapter.py",
            "scripts/ziwei_fact_adapter.py",
        ):
            with self.subTest(relative=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotIn("import " + "sxtwl", source)
                self.assertIn("calendar_core", source)

    def test_adapter_validation_rejects_a_tampered_shared_calendar_digest(self) -> None:
        facts, conflict = bazi_fact_adapter.build_from_birth(
            "1990-10-09T13:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            gender="male",
            expected_pillars=None,
            zi_hour_policy="midnight",
        )
        self.assertFalse(conflict)
        tampered = copy.deepcopy(facts)
        tampered["calendar_normalization"]["ganzhi"]["day"] = "甲子"

        validation = adapter_validate.validate_payload("bazi", tampered)

        self.assertFalse(validation["ok"], validation)
        self.assertIn("calendar_digest_mismatch", validation["codes"])


if __name__ == "__main__":
    unittest.main()
