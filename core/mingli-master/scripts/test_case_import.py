"""Tests for importing known-answer datasets without leaking answers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from case_import import import_baziqa


def _person(person_id: str, answer: str = "B") -> dict:
    return {
        "person_id": person_id,
        "name": "匿名命主",
        "profile": {
            "birth": {
                "year": 1980,
                "month": 8,
                "day": 24,
                "hour": 16,
                "minute": 30,
                "place": "广东，中国",
                "approximate": False,
            },
            "gender": "female",
        },
        "questions": [
            {
                "question_id": f"{person_id}-Q1",
                "question": "以下哪项描述符合命主的学历情况？",
                "options": ["A. 小学", "B. 中学", "C. 大学", "D. 硕士"],
                "answer": answer,
            },
            {
                "question_id": f"{person_id}-Q2",
                "question": "以下哪项描述符合命主的事业情况？",
                "options": ["A. 甲", "B. 乙", "C. 丙", "D. 丁"],
                "answer": "C",
            },
        ],
    }


class BaziQaImportTests(unittest.TestCase):
    def _source(self, root: Path, people: list[dict] | None = None) -> Path:
        source = root / "source"
        data = source / "data"
        data.mkdir(parents=True)
        (source / "README.md").write_text(
            "# BaziQA\n\nLicense: MIT\n",
            encoding="utf-8",
        )
        for year in range(2021, 2026):
            payload = [
                {
                    "contest_id": f"contest8_{year}",
                    "current_year": str(year),
                    "total_questions": len(people or [_person(f"p{year}")]) * 2,
                },
                *(people or [_person(f"p{year}")]),
            ]
            (data / f"contest8_{year}.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
        return source

    def test_import_separates_question_inputs_from_answers(self) -> None:
        with tempfile.TemporaryDirectory() as root_string:
            root = Path(root_string)
            catalog = import_baziqa(
                self._source(root),
                root / "imported",
                source_url="https://github.com/ChenJiangxi/BaziQA",
                source_commit="a" * 40,
            )
            input_path = next(
                path
                for path in (root / "imported" / "inputs").glob("*.json")
                if path.stem.endswith("q1")
            )
            outcome_path = root / "imported" / "outcomes" / input_path.name
            case_input = json.loads(input_path.read_text(encoding="utf-8"))
            outcome = json.loads(outcome_path.read_text(encoding="utf-8"))

            serialized_input = json.dumps(case_input, ensure_ascii=False).lower()
            self.assertNotIn('"answer"', serialized_input)
            self.assertNotIn("correct_option", serialized_input)
            self.assertEqual(outcome["correct_option"], "B")
            self.assertEqual(catalog["case_count"], 10)

    def test_all_questions_for_one_chart_stay_in_the_same_split(self) -> None:
        with tempfile.TemporaryDirectory() as root_string:
            root = Path(root_string)
            import_baziqa(
                self._source(root),
                root / "imported",
                source_url="https://github.com/ChenJiangxi/BaziQA",
                source_commit="a" * 40,
            )
            cases = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in (root / "imported" / "inputs").glob("*.json")
            ]
            by_person: dict[str, set[str]] = {}
            for case in cases:
                by_person.setdefault(case["source_person_id"], set()).add(case["split"])
            self.assertTrue(all(len(splits) == 1 for splits in by_person.values()))

    def test_missing_license_file_is_recorded_even_when_readme_claims_mit(self) -> None:
        with tempfile.TemporaryDirectory() as root_string:
            root = Path(root_string)
            catalog = import_baziqa(
                self._source(root),
                root / "imported",
                source_url="https://github.com/ChenJiangxi/BaziQA",
                source_commit="a" * 40,
            )
            self.assertEqual(
                catalog["license_status"],
                "readme_claims_mit_but_license_file_missing",
            )

    def test_duplicate_question_ids_are_rejected(self) -> None:
        duplicate_people = [_person("same"), _person("same")]
        with tempfile.TemporaryDirectory() as root_string:
            root = Path(root_string)
            source = self._source(root, duplicate_people)
            with self.assertRaisesRegex(ValueError, "duplicate question_id"):
                import_baziqa(
                    source,
                    root / "imported",
                    source_url="https://github.com/ChenJiangxi/BaziQA",
                    source_commit="a" * 40,
                )


if __name__ == "__main__":
    unittest.main()
