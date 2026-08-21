#!/usr/bin/env python3
"""Import external known-answer cases into answer-isolated local fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


BAZIQA_YEARS = tuple(range(2021, 2026))
SOURCE_URL = "https://github.com/ChenJiangxi/BaziQA"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_case_id(year: int, question_id: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", question_id.lower()).strip("-")
    if not normalized:
        normalized = hashlib.sha256(question_id.encode("utf-8")).hexdigest()[:16]
    return f"baziqa-{year}-{normalized}"


def _split_for_person(person_id: str) -> str:
    bucket = int(hashlib.sha256(person_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket < 6:
        return "development"
    if bucket < 8:
        return "validation"
    return "evaluation"


def _license_status(source_root: Path) -> str:
    license_files = [
        source_root / name
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
    ]
    if any(path.is_file() for path in license_files):
        return "license_file_present"
    readme = source_root / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    if re.search(r"\bMIT\b", text, flags=re.IGNORECASE):
        return "readme_claims_mit_but_license_file_missing"
    return "license_not_found"


def import_baziqa(
    source_root: str | Path,
    destination_root: str | Path,
    *,
    source_url: str,
    source_commit: str,
) -> dict[str, Any]:
    source_root = Path(source_root)
    destination_root = Path(destination_root)
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source_commit must be a full 40-character Git SHA")

    seen_question_ids: set[str] = set()
    input_cases: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    counts_by_year: dict[str, int] = {}
    counts_by_split = {"development": 0, "validation": 0, "evaluation": 0}

    for year in BAZIQA_YEARS:
        source_path = source_root / "data" / f"contest8_{year}.json"
        payload = _read_json(source_path)
        if not isinstance(payload, list) or len(payload) < 2:
            raise ValueError(f"invalid BaziQA contest file: {source_path}")
        year_count = 0
        for person in payload[1:]:
            if not isinstance(person, dict):
                raise ValueError(f"invalid person entry in {source_path}")
            person_id = str(person.get("person_id") or "")
            profile = person.get("profile")
            questions = person.get("questions")
            if not person_id or not isinstance(profile, dict) or not isinstance(questions, list):
                raise ValueError(f"incomplete person entry in {source_path}")
            split = _split_for_person(person_id)
            for question in questions:
                if not isinstance(question, dict):
                    raise ValueError(f"invalid question entry in {source_path}")
                question_id = str(question.get("question_id") or "")
                if not question_id:
                    raise ValueError(f"missing question_id in {source_path}")
                if question_id in seen_question_ids:
                    raise ValueError(f"duplicate question_id: {question_id}")
                seen_question_ids.add(question_id)
                prompt = question.get("question")
                options = question.get("options")
                answer = question.get("answer")
                if not isinstance(prompt, str) or not prompt.strip():
                    raise ValueError(f"missing question text: {question_id}")
                if not isinstance(options, list) or len(options) < 2 or not all(
                    isinstance(option, str) for option in options
                ):
                    raise ValueError(f"invalid options: {question_id}")
                if answer not in {"A", "B", "C", "D"}:
                    raise ValueError(f"invalid answer key: {question_id}")

                case_id = _safe_case_id(year, question_id)
                input_cases.append(
                    {
                        "case_schema": "mingli-benchmark-input-v1",
                        "case_id": case_id,
                        "system": "bazi",
                        "split": split,
                        "source_dataset": "BaziQA",
                        "source_year": year,
                        "source_person_id": person_id,
                        "source_question_id": question_id,
                        "birth_profile": profile,
                        "question": prompt,
                        "options": options,
                        "fact_layer_status": "requires_local_bazi_adapter",
                        "answer_isolated": True,
                        "source": {
                            "url": source_url,
                            "commit": source_commit,
                        },
                    }
                )
                outcomes.append(
                    {
                        "outcome_schema": "mingli-benchmark-multiple-choice-outcome-v1",
                        "case_id": case_id,
                        "source_question_id": question_id,
                        "correct_option": answer,
                        "provenance": {
                            "dataset": "BaziQA",
                            "source_url": source_url,
                            "source_commit": source_commit,
                            "answer_published_with_question": True,
                        },
                    }
                )
                year_count += 1
                counts_by_split[split] += 1
        counts_by_year[str(year)] = year_count

    for case_input, outcome in zip(input_cases, outcomes, strict=True):
        filename = f"{case_input['case_id']}.json"
        _write_json(destination_root / "inputs" / filename, case_input)
        _write_json(destination_root / "outcomes" / filename, outcome)

    catalog = {
        "catalog_schema": "mingli-imported-benchmark-catalog-v1",
        "dataset": "BaziQA",
        "source_url": source_url,
        "source_commit": source_commit,
        "license_status": _license_status(source_root),
        "case_count": len(input_cases),
        "counts_by_year": counts_by_year,
        "counts_by_split": counts_by_split,
        "answer_isolation": {
            "inputs_directory": "inputs",
            "outcomes_directory": "outcomes",
            "split_group": "source_person_id",
        },
    }
    _write_json(destination_root / "catalog.json", catalog)
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--destination-root", required=True)
    parser.add_argument("--source-url", default=SOURCE_URL)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    try:
        catalog = import_baziqa(
            args.source_root,
            args.destination_root,
            source_url=args.source_url,
            source_commit=args.source_commit,
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
