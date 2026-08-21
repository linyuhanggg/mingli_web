#!/usr/bin/env python3
"""Optional offline review helpers; never part of a production reading."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ABSOLUTE_PATTERNS = (
    r"一定",
    r"必然",
    r"必定",
    r"绝对",
    r"百分百",
    r"稳赚",
    r"必赚",
    r"肯定会",
)


def _finding(code: str, message: str, level: str = "error") -> dict[str, str]:
    return {"level": level, "code": code, "message": message}


def evaluate_answer(
    text: str,
    mode: str = "answer",
    accuracy_requested: bool = False,
) -> dict:
    """Run an explicitly requested offline prose review.

    This helper does not define the production answer contract, require a
    probability, require case-log markers, or authorize a reading. The v4
    transaction validates structured fact/source references separately.
    """
    findings: list[dict[str, str]] = []
    if accuracy_requested and any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in ABSOLUTE_PATTERNS
    ):
        findings.append(
            _finding(
                "overclaim_absolute_prediction",
                "Offline review found unconditional certainty wording.",
            )
        )
    return {
        "ok": not findings,
        "mode": mode,
        "offline": True,
        "findings": findings,
        "codes": [item["code"] for item in findings],
    }


def evaluate_claim_record(record: dict) -> dict:
    """Validate a structured lab claim without interpreting its prose."""
    from case_log import validate_record

    result = validate_record(record)
    findings = list(result["findings"])
    if record.get("record_type") != "claim":
        findings.append(
            _finding("not_a_claim_record", "Offline evaluation requires a claim record.")
        )
    return {
        "ok": not findings,
        "offline": True,
        "findings": findings,
        "codes": [item["code"] for item in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True)
    parser.add_argument("--mode", default="answer")
    parser.add_argument("--accuracy-requested", action="store_true")
    parser.add_argument("--claim-record", action="store_true")
    args = parser.parse_args()

    source = Path(args.file)
    if args.claim_record:
        payload = json.loads(source.read_text(encoding="utf-8"))
        result = evaluate_claim_record(payload)
    else:
        result = evaluate_answer(
            source.read_text(encoding="utf-8"),
            mode=args.mode,
            accuracy_requested=args.accuracy_requested,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
