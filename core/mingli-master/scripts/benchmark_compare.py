#!/usr/bin/env python3
"""Compare two scored benchmark runs on an identical case set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from prediction_freeze import canonical_digest


SCHEMA_VERSION = "mingli-paired-benchmark-comparison-v1"


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _score_rows(directory: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.score.json")):
        payload = _read_object(path)
        case_id = payload.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"score has no case_id: {path}")
        rows[case_id] = payload
    if not rows:
        raise ValueError(f"score directory is empty: {directory}")
    return rows


def _tool_adoption(
    prediction_directory: Path | None,
    case_ids: list[str],
) -> dict[str, Any] | None:
    if prediction_directory is None:
        return None
    adopted: list[str] = []
    for case_id in case_ids:
        path = prediction_directory / f"{case_id}.mc-prediction.json"
        if not path.is_file():
            raise ValueError(f"challenger prediction missing: {case_id}")
        activation_ids = (
            _read_object(path).get("prediction", {}).get("used_activation_ids") or []
        )
        if any(
            isinstance(activation_id, str)
            and activation_id.startswith("bazi.tool.")
            for activation_id in activation_ids
        ):
            adopted.append(case_id)
    return {
        "any_bazi_tool": len(adopted),
        "coverage": len(adopted) / len(case_ids),
        "case_ids": adopted,
    }


def compare_benchmark_runs(
    champion_score_directory: str | Path,
    challenger_score_directory: str | Path,
    challenger_prediction_directory: str | Path | None = None,
) -> dict[str, Any]:
    champion = _score_rows(Path(champion_score_directory))
    challenger = _score_rows(Path(challenger_score_directory))
    if not set(challenger).issubset(champion):
        raise ValueError(
            "challenger case set must be contained in the champion case set"
        )

    case_ids = sorted(challenger)
    improvements: list[str] = []
    regressions: list[str] = []
    retained_hits: list[str] = []
    unchanged_misses: list[str] = []
    changed_predictions: list[str] = []
    rows: list[dict[str, Any]] = []

    for case_id in case_ids:
        old = champion[case_id]
        new = challenger[case_id]
        old_hit = old.get("result") == "hit"
        new_hit = new.get("result") == "hit"
        if not old_hit and new_hit:
            improvements.append(case_id)
            transition = "improvement"
        elif old_hit and not new_hit:
            regressions.append(case_id)
            transition = "regression"
        elif old_hit and new_hit:
            retained_hits.append(case_id)
            transition = "retained_hit"
        else:
            unchanged_misses.append(case_id)
            transition = "unchanged_miss"
        if old.get("predicted_option") != new.get("predicted_option"):
            changed_predictions.append(case_id)
        rows.append(
            {
                "case_id": case_id,
                "transition": transition,
                "champion_prediction": old.get("predicted_option"),
                "challenger_prediction": new.get("predicted_option"),
                "correct_option": new.get("correct_option"),
            }
        )

    report = {
        "schema_version": SCHEMA_VERSION,
        "paired_total": len(case_ids),
        "champion_unpaired_total": len(champion) - len(case_ids),
        "champion_hits": sum(champion[case_id].get("result") == "hit" for case_id in case_ids),
        "challenger_hits": sum(challenger[case_id].get("result") == "hit" for case_id in case_ids),
        "improvements": improvements,
        "regressions": regressions,
        "retained_hits": retained_hits,
        "unchanged_misses": unchanged_misses,
        "changed_predictions": changed_predictions,
        "tool_adoption": _tool_adoption(
            Path(challenger_prediction_directory)
            if challenger_prediction_directory is not None
            else None,
            case_ids,
        ),
        "rows": rows,
    }
    report["comparison_digest"] = canonical_digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--champion-scores", required=True)
    parser.add_argument("--challenger-scores", required=True)
    parser.add_argument("--challenger-predictions")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = compare_benchmark_runs(
        args.champion_scores,
        args.challenger_scores,
        args.challenger_predictions,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
