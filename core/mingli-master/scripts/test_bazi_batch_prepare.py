"""Tests for answer-isolated batch preparation of Bazi cases."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bazi_batch_prepare import prepare_directory


def _input(case_id: str, person_id: str, *, split: str = "development") -> dict:
    return {
        "case_schema": "mingli-benchmark-input-v1",
        "case_id": case_id,
        "system": "bazi",
        "source_person_id": person_id,
        "split": split,
        "birth_profile": {
            "birth": {
                "year": 1980,
                "month": 8,
                "day": 24,
                "hour": 16,
                "minute": 30,
                "place": "广东，中国",
            },
            "gender": "female",
        },
        "question": "学历如何？",
        "options": ["A. 中学", "B. 大学"],
        "answer_isolated": True,
    }


class BaziBatchPrepareTests(unittest.TestCase):
    def test_reuses_one_chart_calculation_for_questions_of_same_person(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = root / "inputs"
            outputs = root / "prepared"
            inputs.mkdir()
            for index in (1, 2):
                payload = _input(f"case-{index}", "person-1")
                (inputs / f"case-{index}.json").write_text(
                    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
                )

            calls = 0

            def fake_prepare(payload: dict) -> dict:
                nonlocal calls
                calls += 1
                return {
                    "prepared_schema": "mingli-prepared-bazi-case-v1",
                    "case_id": payload["case_id"],
                    "system": "bazi",
                    "source_person_id": payload["source_person_id"],
                    "question": payload["question"],
                    "options": payload["options"],
                    "preparation_status": "calculated",
                    "fact_snapshot": {"stable": "facts"},
                    "facts_digest": "f" * 64,
                }

            with patch("bazi_batch_prepare.prepare_bazi_case", side_effect=fake_prepare):
                summary = prepare_directory(inputs, outputs)

            self.assertEqual(calls, 1)
            self.assertEqual(summary["case_count"], 2)
            self.assertEqual(summary["unique_birth_profiles"], 1)
            self.assertEqual(summary["counts_by_status"], {"calculated": 2})
            second = json.loads((outputs / "case-2.json").read_text(encoding="utf-8"))
            self.assertEqual(second["case_id"], "case-2")
            self.assertEqual(second["fact_snapshot"], {"stable": "facts"})

    def test_outcome_like_input_is_rejected_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = root / "inputs"
            outputs = root / "prepared"
            inputs.mkdir()
            payload = _input("case-leak", "person-leak")
            payload["answer"] = "B"
            (inputs / "case-leak.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "outcome-like"):
                prepare_directory(inputs, outputs)
            self.assertFalse(outputs.exists())

    def test_duplicate_case_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = root / "inputs"
            inputs.mkdir()
            for name in ("one", "two"):
                (inputs / f"{name}.json").write_text(
                    json.dumps(_input("same-id", name), ensure_ascii=False),
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(ValueError, "duplicate case_id"):
                prepare_directory(inputs, root / "prepared")


if __name__ == "__main__":
    unittest.main()
