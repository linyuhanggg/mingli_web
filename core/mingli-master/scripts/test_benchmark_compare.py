"""Tests for paired, post-outcome benchmark run comparison."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from benchmark_compare import compare_benchmark_runs


class BenchmarkCompareTests(unittest.TestCase):
    def _write_score(
        self,
        directory: Path,
        case_id: str,
        result: str,
        predicted: str,
        correct: str,
    ) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{case_id}.score.json").write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "result": result,
                    "predicted_option": predicted,
                    "correct_option": correct,
                }
            ),
            encoding="utf-8",
        )

    def _write_prediction(
        self,
        directory: Path,
        case_id: str,
        activation_ids: list[str],
    ) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{case_id}.mc-prediction.json").write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "prediction": {"used_activation_ids": activation_ids},
                }
            ),
            encoding="utf-8",
        )

    def test_reports_paired_improvements_regressions_and_tool_adoption(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            champion = root / "champion"
            challenger = root / "challenger"
            predictions = root / "predictions"
            cases = [
                ("improved", "miss", "B", "hit", "A", "A"),
                ("regressed", "hit", "C", "miss", "D", "C"),
                ("retained", "hit", "B", "hit", "B", "B"),
                ("unchanged-miss", "miss", "A", "miss", "A", "D"),
            ]
            for case_id, old_result, old_choice, new_result, new_choice, correct in cases:
                self._write_score(champion, case_id, old_result, old_choice, correct)
                self._write_score(challenger, case_id, new_result, new_choice, correct)
                activations = ["bazi.tool.strength_evidence"] if case_id != "unchanged-miss" else []
                self._write_prediction(predictions, case_id, activations)

            report = compare_benchmark_runs(champion, challenger, predictions)

        self.assertEqual(report["paired_total"], 4)
        self.assertEqual(report["champion_hits"], 2)
        self.assertEqual(report["challenger_hits"], 2)
        self.assertEqual(report["improvements"], ["improved"])
        self.assertEqual(report["regressions"], ["regressed"])
        self.assertEqual(report["retained_hits"], ["retained"])
        self.assertEqual(report["unchanged_misses"], ["unchanged-miss"])
        self.assertEqual(report["tool_adoption"]["any_bazi_tool"], 3)
        self.assertEqual(report["tool_adoption"]["coverage"], 0.75)

    def test_rejects_unpaired_score_sets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_score(root / "champion", "only-old", "hit", "A", "A")
            self._write_score(root / "challenger", "only-new", "hit", "B", "B")
            with self.assertRaisesRegex(ValueError, "case set"):
                compare_benchmark_runs(root / "champion", root / "challenger")

    def test_allows_champion_superset_for_smoke_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_score(root / "champion", "shared", "hit", "A", "A")
            self._write_score(root / "champion", "champion-only", "hit", "B", "B")
            self._write_score(root / "challenger", "shared", "miss", "C", "A")

            report = compare_benchmark_runs(root / "champion", root / "challenger")

        self.assertEqual(report["paired_total"], 1)
        self.assertEqual(report["champion_unpaired_total"], 1)
        self.assertEqual(report["champion_hits"], 1)
        self.assertEqual(report["regressions"], ["shared"])


if __name__ == "__main__":
    unittest.main()
