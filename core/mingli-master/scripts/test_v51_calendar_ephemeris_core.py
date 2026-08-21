"""Boundary regressions for the shared V5.1 calendar and ephemeris foundation."""

from __future__ import annotations

import importlib
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reading_engine.contracts import ReadingRequest
from reading_engine.providers import (
    BaziProvider,
    FortuneProvider,
    LiurenProvider,
    ZiweiProvider,
)


ROOT = Path(__file__).resolve().parents[1]


class SharedCalendarCoreTests(unittest.TestCase):
    def _core(self):
        return importlib.import_module("reading_engine.calendar_core")

    def _normalize(self, civil_datetime: str, **overrides):
        core = self._core()
        arguments = {
            "timezone_name": "Asia/Shanghai",
            "location": "上海",
            "latitude": 31.2304,
            "longitude": 121.4737,
            "coordinate_source": "user_supplied_decimal_degrees",
            "zi_hour_policy": "midnight",
        }
        arguments.update(overrides)
        return core.normalize_calendar(civil_datetime, **arguments)

    def test_complete_calendar_identity_is_preserved_and_deterministic(self) -> None:
        first = self._normalize("2000-10-18T06:45:00")
        second = self._normalize("2000-10-18T06:45:00")

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "mingli-calendar-normalization-v2")
        self.assertEqual(first["civil_datetime"], "2000-10-18T06:45:00+08:00")
        self.assertEqual(first["instant_utc"], "2000-10-17T22:45:00+00:00")
        self.assertEqual(first["timezone"], "Asia/Shanghai")
        self.assertEqual(first["timezone_details"]["name"], "Asia/Shanghai")
        self.assertEqual(first["location"]["name"], "上海")
        self.assertEqual(first["location"]["latitude"], 31.2304)
        self.assertEqual(first["location"]["longitude"], 121.4737)
        self.assertEqual(
            first["location"]["coordinate_source"],
            "user_supplied_decimal_degrees",
        )
        self.assertEqual(
            first["ganzhi"],
            {"year": "庚辰", "month": "丙戌", "day": "己酉", "hour": "丁卯"},
        )
        self.assertEqual(
            first["lunar_date"],
            {"year": 2000, "month": 9, "day": 21, "is_leap_month": False},
        )
        self.assertEqual(len(first["calendar_digest"]), 64)

    def test_zi_hour_day_rollover_is_an_explicit_versioned_choice(self) -> None:
        midnight = self._normalize("2000-10-18T23:30:00", zi_hour_policy="midnight")
        late_zi = self._normalize(
            "2000-10-18T23:30:00",
            zi_hour_policy="late-zi-next-day",
        )

        self.assertEqual(midnight["ganzhi"]["day"], "己酉")
        self.assertEqual(midnight["ganzhi"]["hour"], "甲子")
        self.assertEqual(late_zi["ganzhi"]["day"], "庚戌")
        self.assertEqual(late_zi["ganzhi"]["hour"], "丙子")
        self.assertEqual(midnight["lunar_date"], late_zi["lunar_date"])
        self.assertEqual(
            late_zi["calendar_convention"]["day_rollover"],
            "late_zi_advances_day_pillar",
        )
        self.assertNotEqual(midnight["calendar_digest"], late_zi["calendar_digest"])

    def test_lunar_leap_month_state_is_not_collapsed(self) -> None:
        last_regular_day = self._normalize("2023-03-21T12:00:00")
        first_leap_day = self._normalize("2023-03-22T12:00:00")
        last_leap_day = self._normalize("2023-04-19T12:00:00")
        next_regular_month = self._normalize("2023-04-20T12:00:00")

        self.assertEqual(
            last_regular_day["lunar_date"],
            {"year": 2023, "month": 2, "day": 30, "is_leap_month": False},
        )
        self.assertEqual(
            first_leap_day["lunar_date"],
            {"year": 2023, "month": 2, "day": 1, "is_leap_month": True},
        )
        self.assertEqual(last_leap_day["lunar_date"]["is_leap_month"], True)
        self.assertEqual(
            next_regular_month["lunar_date"],
            {"year": 2023, "month": 3, "day": 1, "is_leap_month": False},
        )

    def test_year_and_month_pillars_switch_at_the_exact_li_chun_instant(self) -> None:
        before = self._normalize("2024-02-04T16:26:53.122558+08:00")
        at_boundary = self._normalize("2024-02-04T16:26:53.122559+08:00")

        self.assertEqual(before["ganzhi"]["year"], "癸卯")
        self.assertEqual(before["ganzhi"]["month"], "乙丑")
        self.assertEqual(at_boundary["ganzhi"]["year"], "甲辰")
        self.assertEqual(at_boundary["ganzhi"]["month"], "丙寅")
        self.assertEqual(
            at_boundary["solar_terms"]["active_month_boundary_jie"]["name"],
            "立春",
        )
        self.assertEqual(
            at_boundary["solar_terms"]["active_month_boundary_jie"]["datetime"],
            "2024-02-04T16:26:53.122559+08:00",
        )

    def test_dst_conversion_and_historical_offsets_are_retained(self) -> None:
        dst = self._normalize(
            "2024-03-10T07:30:00+00:00",
            timezone_name="America/New_York",
            location="New York",
            latitude=40.7128,
            longitude=-74.006,
        )
        historical = self._normalize(
            "1900-01-01T12:00:00",
            location="上海",
        )

        self.assertEqual(dst["civil_datetime"], "2024-03-10T03:30:00-04:00")
        self.assertEqual(dst["timezone_details"]["utc_offset_seconds"], -14400)
        self.assertEqual(dst["timezone_details"]["dst_offset_seconds"], 3600)
        self.assertEqual(dst["timezone_details"]["standard_meridian_degrees"], -75.0)
        self.assertEqual(
            historical["civil_datetime"],
            "1900-01-01T12:00:00+08:05:43",
        )
        self.assertEqual(historical["timezone_details"]["utc_offset_seconds"], 29143)

    def test_longitudes_east_and_west_do_not_silently_change_civil_pillars(self) -> None:
        west = self._normalize("2000-10-18T06:45:00", longitude=90.0)
        east = self._normalize("2000-10-18T06:45:00", longitude=135.0)

        self.assertEqual(west["ganzhi"], east["ganzhi"])
        self.assertEqual(west["true_solar_time"]["status"], "not_applied")
        self.assertEqual(east["true_solar_time"]["status"], "not_applied")
        self.assertEqual(west["location"]["longitude_offset_degrees"], -30.0)
        self.assertEqual(east["location"]["longitude_offset_degrees"], 15.0)
        self.assertNotEqual(west["calendar_digest"], east["calendar_digest"])

    def test_time_driven_adapters_bind_the_same_shared_calendar_digest(self) -> None:
        core = self._core()
        bazi = importlib.import_module("bazi_fact_adapter")
        fortune = importlib.import_module("near_time_fortune_adapter")
        liuren = importlib.import_module("liuren_fact_adapter")
        ziwei = importlib.import_module("ziwei_fact_adapter")
        arguments = {
            "timezone_name": "Asia/Shanghai",
            "location": "上海",
            "latitude": 31.2304,
            "longitude": 121.4737,
            "coordinate_source": "user_supplied_decimal_degrees",
            "zi_hour_policy": "midnight",
        }
        expected = core.normalize_calendar("2000-10-18T06:45:00", **arguments)
        bazi_facts, conflict = bazi.build_from_birth(
            "2000-10-18T06:45:00",
            gender="male",
            expected_pillars=None,
            **arguments,
        )
        liuren_facts = liuren.build_from_datetime(
            "2000-10-18T06:45:00",
            question="这次合作能否按期完成？",
            **arguments,
        )
        ziwei_facts = ziwei.build_from_birth(
            "2000-10-18T06:45:00",
            gender="male",
            **arguments,
        )
        snapshot = fortune._snapshot(
            datetime(2000, 10, 18, 6, 45, tzinfo=ZoneInfo("Asia/Shanghai")),
            day_master="己",
            natal_pillars={"year": "庚辰", "month": "丙戌", "day": "己酉", "hour": "丁卯"},
            location="上海",
            latitude=31.2304,
            longitude=121.4737,
            coordinate_source="user_supplied_decimal_degrees",
            zi_hour_policy="midnight",
        )

        self.assertFalse(conflict)
        expected_digest = expected["calendar_digest"]
        self.assertEqual(
            {
                bazi_facts["calendar_normalization"]["calendar_digest"],
                liuren_facts["calendar_normalization"]["calendar_digest"],
                ziwei_facts["calendar_normalization"]["calendar_digest"],
                snapshot["calendar_normalization"]["calendar_digest"],
            },
            {expected_digest},
        )


class VersionedEphemerisCoreTests(unittest.TestCase):
    def _calendar(self):
        core = importlib.import_module("reading_engine.calendar_core")
        return core.normalize_calendar(
            "2000-01-01T12:00:00+00:00",
            timezone_name="UTC",
            location="Greenwich",
            latitude=51.4769,
            longitude=0.0,
            coordinate_source="reference_fixture",
            zi_hour_policy="midnight",
        )

    def test_j2000_seven_luminaries_match_the_independent_frozen_oracle(self) -> None:
        ephemeris = importlib.import_module("reading_engine.ephemeris_core")
        result = ephemeris.calculate_ephemeris(self._calendar())
        expected = {
            "Sun": 280.368738639819,
            "Moon": 223.323891127474,
            "Mercury": 271.888912066463,
            "Venus": 241.565232940362,
            "Mars": 327.963899077903,
            "Jupiter": 25.254199844874,
            "Saturn": 40.396124137178,
        }

        self.assertEqual(result["schema_version"], "mingli-ephemeris-v1")
        self.assertEqual(result["engine"]["name"], "astronomy-engine")
        self.assertEqual(result["engine"]["version"], "2.1.19")
        self.assertEqual(result["engine"]["license"], "MIT")
        self.assertEqual(
            result["coordinate_convention"]["frame"],
            "geocentric_true_ecliptic_of_date",
        )
        for body, longitude in expected.items():
            self.assertAlmostEqual(
                result["positions"][body]["longitude_degrees"],
                longitude,
                places=9,
            )
        self.assertEqual(result, ephemeris.calculate_ephemeris(self._calendar()))
        self.assertEqual(len(result["ephemeris_digest"]), 64)

    def test_ephemeris_rejects_a_tampered_calendar_binding(self) -> None:
        ephemeris = importlib.import_module("reading_engine.ephemeris_core")
        calendar = self._calendar()
        calendar["civil_datetime"] = "2001-01-01T12:00:00+00:00"

        with self.assertRaisesRegex(ValueError, "calendar digest"):
            ephemeris.calculate_ephemeris(calendar)


class TimeDrivenProviderCalendarBindingTests(unittest.TestCase):
    def test_every_time_driven_provider_binds_its_consumed_calendar_digest(self) -> None:
        coordinates = {
            "longitude": 121.4737,
            "latitude": 31.2304,
            "coordinate_source": "user_supplied_decimal_degrees",
        }
        birth = {
            "datetime": "2000-10-18T06:45:00",
            "birth_datetime": "2000-10-18T06:45:00",
            "timezone": "Asia/Shanghai",
            "location": "上海",
            "gender": "male",
            **coordinates,
        }
        calculations = (
            BaziProvider(ROOT).calculate(
                ReadingRequest(
                    query="看命盘",
                    action="new",
                    system="bazi",
                    birth_data=birth,
                    timezone="Asia/Shanghai",
                    location="上海",
                    reference_datetime="2026-07-24T12:00:00+08:00",
                )
            ),
            FortuneProvider(ROOT).calculate(
                ReadingRequest(
                    query="看今天",
                    action="new",
                    system="fortune",
                    birth_data=birth,
                    timezone="Asia/Shanghai",
                    location="上海",
                    reference_datetime="2026-07-24T12:00:00+08:00",
                )
            ),
            LiurenProvider(ROOT).calculate(
                ReadingRequest(
                    query="此事能否按期完成",
                    action="new",
                    system="liuren",
                    timezone="Asia/Shanghai",
                    location="上海",
                    event_datetime="2026-07-24T12:00:00+08:00",
                    metadata=coordinates,
                )
            ),
            ZiweiProvider(ROOT).calculate(
                ReadingRequest(
                    query="看命盘",
                    action="new",
                    system="ziwei",
                    birth_data=birth,
                    timezone="Asia/Shanghai",
                    location="上海",
                )
            ),
        )

        for calculation in calculations:
            with self.subTest(system=calculation.system):
                calendar = calculation.facts["chart_facts"][
                    "calendar_normalization"
                ]
                self.assertEqual(
                    calculation.facts["calendar_digest"],
                    calendar["calendar_digest"],
                )
                self.assertEqual(
                    calculation.facts["calendar_digest"],
                    calendar["digest"],
                )


if __name__ == "__main__":
    unittest.main()
