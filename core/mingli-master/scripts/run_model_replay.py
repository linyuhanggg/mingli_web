#!/usr/bin/env python3
"""Score external Mingli replay outputs without invoking or selecting a model."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


USAGE_FIELDS = ("input_tokens", "output_tokens", "latency_ms", "reported_cost")

# Blind independent review of answer delivery.  Booleans stay booleans and scored
# fields stay bounded so a malformed manifest fails closed instead of
# becoming a lower score.  These are offline release evidence only: no
# production surface reads them and no gate consumes them.
REVIEW_FLAG_FIELDS = (
    "direct_answer",
    "evidence_relevant",
    "main_point_clear",
    "certainty_calibrated",
    "ambient_context_clean",
    "template_smell",
)
REVIEW_SCORE_FIELDS = ("naturalness", "plain_language", "useful_specificity")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row must be an object at {path}:{number}")
        case_id = str(row.get("case_id") or "")
        if not case_id or case_id in seen:
            raise ValueError(f"invalid or duplicate case_id at {path}:{number}")
        seen.add(case_id)
        rows.append(row)
    return rows


def canonical_row_sha256(row: dict[str, Any]) -> str:
    return canonical_value_sha256(row)


def canonical_value_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _average(rows: Iterable[dict[str, Any]], field: str) -> float:
    values = [float(row[field]) for row in rows]
    return mean(values)


def _strict_number(value: Any, *, field: str, integer: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field} must be numeric")
    if integer and not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{field} must be finite and non-negative")
    return number


def _case_map(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    mapped = {row.get("case_id"): row for row in rows}
    if len(mapped) != len(rows) or None in mapped or "" in mapped:
        raise ValueError(f"{label} case ids must be unique and non-empty")
    return mapped


def _require_same_cases(
    expected: dict[str, dict[str, Any]],
    actual: dict[str, dict[str, Any]],
    *,
    label: str,
) -> None:
    unknown = sorted(set(actual) - set(expected))
    missing = sorted(set(expected) - set(actual))
    if unknown:
        raise ValueError(f"unknown {label} cases: {unknown}")
    if missing:
        raise ValueError(f"missing {label} cases: {missing}")


def _validate_usage(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usage_rows: list[dict[str, Any]] = []
    for row in predictions:
        usage = row.get("usage")
        if usage is None:
            continue
        if not isinstance(usage, dict) or not set(USAGE_FIELDS) <= set(usage):
            raise ValueError(f"complete usage missing: {row['case_id']}")
        _strict_number(usage["input_tokens"], field="input_tokens", integer=True)
        _strict_number(usage["output_tokens"], field="output_tokens", integer=True)
        _strict_number(usage["latency_ms"], field="latency_ms")
        _strict_number(usage["reported_cost"], field="reported_cost")
        usage_rows.append(usage)
    return usage_rows


def _validate_answer_reviews(
    *,
    predictions: list[dict[str, Any]],
    reviews: list[dict[str, Any]] | None,
    run_label: str | None,
) -> tuple[list[dict[str, Any]], int, int, int]:
    if reviews is None or not run_label:
        raise ValueError("answer scoring requires a separate review manifest and run label")
    if any("review" in row for row in predictions):
        raise ValueError("semantic review must not be embedded in prediction rows")
    prediction_map = _case_map(predictions, label="prediction")
    review_map = _case_map(reviews, label="review")
    _require_same_cases(prediction_map, review_map, label="review")
    ordered_reviews: list[dict[str, Any]] = []
    unsupported_claims = 0
    reviewed_claims = 0
    untraced_claims = 0
    for prediction in predictions:
        case_id = prediction["case_id"]
        review = review_map[case_id]
        if review.get("prediction_sha256") != canonical_row_sha256(prediction):
            raise ValueError(f"review is not bound to prediction: {case_id}")
        reviewer = review.get("reviewer")
        if (
            not isinstance(reviewer, dict)
            or not str(reviewer.get("reviewer_id") or "").strip()
            or reviewer.get("reviewer_kind") not in {"human", "independent_agent"}
            or reviewer.get("independent") is not True
            or reviewer.get("blinded_run_label") != run_label
        ):
            raise ValueError(f"blind review protocol metadata missing: {case_id}")
        for field in REVIEW_FLAG_FIELDS:
            if not isinstance(review.get(field), bool):
                raise ValueError(f"{field} must be boolean: {case_id}")
        for field in REVIEW_SCORE_FIELDS:
            score = _strict_number(review.get(field), field=field)
            if score < 1 or score > 5:
                raise ValueError(f"{field} outside 1..5: {case_id}")
        traces = (prediction.get("prediction") or {}).get("claim_traces") or []
        claim_reviews = review.get("claim_reviews")
        if review.get("main_answer_claims_complete") is not True:
            raise ValueError(f"reviewer did not attest complete claim enumeration: {case_id}")
        if not isinstance(claim_reviews, list) or not claim_reviews:
            raise ValueError(f"independent claim enumeration missing: {case_id}")
        indexes: set[int] = set()
        for claim_review in claim_reviews:
            if not isinstance(claim_review, dict):
                raise ValueError(f"invalid claim review: {case_id}")
            index = claim_review.get("claim_index")
            claim_text = claim_review.get("claim_text")
            trace_indexes = claim_review.get("trace_indexes")
            unsupported = claim_review.get("unsupported")
            if not isinstance(index, int) or isinstance(index, bool):
                raise ValueError(f"invalid claim review index: {case_id}")
            if not isinstance(claim_text, str) or not claim_text.strip():
                raise ValueError(f"reviewed claim text missing: {case_id}")
            if (
                not isinstance(trace_indexes, list)
                or any(not isinstance(item, int) or isinstance(item, bool) for item in trace_indexes)
                or len(set(trace_indexes)) != len(trace_indexes)
                or any(item < 0 or item >= len(traces) for item in trace_indexes)
            ):
                raise ValueError(f"reviewed claim trace binding invalid: {case_id}")
            if not isinstance(unsupported, bool):
                raise ValueError(f"unsupported must be boolean: {case_id}")
            indexes.add(index)
            untraced_claims += int(not trace_indexes)
            reviewed_claims += 1
            unsupported_claims += int(unsupported)
        if indexes != set(range(len(claim_reviews))):
            raise ValueError(f"claim reviews must be consecutively indexed: {case_id}")
        ordered_reviews.append(review)
    return ordered_reviews, unsupported_claims, reviewed_claims, untraced_claims


def score_predictions(
    cases: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    kind: str,
    reviews: list[dict[str, Any]] | None = None,
    run_label: str | None = None,
) -> dict[str, Any]:
    if kind not in {"routing", "answer"}:
        raise ValueError("kind must be routing or answer")
    if not cases or not predictions:
        # An empty run is a protocol error, not a perfect score: rates below
        # divide by case and claim counts.
        raise ValueError("scoring requires at least one case and one prediction")
    case_map = _case_map(cases, label="case")
    prediction_map = _case_map(predictions, label="prediction")
    _require_same_cases(case_map, prediction_map, label="prediction")
    if kind == "routing" and reviews:
        raise ValueError("routing scoring does not accept semantic reviews")

    report: dict[str, Any] = {
        "kind": kind,
        "case_count": len(cases),
        "prediction_count": len(predictions),
        "coverage": 1.0,
    }
    if kind == "routing":
        correct = sum(
            row.get("prediction") == case_map[row["case_id"]].get("expected")
            for row in predictions
        )
        report["route_correctness"] = correct / len(predictions)
        continuity_rows = [
            row
            for row in predictions
            if set(case_map[row["case_id"]].get("coverage_tags") or ())
            & {"continue", "correct", "recast", "resume"}
        ]
        report["continuity_correctness"] = (
            sum(
                row.get("prediction") == case_map[row["case_id"]].get("expected")
                for row in continuity_rows
            )
            / len(continuity_rows)
            if continuity_rows
            else None
        )
    else:
        trace_count = 0
        reference_violations = 0
        for row in predictions:
            case = case_map[row["case_id"]]
            brief = case.get("brief")
            if not isinstance(brief, dict):
                raise ValueError(f"public brief missing: {row['case_id']}")
            expected_brief_sha256 = case.get("brief_sha256")
            if (
                not isinstance(expected_brief_sha256, str)
                or canonical_value_sha256(brief) != expected_brief_sha256
            ):
                raise ValueError(f"frozen brief digest mismatch: {row['case_id']}")
            if row.get("brief_sha256") != expected_brief_sha256:
                raise ValueError(f"brief identity drift: {row['case_id']}")
            if "artifact_identity" in row:
                raise ValueError(
                    f"answer replay starts at ReadingBrief, not private artifacts:"
                    f" {row['case_id']}"
                )
            allowed_facts = {
                str(item["ref"])
                for item in brief.get("facts") or ()
                if isinstance(item, dict) and item.get("ref")
            }
            allowed_evidence = {
                str(item["ref"])
                for item in brief.get("evidence") or ()
                if isinstance(item, dict) and item.get("ref")
            }
            prediction = row.get("prediction") or {}
            if not isinstance(prediction, dict) or not str(prediction.get("main_answer") or "").strip():
                raise ValueError(f"main answer missing: {row['case_id']}")
            traces = prediction.get("claim_traces") or ()
            if not isinstance(traces, list) or not traces:
                raise ValueError(f"claim traces missing: {row['case_id']}")
            for trace in traces:
                if not isinstance(trace, dict):
                    raise ValueError(f"invalid claim trace: {row['case_id']}")
                trace_count += 1
                if (
                    not set(trace.get("fact_refs") or ()) <= allowed_facts
                    or not set(trace.get("evidence_refs") or ()) <= allowed_evidence
                    or bool(trace.get("counter_evidence_refs") or ())
                ):
                    reference_violations += 1
        (
            validated_reviews,
            unsupported_count,
            reviewed_claim_count,
            untraced_claim_count,
        ) = _validate_answer_reviews(
            predictions=predictions,
            reviews=reviews,
            run_label=run_label,
        )
        report.update(
            {
                "brief_invariance_rate": 1.0,
                "reference_violation_rate": reference_violations / trace_count,
                "unsupported_claim_rate": unsupported_count / reviewed_claim_count,
                "evidence_relevance_rate": mean(
                    int(row["evidence_relevant"]) for row in validated_reviews
                ),
                "direct_answer_rate": mean(
                    int(row["direct_answer"]) for row in validated_reviews
                ),
                "naturalness_mean": _average(validated_reviews, "naturalness"),
                "main_point_clear_rate": mean(
                    int(row["main_point_clear"]) for row in validated_reviews
                ),
                "plain_language_mean": _average(validated_reviews, "plain_language"),
                "useful_specificity_mean": _average(
                    validated_reviews, "useful_specificity"
                ),
                "certainty_calibrated_rate": mean(
                    int(row["certainty_calibrated"]) for row in validated_reviews
                ),
                "ambient_memory_contamination_rate": 1.0
                - mean(
                    int(row["ambient_context_clean"])
                    for row in validated_reviews
                ),
                "template_smell_rate": mean(
                    int(row["template_smell"]) for row in validated_reviews
                ),
                "independent_review_coverage": 1.0,
                "main_answer_claim_review_coverage": 1.0,
                "reviewed_claim_count": reviewed_claim_count,
                "untraced_claim_rate": untraced_claim_count / reviewed_claim_count,
                "review_independence_attestation_only": True,
                "reviewer_kind_counts": {
                    kind: sum(
                        row["reviewer"]["reviewer_kind"] == kind
                        for row in validated_reviews
                    )
                    for kind in ("human", "independent_agent")
                },
            }
        )

    usage = _validate_usage(predictions)
    report["usage"] = {
        "coverage": len(usage) / len(predictions),
        "input_tokens_mean": _average(usage, "input_tokens") if usage else None,
        "output_tokens_mean": _average(usage, "output_tokens") if usage else None,
        "latency_ms_mean": _average(usage, "latency_ms") if usage else None,
        "reported_cost_mean": _average(usage, "reported_cost") if usage else None,
    }
    return report


def evaluate_files(
    *,
    cases_path: Path,
    prediction_paths: tuple[Path, ...],
    kind: str,
    review_paths: tuple[Path, ...] = (),
) -> dict[str, Any]:
    if kind == "answer" and len(review_paths) != len(prediction_paths):
        raise ValueError("answer runs require one separate review file per prediction file")
    if kind == "routing" and review_paths:
        raise ValueError("routing runs do not accept review files")
    cases = load_jsonl(cases_path)
    runs: list[dict[str, Any]] = []
    for index, path in enumerate(prediction_paths):
        label = path.stem
        review_path = review_paths[index] if kind == "answer" else None
        runs.append(
            {
                "label": label,
                "reviews_path": str(review_path) if review_path else None,
                **score_predictions(
                    cases,
                    load_jsonl(path),
                    kind=kind,
                    reviews=load_jsonl(review_path) if review_path else None,
                    run_label=label if review_path else None,
                ),
            }
        )
    return {
        "schema_version": "mingli-model-replay-report-v2",
        "kind": kind,
        "cases_path": str(cases_path),
        "runs": runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("routing", "answer"), required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, nargs="+", required=True)
    parser.add_argument("--reviews", type=Path, nargs="*", default=())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate_files(
        cases_path=args.cases,
        prediction_paths=tuple(args.predictions),
        review_paths=tuple(args.reviews),
        kind=args.kind,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
