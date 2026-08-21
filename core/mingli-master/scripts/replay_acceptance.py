#!/usr/bin/env python3
"""Strictly score Mingli replay evidence without inferring a human verdict."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_LABELS = (
    "broad-01-tomorrow",
    "broad-02-today",
    "broad-03-this-week",
    "broad-04-recent",
    "domain-01-huikuan",
    "domain-02-work",
    "domain-03-relationship",
    "domain-04-monthly-finance",
    "rebuttal-01-taifan",
    "rebuttal-02-notoutput",
    "insufficient-01-no-birth",
    "insufficient-02-no-hour",
    "liuren-01-no-city-required",
    "liuren-02-elaboration-reuses-lesson",
    "bazi-01-complete-birth",
)


def _explicit_true(entry: dict[str, Any], field: str) -> bool:
    return entry.get(field) is True


def summarize_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    labels = [
        str(entry.get("label") or "")
        for entry in entries
        if isinstance(entry, dict)
    ]
    double_pass_labels = [
        str(entry.get("label") or "")
        for entry in entries
        if isinstance(entry, dict)
        and _explicit_true(entry, "gate_ok")
        and _explicit_true(entry, "human_ok")
    ]
    failed_labels = [
        str(entry.get("label") or "")
        for entry in entries
        if not (
            isinstance(entry, dict)
            and _explicit_true(entry, "gate_ok")
            and _explicit_true(entry, "human_ok")
        )
    ]
    missing_labels = [label for label in EXPECTED_LABELS if label not in labels]
    unexpected_labels = [label for label in labels if label not in EXPECTED_LABELS]
    duplicate_labels = sorted({
        label for label in labels if label and labels.count(label) > 1
    })
    release_ready = bool(
        len(entries) == len(EXPECTED_LABELS)
        and not failed_labels
        and not missing_labels
        and not unexpected_labels
        and not duplicate_labels
    )
    return {
        "entry_count": len(entries),
        "gate_pass_count": sum(
            1 for entry in entries
            if isinstance(entry, dict) and _explicit_true(entry, "gate_ok")
        ),
        "human_pass_count": sum(
            1 for entry in entries
            if isinstance(entry, dict) and _explicit_true(entry, "human_ok")
        ),
        "double_pass_count": len(double_pass_labels),
        "double_pass_labels": double_pass_labels,
        "failed_labels": failed_labels,
        "missing_labels": missing_labels,
        "unexpected_labels": unexpected_labels,
        "duplicate_labels": duplicate_labels,
        "release_ready": release_ready,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_file")
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.summary_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        parser.error("summary file must contain a JSON list of objects")
    summary = summarize_entries(data)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["release_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
