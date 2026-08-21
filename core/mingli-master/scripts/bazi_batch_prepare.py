#!/usr/bin/env python3
"""Prepare an answer-isolated directory of Bazi benchmark inputs."""

from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from bazi_case_prepare import _outcome_path, prepare_bazi_case
from prediction_freeze import canonical_digest


def _read_inputs(input_directory: Path) -> list[dict[str, Any]]:
    if not input_directory.is_dir():
        raise ValueError(f"input directory does not exist: {input_directory}")
    cases: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    for path in sorted(input_directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"benchmark input must be an object: {path}")
        leak_path = _outcome_path(payload)
        if leak_path:
            raise ValueError(f"outcome-like field is forbidden in {path.name}: {leak_path}")
        case_id = payload.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"benchmark input has no case_id: {path}")
        if case_id in case_ids:
            raise ValueError(f"duplicate case_id: {case_id}")
        case_ids.add(case_id)
        cases.append(payload)
    if not cases:
        raise ValueError(f"input directory has no JSON cases: {input_directory}")
    return cases


def _case_projection(template: dict[str, Any], case_input: dict[str, Any]) -> dict[str, Any]:
    prepared = copy.deepcopy(template)
    prepared.update(
        {
            "case_id": case_input["case_id"],
            "source_person_id": case_input.get("source_person_id"),
            "question": case_input.get("question"),
            "options": case_input.get("options") or [],
        }
    )
    return prepared


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def prepare_directory(
    input_directory: str | Path,
    output_directory: str | Path,
) -> dict[str, Any]:
    inputs = Path(input_directory)
    outputs = Path(output_directory)
    cases = _read_inputs(inputs)

    profile_cache: dict[str, dict[str, Any]] = {}
    prepared_cases: list[tuple[str, dict[str, Any]]] = []
    status_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()

    for case_input in cases:
        profile = case_input.get("birth_profile")
        if not isinstance(profile, dict):
            raise ValueError(f"Bazi case has no birth_profile: {case_input['case_id']}")
        profile_key = canonical_digest(profile)
        if profile_key not in profile_cache:
            profile_cache[profile_key] = prepare_bazi_case(case_input)
        prepared = _case_projection(profile_cache[profile_key], case_input)
        status = str(prepared.get("preparation_status") or "invalid")
        status_counts[status] += 1
        split_counts[str(case_input.get("split") or "unspecified")] += 1
        prepared_cases.append((case_input["case_id"], prepared))

    outputs.mkdir(parents=True, exist_ok=True)
    for case_id, prepared in prepared_cases:
        _write_json_atomic(outputs / f"{case_id}.json", prepared)

    summary = {
        "summary_schema": "mingli-bazi-preparation-summary-v1",
        "case_count": len(prepared_cases),
        "unique_birth_profiles": len(profile_cache),
        "counts_by_status": dict(sorted(status_counts.items())),
        "counts_by_split": dict(sorted(split_counts.items())),
        "input_directory": str(inputs),
        "output_directory": str(outputs),
    }
    _write_json_atomic(outputs / "preparation-summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-directory", required=True)
    parser.add_argument("--output-directory", required=True)
    args = parser.parse_args()
    summary = prepare_directory(args.input_directory, args.output_directory)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
