from __future__ import annotations

import json
import unittest
from pathlib import Path

from reading_engine.ephemeris_core import calculate_ephemeris


ROOT = Path(__file__).resolve().parents[1]


class EphemerisCoreTests(unittest.TestCase):
    def test_pinned_engine_provenance_and_license_are_bound(self) -> None:
        result = calculate_ephemeris(
            "2000-01-01T12:00:00Z",
            longitude=0.0,
            latitude=0.0,
            coordinate_source="J2000 fixture",
        )

        self.assertEqual(result["schema_version"], "mingli-ephemeris-v1")
        self.assertEqual(
            result["engine"],
            {
                "name": "astronomy-engine",
                "version": "2.1.19",
                "license": "MIT",
                "provenance": "vendor/astronomy-engine-2.1.19/PROVENANCE.json",
                "distribution_sha256": "95b797b87b659adc0602a6a205143ce5a10451664e80650bb7cd8ba3c8f1f02b",
                "license_sha256": "b4d9dd0fd80fce3879c4cd9e3754364f74fc5ec046f33276475ba3876785c8b7",
                "data_files": [],
                "data_model": "versioned_coefficients_embedded_in_distribution",
            },
        )
        provenance = json.loads(
            (ROOT / result["engine"]["provenance"]).read_text(encoding="utf-8")
        )
        self.assertEqual(provenance["version"], result["engine"]["version"])

    def test_j2000_seven_luminary_longitudes_match_frozen_oracle(self) -> None:
        result = calculate_ephemeris(
            "2000-01-01T12:00:00Z",
            longitude=0.0,
            latitude=0.0,
            coordinate_source="J2000 fixture",
        )
        expected = {
            "Sun": 280.368738639819,
            "Moon": 223.323891127474,
            "Mercury": 271.888912066463,
            "Venus": 241.565232940362,
            "Mars": 327.963899077903,
            "Jupiter": 25.254199844874,
            "Saturn": 40.396124137178,
        }

        self.assertEqual(
            result["convention"]["frame"],
            "geocentric_true_ecliptic_of_date",
        )
        self.assertIs(result["convention"]["aberration"], True)
        actual = {
            body: item["longitude_degrees"]
            for body, item in result["positions"].items()
        }
        for body, longitude in expected.items():
            with self.subTest(body=body):
                self.assertAlmostEqual(actual[body], longitude, places=9)

    def test_ephemeris_digest_is_deterministic_and_observer_bound(self) -> None:
        arguments = {
            "instant": "2026-07-24T12:00:00+08:00",
            "longitude": 121.4737,
            "latitude": 31.2304,
            "coordinate_source": "user_measurement",
        }
        first = calculate_ephemeris(**arguments)
        second = calculate_ephemeris(**arguments)
        moved = calculate_ephemeris(**{**arguments, "longitude": 116.4074})

        self.assertEqual(first, second)
        self.assertEqual(first["instant_utc"], "2026-07-24T04:00:00+00:00")
        self.assertEqual(first["observer"]["coordinate_source"], "user_measurement")
        self.assertNotEqual(first["digest"], moved["digest"])
        self.assertEqual(len(first["digest"]), 64)


if __name__ == "__main__":
    unittest.main()
