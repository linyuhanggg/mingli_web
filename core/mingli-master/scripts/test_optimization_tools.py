#!/usr/bin/env python3
"""Regression tests for accuracy optimization tools."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import adapter_validate
import bazi_fact_adapter
import case_log
import evaluate_answer


SKILL_DIR = Path(__file__).resolve().parents[1]


class AdapterValidateTests(unittest.TestCase):
    def test_bazi_payload_requires_tiaohou_and_luck_fields(self) -> None:
        payload = {
            "adapter": {"name": "tool.bazi", "version": "0.1", "rule_profile": "子平"},
            "calendar_normalization": {
                "civil_datetime": "1990-01-01T08:00:00+08:00",
                "lunar_date": "己巳年腊月初五",
                "ganzhi": {"year": "己巳", "month": "丙子", "day": "丙寅", "hour": "壬辰"},
                "solar_terms": "小寒前",
            },
            "output": {
                "four_pillars": ["己巳", "丙子", "丙寅", "壬辰"],
                "hidden_stems": {"巳": ["丙", "戊", "庚"]},
                "ten_gods": {"year_stem": "伤官"},
            },
        }

        result = adapter_validate.validate_payload("bazi", payload)

        self.assertFalse(result["ok"])
        self.assertIn("missing_output:seasonal_profile", result["codes"])
        self.assertIn("missing_output:tiaohou_markers", result["codes"])
        self.assertIn("missing_output:luck_cycles", result["codes"])

    def test_bazi_payload_with_required_fields_passes(self) -> None:
        payload = bazi_fact_adapter.build_from_pillars(
            ["己巳", "丙子", "丙寅", "壬辰"],
            gender="male",
            source="text",
            source_ref="optimization-tools-fixture",
        )

        result = adapter_validate.validate_payload("bazi", payload)

        self.assertTrue(result["ok"], result)


class CaseLogTests(unittest.TestCase):
    def test_claim_and_outcome_are_separate_append_only_records(self) -> None:
        claim = case_log.build_claim(
            case_id="case-1",
            system="bazi",
            question="财运何时转好",
            prediction_text="30天内有一笔延迟款项到账",
            published_at="2026-07-01T00:00:00Z",
            resolution_window="2026-07-01/2026-07-31",
            method="prospective-human-review",
            source_references=["bazi/sanming-tonghui#财帛"],
            evidence_strength="textual-high",
        )
        unknown = case_log.build_outcome(
            claim=claim,
            status="unknown",
            observed_at=None,
            provenance=None,
        )

        self.assertNotIn("outcome", claim)
        self.assertEqual(unknown["status"], "unknown")
        self.assertEqual(unknown["claim_digest"], claim["claim_digest"])
        self.assertRegex(claim["claim_digest"], r"^[0-9a-f]{64}$")
        self.assertRegex(unknown["outcome_digest"], r"^[0-9a-f]{64}$")

    def test_qualitative_evidence_strength_is_not_converted_to_probability(self) -> None:
        claim = case_log.build_claim(
            case_id="case-qualitative",
            system="liuren",
            question="谈判成不成",
            prediction_text="更可能推进",
            published_at="2026-07-01T00:00:00Z",
            resolution_window="2026-W27",
            method="prospective-human-review",
            source_references=["大六壬大全/卷三"],
            evidence_strength="high",
        )
        outcome = case_log.build_outcome(
            claim=claim,
            status="hit",
            observed_at="2026-07-08T00:00:00Z",
            provenance={"kind": "timestamped_record", "reference": "event-1"},
        )

        summary = case_log.summarize_records([claim, outcome])

        self.assertEqual(summary["scorable_claims"], 1)
        self.assertEqual(summary["hit_rate"], 1.0)
        self.assertIsNone(summary["brier_score"])
        self.assertEqual(summary["brier_reason"], "no explicit numeric probabilities")

    def test_brier_and_interval_scores_require_explicit_objective_values(self) -> None:
        binary = case_log.build_claim(
            case_id="case-binary",
            system="liuren",
            question="是否发生",
            prediction_text="会发生",
            published_at="2026-07-01T00:00:00Z",
            resolution_window="2026-07-01/2026-07-31",
            method="prospective-human-review",
            source_references=["rule-1"],
            probability=0.7,
        )
        interval = case_log.build_claim(
            case_id="case-interval",
            system="liuren",
            question="金额范围",
            prediction_text="金额落在区间内",
            published_at="2026-07-01T00:00:00Z",
            resolution_window="2026-07-01/2026-07-31",
            method="prospective-human-review",
            source_references=["rule-2"],
            prediction_interval=[80.0, 120.0],
        )
        records = [
            binary,
            case_log.build_outcome(
                claim=binary,
                status="hit",
                observed_at="2026-07-15T00:00:00Z",
                provenance={"kind": "document", "reference": "doc-1"},
                observed_value=1.0,
            ),
            interval,
            case_log.build_outcome(
                claim=interval,
                status="hit",
                observed_at="2026-07-15T00:00:00Z",
                provenance={"kind": "document", "reference": "doc-2"},
                observed_value=100.0,
            ),
        ]

        summary = case_log.summarize_records(records)

        self.assertAlmostEqual(summary["brier_score"], 0.09)
        self.assertEqual(summary["interval_scores"]["case-interval"], 40.0)

    def test_case_log_jsonl_roundtrip(self) -> None:
        claim = case_log.build_claim(
            case_id="case-jsonl",
            system="selection",
            question="哪天搬家",
            prediction_text="候选日A比候选日B更适合",
            published_at="2026-07-01T00:00:00Z",
            resolution_window="2026-07",
            method="prospective-human-review",
            source_references=["selection/xieji-bianfang-shu"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cases.jsonl"
            case_log.append_record(path, claim)
            loaded = case_log.load_records(path)

        self.assertEqual(loaded[0]["case_id"], "case-jsonl")
        self.assertEqual(case_log.validate_record(loaded[0])["ok"], True)


class EvaluateAnswerTests(unittest.TestCase):
    def test_absolute_wording_can_be_flagged_only_by_explicit_offline_review(self) -> None:
        answer = """
【问题分类】八字财运
【需要的事实层输入/工具】用户已提供四柱、藏干、十神、节气/月令/寒暖燥湿/调候、大运/流年；calendar_normalization 农历 干支 四柱 节气 时区。
【加载的古籍包】bazi/sanming-tonghui
【文本依据】quote-index: 财星透出。
【综合判断】你今年一定发财，绝对能中大财。
【准确度/校准状态】textual_high
【边界与版本说明】传统参考。
"""

        result = evaluate_answer.evaluate_answer(answer, mode="answer", accuracy_requested=True)

        self.assertFalse(result["ok"])
        self.assertIn("overclaim_absolute_prediction", result["codes"])
        self.assertNotIn("missing_empirical_calibration_status", result["codes"])

    def test_public_answer_never_needs_a_probability_or_case_log_marker(self) -> None:
        answer = "元首课，初传为子。\n我判断事情更可能推进，但空亡使时间点不能锁死。"

        result = evaluate_answer.evaluate_answer(answer, mode="answer", accuracy_requested=True)

        self.assertTrue(result["ok"], result)


class ReferenceWiringTests(unittest.TestCase):
    def test_production_skill_excludes_optional_lab_tools(self) -> None:
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("唯一 JSON Adapter", text)
        for command in ("describe", "prepare", "complete"):
            self.assertIn(f"`{command}`", text)
        self.assertNotIn("scripts/", text)
        for excluded in [
            "scripts/case_log.py",
            "scripts/evaluate_answer.py",
        ]:
            self.assertNotIn(excluded, text)

    def test_runtime_transaction_does_not_import_lab_modules(self) -> None:
        runtime_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                SKILL_DIR / "scripts" / "reading_transaction.py",
                *(SKILL_DIR / "scripts" / "reading_engine").glob("*.py"),
            ]
        )
        for module in ("case_log", "evaluate_answer", "prediction_freeze"):
            self.assertNotIn(f"import {module}", runtime_text)

    def test_lab_architecture_document_marks_sidecar_optional(self) -> None:
        text = (SKILL_DIR / "docs" / "architecture" / "mingli-lab-sidecar.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("offline", text.lower())
        self.assertIn("optional", text.lower())
        self.assertIn("unknown", text)


if __name__ == "__main__":
    unittest.main()
