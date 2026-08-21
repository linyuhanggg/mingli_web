#!/usr/bin/env python3
"""Regression tests for the deterministic Da Liu Ren fact adapter."""

from __future__ import annotations

import json
import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import adapter_validate  # noqa: E402
import audit_algorithm_sources  # noqa: E402
import audit_liuren_provider  # noqa: E402
import liuren_fact_adapter as liuren  # noqa: E402
from reading_engine import calendar_core  # noqa: E402


class LiurenFactAdapterTests(unittest.TestCase):
    def test_runtime_and_subprocess_pin_the_current_source_table(self):
        digest = audit_liuren_provider._sha256(audit_liuren_provider.SOURCE_TABLE)
        self.assertEqual(liuren.SOURCE_TABLE_SHA256, digest)
        self.assertEqual(audit_liuren_provider.liuren_calc.LIUREN_SOURCE_TABLE_SHA256, digest)

    def test_month_general_audit_uses_an_independent_fixed_oracle(self):
        source_table = yaml.safe_load(
            audit_liuren_provider.SOURCE_TABLE.read_text(encoding="utf-8")
        )
        algorithm_matrix = yaml.safe_load(
            audit_liuren_provider.MATRIX.read_text(encoding="utf-8")
        )
        research_root = audit_algorithm_sources._research_root(
            algorithm_matrix,
            audit_liuren_provider.ROOT,
        )
        self.assertIsNotNone(research_root)
        self.assertTrue(
            audit_liuren_provider._month_general_oracle_ready(
                source_table=source_table,
                research_root=research_root,
            )
        )
        with mock.patch.dict(
            liuren.TERM_TO_MONTH_GENERAL,
            {"雨水": "子"},
        ):
            self.assertFalse(
                audit_liuren_provider._month_general_oracle_ready(
                    source_table=source_table,
                    research_root=research_root,
                )
            )

        mapping = source_table["month_general_solar_term_mapping"]["terms"]
        self.assertEqual(set(mapping), set(audit_liuren_provider.EXPECTED_TERM_TO_MONTH_GENERAL))
        for term, expected_general in mapping.items():
            with self.subTest(term=term):
                mutated = copy.deepcopy(source_table)
                mutated["month_general_solar_term_mapping"]["terms"][term] = (
                    "子" if expected_general != "子" else "丑"
                )
                self.assertFalse(
                    audit_liuren_provider._month_general_oracle_ready(
                        source_table=mutated,
                        research_root=research_root,
                    )
                )

        transitions = source_table["month_general_solar_term_mapping"][
            "source_transitions"
        ]
        self.assertEqual(
            set(transitions),
            {
                transition[0]
                for transition in audit_liuren_provider.EXPECTED_MONTH_GENERAL_TRANSITIONS
            },
        )
        for term in transitions:
            with self.subTest(source_transition=term):
                mutated = copy.deepcopy(source_table)
                mutated["month_general_solar_term_mapping"]["source_transitions"][
                    term
                ] += "伪"
                self.assertFalse(
                    audit_liuren_provider._month_general_oracle_ready(
                        source_table=mutated,
                        research_root=research_root,
                    )
                )

    def _chart(self, **overrides):
        kwargs = {
            "day_ganzhi": "己未",
            "hour_ganzhi": "庚午",
            "month_general": "亥",
            "question": "这次合作能否在约定日期前签定正式合同？",
            "location": "中国上海",
            "guiren_profile": "official-corrected",
            "day_night_profile": "civil-double-hour",
        }
        kwargs.update(overrides)
        return liuren.build_from_chart(**kwargs)

    def test_classical_jwei_fixture_has_biyong_transmissions(self):
        payload = self._chart()

        self.assertEqual(payload["output"]["month_general"]["branch"], "亥")
        self.assertEqual(
            [(item["upper"], item["lower"]) for item in payload["output"]["four_lessons"]],
            [("子", "己"), ("巳", "子"), ("子", "未"), ("巳", "子")],
        )
        self.assertEqual(
            [item["branch"] for item in payload["output"]["three_transmissions"]],
            list("巳戌卯"),
        )
        self.assertEqual(payload["output"]["transmission_method"]["primary"], "比用")
        self.assertNotIn("反吟", payload["output"]["structural_patterns"])
        self.assertTrue(adapter_validate.validate_payload("liuren", payload)["ok"])

    def test_impossible_hour_stem_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "incompatible hour pillar"):
            self._chart(hour_ganzhi="甲午")

    def test_datetime_calendar_hour_policy_is_structured_and_validator_safe(self):
        for zi_hour_policy in ("midnight", "late-zi-next-day"):
            with self.subTest(zi_hour_policy=zi_hour_policy):
                payload = liuren.build_from_datetime(
                    "2024-01-15T23:30:00",
                    timezone_name="Asia/Shanghai",
                    location="上海",
                    question="边界核验",
                    zi_hour_policy=zi_hour_policy,
                )
                self.assertEqual(
                    payload["adapter"]["rule_profile"]["hour_stem_validation"],
                    "five-rat-strict",
                )
                expected = (
                    {"day": "戊寅", "hour": "壬子"}
                    if zi_hour_policy == "midnight"
                    else {"day": "己卯", "hour": "甲子"}
                )
                self.assertEqual(payload["output"]["day_hour"], expected)
                self.assertTrue(
                    adapter_validate.validate_payload("liuren", payload)["ok"]
                )

    def test_validator_rejects_hour_policy_downgrade_tampering(self):
        payload = copy.deepcopy(self._chart())
        payload["adapter"]["rule_profile"]["hour_stem_validation"] = (
            "shared-calendar-authoritative"
        )
        payload["output"]["day_hour"]["hour"] = "甲午"
        payload["input"]["normalized_chart_input"]["hour"] = "甲午"
        payload["calendar_normalization"]["ganzhi"]["hour"] = "甲午"

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_missing_hour_stem_validation", result["codes"])

    def test_validator_rejects_a_valid_but_foreign_calendar_block(self):
        late = liuren.build_from_datetime(
            "2024-01-15T23:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            question="边界核验",
            zi_hour_policy="late-zi-next-day",
        )
        midnight = liuren.build_from_datetime(
            "2024-01-15T23:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            question="边界核验",
            zi_hour_policy="midnight",
        )
        late["calendar_normalization"] = copy.deepcopy(
            midnight["calendar_normalization"]
        )

        result = adapter_validate.validate_payload("liuren", late)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_calendar_output_mismatch", result["codes"])

    def test_validator_rejects_input_policy_that_disagrees_with_calendar(self):
        payload = liuren.build_from_datetime(
            "2024-01-15T23:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            question="边界核验",
            zi_hour_policy="late-zi-next-day",
        )
        payload["input"]["zi_hour_policy"] = "midnight"

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_calendar_input_policy_mismatch", result["codes"])

    def test_validator_rejects_non_calculated_calendar_status(self):
        payload = liuren.build_from_datetime(
            "2024-01-15T23:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            question="边界核验",
            zi_hour_policy="midnight",
        )
        payload["calendar_normalization"]["status"] = "forged"

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_calendar_status_mismatch", result["codes"])

    def test_validator_cannot_disable_calendar_closure_with_status_tampering(self):
        payload = liuren.build_from_datetime(
            "2024-01-15T23:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            question="边界核验",
            zi_hour_policy="midnight",
        )
        payload["calendar_normalization"]["status"] = "forged"
        payload["calendar_normalization"]["ganzhi"].update(
            {"day": "甲子", "hour": "甲子"}
        )
        payload["input"]["normalized_chart_input"].update(
            {"day": "甲子", "hour": "甲子"}
        )

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_calendar_status_mismatch", result["codes"])

    def test_validator_rejects_supplied_chart_input_output_tampering(self):
        payload = copy.deepcopy(self._chart())
        payload["input"]["normalized_chart_input"].update(
            {"day": "甲子", "hour": "甲子", "month_general": "子"}
        )

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_input_output_mismatch", result["codes"])

    def test_validator_rejects_datetime_payload_masquerading_as_supplied_chart(self):
        payload = liuren.build_from_datetime(
            "2024-01-15T23:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            question="边界核验",
            zi_hour_policy="midnight",
        )
        for key in (
            "civil_datetime",
            "timezone",
            "zi_hour_policy",
            "longitude",
            "latitude",
            "coordinate_source",
        ):
            payload["input"].pop(key, None)
        payload["calendar_normalization"]["status"] = "supplied_chart_inputs"
        payload["calendar_normalization"]["ganzhi"].update(
            {"day": "甲子", "hour": "甲子"}
        )
        payload["input"]["normalized_chart_input"].update(
            {"day": "甲子", "hour": "甲子"}
        )

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_input_output_mismatch", result["codes"])

    def test_validator_rejects_facts_injected_into_supplied_calendar_sentinels(self):
        mutations = {
            "lunar-status": lambda calendar: calendar["lunar_date"].update(
                {"status": "calculated"}
            ),
            "solar-term-status": lambda calendar: calendar["solar_terms"].update(
                {"status": "calculated"}
            ),
            "extra-year-pillar": lambda calendar: calendar["ganzhi"].update(
                {"year": "甲子"}
            ),
            "extra-timezone": lambda calendar: calendar.update(
                {"timezone": "UTC"}
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                payload = copy.deepcopy(self._chart())
                mutate(payload["calendar_normalization"])

                result = adapter_validate.validate_payload("liuren", payload)

                self.assertFalse(result["ok"])
                self.assertIn(
                    "liuren_supplied_calendar_mismatch", result["codes"]
                )

    def test_validator_rejects_calendar_datetime_context_tampering(self):
        payload = liuren.build_from_datetime(
            "2024-01-15T23:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            question="边界核验",
            zi_hour_policy="midnight",
            longitude=121.47,
            latitude=31.23,
            coordinate_source="test-fixture",
        )
        payload["input"]["civil_datetime"] = "2030-05-01T10:00:00"
        payload["input"]["longitude"] = 120.0

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_calendar_input_context_mismatch", result["codes"])

    def test_validator_rejects_a_valid_foreign_time_basis_calendar(self):
        civil_datetime = "2024-01-15T12:30:00"
        payload = liuren.build_from_datetime(
            civil_datetime,
            timezone_name="Asia/Shanghai",
            location="上海",
            question="边界核验",
            zi_hour_policy="midnight",
            longitude=121.47,
            latitude=31.23,
            coordinate_source="test-fixture",
        )
        foreign_calendar = calendar_core.normalize_calendar(
            civil_datetime,
            timezone_name="Asia/Shanghai",
            location="上海",
            longitude=121.47,
            latitude=31.23,
            coordinate_source="test-fixture",
            zi_hour_policy="midnight",
            time_basis_policy="longitude_mean_solar-v1",
        )
        self.assertEqual(
            foreign_calendar["ganzhi"]["day"],
            payload["output"]["day_hour"]["day"],
        )
        self.assertEqual(
            foreign_calendar["ganzhi"]["hour"],
            payload["output"]["day_hour"]["hour"],
        )
        payload["calendar_normalization"] = foreign_calendar

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_calendar_input_digest_mismatch", result["codes"])

    def test_validator_rejects_calendar_valid_chart_with_wrong_month_general(self):
        original = liuren.build_from_datetime(
            "2024-01-15T12:30:00",
            timezone_name="Asia/Shanghai",
            location="上海",
            question="边界核验",
            zi_hour_policy="midnight",
            longitude=121.47,
            latitude=31.23,
            coordinate_source="test-fixture",
        )
        actual_general = original["output"]["month_general"]["branch"]
        wrong_general = "子" if actual_general != "子" else "丑"
        forged = liuren.build_from_chart(
            day_ganzhi=original["output"]["day_hour"]["day"],
            hour_ganzhi=original["output"]["day_hour"]["hour"],
            month_general=wrong_general,
            question="边界核验",
            location="上海",
        )
        for field in (
            "civil_datetime",
            "timezone",
            "zi_hour_policy",
            "longitude",
            "latitude",
            "coordinate_source",
        ):
            forged["input"][field] = original["input"][field]
        forged["calendar_normalization"] = copy.deepcopy(
            original["calendar_normalization"]
        )

        result = adapter_validate.validate_payload("liuren", forged)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_calendar_month_general_mismatch", result["codes"])

    def test_datetime_location_whitespace_is_canonicalized_once(self):
        payload = liuren.build_from_datetime(
            "2024-01-15T12:30:00",
            timezone_name="Asia/Shanghai",
            location=" 上海 ",
            question="边界核验",
            zi_hour_policy="midnight",
        )

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertTrue(result["ok"], result)
        self.assertEqual(payload["input"]["location"], "上海")
        self.assertEqual(
            payload["calendar_normalization"]["location"]["name"],
            "上海",
        )

    def test_validator_rejects_extra_supplied_chart_claims(self):
        payload = copy.deepcopy(self._chart())
        payload["input"]["normalized_chart_input"]["year"] = "甲子"

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_supplied_input_shape_mismatch", result["codes"])

    def test_validator_rejects_month_general_name_branch_mismatch(self):
        payloads = {
            "chart": self._chart(),
            "datetime": liuren.build_from_datetime(
                "2024-01-15T12:30:00",
                timezone_name="Asia/Shanghai",
                location="上海",
                question="边界核验",
                zi_hour_policy="midnight",
            ),
        }
        for mode, payload in payloads.items():
            with self.subTest(mode=mode):
                payload["output"]["month_general"]["name"] = "伪造月将名"
                result = adapter_validate.validate_payload("liuren", payload)
                self.assertFalse(result["ok"])
                self.assertIn(
                    "liuren_month_general_name_mismatch",
                    result["codes"],
                )

    def test_validator_rejects_a_tampered_liuren_plate(self):
        payload = copy.deepcopy(self._chart())
        payload["output"]["heaven_plate"][0]["heaven"] = payload["output"]["heaven_plate"][1]["heaven"]

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_heaven_plate_not_bijection", result["codes"])

    def test_validator_rejects_an_unverified_transmission_claim(self):
        payload = copy.deepcopy(self._chart())
        payload["output"]["transmission_method"]["calculation_source"] = "language_model_guess"

        result = adapter_validate.validate_payload("liuren", payload)

        self.assertFalse(result["ok"])
        self.assertIn("liuren_unverified_transmission_source", result["codes"])

    def test_official_and_traditional_guiren_profiles_are_explicit(self):
        official = self._chart()
        traditional = self._chart(guiren_profile="traditional-common")

        self.assertEqual(official["output"]["noble_person"]["branch"], "子")
        self.assertEqual(traditional["output"]["noble_person"]["branch"], "子")
        self.assertEqual(official["adapter"]["rule_profile"]["guiren"], "official-corrected")
        self.assertEqual(traditional["adapter"]["rule_profile"]["guiren"], "traditional-common")
        self.assertEqual(official["output"]["four_lessons"], traditional["output"]["four_lessons"])
        self.assertEqual(official["output"]["three_transmissions"], traditional["output"]["three_transmissions"])

        official_jia = self._chart(day_ganzhi="甲子", hour_ganzhi="庚午")
        traditional_jia = self._chart(
            day_ganzhi="甲子",
            hour_ganzhi="庚午",
            guiren_profile="traditional-common",
        )
        self.assertEqual(official_jia["output"]["noble_person"]["branch"], "未")
        self.assertEqual(traditional_jia["output"]["noble_person"]["branch"], "丑")
        self.assertNotEqual(
            official_jia["output"]["heavenly_generals"],
            traditional_jia["output"]["heavenly_generals"],
        )

    def test_fuyin_and_fanyin_are_structural_patterns(self):
        fuyin = self._chart(month_general="午")
        fanyin = self._chart(month_general="子")

        self.assertIn("伏吟", fuyin["output"]["structural_patterns"])
        self.assertIn("反吟", fanyin["output"]["structural_patterns"])
        self.assertEqual(fuyin["output"]["plate_offset"], 0)
        self.assertEqual(fanyin["output"]["plate_offset"], 6)

    def test_classical_shehai_depth_example_uses_hai(self):
        payload = self._chart(
            day_ganzhi="丁卯",
            hour_ganzhi="辛丑",
            month_general="亥",
        )

        self.assertEqual(payload["output"]["transmission_method"]["primary"], "涉害")
        self.assertEqual(payload["output"]["transmission_method"]["selected_initial"], "亥")
        self.assertEqual(
            "".join(item["branch"] for item in payload["output"]["three_transmissions"]),
            "亥酉未",
        )
        self.assertEqual(payload["output"]["transmission_method"]["source_anchor"], "daliuren-daquan L7082/L7212")
        paths = payload["output"]["transmission_method"]["selection_trace"]["shehai"]["candidate_harm_paths"]
        self.assertEqual({item["upper"]: item["depth"] for item in paths}, {"丑": 1, "亥": 5})

    def test_table_disagreement_does_not_override_classical_transmissions(self):
        payload = self._chart(
            day_ganzhi="己卯",
            hour_ganzhi="甲子",
            month_general="戌",
        )
        method = payload["output"]["transmission_method"]

        self.assertEqual(method["calculation_source"], "classical_nine-method_algorithm")
        self.assertEqual(method["selected_initial"], "亥")
        self.assertEqual(method["table_transmissions"], "丑亥酉")
        self.assertEqual(
            "".join(item["branch"] for item in payload["output"]["three_transmissions"]),
            "亥酉未",
        )
        self.assertTrue(any(item["type"] == "transmission_table_result" for item in payload["conflicts"]))

    def test_special_method_examples_follow_classical_branches(self):
        cases = (
            ("壬辰", "丙午", "午", "伏吟", "亥辰戌"),
            ("辛丑", "癸巳", "亥", "反吟", "亥未辰"),
            ("甲寅", "戊辰", "丑", "八专", "丑亥亥"),
            ("丙辰", "辛卯", "辰", "别责", "亥午午"),
            ("戊申", "乙卯", "辰", "昴星", "戌酉午"),
        )
        for day, hour, month_general, method, transmissions in cases:
            with self.subTest(method=method):
                payload = self._chart(
                    day_ganzhi=day,
                    hour_ganzhi=hour,
                    month_general=month_general,
                )
                self.assertEqual(payload["output"]["transmission_method"]["primary"], method)
                self.assertEqual(
                    "".join(item["branch"] for item in payload["output"]["three_transmissions"]),
                    transmissions,
                )
                if method == "反吟":
                    self.assertEqual(payload["output"]["transmission_method"]["well_rail_trace"]["result"], "井栏射")

    def test_yin_biezhe_source_variant_requires_an_explicit_profile(self):
        common = self._chart(
            day_ganzhi="辛未",
            hour_ganzhi="戊子",
            month_general="卯",
        )
        upper = self._chart(
            day_ganzhi="辛未",
            hour_ganzhi="戊子",
            month_general="卯",
            biezhe_profile="daliuren-daquan-upper-over-branch",
        )

        self.assertEqual(common["output"]["transmission_method"]["biezhe_profile"], "daliuren-daquan-body-branch")
        self.assertEqual(common["output"]["transmission_method"]["calculated_transmissions"], "亥丑丑")
        self.assertEqual(upper["output"]["transmission_method"]["calculated_transmissions"], "寅丑丑")
        self.assertTrue(any(item["type"] == "biezhe_yin_source_variant" for item in common["conflicts"]))

    def test_table_label_errors_are_overridden_by_classical_direct_ke_rules(self):
        cases = (
            ("戊辰", "壬子", "亥", "元首", "卯寅丑"),
            ("己丑", "甲子", "亥", "重审", "子亥戌"),
            ("辛巳", "戊子", "戌", "重审", "丑亥酉"),
        )
        for day, hour, month_general, method, transmissions in cases:
            with self.subTest(day=day, hour=hour, month_general=month_general):
                payload = self._chart(
                    day_ganzhi=day,
                    hour_ganzhi=hour,
                    month_general=month_general,
                )
                self.assertEqual(payload["output"]["transmission_method"]["primary"], method)
                self.assertEqual(
                    "".join(item["branch"] for item in payload["output"]["three_transmissions"]),
                    transmissions,
                )
                self.assertEqual(payload["output"]["transmission_method"]["table_disagreement"], True)

    def test_vendored_table_has_all_720_records_and_fixed_provenance(self):
        audit = liuren.audit_transmission_table()
        self.assertEqual(audit["days"], 60)
        self.assertEqual(audit["records"], 720)
        self.assertEqual(audit["invalid_records"], [])
        self.assertEqual(audit["direct_candidate_mismatches"], [])
        self.assertCountEqual(
            audit["method_label_disagreements"],
            [
                {"day": "戊辰", "offset": 11, "table": "比用", "derived": "元首"},
                {"day": "己丑", "offset": 11, "table": "元首", "derived": "重审"},
                {"day": "辛巳", "offset": 10, "table": "比用", "derived": "重审"},
                {"day": "丁卯", "offset": 4, "table": "重审", "derived": "涉害"},
            ],
        )
        self.assertEqual(audit["upstream_commit"], "8e9a7b53245c8ae19fa12773087e1f90b3376d5e")
        self.assertEqual(audit["license"], "Apache-2.0")
        self.assertEqual(len(audit["result_disagreements"]), 16)
        self.assertIn(
            {"day": "己卯", "offset": 10, "table": "丑亥酉", "classical": "亥酉未", "method": "涉害"},
            audit["result_disagreements"],
        )

    def test_cast_payload_embeds_only_a_compact_table_audit(self):
        payload = self._chart()
        audit = payload["source_trace"]["transmission_table"]

        self.assertEqual(audit["records"], 720)
        self.assertEqual(audit["method_label_disagreement_count"], 4)
        self.assertEqual(audit["result_disagreement_count"], 16)
        self.assertNotIn("method_label_disagreements", audit)
        self.assertNotIn("result_disagreements", audit)

    def test_full_table_audit_has_a_dedicated_cli(self):
        command = [
            sys.executable,
            str(SCRIPT_DIR / "liuren_fact_adapter.py"),
            "audit-table",
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(len(payload["method_label_disagreements"]), 4)
        self.assertEqual(len(payload["result_disagreements"]), 16)

    def test_all_8640_day_hour_general_combinations_validate(self):
        for day in liuren.JIAZI:
            for hour_branch in liuren.BRANCHES:
                hour = liuren.expected_hour_pillar(day, hour_branch)
                for month_general in liuren.BRANCHES:
                    payload = self._chart(
                        day_ganzhi=day,
                        hour_ganzhi=hour,
                        month_general=month_general,
                    )
                    result = adapter_validate.validate_payload("liuren", payload)
                    self.assertTrue(result["ok"], (day, hour, month_general, result))
                    self.assertEqual(len(payload["output"]["four_lessons"]), 4)
                    self.assertEqual(len(payload["output"]["three_transmissions"]), 3)
                    self.assertEqual(len(payload["output"]["heavenly_generals"]), 12)

    def test_datetime_cli_for_real_cst_fixture(self):
        command = [
            "/usr/bin/python3",
            str(SCRIPT_DIR / "liuren_fact_adapter.py"),
            "cast",
            "--datetime",
            "2000-03-02T12:00:00",
            "--timezone",
            "Asia/Shanghai",
            "--location",
            "中国上海",
            "--question",
            "这次合作能否在约定日期前签定正式合同？",
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["calendar_normalization"]["ganzhi"]["day"], "己未")
        self.assertEqual(payload["calendar_normalization"]["ganzhi"]["hour"], "庚午")
        self.assertEqual(payload["output"]["month_general"]["branch"], "亥")
        self.assertEqual(
            "".join(item["branch"] for item in payload["output"]["three_transmissions"]),
            "巳戌卯",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "cast.json"
            completed = subprocess.run(command + ["--output", str(target)], text=True, capture_output=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), json.loads(completed.stdout))


if __name__ == "__main__":
    unittest.main()
