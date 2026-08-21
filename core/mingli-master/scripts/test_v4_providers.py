"""V4 calculation-provider regressions independent of retired semantic gates."""

from __future__ import annotations

from pathlib import Path
import unittest

from reading_engine.contracts import ReadingRequest
from reading_engine.providers import (
    BaziProvider,
    PhysiognomyProvider,
    STRUCTURED_SYSTEMS,
    StructuredChartProvider,
    _resolved_profile,
)
from test_v51_physiognomy_completion import _request as physiognomy_request


ROOT = Path(__file__).resolve().parents[1]


class V4BaziProviderCompatibilityTests(unittest.TestCase):
    def test_supplied_pillars_do_not_require_coordinate_accuracy(self) -> None:
        result = BaziProvider(ROOT).calculate(
            ReadingRequest(
                query="看命盘",
                action="new",
                system="bazi",
                timezone="Asia/Shanghai",
                location="fixture",
                birth_data={"gender": "male"},
                chart_data={"pillars": ["庚辰", "丙戌", "己酉", "丁卯"]},
            )
        )
        self.assertEqual(result.system, "bazi")


class V4FortuneProviderTests(unittest.TestCase):
    def test_top_level_birth_place_and_timezone_complete_supplied_identity(self) -> None:
        request = ReadingRequest(
            query="看指定日期的日运",
            action="new",
            system="fortune",
            timezone="Asia/Shanghai",
            location="上海",
            birth_data={
                "birth_datetime": "1990-01-01T12:00:00",
                "gender": "female",
            },
        )

        profile = _resolved_profile(request, {})

        self.assertEqual(profile["birth_datetime"], "1990-01-01T12:00:00")
        self.assertEqual(profile["timezone"], "Asia/Shanghai")
        self.assertEqual(profile["location"], "上海")
        self.assertEqual(profile["gender"], "female")


class V4DedicatedPhysiognomyProviderTests(unittest.TestCase):
    def test_generic_structured_provider_cannot_serve_physiognomy(self) -> None:
        self.assertNotIn("physiognomy", STRUCTURED_SYSTEMS)
        with self.assertRaisesRegex(ValueError, "unsupported structured route"):
            StructuredChartProvider(ROOT, "physiognomy")

    def test_observation_provider_cannot_extrapolate_a_requested_period(self) -> None:
        provider = PhysiognomyProvider(ROOT)
        result = provider.calculate(physiognomy_request())

        extended = provider.extend(
            result,
            ("timing",),
            {"kind": "day", "start": "2026-07-24", "end": "2026-07-24"},
        )

        self.assertEqual(extended.fact_extension.status, "unsupported")
        self.assertEqual(extended.result_hash, result.result_hash)


if __name__ == "__main__":
    unittest.main()
