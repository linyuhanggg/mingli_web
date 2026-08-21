#!/usr/bin/env python3
"""Tests for the source-family-aware near-time Bazi fact adapter."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import adapter_validate


SCRIPT = Path(__file__).with_name("near_time_fortune_adapter.py")


class NearTimeFortuneAdapterTests(unittest.TestCase):
    def run_adapter(self, *extra: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        if not SCRIPT.exists():
            self.fail(f"missing implementation: {SCRIPT.name}")
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--birth-datetime",
                "2000-10-18T06:45:00",
                "--timezone",
                "Asia/Shanghai",
                "--location",
                "合成测试地点",
                "--gender",
                "male",
                "--expected-pillars",
                "庚辰",
                "丙戌",
                "己酉",
                "丁卯",
                "--at",
                "2026-07-10T14:35:00+08:00",
                *extra,
            ],
            check=check,
            capture_output=True,
            text=True,
        )

    def test_complete_birth_profile_and_active_luck_are_required(self) -> None:
        completed = self.run_adapter(
            "--window",
            "2026-07-11 09:00-2026-07-11 21:00",
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(payload["fact_layer_status"], "near_time_bazi_transit_facts")
        self.assertEqual(payload["contract_version"], "fortune-public-v6-mechanism-stack")
        self.assertEqual(payload["adapter"]["version"], "2.2.1")
        self.assertEqual(
            payload["adapter"]["rule_profile"],
            "full-birth/transit-mechanism-stack-v5",
        )
        self.assertEqual(
            payload["birth_fact_layer"]["status"],
            "calculated_natal_chart_from_birth_datetime",
        )
        self.assertEqual(payload["birth_fact_layer"]["active_luck_cycle"], "戊子")
        self.assertEqual(
            payload["birth_fact_layer"]["four_pillars"],
            payload["birth_fact_layer"]["natal_pillars"],
        )
        self.assertEqual(payload["birth_fact_layer"]["day_master"]["stem"], "己")
        self.assertEqual(payload["birth_fact_layer"]["month_command"]["branch"], "戌")
        self.assertIn("ten_gods", payload["birth_fact_layer"])
        self.assertIn("hidden_stems", payload["birth_fact_layer"])
        self.assertEqual(payload["target_date"], "2026-07-11")
        self.assertEqual(payload["calendar_normalization"]["ganzhi"]["day"], "丙戌")
        self.assertEqual(payload["calendar_normalization"]["lunar_date"]["month"], 5)
        self.assertEqual(payload["calendar_normalization"]["lunar_date"]["day"], 27)

        stale = json.loads(json.dumps(payload, ensure_ascii=False))
        stale["adapter"]["version"] = "2.0.0"
        stale["adapter"]["rule_profile"] = "full-birth/transit-mechanism-stack-v3"
        validation = adapter_validate.validate_payload("fortune", stale)
        self.assertFalse(validation["ok"], validation)
        self.assertIn("fortune_stale_adapter_contract", validation["codes"])

    def test_day_branch_relations_form_a_mechanism_stack_without_scene_labels(self) -> None:
        completed = self.run_adapter(
            "--window",
            "2026-07-11 09:00-2026-07-11 21:00",
        )
        payload = json.loads(completed.stdout)

        stack = payload["mechanism_stack"]
        self.assertEqual(stack["target_day"]["pillar"], "丙戌")
        self.assertEqual(stack["target_day"]["stem_ten_god"], "正印")
        self.assertEqual(stack["target_day"]["branch"], "戌")
        self.assertGreaterEqual(len(stack["target_day"]["relations_to_natal"]), 3)
        self.assertTrue(stack["decisive_mechanisms"])
        self.assertTrue(all(item["source_family"] for item in stack["decisive_mechanisms"]))
        relation_family = payload["source_family_evidence"]["transit_day_branch_relations"]
        self.assertEqual(relation_family["independent_family_count"], 1)
        self.assertGreaterEqual(len(relation_family["signals"]), 3)
        raw = json.dumps(payload, ensure_ascii=False)
        for forbidden in ("communication_documents", "public_vocabulary", "action_vocabulary"):
            self.assertNotIn(forbidden, raw)

    def test_target_day_detects_cross_layer_three_branch_formation(self) -> None:
        completed = self.run_adapter(
            "--window",
            "2026-07-12 00:00-2026-07-12 23:59",
        )
        payload = json.loads(completed.stdout)
        stack = payload["mechanism_stack"]

        formation = next(
            item
            for item in stack["multi_branch_formations"]
            if item["relation"] == "三合" and item["branches"] == ["亥", "卯", "未"]
        )
        self.assertEqual(formation["nominal_element"], "木")
        self.assertEqual(formation["nominal_element_role_family"], "官杀")
        self.assertEqual(
            formation["branch_set_status"],
            "complete_branch_set_present_across_natal_and_timing_layers",
        )
        self.assertEqual(
            formation["transformation_status"],
            "unadjudicated_requires_classical_conditions",
        )
        self.assertNotIn("transformed_element", formation)
        member_keys = {
            (item["scope"], item.get("layer"), item.get("position"), item["branch"])
            for item in formation["members"]
        }
        self.assertIn(("transit", "day", None, "亥"), member_keys)
        self.assertIn(("transit", "month", None, "未"), member_keys)
        self.assertIn(("natal", None, "hour", "卯"), member_keys)
        self.assertIn(formation["id"], stack["judgment_resolution"]["primary_mechanism_ids"])
        self.assertIn(
            formation["id"],
            payload["public_claim_contract"]["primary_mechanism_ids"],
        )
        self.assertTrue(any(
            item["id"] == formation["id"]
            and item["source_family"] == "transit_day_multi_branch_formations"
            for item in stack["decisive_mechanisms"]
        ))
        family = payload["source_family_evidence"]["transit_day_multi_branch_formations"]
        self.assertEqual(family["independent_family_count"], 1)
        self.assertEqual(family["signals"], stack["multi_branch_formations"])

        valid = adapter_validate.validate_payload("fortune", payload)
        self.assertTrue(valid["ok"], valid)
        tampered = json.loads(json.dumps(payload, ensure_ascii=False))
        tampered["mechanism_stack"]["multi_branch_formations"][0]["branches"] = [
            "亥", "卯", "戌",
        ]
        invalid = adapter_validate.validate_payload("fortune", tampered)
        self.assertFalse(invalid["ok"], invalid)
        self.assertIn("fortune_multi_branch_formation_mismatch", invalid["codes"])

        correlated_tampers = {
            "wrong-member-layer": lambda item: item["members"][1].__setitem__(
                "layer",
                "year",
            ),
            "wrong-element-role": lambda item: item.__setitem__(
                "nominal_element_role_family",
                "财",
            ),
        }
        for name, mutate in correlated_tampers.items():
            correlated = json.loads(json.dumps(payload, ensure_ascii=False))
            targets = [
                correlated["mechanism_stack"]["multi_branch_formations"][0],
                next(
                    item
                    for item in correlated["mechanism_stack"]["decisive_mechanisms"]
                    if item["id"] == formation["id"]
                ),
                correlated["source_family_evidence"][
                    "transit_day_multi_branch_formations"
                ]["signals"][0],
            ]
            for target in targets:
                mutate(target)
            with self.subTest(name=name):
                invalid = adapter_validate.validate_payload("fortune", correlated)
                self.assertFalse(invalid["ok"], invalid)
                self.assertIn(
                    "fortune_multi_branch_formation_mismatch",
                    invalid["codes"],
                )

    def test_hour_profiles_remain_optional_facts_not_required_public_phases(self) -> None:
        completed = self.run_adapter(
            "--window",
            "2026-07-11 09:00-2026-07-11 21:00",
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(
            [item["phase"] for item in payload["hour_profiles"]],
            ["morning", "afternoon", "evening"],
        )
        self.assertFalse(payload["public_claim_contract"]["require_phase_narrative"])
        self.assertEqual(
            payload["public_claim_contract"]["required_coverage"],
            ["time_basis", "direct_judgment", "mechanism_explanation"],
        )
        raw = json.dumps(payload, ensure_ascii=False)
        for invented_scene in (
            "旧关系互动",
            "旧话题",
            "物品黏手",
            "事情黏住",
            "收尾",
            "回款",
            "等回复",
        ):
            self.assertNotIn(invented_scene, raw)

    def test_ten_gods_do_not_select_a_life_domain_or_public_wording(self) -> None:
        completed = self.run_adapter(
            "--window",
            "2026-07-10 09:00-2026-07-10 21:00",
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(payload["mechanism_stack"]["target_day"]["stem_ten_god"], "七杀")
        self.assertNotIn("domain_hypotheses", payload)
        contract = payload["public_claim_contract"]
        self.assertTrue(contract["user_selected_domains_only"])
        self.assertEqual(contract["supported_specific_events"], [])
        raw = json.dumps(payload, ensure_ascii=False)
        for scene in ("回复", "文件", "付款", "工作", "感情"):
            self.assertNotIn(scene, raw)

    def test_luck_year_month_day_layers_are_explicit_without_vote_counting(self) -> None:
        completed = self.run_adapter(
            "--window",
            "2026-07-10 09:00-2026-07-10 21:00",
        )
        payload = json.loads(completed.stdout)
        layers = payload["transit_layers"]
        self.assertEqual(set(layers), {"major_luck", "year", "month", "day"})
        self.assertEqual(layers["major_luck"]["pillar"], "戊子")
        self.assertEqual(layers["month"]["stem_ten_god"], "七杀")
        self.assertEqual(layers["day"]["stem_ten_god"], "七杀")
        self.assertTrue(layers["day"]["branch_relations_to_natal"])
        self.assertFalse(payload["mechanism_stack"]["empirical_independence_claimed"])

    def test_daily_dialogue_contract_answers_before_optional_probe(self) -> None:
        completed = self.run_adapter(
            "--window",
            "2026-07-10 09:00-2026-07-10 21:00",
        )
        payload = json.loads(completed.stdout)
        dialogue = payload["dialogue_contract"]

        self.assertEqual(dialogue["mode"], "answer_then_optional_probe")
        self.assertFalse(dialogue["question_required"])
        self.assertEqual(dialogue["maximum_follow_up_questions"], 1)
        self.assertIn("question_only_deferral", dialogue["prohibited_question_styles"])
        self.assertIn("repeat_known_birth_data", dialogue["prohibited_question_styles"])
        self.assertIn("leading_confirmation", dialogue["prohibited_question_styles"])

        repair = dialogue["repair_after_user_dissatisfaction"]
        self.assertEqual(repair["mode"], "recalculate_answer_then_one_open_probe")
        self.assertTrue(repair["question_required"])
        self.assertEqual(repair["maximum_follow_up_questions"], 1)
        self.assertIn("meta_explanation_only", repair["prohibited_responses"])
        self.assertIn("domain_menu", repair["prohibited_responses"])

        continuation = dialogue["after_user_answers_probe"]
        self.assertEqual(continuation["mode"], "continue_from_user_event_context")
        self.assertTrue(continuation["reuse_validated_baseline"])
        self.assertFalse(continuation["treat_reply_as_chart_proof"])

    def test_repeated_probes_inside_one_shichen_do_not_inflate_evidence(self) -> None:
        completed = self.run_adapter(
            "--window",
            "2026-07-11 19:05-2026-07-11 19:50",
        )
        payload = json.loads(completed.stdout)
        hour_family = payload["source_family_evidence"]["transit_hour_stem"]

        self.assertEqual(len(payload["hour_profiles"]), 3)
        self.assertEqual(hour_family["independent_family_count"], 1)
        self.assertEqual(hour_family["distinct_signal_count"], 1)
        self.assertEqual(len(hour_family["signals"]), 1)

    def test_invalid_window_fails_closed(self) -> None:
        completed = self.run_adapter("--window", "tomorrow", check=False)

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid window", completed.stderr.lower())

    def test_independent_validator_accepts_v6_and_rejects_tampering(self) -> None:
        completed = self.run_adapter(
            "--window",
            "2026-07-11 09:00-2026-07-11 21:00",
        )
        payload = json.loads(completed.stdout)

        valid = adapter_validate.validate_payload("fortune", payload)
        self.assertTrue(valid["ok"], valid)

        payload["source_family_evidence"]["transit_day_branch_relations"][
            "independent_family_count"
        ] = 2
        invalid = adapter_validate.validate_payload("fortune", payload)
        self.assertFalse(invalid["ok"], invalid)
        self.assertIn("fortune_relation_pseudoreplication", invalid["codes"])

        payload["source_family_evidence"]["transit_day_branch_relations"][
            "independent_family_count"
        ] = 1
        payload["source_family_evidence"]["transit_hour_stem"][
            "independent_family_count"
        ] = 3
        invalid_hour = adapter_validate.validate_payload("fortune", payload)
        self.assertFalse(invalid_hour["ok"], invalid_hour)
        self.assertIn("fortune_hour_pseudoreplication", invalid_hour["codes"])


if __name__ == "__main__":
    unittest.main()
