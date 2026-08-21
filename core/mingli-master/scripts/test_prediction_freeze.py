"""Regression tests for blind, immutable Mingli predictions."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from prediction_freeze import (
    MultipleChoicePredictionStore,
    PredictionConflictError,
    PredictionStore,
)


SKILL_ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = SKILL_ROOT / "references" / "regression" / "cases" / "real"


def _read_json(name: str) -> dict:
    return json.loads((CASE_ROOT / name).read_text(encoding="utf-8"))


class PredictionFreezeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_input = {
            **_read_json("liuren-stock-loss-v1.input.json"),
            "published_at": "2026-07-22T09:00:00Z",
            "resolution_window": "2026-07-22/2026-08-22",
            "method": "blind-structured-inference-v1",
            "source_references": ["大六壬大全/卷三"],
        }
        self.case_outcome = _read_json("liuren-stock-loss-v1.outcome.json")
        self.support_inference = {
            "schema_version": "mingli-inference-v1",
            "case_id": self.case_input["case_id"],
            "verdict": "support",
            "confidence_bucket": "low",
            "decisive_activation_ids": ["LR-TEST-SUPPORT"],
            "counter_evidence_ids": [],
        }
        self.oppose_inference = {
            **self.support_inference,
            "verdict": "oppose",
            "decisive_activation_ids": ["LR-TEST-OPPOSE"],
        }

    def test_case_input_contains_no_outcome_payload(self) -> None:
        serialized = json.dumps(self.case_input, ensure_ascii=False).lower()
        self.assertNotIn('"outcome"', serialized)
        self.assertNotIn('"label": "loss"', serialized)

    def test_store_rejects_outcome_leak_in_prediction_input(self) -> None:
        contaminated = {**self.case_input, "outcome": self.case_outcome["outcome"]}
        with tempfile.TemporaryDirectory() as root:
            store = PredictionStore(root)
            with self.assertRaisesRegex(ValueError, "outcome"):
                store.freeze(contaminated, self.support_inference)

    def test_same_case_and_fact_snapshot_cannot_flip_polarity(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = PredictionStore(root)
            first = store.freeze(self.case_input, self.support_inference)

            with self.assertRaises(PredictionConflictError):
                store.freeze(self.case_input, self.oppose_inference)

            loaded = store.load(self.case_input["case_id"])
            self.assertEqual(loaded, first)
            self.assertEqual(loaded["prediction"]["verdict"], "support")

    def test_repeating_identical_prediction_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = PredictionStore(root)
            first = store.freeze(self.case_input, self.support_inference)
            second = store.freeze(self.case_input, self.support_inference)
            self.assertEqual(first, second)
            self.assertEqual(first["prediction_digest"], second["prediction_digest"])

    def test_outcome_is_scored_only_against_frozen_prediction(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = PredictionStore(root)
            frozen = store.freeze(self.case_input, self.support_inference)
            score = store.score(frozen, self.case_outcome)

            self.assertEqual(score["case_id"], self.case_input["case_id"])
            self.assertEqual(score["prediction_digest"], frozen["prediction_digest"])
            self.assertEqual(score["result"], "miss")
            self.assertEqual(score["outcome_provenance"], self.case_outcome["provenance"])

    def test_frozen_claim_keeps_publication_method_sources_and_resolution_window(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            frozen = PredictionStore(root).freeze(
                self.case_input,
                self.support_inference,
            )

        self.assertEqual(frozen["published_at"], "2026-07-22T09:00:00Z")
        self.assertEqual(frozen["resolution_window"], "2026-07-22/2026-08-22")
        self.assertEqual(frozen["method"], "blind-structured-inference-v1")
        self.assertEqual(frozen["source_references"], ["大六壬大全/卷三"])
        self.assertEqual(frozen["prediction_text"], "support")
        self.assertNotIn("probability", frozen["prediction"])

    def test_missing_feedback_is_unknown_and_never_counted_as_a_miss(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = PredictionStore(root)
            frozen = store.freeze(self.case_input, self.support_inference)
            score = store.score(frozen, None)

        self.assertEqual(score["result"], "unknown")
        self.assertIsNone(score["outcome_digest"])
        self.assertIsNone(score["outcome_provenance"])


class MultipleChoicePredictionFreezeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_input = {
            "case_id": "baziqa-test-q1",
            "system": "bazi",
            "question": "哪项符合命主学历？",
            "options": ["A. 小学", "B. 中学", "C. 大学", "D. 硕士"],
            "fact_snapshot": {"output": {"four_pillars": {"year": "庚申"}}},
        }
        self.prediction = {
            "choice": "C",
            "confidence_bucket": "low",
            "reason": "印星与岁运组合更接近高等教育选项。",
            "used_activation_ids": ["bazi.day_master"],
        }

    def test_mc_prediction_is_immutable_and_scored_after_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = MultipleChoicePredictionStore(root)
            frozen = store.freeze(
                self.case_input,
                inference_digest="1" * 64,
                prompt_digest="2" * 64,
                model_id="test/model",
                prediction=self.prediction,
            )
            changed = {**self.prediction, "choice": "B"}
            with self.assertRaises(PredictionConflictError):
                store.freeze(
                    self.case_input,
                    inference_digest="1" * 64,
                    prompt_digest="2" * 64,
                    model_id="test/model",
                    prediction=changed,
                )
            score = store.score(
                frozen,
                {
                    "case_id": "baziqa-test-q1",
                    "correct_option": "C",
                },
            )
            self.assertEqual(score["result"], "hit")

    def test_mc_store_rejects_answer_leak_and_invalid_choice(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = MultipleChoicePredictionStore(root)
            leaked = {**self.case_input, "correct_option": "C"}
            with self.assertRaisesRegex(ValueError, "outcome"):
                store.freeze(
                    leaked,
                    inference_digest="1" * 64,
                    prompt_digest="2" * 64,
                    model_id="test/model",
                    prediction=self.prediction,
                )
            with self.assertRaisesRegex(ValueError, "choice"):
                store.freeze(
                    self.case_input,
                    inference_digest="1" * 64,
                    prompt_digest="2" * 64,
                    model_id="test/model",
                    prediction={**self.prediction, "choice": "E"},
                )

    def test_mc_store_assigns_missing_option_label_by_position(self) -> None:
        case_input = {
            **self.case_input,
            "options": [
                "A跟随母亲生活",
                "B在孤儿院长大",
                "跟随父亲生活",
                "D跟随收养父母生活",
            ],
        }
        with tempfile.TemporaryDirectory() as root:
            frozen = MultipleChoicePredictionStore(root).freeze(
                case_input,
                inference_digest="1" * 64,
                prompt_digest="2" * 64,
                model_id="test/model",
                prediction={**self.prediction, "choice": "C"},
            )
        self.assertEqual(frozen["prediction"]["choice"], "C")

    def test_mc_sidecar_records_a_generic_method_without_requiring_model_identity(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            frozen = MultipleChoicePredictionStore(root).freeze(
                self.case_input,
                inference_digest="1" * 64,
                prompt_digest="2" * 64,
                method="blind-multiple-choice-v1",
                prediction=self.prediction,
            )

        self.assertEqual(frozen["method"], "blind-multiple-choice-v1")
        self.assertNotIn("model_id", frozen)


if __name__ == "__main__":
    unittest.main()
