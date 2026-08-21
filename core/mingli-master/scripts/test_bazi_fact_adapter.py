#!/usr/bin/env python3
"""Regression tests for deterministic Bazi fact generation."""

from __future__ import annotations

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

PARTIAL_TIMING_FIELDS = (
    "start_age_years",
    "end_age_years",
    "approximate_start_datetime",
    "boundary_term",
    "start_age_rule",
    "interval_days",
)


def run_adapter(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ADAPTER), *args],
        cwd=SKILL_DIR,
        text=True,
        capture_output=True,
        check=check,
        timeout=30,
    )


def _pillar_payload(*pillars: str, gender: str | None = None) -> dict:
    args = ["pillars", "--pillars", *pillars, "--source", "text"]
    if gender is not None:
        args.extend(["--gender", gender])
    return json.loads(run_adapter(*args).stdout)



class SuppliedPillarsTests(unittest.TestCase):
    def test_first_captured_screenshot_is_deterministically_derived(self) -> None:
        result = run_adapter(
            "pillars",
            "--pillars",
            "乙酉",
            "辛巳",
            "丙午",
            "癸巳",
            "--gender",
            "male",
            "--source",
            "image",
            "--source-ref",
            "attachment:synthetic-bazi-fixture",
        )
        payload = json.loads(result.stdout)

        self.assertEqual(payload["fact_layer_status"], "validated_user_provided_four_pillars")
        self.assertEqual(payload["fact_layer_scope"], "natal_static")
        self.assertEqual(payload["output"]["day_master"], {"stem": "丙", "element": "火", "polarity": "阳"})
        self.assertEqual(payload["output"]["four_pillars"]["month"], "辛巳")
        self.assertEqual(payload["output"]["hidden_stems"]["month"]["stems"], ["丙", "庚", "戊"])
        self.assertEqual(payload["output"]["ten_gods"]["heavenly_stems"]["year"]["ten_god"], "正印")
        self.assertEqual(payload["output"]["ten_gods"]["heavenly_stems"]["month"]["ten_god"], "正财")
        self.assertEqual(payload["output"]["ten_gods"]["heavenly_stems"]["hour"]["ten_god"], "正官")
        self.assertEqual(payload["output"]["month_command"]["branch"], "巳")
        self.assertIn("static_natal_interpretation", payload["capabilities"]["allowed"])
        self.assertIn("luck_cycle_timing", payload["capabilities"]["blocked"])
        self.assertTrue(adapter_validate.validate_payload("bazi", payload)["ok"])

    def test_second_captured_screenshot_gets_the_same_fact_gate(self) -> None:
        result = run_adapter(
            "pillars",
            "--pillars",
            "乙巳",
            "戊寅",
            "丁卯",
            "甲辰",
            "--gender",
            "male",
            "--source",
            "image",
        )
        payload = json.loads(result.stdout)

        self.assertEqual(payload["output"]["day_master"]["stem"], "丁")
        self.assertEqual(payload["output"]["ten_gods"]["heavenly_stems"]["year"]["ten_god"], "偏印")
        self.assertEqual(payload["output"]["ten_gods"]["heavenly_stems"]["month"]["ten_god"], "伤官")
        self.assertEqual(payload["output"]["ten_gods"]["heavenly_stems"]["hour"]["ten_god"], "正印")

    def test_shell_quoted_four_pillars_are_normalized_without_retry(self) -> None:
        result = run_adapter(
            "pillars",
            "--pillars",
            "乙巳 戊寅 丁卯 甲辰",
            "--source",
            "image",
        )
        payload = json.loads(result.stdout)

        self.assertEqual(
            payload["output"]["four_pillars"],
            {"year": "乙巳", "month": "戊寅", "day": "丁卯", "hour": "甲辰"},
        )

    def test_common_user_text_source_alias_does_not_break_the_runtime_call(self) -> None:
        result = run_adapter(
            "pillars",
            "--pillars",
            "乙酉",
            "辛巳",
            "丙午",
            "癸巳",
            "--source",
            "user_text",
        )
        payload = json.loads(result.stdout)

        self.assertEqual(payload["input"]["source"], "text")
        self.assertEqual(payload["fact_layer_status"], "validated_user_provided_four_pillars")

    def test_invalid_non_jiazi_pair_is_rejected(self) -> None:
        result = run_adapter(
            "pillars",
            "--pillars",
            "甲丑",
            "辛巳",
            "丙午",
            "癸巳",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid sexagenary pillar", result.stderr)


class SuppliedPillarsPartialLuckTests(unittest.TestCase):
    """Pillars plus gender determine direction and sequence, never timing."""

    def test_male_with_yin_year_stem_derives_reverse_sequence_only_luck(self) -> None:
        payload = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="male")
        luck = payload["output"]["luck_cycles"]

        self.assertEqual(luck["status"], "sequence_only")
        self.assertEqual(luck["direction"], "reverse")
        self.assertEqual(
            luck["direction_rule"],
            "阳年男/阴年女顺，阴年男/阳年女逆；阴阳取年干",
        )
        self.assertEqual(len(luck["cycles"]), 10)
        self.assertEqual(
            [cycle["pillar"] for cycle in luck["cycles"][:3]],
            ["庚辰", "己卯", "戊寅"],
        )
        for index, cycle in enumerate(luck["cycles"], start=1):
            self.assertEqual(set(cycle), {"sequence", "pillar"})
            self.assertEqual(cycle["sequence"], index)
        self.assertEqual(
            luck["unavailable"],
            [
                "start_age",
                "calendar_year_mapping",
                "active_cycle",
                "precise_timing",
            ],
        )
        self.assertIn("luck_cycle_timing", payload["capabilities"]["blocked"])
        self.assertIn("luck_cycle_sequence", payload["capabilities"]["allowed"])
        self.assertTrue(adapter_validate.validate_payload("bazi", payload)["ok"])

    def test_female_with_same_pillars_reverses_the_direction(self) -> None:
        payload = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="female")
        luck = payload["output"]["luck_cycles"]

        self.assertEqual(luck["status"], "sequence_only")
        self.assertEqual(luck["direction"], "forward")
        self.assertEqual(
            [cycle["pillar"] for cycle in luck["cycles"][:3]],
            ["壬午", "癸未", "甲申"],
        )
        self.assertTrue(adapter_validate.validate_payload("bazi", payload)["ok"])

    def test_missing_gender_keeps_static_facts_with_explicit_partial_status(self) -> None:
        payload = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳")
        luck = payload["output"]["luck_cycles"]

        self.assertEqual(luck["status"], "not_calculated_missing_gender")
        self.assertEqual(luck["cycles"], [])
        self.assertEqual(
            luck["unavailable"],
            [
                "direction",
                "sequence",
                "start_age",
                "calendar_year_mapping",
                "active_cycle",
                "precise_timing",
            ],
        )
        self.assertIsNone(payload["input"]["normalized_input"]["gender"])
        self.assertEqual(
            payload["fact_layer_status"],
            "validated_user_provided_four_pillars",
        )
        self.assertEqual(payload["output"]["day_master"]["stem"], "丙")
        self.assertIn(
            "static_natal_interpretation", payload["capabilities"]["allowed"]
        )
        self.assertNotIn(
            "luck_cycle_sequence", payload["capabilities"]["allowed"]
        )
        self.assertTrue(adapter_validate.validate_payload("bazi", payload)["ok"])

    def test_chinese_gender_token_derives_the_same_sequence(self) -> None:
        chinese = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="男")
        english = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="male")

        self.assertEqual(
            chinese["input"]["normalized_input"]["gender"], "male"
        )
        self.assertEqual(
            chinese["output"]["luck_cycles"], english["output"]["luck_cycles"]
        )

    def test_invalid_gender_is_still_rejected(self) -> None:
        result = run_adapter(
            "pillars",
            "--pillars",
            "乙酉",
            "辛巳",
            "丙午",
            "癸巳",
            "--gender",
            "unknown",
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported gender convention", result.stderr)

    def test_sequence_wraps_across_the_sexagenary_boundary(self) -> None:
        payload = _pillar_payload("癸亥", "癸亥", "甲子", "甲子", gender="female")
        luck = payload["output"]["luck_cycles"]

        self.assertEqual(luck["direction"], "forward")
        self.assertEqual(
            [cycle["pillar"] for cycle in luck["cycles"][:3]],
            ["甲子", "乙丑", "丙寅"],
        )

    def test_partial_luck_carries_no_timing_fields(self) -> None:
        payload = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="male")
        rendered = json.dumps(
            payload["output"]["luck_cycles"], ensure_ascii=False
        )

        for field in PARTIAL_TIMING_FIELDS:
            self.assertNotIn(field, rendered)

    def test_validator_rejects_partial_luck_with_fabricated_timing(self) -> None:
        payload = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="male")
        payload["output"]["luck_cycles"]["cycles"][0]["start_age_years"] = 3.0

        report = adapter_validate.validate_payload("bazi", payload)

        self.assertFalse(report["ok"])
        self.assertIn("bazi_partial_luck_fabricated_timing", report["codes"])

    def test_validator_rejects_missing_gender_payload_with_cycles(self) -> None:
        payload = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳")
        payload["output"]["luck_cycles"]["cycles"] = [
            {"sequence": 1, "pillar": "庚辰"}
        ]

        report = adapter_validate.validate_payload("bazi", payload)

        self.assertFalse(report["ok"])
        self.assertIn("bazi_partial_luck_invalid_shape", report["codes"])


class PartialLuckClosedSchemaTests(unittest.TestCase):
    """Supplied-pillars payloads must fail closed on any tampered shape."""

    @staticmethod
    def _mutated_partial(gender: str | None = "male") -> dict:
        return _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender=gender)

    def _assert_rejected(self, payload: dict, code: str) -> None:
        report = adapter_validate.validate_payload("bazi", payload)
        self.assertFalse(report["ok"], report)
        self.assertIn(code, report["codes"], report)

    def test_deleting_luck_cycles_is_rejected(self) -> None:
        payload = self._mutated_partial()
        del payload["output"]["luck_cycles"]
        self._assert_rejected(payload, "bazi_partial_luck_missing")

    def test_unknown_status_is_rejected(self) -> None:
        payload = self._mutated_partial()
        payload["output"]["luck_cycles"]["status"] = "bogus"
        self._assert_rejected(payload, "bazi_partial_luck_invalid_shape")

    def test_luck_status_rejects_non_text_values_without_crashing(self) -> None:
        for status in ({}, []):
            with self.subTest(status=status):
                payload = self._mutated_partial()
                payload["output"]["luck_cycles"]["status"] = status
                self._assert_rejected(payload, "bazi_partial_luck_invalid_shape")

    def test_supplied_mode_cannot_bypass_strict_validation_via_fact_status(self) -> None:
        for status in ("garbage", "calculated_natal_chart_from_birth_datetime", None):
            with self.subTest(status=status):
                payload = self._mutated_partial()
                payload["fact_layer_status"] = status
                self._assert_rejected(payload, "bazi_partial_luck_invalid_input")

    def test_partial_fact_status_requires_matching_input_mode_and_scope(self) -> None:
        for key, value in (
            ("mode", "birth_datetime"),
            ("fact_layer_scope", "natal_and_timing"),
        ):
            with self.subTest(key=key):
                payload = self._mutated_partial()
                if key == "mode":
                    payload["input"][key] = value
                else:
                    payload[key] = value
                self._assert_rejected(payload, "bazi_partial_luck_invalid_input")

    def test_disguised_calculated_with_start_ages_is_rejected(self) -> None:
        payload = self._mutated_partial()
        luck = payload["output"]["luck_cycles"]
        luck["status"] = "calculated"
        luck["cycles"][0]["start_age_years"] = 3.2
        self._assert_rejected(payload, "bazi_partial_luck_invalid_shape")

    def test_timing_capabilities_inside_partial_payload_are_rejected(self) -> None:
        for extra in ("calendar_year_mapping", "active_cycle", "precise_timing"):
            payload = self._mutated_partial()
            payload["output"]["luck_cycles"][extra] = "2031"
            self._assert_rejected(payload, "bazi_partial_luck_fabricated_timing")

    def test_extra_unavailable_entries_are_rejected(self) -> None:
        payload = self._mutated_partial()
        payload["output"]["luck_cycles"]["unavailable"].append("something_else")
        self._assert_rejected(payload, "bazi_partial_luck_invalid_shape")

    def test_unavailable_requires_unique_text_items(self) -> None:
        for extra in ({}, "start_age"):
            with self.subTest(extra=extra):
                payload = self._mutated_partial()
                payload["output"]["luck_cycles"]["unavailable"].append(extra)
                self._assert_rejected(payload, "bazi_partial_luck_invalid_shape")

    def test_wrong_first_step_pillar_is_rejected(self) -> None:
        payload = self._mutated_partial()
        payload["output"]["luck_cycles"]["cycles"][0]["pillar"] = "辛巳"
        self._assert_rejected(payload, "bazi_partial_luck_recompute_mismatch")

    def test_cycle_sequence_rejects_boolean_indexes(self) -> None:
        payload = self._mutated_partial()
        payload["output"]["luck_cycles"]["cycles"][0]["sequence"] = True
        self._assert_rejected(payload, "bazi_partial_luck_invalid_shape")

    def test_flipped_direction_is_rejected(self) -> None:
        payload = self._mutated_partial(gender="female")
        payload["output"]["luck_cycles"]["direction"] = "reverse"
        self._assert_rejected(payload, "bazi_partial_luck_recompute_mismatch")

    def test_invalid_normalized_gender_is_rejected(self) -> None:
        for gender in ("", "unknown", {}, []):
            with self.subTest(gender=gender):
                payload = self._mutated_partial()
                payload["input"]["normalized_input"]["gender"] = gender
                self._assert_rejected(payload, "bazi_partial_luck_invalid_input")

    def test_missing_or_incomplete_normalized_pillars_are_rejected(self) -> None:
        for pillars in ({}, {"year": "乙酉", "month": "辛巳"}):
            with self.subTest(pillars=pillars):
                payload = self._mutated_partial()
                payload["input"]["normalized_input"]["pillars"] = pillars
                self._assert_rejected(payload, "bazi_partial_luck_invalid_input")

    def test_invalid_normalized_jiazi_is_reported_instead_of_crashing(self) -> None:
        payload = self._mutated_partial()
        payload["input"]["normalized_input"]["pillars"]["year"] = "甲丑"
        self._assert_rejected(payload, "bazi_partial_luck_invalid_input")

    def test_output_pillars_must_match_the_normalized_input(self) -> None:
        payload = self._mutated_partial()
        payload["output"]["four_pillars"]["year"] = "甲申"
        self._assert_rejected(payload, "bazi_partial_luck_input_output_mismatch")

    def test_calendar_pillars_must_match_the_normalized_input(self) -> None:
        payload = self._mutated_partial()
        payload["input"]["normalized_input"]["pillars"]["year"] = "丁亥"
        payload["output"]["four_pillars"]["year"] = "丁亥"
        self._assert_rejected(payload, "bazi_partial_luck_input_output_mismatch")

    def test_genderless_luck_still_requires_an_explicit_cycles_field(self) -> None:
        payload = self._mutated_partial(gender=None)
        del payload["output"]["luck_cycles"]["cycles"]
        self._assert_rejected(payload, "bazi_partial_luck_invalid_shape")

    def test_genderless_cycles_must_be_an_explicit_empty_list(self) -> None:
        for cycles in (None, {}):
            with self.subTest(cycles=cycles):
                payload = self._mutated_partial(gender=None)
                payload["output"]["luck_cycles"]["cycles"] = cycles
                self._assert_rejected(payload, "bazi_partial_luck_invalid_shape")

    def test_missing_salience_signals_is_rejected(self) -> None:
        payload = self._mutated_partial()
        del payload["output"]["interpretive_candidates"]["salience_signals"]
        self._assert_rejected(payload, "bazi_missing_salience_signals")

    def test_salience_signal_with_confidence_is_rejected(self) -> None:
        for mutate, label in (
            (lambda item: item.update(confidence=0.99), "confidence"),
            (lambda item: item.update(probability=0.5), "probability"),
            (lambda item: item.update(score=7), "score"),
        ):
            payload = self._mutated_partial()
            mutate(payload["output"]["interpretive_candidates"]["salience_signals"][0])
            report = adapter_validate.validate_payload("bazi", payload)
            self.assertFalse(report["ok"], label)
            self.assertIn("bazi_invalid_salience_signal", report["codes"], label)

    def test_salience_signal_requires_its_complete_declared_shape(self) -> None:
        payload = self._mutated_partial()
        del payload["output"]["interpretive_candidates"]["salience_signals"][0][
            "hard_verdict"
        ]
        self._assert_rejected(payload, "bazi_invalid_salience_signal")

    def test_salience_basis_cannot_smuggle_score_or_verdict_metadata(self) -> None:
        for key, value in (("confidence", 0.99), ("hard_verdict", "final")):
            with self.subTest(key=key):
                payload = self._mutated_partial()
                signal = payload["output"]["interpretive_candidates"][
                    "salience_signals"
                ][0]
                signal["basis"][key] = value
                self._assert_rejected(payload, "bazi_invalid_salience_signal")

    def test_missing_gender_payload_with_cycles_is_rejected(self) -> None:
        payload = self._mutated_partial(gender=None)
        payload["output"]["luck_cycles"]["cycles"] = [
            {"sequence": 1, "pillar": "庚辰"}
        ]
        self._assert_rejected(payload, "bazi_partial_luck_invalid_shape")

    def test_capability_state_must_match_partial_scope(self) -> None:
        with_timing_unblocked = self._mutated_partial()
        with_timing_unblocked["capabilities"]["blocked"].remove(
            "luck_cycle_timing"
        )
        self._assert_rejected(
            with_timing_unblocked, "bazi_partial_luck_capability_mismatch"
        )

        without_sequence = self._mutated_partial()
        without_sequence["capabilities"]["allowed"].remove(
            "luck_cycle_sequence"
        )
        self._assert_rejected(
            without_sequence, "bazi_partial_luck_capability_mismatch"
        )

        no_gender_with_sequence = self._mutated_partial(gender=None)
        no_gender_with_sequence["capabilities"]["allowed"].append(
            "luck_cycle_sequence"
        )
        self._assert_rejected(
            no_gender_with_sequence, "bazi_partial_luck_capability_mismatch"
        )

    def test_capability_cannot_be_allowed_and_blocked_at_once(self) -> None:
        payload = self._mutated_partial()
        payload["capabilities"]["blocked"].append("static_natal_interpretation")
        self._assert_rejected(payload, "bazi_partial_luck_capability_mismatch")

    def test_capabilities_require_unique_text_items(self) -> None:
        for key, extra in (
            ("allowed", {}),
            ("blocked", {}),
            ("allowed", "static_natal_interpretation"),
        ):
            with self.subTest(key=key, extra=extra):
                payload = self._mutated_partial()
                payload["capabilities"][key].append(extra)
                self._assert_rejected(
                    payload, "bazi_partial_luck_capability_mismatch"
                )

    def test_blocked_capabilities_must_match_the_declared_partial_scope(self) -> None:
        missing = self._mutated_partial()
        missing["capabilities"]["blocked"].remove(
            "birth_calendar_verification"
        )
        self._assert_rejected(
            missing, "bazi_partial_luck_capability_mismatch"
        )

        extra = self._mutated_partial()
        extra["capabilities"]["blocked"].append("bogus")
        self._assert_rejected(extra, "bazi_partial_luck_capability_mismatch")


class SuppliedPillarsSalienceTests(unittest.TestCase):
    """Provider-owned mechanical salience candidates, never verdicts."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.chart_a = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="male")
        cls.chart_b = _pillar_payload("甲子", "甲子", "甲子", "甲子", gender="male")
        cls.chart_c = _pillar_payload("庚申", "戊子", "丙辰", "壬辰", gender="female")

    @staticmethod
    def _signals(payload: dict) -> list[dict]:
        return payload["output"]["interpretive_candidates"]["salience_signals"]

    def test_distinct_charts_produce_distinct_deterministic_signals(self) -> None:
        first = self._signals(self.chart_a)
        second = self._signals(self.chart_b)
        third = self._signals(self.chart_c)

        self.assertTrue(first and second and third)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertNotEqual(second, third)
        for signals in (first, second, third):
            ids = [item["signal_id"] for item in signals]
            self.assertEqual(len(ids), len(set(ids)))
        replay = _pillar_payload("乙酉", "辛巳", "丙午", "癸巳", gender="male")
        self.assertEqual(first, self._signals(replay))

    def test_repetition_relations_and_anchors_are_recognized(self) -> None:
        by_id_a = {
            item["signal_id"]: item for item in self._signals(self.chart_a)
        }
        repeated = by_id_a["bazi.salience.repeated-branch:巳"]
        self.assertEqual(repeated["basis"]["positions"], ["month", "hour"])
        combination = by_id_a["bazi.salience.stem-combination:丙辛:month"]
        self.assertEqual(
            combination["basis"]["status"],
            "combination_present_conditions_unadjudicated",
        )
        anchor = by_id_a["bazi.salience.seasonal-anchor:巳"]
        self.assertEqual(anchor["basis"]["day_stem"], "丙")
        self.assertEqual(anchor["basis"]["season"], "初夏")

        ids_c = {item["signal_id"] for item in self._signals(self.chart_c)}
        self.assertIn("bazi.salience.branch-relation:三合:申子辰", ids_c)
        self.assertIn("bazi.salience.repeated-branch:辰", ids_c)

        transparent = _pillar_payload(
            "甲寅", "丙寅", "戊午", "甲寅", gender="male"
        )
        by_id_d = {
            item["signal_id"]: item for item in self._signals(transparent)
        }
        exposed = by_id_d["bazi.salience.month-qi-transparent:甲"]
        self.assertEqual(exposed["basis"]["visible_positions"], ["year", "hour"])

    def test_signals_stay_mechanical_without_scores_or_verdicts(self) -> None:
        for payload in (self.chart_a, self.chart_b, self.chart_c):
            signals = self._signals(payload)
            for item in signals:
                self.assertEqual(item["status"], "mechanical_candidate")
                self.assertIsNone(item["hard_verdict"])
                self.assertIsInstance(item["basis"], dict)
                self.assertTrue(item["basis"])
                self.assertTrue(str(item["boundary"]).strip())
            rendered = json.dumps(signals, ensure_ascii=False).casefold()
            for banned in ("score", "probability", "confidence", "percent", "%"):
                self.assertNotIn(banned, rendered)

    def test_validator_rejects_illegal_salience_signals(self) -> None:
        for mutate, label in (
            (lambda item: item.update(hard_verdict="身强"), "verdict"),
            (lambda item: item.update(basis={}), "empty basis"),
            (lambda item: item.update(status="final_judgment"), "status"),
        ):
            payload = json.loads(json.dumps(self.chart_a))
            mutate(payload["output"]["interpretive_candidates"]["salience_signals"][0])
            report = adapter_validate.validate_payload("bazi", payload)
            self.assertFalse(report["ok"], label)
            self.assertIn("bazi_invalid_salience_signal", report["codes"], label)

        duplicated = json.loads(json.dumps(self.chart_a))
        signals = duplicated["output"]["interpretive_candidates"]["salience_signals"]
        signals.append(json.loads(json.dumps(signals[0])))
        report = adapter_validate.validate_payload("bazi", duplicated)
        self.assertFalse(report["ok"])
        self.assertIn("bazi_invalid_salience_signal", report["codes"])

    def test_full_birth_payload_exposes_the_same_signal_families(self) -> None:
        result = run_adapter(
            "birth",
            "--datetime",
            "2000-10-18T06:45:00",
            "--timezone",
            "Asia/Shanghai",
            "--location",
            "合成测试地点",
            "--gender",
            "male",
        )
        payload = json.loads(result.stdout)
        signals = self._signals(payload)

        self.assertTrue(signals)
        self.assertTrue(
            any(
                item["signal_id"].startswith("bazi.salience.seasonal-anchor:")
                for item in signals
            )
        )
        self.assertTrue(adapter_validate.validate_payload("bazi", payload)["ok"])


class BirthCalculationTests(unittest.TestCase):
    def test_birth_datetime_is_converted_to_lunar_calendar_and_four_pillars(self) -> None:
        result = run_adapter(
            "birth",
            "--datetime",
            "2000-10-18T06:45:00",
            "--timezone",
            "Asia/Shanghai",
            "--location",
            "合成测试地点",
            "--gender",
            "male",
        )
        payload = json.loads(result.stdout)

        self.assertEqual(payload["fact_layer_status"], "calculated_natal_chart_from_birth_datetime")
        self.assertEqual(
            payload["output"]["four_pillars"],
            {"year": "庚辰", "month": "丙戌", "day": "己酉", "hour": "丁卯"},
        )
        self.assertEqual(payload["calendar_normalization"]["lunar_date"]["month"], 9)
        self.assertEqual(payload["calendar_normalization"]["lunar_date"]["day"], 21)
        self.assertEqual(payload["calendar_normalization"]["lunar_date"]["is_leap_month"], False)
        self.assertEqual(payload["output"]["luck_cycles"]["direction"], "forward")
        self.assertGreaterEqual(len(payload["output"]["luck_cycles"]["cycles"]), 8)
        self.assertIn(
            "start_age_years", payload["output"]["luck_cycles"]["cycles"][0]
        )
        self.assertTrue(adapter_validate.validate_payload("bazi", payload)["ok"])

    def test_birth_calculation_detects_conflict_with_screenshot_pillars(self) -> None:
        result = run_adapter(
            "birth",
            "--datetime",
            "2000-10-18T06:45:00",
            "--timezone",
            "Asia/Shanghai",
            "--location",
            "合成测试地点",
            "--gender",
            "male",
            "--expected-pillars",
            "乙酉",
            "辛巳",
            "丙午",
            "癸巳",
            check=False,
        )
        payload = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(payload["fact_layer_status"], "conflict_birth_data_vs_supplied_pillars")
        self.assertTrue(payload["conflicts"])

    def test_non_china_east_asia_timezone_is_preserved_and_calculated(self) -> None:
        result = run_adapter(
            "birth",
            "--datetime",
            "1983-04-21T06:30:00+09:00",
            "--timezone",
            "Asia/Tokyo",
            "--location",
            "日本宫崎县",
            "--gender",
            "male",
        )
        payload = json.loads(result.stdout)

        self.assertEqual(payload["input"]["timezone"], "Asia/Tokyo")
        self.assertEqual(payload["calendar_normalization"]["timezone"], "Asia/Tokyo")
        self.assertTrue(
            payload["calendar_normalization"]["civil_datetime"].endswith("+09:00")
        )
        self.assertEqual(set(payload["output"]["four_pillars"]), {"year", "month", "day", "hour"})
        self.assertTrue(adapter_validate.validate_payload("bazi", payload)["ok"])


if __name__ == "__main__":
    unittest.main()
