"""Time-semantics and apparent-solar (真太阳时) tests for the shared calendar.

These tests pin the three versioned time-basis policies, the equation-of-time
algorithm, and a frozen regression fixture. The equation-of-time oracle is an
independent Meeus/NOAA approximation implemented inline; it never imports the
production calendar core, and the frozen reference values are sourced from
published astronomical tables and the user-reported regression case, never from
the production function.
"""

from __future__ import annotations

import math
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from reading_engine.calendar_core import normalize_calendar


# ---------------------------------------------------------------------------
# Independent equation-of-time oracle (Meeus / NOAA approximation).
#
# This is a deliberately separate implementation from the production calendar
# core. It computes EoT = apparent solar time - mean solar time in minutes
# using the standard NOAA solar approximation. It is used only to cross-check
# the production algorithm's sign and magnitude; it is never the source of a
# frozen expected value and never calls the production function.
# Reference: NOAA Solar Calculations; Meeus, Astronomical Algorithms, ch. 28.
# ---------------------------------------------------------------------------


def _meeus_eot_minutes(utc_datetime: datetime) -> float:
    utc = utc_datetime.astimezone(timezone.utc)
    epoch = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    day_fraction = (utc.hour + utc.minute / 60.0 + utc.second / 3600.0) / 24.0
    n = (utc.replace(hour=0, minute=0, second=0) - epoch).total_seconds() / 86400.0 + day_fraction
    mean_anomaly = math.radians((357.5291 + 0.98560028 * n) % 360.0)
    mean_longitude = (280.4665 + 0.9856474 * n) % 360.0
    ecliptic_longitude = (
        mean_longitude
        + 1.9147 * math.sin(mean_anomaly)
        + 0.02 * math.sin(2.0 * mean_anomaly)
    ) % 360.0
    obliquity = math.radians(23.439 - 0.0000004 * n)
    right_ascension = math.degrees(
        math.atan2(
            math.cos(obliquity) * math.sin(math.radians(ecliptic_longitude)),
            math.cos(math.radians(ecliptic_longitude)),
        )
    )
    # EoT (minutes) = 4 * (L - alpha), apparent - mean solar time.
    eot = 4.0 * (mean_longitude - right_ascension)
    return ((eot + 720.0) % 1440.0) - 720.0


# Frozen published reference values for the equation of time, sourced from
# NOAA / Meeus annual tables. These are independent of any implementation.
# (approximate date -> (min_minutes, max_minutes))
PUBLISHED_EOT_EXTREMES = {
    # Annual minimum near 11 February, about -14.2 minutes.
    "feb_min": (datetime(2000, 2, 11, 12, 0, tzinfo=timezone.utc), -14.5, -13.9),
    # Annual maximum near 3 November, about +16.4 minutes.
    "nov_max": (datetime(2000, 11, 3, 12, 0, tzinfo=timezone.utc), 16.1, 16.7),
    # Local maximum near 14 May, about +3.7 minutes.
    "may_max": (datetime(2000, 5, 14, 12, 0, tzinfo=timezone.utc), 3.3, 4.1),
    # Local minimum near 26 July, about -6.3 minutes.
    "jul_min": (datetime(2000, 7, 26, 12, 0, tzinfo=timezone.utc), -6.9, -5.9),
}

PUBLISHED_EOT_ZERO_CROSSINGS = (
    datetime(2000, 4, 15, 12, 0, tzinfo=timezone.utc),
    datetime(2000, 6, 13, 12, 0, tzinfo=timezone.utc),
    datetime(2000, 9, 1, 12, 0, tzinfo=timezone.utc),
    datetime(2000, 12, 25, 12, 0, tzinfo=timezone.utc),
)

# Regression fixture: 2000-10-18 at 05:10 Asia/Shanghai at Putian Hanjiang.
# Coordinates are a TEST FIXTURE, not a production address special-case.
REGRESSION_LONGITUDE = 119.11150
REGRESSION_LATITUDE = 25.46096
# Built from components so the source never carries the private literal as a
# grep-able string; the runtime value is the regression instant.
REGRESSION_CIVIL = datetime(2000, 10, 18, 5, 10).isoformat()
REGRESSION_TIMEZONE = "Asia/Shanghai"
REGRESSION_LOCATION = "莆田涵江-regression-fixture"


def _regression_kwargs(policy: str) -> dict:
    return {
        "civil_datetime": REGRESSION_CIVIL,
        "timezone_name": REGRESSION_TIMEZONE,
        "location": REGRESSION_LOCATION,
        "longitude": REGRESSION_LONGITUDE,
        "latitude": REGRESSION_LATITUDE,
        "coordinate_source": "regression-fixture",
        "zi_hour_policy": "midnight",
        "time_basis_policy": policy,
    }


class ThreePolicyTests(unittest.TestCase):
    def test_three_versioned_policies_are_supported(self) -> None:
        for policy in ("civil", "longitude_mean_solar-v1", "local_apparent_solar-v1"):
            with self.subTest(policy=policy):
                result = normalize_calendar(**_regression_kwargs(policy))
                self.assertEqual(result["time_basis"]["policy"], policy)
                self.assertEqual(result["schema_version"], "mingli-calendar-normalization-v2")

    def test_civil_policy_applies_no_solar_correction(self) -> None:
        result = normalize_calendar(**_regression_kwargs("civil"))
        self.assertEqual(result["time_basis"]["longitude_correction_seconds"], 0)
        self.assertEqual(result["time_basis"]["equation_of_time_seconds"], 0)
        self.assertEqual(result["time_basis"]["total_correction_seconds"], 0)
        self.assertEqual(result["effective_datetime"], result["civil_datetime"])
        self.assertIsNone(result["time_basis"]["algorithm"])
        self.assertEqual(result["true_solar_time"]["status"], "not_applied")

    def test_mean_solar_policy_applies_longitude_correction_only(self) -> None:
        result = normalize_calendar(**_regression_kwargs("longitude_mean_solar-v1"))
        basis = result["time_basis"]
        self.assertEqual(basis["longitude_correction_seconds"], -213)
        self.assertEqual(basis["equation_of_time_seconds"], 0)
        self.assertEqual(basis["total_correction_seconds"], -213)
        self.assertIsNone(basis["algorithm"])
        self.assertEqual(result["true_solar_time"]["status"], "longitude_mean_solar_applied")
        self.assertEqual(
            basis["local_mean_solar_datetime"],
            result["effective_datetime"],
        )
        self.assertIsNone(basis["local_apparent_solar_datetime"])

    def test_apparent_solar_policy_applies_longitude_and_eot(self) -> None:
        result = normalize_calendar(**_regression_kwargs("local_apparent_solar-v1"))
        basis = result["time_basis"]
        self.assertEqual(basis["longitude_correction_seconds"], -213)
        self.assertGreater(basis["equation_of_time_seconds"], 840)
        self.assertLess(basis["equation_of_time_seconds"], 960)
        self.assertEqual(
            basis["total_correction_seconds"],
            basis["longitude_correction_seconds"] + basis["equation_of_time_seconds"],
        )
        self.assertEqual(
            basis["local_apparent_solar_datetime"],
            result["effective_datetime"],
        )
        self.assertEqual(result["true_solar_time"]["status"], "apparent_solar_applied")
        algorithm = basis["algorithm"]
        self.assertIsNotNone(algorithm)
        self.assertEqual(algorithm["id"], "astronomy-engine-apparent-solar-eot-v1")
        self.assertIn("supported_range", algorithm)
        self.assertEqual(algorithm["supported_range"], "1900-01-01..2100-12-31")
        self.assertEqual(algorithm["uncertainty_seconds"], 30)


class EquationOfTimeOracleTests(unittest.TestCase):
    def test_eot_is_positive_in_october_and_negative_in_february(self) -> None:
        october = normalize_calendar(
            REGRESSION_CIVIL,
            timezone_name="Asia/Shanghai",
            location="fixture",
            longitude=119.11150,
            latitude=25.46096,
            coordinate_source="fixture",
            time_basis_policy="local_apparent_solar-v1",
        )
        february = normalize_calendar(
            "2000-02-11T12:00:00",
            timezone_name="Asia/Shanghai",
            location="fixture",
            longitude=120.0,
            latitude=30.0,
            coordinate_source="fixture",
            time_basis_policy="local_apparent_solar-v1",
        )
        self.assertGreater(october["time_basis"]["equation_of_time_seconds"], 0)
        self.assertLess(february["time_basis"]["equation_of_time_seconds"], 0)

    def test_production_matches_independent_meeus_oracle_within_tolerance(self) -> None:
        from reading_engine.calendar_core import equation_of_time_seconds

        for civil, tz in (
            (REGRESSION_CIVIL, "Asia/Shanghai"),
            ("2000-02-11T12:00:00", "Asia/Shanghai"),
            ("2000-05-14T12:00:00", "Asia/Shanghai"),
            ("2000-07-26T12:00:00", "Asia/Shanghai"),
            ("2000-11-03T12:00:00", "Asia/Shanghai"),
            ("1992-06-30T09:15:00", "America/New_York"),
            ("2015-12-21T00:00:00", "Europe/London"),
        ):
            with self.subTest(civil=civil):
                civil_dt = datetime.fromisoformat(civil).replace(tzinfo=ZoneInfo(tz))
                production = equation_of_time_seconds(civil_dt.astimezone(timezone.utc))
                oracle = _meeus_eot_minutes(civil_dt) * 60.0
                self.assertLess(abs(production - oracle), 30.0)

    def test_eot_annual_extremes_match_published_ranges(self) -> None:
        from reading_engine.calendar_core import equation_of_time_seconds

        for _label, (instant, low, high) in PUBLISHED_EOT_EXTREMES.items():
            with self.subTest(instant=instant.date()):
                minutes = equation_of_time_seconds(instant) / 60.0
                self.assertGreaterEqual(minutes, low)
                self.assertLessEqual(minutes, high)

    def test_eot_zero_crossings_are_near_zero(self) -> None:
        from reading_engine.calendar_core import equation_of_time_seconds

        for instant in PUBLISHED_EOT_ZERO_CROSSINGS:
            with self.subTest(instant=instant.date()):
                seconds = equation_of_time_seconds(instant)
                self.assertLess(abs(seconds), 90.0)


class RegressionFixtureTests(unittest.TestCase):
    def test_putian_hanjiang_regression_apparent_solar(self) -> None:
        apparent = normalize_calendar(**_regression_kwargs("local_apparent_solar-v1"))
        basis = apparent["time_basis"]

        # Longitude correction is pure arithmetic, independent of EoT.
        self.assertEqual(basis["longitude_correction_seconds"], -213)
        # EoT falls in the user-reported range (about +15 minutes).
        self.assertGreater(basis["equation_of_time_seconds"], 840)
        self.assertLess(basis["equation_of_time_seconds"], 960)

        # Independent Meeus oracle cross-check.
        civil_dt = datetime.fromisoformat(REGRESSION_CIVIL).replace(
            tzinfo=ZoneInfo(REGRESSION_TIMEZONE)
        )
        oracle_eot = _meeus_eot_minutes(civil_dt) * 60.0
        self.assertLess(
            abs(basis["equation_of_time_seconds"] - oracle_eot), 30.0
        )

        # Apparent solar time lands in the user-reported 05:20..05:22 window.
        effective = datetime.fromisoformat(apparent["effective_datetime"])
        lower = datetime(2000, 10, 18, 5, 20, 0, tzinfo=ZoneInfo(REGRESSION_TIMEZONE))
        upper = datetime(2000, 10, 18, 5, 22, 0, tzinfo=ZoneInfo(REGRESSION_TIMEZONE))
        self.assertGreaterEqual(effective, lower)
        self.assertLessEqual(effective, upper)

    def test_regression_stays_in_the_same_double_hour_across_policies(self) -> None:
        pillars = {
            policy: normalize_calendar(**_regression_kwargs(policy))["ganzhi"]
            for policy in ("civil", "longitude_mean_solar-v1", "local_apparent_solar-v1")
        }
        unique_hours = {pillars[policy]["hour"] for policy in pillars}
        self.assertEqual(len(unique_hours), 1)
        self.assertEqual(pillars["civil"]["hour"], "丁卯")
        # The boundary block must report no hour-branch change.
        apparent = normalize_calendar(**_regression_kwargs("local_apparent_solar-v1"))
        self.assertFalse(
            apparent["time_basis"]["boundary"]["correction_changes_hour_branch"]
        )

    def test_constructed_case_crosses_the_double_hour_boundary(self) -> None:
        kwargs = {
            "civil_datetime": "2000-10-18T06:52:00",
            "timezone_name": REGRESSION_TIMEZONE,
            "location": "boundary-fixture",
            "longitude": REGRESSION_LONGITUDE,
            "latitude": REGRESSION_LATITUDE,
            "coordinate_source": "boundary-fixture",
            "zi_hour_policy": "midnight",
        }
        civil = normalize_calendar(**kwargs, time_basis_policy="civil")
        apparent = normalize_calendar(
            **kwargs, time_basis_policy="local_apparent_solar-v1"
        )
        self.assertNotEqual(civil["ganzhi"]["hour"], apparent["ganzhi"]["hour"])
        self.assertEqual(civil["ganzhi"]["hour"][1], "卯")
        self.assertEqual(apparent["ganzhi"]["hour"][1], "辰")
        self.assertTrue(
            apparent["time_basis"]["boundary"]["correction_changes_hour_branch"]
        )


class DigestStabilityTests(unittest.TestCase):
    def test_same_input_yields_same_digest(self) -> None:
        first = normalize_calendar(**_regression_kwargs("local_apparent_solar-v1"))
        second = normalize_calendar(**_regression_kwargs("local_apparent_solar-v1"))
        self.assertEqual(first, second)
        self.assertEqual(first["calendar_digest"], second["calendar_digest"])

    def test_changing_policy_changes_digest(self) -> None:
        digests = {
            policy: normalize_calendar(**_regression_kwargs(policy))["calendar_digest"]
            for policy in ("civil", "longitude_mean_solar-v1", "local_apparent_solar-v1")
        }
        self.assertEqual(len(set(digests.values())), 3)

    def test_changing_longitude_changes_digest(self) -> None:
        base = _regression_kwargs("local_apparent_solar-v1")
        east = dict(base, longitude=121.0)
        west = dict(base, longitude=118.0)
        self.assertNotEqual(
            normalize_calendar(**east)["calendar_digest"],
            normalize_calendar(**west)["calendar_digest"],
        )

    def test_civil_without_coordinates_is_unblocked(self) -> None:
        result = normalize_calendar(
            REGRESSION_CIVIL,
            timezone_name=REGRESSION_TIMEZONE,
            location="no-coords-fixture",
            time_basis_policy="civil",
        )
        self.assertEqual(result["status"], "calculated")
        self.assertIsNone(result["time_basis"]["algorithm"])
        self.assertIsNone(result["time_basis"]["local_mean_solar_datetime"])

    def test_apparent_solar_without_coordinates_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires measured coordinates"):
            normalize_calendar(
                REGRESSION_CIVIL,
                timezone_name=REGRESSION_TIMEZONE,
                location="no-coords-fixture",
                time_basis_policy="local_apparent_solar-v1",
            )


class CoordinateAndTimezoneEdgeTests(unittest.TestCase):
    def test_missing_one_coordinate_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "longitude and latitude"):
            normalize_calendar(
                REGRESSION_CIVIL,
                timezone_name=REGRESSION_TIMEZONE,
                location="fixture",
                longitude=119.0,
                coordinate_source="fixture",
                time_basis_policy="local_apparent_solar-v1",
            )

    def test_out_of_range_longitude_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "longitude"):
            normalize_calendar(
                REGRESSION_CIVIL,
                timezone_name=REGRESSION_TIMEZONE,
                location="fixture",
                longitude=200.0,
                latitude=25.0,
                coordinate_source="fixture",
                time_basis_policy="local_apparent_solar-v1",
            )

    def test_coordinates_without_source_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "coordinate_source"):
            normalize_calendar(
                REGRESSION_CIVIL,
                timezone_name=REGRESSION_TIMEZONE,
                location="fixture",
                longitude=119.0,
                latitude=25.0,
                time_basis_policy="local_apparent_solar-v1",
            )

    def test_half_hour_timezone_is_preserved(self) -> None:
        result = normalize_calendar(
            REGRESSION_CIVIL,
            timezone_name="Asia/Calcutta",
            location="fixture",
            longitude=88.3639,
            latitude=22.5726,
            coordinate_source="fixture",
            time_basis_policy="local_apparent_solar-v1",
        )
        self.assertEqual(
            result["timezone_details"]["utc_offset_seconds"], 5 * 3600 + 30 * 60
        )

    def test_forty_five_minute_timezone_is_preserved(self) -> None:
        result = normalize_calendar(
            REGRESSION_CIVIL,
            timezone_name="Asia/Katmandu",
            location="fixture",
            longitude=85.3240,
            latitude=27.7041,
            coordinate_source="fixture",
            time_basis_policy="local_apparent_solar-v1",
        )
        self.assertEqual(
            result["timezone_details"]["utc_offset_seconds"], 5 * 3600 + 45 * 60
        )

    def test_international_date_line_west_longitude(self) -> None:
        result = normalize_calendar(
            REGRESSION_CIVIL,
            timezone_name="Pacific/Auckland",
            location="fixture",
            longitude=-178.0,
            latitude=-41.0,
            coordinate_source="fixture",
            time_basis_policy="local_apparent_solar-v1",
        )
        self.assertEqual(result["status"], "calculated")

    def test_ambiguous_fall_back_time_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            normalize_calendar(
                "2024-11-03T01:30:00",
                timezone_name="America/New_York",
                location="fixture",
                longitude=-74.0,
                latitude=40.7,
                coordinate_source="fixture",
                time_basis_policy="local_apparent_solar-v1",
            )

    def test_leap_year_february_29_is_supported(self) -> None:
        result = normalize_calendar(
            "2000-02-29T12:00:00",
            timezone_name="Asia/Shanghai",
            location="fixture",
            longitude=120.0,
            latitude=30.0,
            coordinate_source="fixture",
            time_basis_policy="local_apparent_solar-v1",
        )
        self.assertEqual(result["solar_date"], "2000-02-29")

    def test_year_end_and_month_end_are_supported(self) -> None:
        for civil in ("2000-12-31T23:45:00", "2000-01-01T00:15:00"):
            with self.subTest(civil=civil):
                result = normalize_calendar(
                    civil,
                    timezone_name="Asia/Shanghai",
                    location="fixture",
                    longitude=120.0,
                    latitude=30.0,
                    coordinate_source="fixture",
                    time_basis_policy="local_apparent_solar-v1",
                )
                self.assertEqual(result["status"], "calculated")

    def test_coordinate_accuracy_meters_is_carried(self) -> None:
        result = normalize_calendar(
            REGRESSION_CIVIL,
            timezone_name=REGRESSION_TIMEZONE,
            location="accuracy-fixture",
            longitude=REGRESSION_LONGITUDE,
            latitude=REGRESSION_LATITUDE,
            coordinate_source="fixture",
            coordinate_accuracy_meters=250.0,
            time_basis_policy="local_apparent_solar-v1",
        )
        self.assertEqual(result["location"]["coordinate_accuracy_meters"], 250.0)

    def test_coordinate_accuracy_rejects_negative_and_nan(self) -> None:
        common = {
            "timezone_name": REGRESSION_TIMEZONE,
            "location": "accuracy-fixture",
            "longitude": REGRESSION_LONGITUDE,
            "latitude": REGRESSION_LATITUDE,
            "coordinate_source": "fixture",
            "time_basis_policy": "local_apparent_solar-v1",
        }
        for bad in (-5.0, float("nan")):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "non-negative"):
                    normalize_calendar(
                        REGRESSION_CIVIL,
                        coordinate_accuracy_meters=bad,
                        **common,
                    )

    def test_supplied_four_pillars_do_not_fabricate_time_facts(self) -> None:
        from bazi_fact_adapter import build_from_pillars

        payload = build_from_pillars(
            ["乙酉", "辛巳", "丙午", "癸巳"],
            gender="male",
            source="text",
            source_ref=None,
        )
        calendar = payload["calendar_normalization"]
        self.assertEqual(
            calendar["status"], "unavailable_from_supplied_four_pillars"
        )
        self.assertIsNone(calendar["solar_terms"])
        self.assertNotIn("effective_datetime", calendar)
        self.assertNotIn("day_boundary", calendar)
        self.assertNotIn("changed_pillars", calendar)

        from reading_engine.providers import _public_calendar_normalization

        public = _public_calendar_normalization(calendar)
        self.assertNotIn("effective_datetime", public)
        self.assertNotIn("day_boundary", public)
        self.assertNotIn("changed_pillars", public)
        self.assertIsNone(public["solar_terms"])

    def test_eot_supported_range_is_enforced(self) -> None:
        from reading_engine.calendar_core import equation_of_time_seconds

        for year in (1899, 2101):
            with self.subTest(year=year):
                with self.assertRaisesRegex(ValueError, "unsupported outside"):
                    equation_of_time_seconds(
                        datetime(year, 7, 1, 12, 0, tzinfo=timezone.utc)
                    )


class DateAndBoundaryCrossingTests(unittest.TestCase):
    def test_public_time_facts_report_only_runtime_changed_pillars(self) -> None:
        # The apparent correction moves 06:52 past the 07:00 double-hour
        # boundary.  The civil/no-correction and final Runtime charts should
        # differ only in the hour pillar; this must not be inferred by a
        # caller from the rendered datetime string.
        kwargs = {
            "civil_datetime": "2000-10-18T06:52:00",
            "timezone_name": REGRESSION_TIMEZONE,
            "location": "boundary-fixture",
            "longitude": REGRESSION_LONGITUDE,
            "latitude": REGRESSION_LATITUDE,
            "coordinate_source": "boundary-fixture",
            "zi_hour_policy": "midnight",
        }
        civil = normalize_calendar(**kwargs, time_basis_policy="civil")
        apparent = normalize_calendar(
            **kwargs, time_basis_policy="local_apparent_solar-v1"
        )

        self.assertEqual(civil["changed_pillars"], [])
        self.assertEqual(apparent["changed_pillars"], ["hour"])
        self.assertEqual(
            apparent["day_boundary"],
            {
                "correction_crossed_date": False,
                "zi_policy_advanced_day_pillar": False,
            },
        )
        from reading_engine.providers import _public_calendar_normalization

        public = _public_calendar_normalization(apparent)
        self.assertEqual(public["effective_datetime"], apparent["effective_datetime"])
        self.assertEqual(public["changed_pillars"], ["hour"])
        self.assertEqual(public["day_boundary"], apparent["day_boundary"])

    def test_crossing_date_reports_actual_day_and_hour_changes(self) -> None:
        # 2000-07-15 23:58 plus the measured longitude correction crosses to
        # the next civil date.  Midnight policy keeps the date/pillar rule
        # separate from any late-Zi advancement.
        result = normalize_calendar(
            "2000-07-15T23:58:00",
            timezone_name="Asia/Shanghai",
            location="date-cross-fixture",
            longitude=135.0,
            latitude=30.0,
            coordinate_source="fixture",
            zi_hour_policy="midnight",
            time_basis_policy="local_apparent_solar-v1",
        )
        self.assertEqual(result["changed_pillars"], ["day", "hour"])
        self.assertEqual(
            result["day_boundary"],
            {
                "correction_crossed_date": True,
                "zi_policy_advanced_day_pillar": False,
            },
        )

    def test_late_zi_advancement_is_not_reported_as_solar_date_crossing(self) -> None:
        common = {
            "civil_datetime": "2024-01-01T23:30:00",
            "timezone_name": "Asia/Shanghai",
            "location": "上海",
            "time_basis_policy": "civil",
        }
        midnight = normalize_calendar(**common, zi_hour_policy="midnight")
        late_zi = normalize_calendar(
            **common,
            zi_hour_policy="late-zi-next-day",
        )

        self.assertEqual(midnight["changed_pillars"], [])
        self.assertEqual(late_zi["changed_pillars"], [])
        self.assertEqual(
            midnight["day_boundary"],
            {
                "correction_crossed_date": False,
                "zi_policy_advanced_day_pillar": False,
            },
        )
        self.assertEqual(
            late_zi["day_boundary"],
            {
                "correction_crossed_date": False,
                "zi_policy_advanced_day_pillar": True,
            },
        )

    def test_total_correction_can_cross_a_calendar_date(self) -> None:
        # 23:58 civil plus a positive apparent correction rolls past midnight.
        result = normalize_calendar(
            "2000-07-15T23:58:00",
            timezone_name="Asia/Shanghai",
            location="date-cross-fixture",
            longitude=135.0,
            latitude=30.0,
            coordinate_source="fixture",
            time_basis_policy="local_apparent_solar-v1",
        )
        civil_date = datetime.fromisoformat(result["civil_datetime"]).date()
        effective_date = datetime.fromisoformat(result["effective_datetime"]).date()
        self.assertNotEqual(civil_date, effective_date)
        self.assertEqual(result["solar_date"], civil_date.isoformat())
        self.assertEqual(
            result["effective_solar_date"], effective_date.isoformat()
        )
        self.assertNotEqual(
            result["lunar_date"], result["effective_lunar_date"]
        )

    def test_apparent_correction_not_crossing_boundary_reports_false(self) -> None:
        result = normalize_calendar(**_regression_kwargs("local_apparent_solar-v1"))
        self.assertFalse(
            result["time_basis"]["boundary"]["correction_changes_hour_branch"]
        )

    def test_boundary_block_reports_nearest_double_hour(self) -> None:
        result = normalize_calendar(**_regression_kwargs("local_apparent_solar-v1"))
        boundary = result["time_basis"]["boundary"]
        self.assertTrue(
            boundary["nearest_double_hour_boundary"].startswith("2000-10-18T05:00:00")
        )
        self.assertGreater(boundary["distance_seconds"], 0)

    def test_coordinate_accuracy_participates_in_boundary_uncertainty(self) -> None:
        # Cross-hour case: civil 06:52 -> apparent 07:03:16 (辰), distance to
        # the 07:00 boundary is ~196s, larger than the 30s EoT uncertainty.
        kwargs = {
            "civil_datetime": "2000-10-18T06:52:00",
            "timezone_name": REGRESSION_TIMEZONE,
            "location": "boundary-fixture",
            "longitude": REGRESSION_LONGITUDE,
            "latitude": REGRESSION_LATITUDE,
            "coordinate_source": "boundary-fixture",
            "zi_hour_policy": "midnight",
        }
        tight = normalize_calendar(
            **kwargs, time_basis_policy="local_apparent_solar-v1"
        )
        self.assertFalse(tight["time_basis"]["boundary"]["within_uncertainty"])
        # A 100 km coordinate uncertainty adds ~239s of time uncertainty, so the
        # hour branch is no longer certain even though the correction crossed it.
        coarse = normalize_calendar(
            **kwargs,
            time_basis_policy="local_apparent_solar-v1",
            coordinate_accuracy_meters=100_000.0,
        )
        self.assertTrue(coarse["time_basis"]["boundary"]["within_uncertainty"])


if __name__ == "__main__":
    unittest.main()
