#!/usr/bin/env python3
"""V4 regressions for caller-directed, fact-bound classical source plans."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

import reading_source_plan
import yaml


ROOT = Path(__file__).resolve().parents[1]


class ReadingSourcePlanTests(unittest.TestCase):
    def assert_valid_paths(self, plan: dict) -> None:
        self.assertEqual(plan["schema_version"], "mingli-reading-source-plan-v1")
        self.assertTrue(plan["required_packs"])
        self.assertEqual(len(plan["sources"]), len(plan["required_rule_files"]))
        for source in plan["sources"]:
            for field in ("rule_file", "quote_index_file"):
                path = ROOT / source[field]
                self.assertTrue(path.is_file(), source[field])
                self.assertGreater(path.stat().st_size, 0, source[field])

    def test_goal_is_preserved_without_query_taxonomy(self) -> None:
        goal = {
            "requested_resolution": "比较当前事实可支持与不能支持的范围",
            "evidence_questions": ["哪些规则适用于当前月令"],
            "counter_evidence_questions": ["哪些条件构成反例"],
            "question_dimensions": ["state", "timing"],
        }

        plan = reading_source_plan.compile_source_plan(
            "bazi",
            goal,
            {"chart": {"day_master": "丙"}},
        )

        self.assertEqual(plan["requested_resolution"], goal["requested_resolution"])
        self.assertEqual(plan["evidence_questions"], goal["evidence_questions"])
        self.assertEqual(
            plan["counter_evidence_questions"],
            goal["counter_evidence_questions"],
        )
        self.assertEqual(
            plan["question_dimensions"], goal["question_dimensions"]
        )
        self.assertNotIn("query", plan)
        self.assertNotIn("question_type", plan)
        self.assertIn("fact:/chart/day_master", plan["fact_ids"])
        self.assert_valid_paths(plan)

    def test_divination_route_is_selected_only_by_explicit_capability_id(self) -> None:
        goal = {"evidence_questions": ["核对本卦与动爻"]}

        liuyao = reading_source_plan.compile_source_plan("liuyao", goal)
        meihua = reading_source_plan.compile_source_plan("meihua", goal)

        self.assertEqual(liuyao["system"], "divination")
        self.assertEqual(liuyao["subsystem"], "liuyao")
        self.assertIn("divination/zengshan-buyi", liuyao["required_packs"])
        self.assertEqual(meihua["system"], "divination")
        self.assertEqual(meihua["subsystem"], "meihua")
        self.assertEqual(
            meihua["required_packs"],
            [
                "divination/meihua-yishu",
                "divination/zhouyi-zhezhong",
                "divination/huangji-jingshi",
            ],
        )

    def test_goal_may_select_support_and_comparison_packs(self) -> None:
        goal = {
            "source_packs": ["bazi/yuanhai-ziping", "bazi/ditiansui-chanwei"],
            "comparison_packs": ["bazi/qiongtong-baojian"],
            "evidence_questions": ["找支持规则"],
            "counter_evidence_questions": ["找限制条件"],
        }

        plan = reading_source_plan.compile_source_plan("bazi", goal)

        self.assertEqual(plan["required_packs"], goal["source_packs"])
        self.assertEqual(plan["comparison_packs"], goal["comparison_packs"])
        roles = {source["pack"]: source["role"] for source in plan["sources"]}
        self.assertEqual(roles["bazi/yuanhai-ziping"], "support")
        self.assertEqual(roles["bazi/qiongtong-baojian"], "counter")
        self.assert_valid_paths(plan)

    def test_qiongtong_applicability_comes_from_deterministic_facts(self) -> None:
        facts = {
            "chart_facts": {
                "output": {
                    "day_master": {"stem": "甲"},
                    "month_command": {"branch": "申"},
                }
            }
        }

        plan = reading_source_plan.compile_source_plan("bazi", {}, facts)

        applicability = plan["qiongtong_applicability"]
        self.assertEqual(applicability["day_master"], "甲")
        self.assertEqual(applicability["month_branch"], "申")
        self.assertEqual(applicability["resolution"], "applicable")
        self.assertTrue(applicability["applicable_chapter"])
        self.assertEqual(
            len(applicability["matrix_source"]["sha256"]),
            64,
        )

    def test_all_explicit_system_routes_resolve_without_blocked_packs(self) -> None:
        systems = (
            "bazi",
            "time-check",
            "fortune",
            "liuyao",
            "meihua",
            "ziwei",
            "xingming",
            "liuren",
            "qimen",
            "taiyi",
            "selection",
            "fengshui",
            "physiognomy",
            "luming-nayin",
        )

        for system in systems:
            with self.subTest(system=system):
                plan = reading_source_plan.compile_source_plan(system, {})
                self.assertFalse(
                    reading_source_plan.BLOCKED_PACKS.intersection(
                        plan["required_packs"]
                    )
                )
                if system == "physiognomy":
                    self.assertEqual(
                        plan["schema_version"],
                        "mingli-reading-source-plan-v1",
                    )
                    self.assertEqual(plan["required_packs"], [])
                    self.assertEqual(plan["sources"], [])
                    self.assertEqual(plan["required_rule_files"], [])
                else:
                    self.assert_valid_paths(plan)

    def test_invalid_goal_shapes_and_unknown_system_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "goal must be an object"):
            reading_source_plan.compile_source_plan("bazi", "旧查询")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "evidence_questions"):
            reading_source_plan.compile_source_plan(
                "bazi", {"evidence_questions": "不是列表"}
            )
        with self.assertRaisesRegex(ValueError, "question_dimensions"):
            reading_source_plan.compile_source_plan(
                "bazi", {"question_dimensions": "不是列表"}
            )
        with self.assertRaisesRegex(ValueError, "unknown capability id"):
            reading_source_plan.compile_source_plan("xiaoliuren", {})

    def test_runtime_source_registry_covers_exact_routes_and_source_roles(self) -> None:
        registry = reading_source_plan.load_runtime_source_registry()

        self.assertEqual(
            reading_source_plan.EXPECTED_RUNTIME_SOURCE_REGISTRY_SHA256,
            registry["sha256"],
        )
        self.assertEqual(
            registry["required_always_semantics"],
            "route_readiness_required_goal_may_select_subset",
        )

        self.assertEqual(
            set(registry["routes"]),
            {
                "bazi", "time-check", "fortune", "ziwei", "luming-nayin", "xingming",
                "liuyao", "meihua", "liuren", "qimen", "taiyi",
                "selection", "fengshui", "physiognomy",
            },
        )
        self.assertEqual(
            registry["routes"]["selection"]["comparison_only"],
            ["selection/yuqia-ji", "selection/donggong-zeri"],
        )
        self.assertEqual(
            registry["routes"]["selection"]["required_roles_by_pack"],
            {
                "selection/xieji-bianfang-shu": [
                    "issue_specific_judgment_rule"
                ],
                "selection/xingli-kaoyuan": ["methodology_rule"],
            },
        )
        self.assertEqual(
            registry["routes"]["physiognomy"]["comparison_only"],
            ["physiognomy/bingjian"],
        )
        self.assertNotIn(
            "physiognomy/bingjian",
            registry["routes"]["physiognomy"]["required_always"],
        )

    def test_runtime_source_registry_rejects_schema_route_and_pack_identity_drift(self) -> None:
        registry = yaml.safe_load(
            reading_source_plan.RUNTIME_SOURCE_REGISTRY_PATH.read_text(encoding="utf-8")
        )
        mutations = []

        missing_route = yaml.safe_load(yaml.safe_dump(registry, allow_unicode=True))
        del missing_route["routes"]["taiyi"]
        mutations.append((missing_route, "exactly the 13 runtime routes"))

        malformed_pack = yaml.safe_load(yaml.safe_dump(registry, allow_unicode=True))
        malformed_pack["routes"]["taiyi"]["required_always"] = ["not-a-pack"]
        mutations.append((malformed_pack, "invalid pack identity"))

        comparison_overlap = yaml.safe_load(yaml.safe_dump(registry, allow_unicode=True))
        comparison_overlap["routes"]["selection"]["comparison_only"].append(
            "selection/xieji-bianfang-shu"
        )
        mutations.append((comparison_overlap, "both required and comparison-only"))

        missing_role_contract = yaml.safe_load(
            yaml.safe_dump(registry, allow_unicode=True)
        )
        del missing_role_contract["routes"]["selection"][
            "required_roles_by_pack"
        ]["selection/xieji-bianfang-shu"]
        mutations.append((missing_role_contract, "role contract must cover"))

        for payload, message in mutations:
            with self.subTest(message=message):
                with tempfile.TemporaryDirectory() as temp_dir:
                    path = Path(temp_dir) / "registry.yaml"
                    path.write_text(
                        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(ValueError, message):
                        reading_source_plan.load_runtime_source_registry(path)

    def test_production_runtime_source_registry_is_hash_pinned(self) -> None:
        payload = reading_source_plan.RUNTIME_SOURCE_REGISTRY_PATH.read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as temporary:
            mutated = Path(temporary) / "runtime-source-families-v1.yaml"
            mutated.write_text(payload + "\n", encoding="utf-8")
            with mock.patch.object(
                reading_source_plan,
                "RUNTIME_SOURCE_REGISTRY_PATH",
                mutated,
            ), mock.patch.object(
                reading_source_plan,
                "_RUNTIME_SOURCE_REGISTRY_CACHE",
                None,
            ):
                with self.assertRaisesRegex(ValueError, "sha256 mismatch"):
                    reading_source_plan.load_runtime_source_registry()

    def test_fengshui_fact_bound_family_does_not_require_all_sixteen_packs(self) -> None:
        facts = {
            "chart_facts": {
                "output": {
                    "active_subprofiles": ["form"],
                    "form": {
                        "observations": [
                            {
                                "source_rule_ids": ["fengshui/zangshu#R-02"],
                            }
                        ],
                    },
                    "active_source_rule_ids": ["fengshui/zangshu#R-02"],
                }
            }
        }

        plan = reading_source_plan.compile_source_plan("fengshui", {}, facts)

        self.assertEqual(plan["required_packs"], ["fengshui/zangshu"])
        family = plan["runtime_source_family"]
        self.assertEqual(family["route"], "fengshui")
        self.assertEqual(family["required_when_active_subprofile"]["form"]["selection_mode"], "activated_rule_packs")
        self.assertEqual(family["selected_required_packs"], ["fengshui/zangshu"])
        self.assertLess(len(plan["required_packs"]), 16)

    def test_comparison_only_pack_cannot_be_selected_as_required_support(self) -> None:
        with self.assertRaisesRegex(ValueError, "comparison-only"):
            reading_source_plan.compile_source_plan(
                "selection",
                {"source_packs": ["selection/yuqia-ji"]},
            )


if __name__ == "__main__":
    unittest.main()
