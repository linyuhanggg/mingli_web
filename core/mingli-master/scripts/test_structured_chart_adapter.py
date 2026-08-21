#!/usr/bin/env python3
"""Regression tests for complete user-provided Mingli chart validation."""

from __future__ import annotations

import unittest
from copy import deepcopy

import adapter_validate
import structured_chart_adapter


def calendar() -> dict:
    return {
        "status": "user_provided_not_recalculated",
        "civil_datetime": "2026-07-10T20:00:00+08:00",
        "lunar_date": {"year": 2026, "month": 5, "day": 26, "leap_month": False},
        "ganzhi": {"year": "丙午", "month": "乙未", "day": "乙酉", "hour": "丙戌"},
        "solar_terms": {"previous": "小暑", "next": "大暑"},
    }


def source(output: dict, *, subsystem: str | None = None, timed: bool = True) -> dict:
    value = {
        "provenance": {
            "source_type": "user_text",
            "calculation_status": "not_recalculated",
            "raw_excerpt": "用户提供的完整盘面",
            "uncertainties": [],
        },
        "calendar_normalization": calendar() if timed else {
            "status": "not_applicable",
            "reason": "non_time_observation",
        },
        "output": output,
    }
    if subsystem:
        value["subsystem"] = subsystem
    return value


VALID_CASES = {
    "ziwei": source({
        "palaces": [{"name": "命宫", "branch": "子"}],
        "ming_shen": {"ming": "子", "shen": "寅"},
        "stars": [{"name": "紫微", "palace": "命宫"}],
        "sihua": {"化禄": "廉贞", "化权": "破军", "化科": "武曲", "化忌": "太阳"},
        "major_limits": [{"age_start": 2, "age_end": 11, "palace": "命宫"}],
    }),
    "xingming": source({
        "ephemeris": {"name": "user-supplied", "version": "unknown"},
        "positions": [{"body": "日", "longitude": 120.5}],
        "houses": [{"name": "命宫", "start_degree": 90.0}],
    }),
    "divination/liuyao": source({
        "hexagram": "地天泰",
        "primary_hexagram": "地天泰",
        "changed_hexagram": "地泽临",
        "moving_lines": [3],
        "shi_ying": {"shi": 3, "ying": 6},
        "six_relatives": ["兄弟", "子孙", "妻财", "官鬼", "父母", "兄弟"],
        "six_spirits": ["青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武"],
        "najia": ["甲子", "甲寅", "甲辰", "癸丑", "癸亥", "癸酉"],
        "casting_method": "user_provided_coins",
    }, subsystem="liuyao"),
    "divination/meihua": source({
        "hexagram": "地雷复",
        "primary_hexagram": "地雷复",
        "mutual_hexagram": "坤为地",
        "changed_hexagram": "地泽临",
        "moving_lines": [2],
        "body_use": {"body": "坤", "use": "震"},
        "casting_method": "user_provided_time_method",
    }, subsystem="meihua"),
    "taiyi": source({
        "taiyi_plate": {"scope": "year"},
        "ju": "阳遁一局",
        "taiyi_position": "乾宫",
        "host_guest_counts": {"host": 7, "guest": 3},
    }),
}


class StructuredChartAdapterTests(unittest.TestCase):
    def test_accepts_complete_user_provided_profiles_without_claiming_recalculation(self) -> None:
        for route, raw in VALID_CASES.items():
            with self.subTest(route=route):
                payload = structured_chart_adapter.build_payload(route, deepcopy(raw))
                system = route.split("/", 1)[0]
                self.assertEqual(payload["fact_layer_status"], "validated_user_provided_chart")
                self.assertEqual(payload["fact_layer_scope"], "supplied_facts_only")
                self.assertEqual(payload["adapter"]["name"], "mingli-master.structured_chart_adapter")
                self.assertEqual(payload["adapter"]["rule_profile"], "user-provided-no-recalculation")
                self.assertEqual(payload["input"]["provenance"]["calculation_status"], "not_recalculated")
                result = adapter_validate.validate_payload(system, payload)
                self.assertTrue(result["ok"], result)

    def test_rejects_incomplete_required_output(self) -> None:
        raw = deepcopy(VALID_CASES["taiyi"])
        del raw["output"]["host_guest_counts"]

        with self.assertRaisesRegex(ValueError, "missing_output:host_guest_counts"):
            structured_chart_adapter.build_payload("taiyi", raw)

    def test_rejects_scalar_garbage_in_every_tier_b_output_schema(self) -> None:
        for route, valid in VALID_CASES.items():
            with self.subTest(route=route):
                raw = deepcopy(valid)
                raw["output"] = {key: 1 for key in raw["output"]}
                with self.assertRaisesRegex(ValueError, "invalid_output"):
                    structured_chart_adapter.build_payload(route, raw)

    def test_rejects_nested_garbage_in_every_tier_b_output_schema(self) -> None:
        mutations = {
            "ziwei": lambda output: output["palaces"].__setitem__(0, {"name": 7, "branch": []}),
            "xingming": lambda output: output["positions"].__setitem__(0, {"body": {}, "longitude": "east"}),
            "divination/liuyao": lambda output: output.__setitem__("shi_ying", {"shi": "third", "ying": []}),
            "divination/meihua": lambda output: output.__setitem__("body_use", {"body": {}, "use": 8}),
            "taiyi": lambda output: output.__setitem__("host_guest_counts", {"host": "seven", "guest": []}),
        }
        for route, mutate in mutations.items():
            with self.subTest(route=route):
                raw = deepcopy(VALID_CASES[route])
                mutate(raw["output"])
                with self.assertRaisesRegex(ValueError, "invalid_output"):
                    structured_chart_adapter.build_payload(route, raw)

    def test_every_individual_tier_b_output_field_fails_closed_on_a_scalar(self) -> None:
        for route, valid in VALID_CASES.items():
            for field in valid["output"]:
                with self.subTest(route=route, field=field):
                    raw = deepcopy(valid)
                    raw["output"][field] = (
                        "not-a-number" if field == "facing_degrees" else 1
                    )
                    with self.assertRaisesRegex(ValueError, "invalid_output"):
                        structured_chart_adapter.build_payload(route, raw)

    def test_rejects_model_generated_or_recalculated_provenance_claims(self) -> None:
        generated = deepcopy(VALID_CASES["ziwei"])
        generated["provenance"]["source_type"] = "model_generated"
        with self.assertRaisesRegex(ValueError, "source_type"):
            structured_chart_adapter.build_payload("ziwei", generated)

        claimed = deepcopy(VALID_CASES["ziwei"])
        claimed["provenance"]["calculation_status"] = "calculated"
        with self.assertRaisesRegex(ValueError, "not_recalculated"):
            structured_chart_adapter.build_payload("ziwei", claimed)

    def test_calculation_routes_must_use_their_real_adapters(self) -> None:
        for system in (
            "bazi",
            "fengshui",
            "liuren",
            "fortune",
            "physiognomy",
            "qimen",
            "selection",
        ):
            with self.subTest(system=system):
                with self.assertRaisesRegex(ValueError, "dedicated deterministic adapter"):
                    structured_chart_adapter.build_payload(
                        system,
                        source({"placeholder": True}),
                    )

    def test_generic_validator_rejects_legacy_fengshui_chart_payload(self) -> None:
        payload = {
            "fact_layer_status": "validated_user_provided_chart",
            "adapter": {
                "name": "mingli-master.structured_chart_adapter",
                "version": "1.0.0",
                "rule_profile": "user-provided-no-recalculation",
            },
            "calendar_normalization": {
                "status": "not_applicable",
                "reason": "legacy observation",
            },
            "output": {
                "facing_degrees": 182.5,
                "period": "九运",
                "layout": {"door": "南"},
                "school_variables": {"school": "玄空"},
            },
        }

        report = adapter_validate.validate_payload("fengshui", payload)

        self.assertFalse(report["ok"])
        self.assertIn("fengshui_dedicated_provider_required", report["codes"])

    def test_generic_validator_rejects_legacy_physiognomy_chart_payload(self) -> None:
        payload = {
            "fact_layer_status": "validated_user_provided_chart",
            "adapter": {
                "name": "mingli-master.structured_chart_adapter",
                "version": "1.0.0",
                "rule_profile": "user-provided-no-recalculation",
            },
            "calendar_normalization": {
                "status": "not_applicable",
                "reason": "legacy observation",
            },
            "output": {
                "observation_source": "user_provided_front_photo",
                "observed_features": ["额部较宽"],
                "uncertainty": ["光线可能改变肤色观感"],
            },
        }

        report = adapter_validate.validate_payload("physiognomy", payload)

        self.assertFalse(report["ok"])
        self.assertIn("physiognomy_dedicated_provider_required", report["codes"])

    def test_rejects_missing_calendar_for_time_based_system(self) -> None:
        raw = deepcopy(VALID_CASES["taiyi"])
        raw["calendar_normalization"] = {"status": "not_applicable"}

        with self.assertRaisesRegex(ValueError, "missing_calendar"):
            structured_chart_adapter.build_payload("taiyi", raw)

    def test_image_transcription_keeps_uncertainty_and_never_upgrades_scope(self) -> None:
        raw = deepcopy(VALID_CASES["divination/meihua"])
        raw["provenance"] = {
            "source_type": "image_transcription",
            "calculation_status": "not_recalculated",
            "raw_excerpt": "截图显示地雷复二爻动变地泽临",
            "uncertainties": ["互卦字号较小"],
        }

        payload = structured_chart_adapter.build_payload("divination/meihua", raw)

        self.assertEqual(payload["fact_layer_scope"], "supplied_facts_only")
        self.assertEqual(payload["input"]["provenance"]["source_type"], "image_transcription")
        self.assertEqual(payload["warnings"], ["互卦字号较小"])


if __name__ == "__main__":
    unittest.main()
