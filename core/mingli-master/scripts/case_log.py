#!/usr/bin/env python3
"""Offline, opt-in append-only claim/outcome ledger for Mingli research."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


CLAIM_SCHEMA_VERSION = "mingli-lab-claim-v1"
OUTCOME_SCHEMA_VERSION = "mingli-lab-outcome-v1"
CASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
RESOLVED_OUTCOMES = frozenset({"hit", "partial", "miss", "unscorable"})
VALID_OUTCOMES = RESOLVED_OUTCOMES | {"unknown"}
SCORABLE_OUTCOMES = frozenset({"hit", "partial", "miss"})


def canonical_digest(value: Any) -> str:
    rendered = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _required_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _case_id(value: Any) -> str:
    case_id = str(value or "")
    if not CASE_ID_RE.fullmatch(case_id):
        raise ValueError("case_id must be a safe lowercase identifier")
    return case_id


def _string_list(name: str, values: Any, *, required: bool = False) -> list[str]:
    if not isinstance(values, (list, tuple)) or not all(
        isinstance(item, str) and item.strip() for item in values
    ):
        raise ValueError(f"{name} must be a list of non-empty strings")
    normalized = [item.strip() for item in values]
    if required and not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


def _optional_probability(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("probability must be numeric")
    probability = float(value)
    if probability < 0.0 or probability > 1.0:
        raise ValueError("probability must be between zero and one")
    return probability


def _optional_interval(value: Any) -> list[float] | None:
    if value is None:
        return None
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value)
    ):
        raise ValueError("prediction_interval must contain two numeric bounds")
    lower, upper = float(value[0]), float(value[1])
    if lower > upper:
        raise ValueError("prediction_interval bounds are reversed")
    return [lower, upper]


def build_claim(
    *,
    case_id: str,
    system: str,
    question: str,
    prediction_text: str,
    published_at: str,
    resolution_window: str,
    method: str,
    source_references: list[str],
    evidence_strength: str | None = None,
    probability: float | None = None,
    prediction_interval: list[float] | tuple[float, float] | None = None,
    fact_snapshot_digest: str | None = None,
    counter_evidence: list[str] | None = None,
) -> dict[str, Any]:
    """Build one immutable prospective claim; it never contains an outcome."""
    normalized_probability = _optional_probability(probability)
    normalized_interval = _optional_interval(prediction_interval)
    if fact_snapshot_digest is not None and re.fullmatch(
        r"[0-9a-f]{64}", fact_snapshot_digest
    ) is None:
        raise ValueError("fact_snapshot_digest must be a SHA-256 digest")
    core = {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "record_type": "claim",
        "case_id": _case_id(case_id),
        "system": _required_text("system", system),
        "question": _required_text("question", question),
        "prediction_text": _required_text("prediction_text", prediction_text),
        "published_at": _required_text("published_at", published_at),
        "resolution_window": _required_text(
            "resolution_window", resolution_window
        ),
        "method": _required_text("method", method),
        "source_references": _string_list(
            "source_references", source_references, required=True
        ),
        "fact_snapshot_digest": fact_snapshot_digest,
        "evidence_strength": (
            _required_text("evidence_strength", evidence_strength)
            if evidence_strength is not None
            else None
        ),
        # Numeric probability is optional and must be explicitly supplied by
        # an empirical protocol. Evidence strength is never mapped into it.
        "probability": normalized_probability,
        "prediction_interval": normalized_interval,
        "counter_evidence": _string_list(
            "counter_evidence", counter_evidence or []
        ),
    }
    return {**core, "claim_digest": canonical_digest(core)}


def build_outcome(
    *,
    claim: dict[str, Any],
    status: str = "unknown",
    observed_at: str | None = None,
    provenance: dict[str, Any] | None = None,
    observed_value: float | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Build a separate immutable outcome; absent feedback stays ``unknown``."""
    validated = validate_record(claim)
    if not validated["ok"] or claim.get("record_type") != "claim":
        raise ValueError("outcome requires a valid claim record")
    if status not in VALID_OUTCOMES:
        raise ValueError(f"invalid outcome status: {status}")
    if status == "unknown":
        if observed_at is not None or provenance is not None:
            raise ValueError("unknown outcome cannot claim an observation")
    else:
        _required_text("observed_at", observed_at)
        if not isinstance(provenance, dict) or not provenance:
            raise ValueError("resolved outcome requires provenance")
    if observed_value is not None and (
        isinstance(observed_value, bool)
        or not isinstance(observed_value, (int, float))
    ):
        raise ValueError("observed_value must be numeric")
    core = {
        "schema_version": OUTCOME_SCHEMA_VERSION,
        "record_type": "outcome",
        "case_id": claim["case_id"],
        "claim_digest": claim["claim_digest"],
        "status": status,
        "observed_at": observed_at,
        "observed_value": (
            float(observed_value) if observed_value is not None else None
        ),
        "provenance": provenance,
        "notes": str(notes or ""),
    }
    return {**core, "outcome_digest": canonical_digest(core)}


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    if not isinstance(record, dict):
        return {
            "ok": False,
            "findings": [{"level": "error", "code": "record_not_object"}],
            "codes": ["record_not_object"],
        }
    try:
        record_type = record.get("record_type")
        if record_type == "claim":
            rebuilt = build_claim(
                case_id=record.get("case_id"),
                system=record.get("system"),
                question=record.get("question"),
                prediction_text=record.get("prediction_text"),
                published_at=record.get("published_at"),
                resolution_window=record.get("resolution_window"),
                method=record.get("method"),
                source_references=record.get("source_references"),
                evidence_strength=record.get("evidence_strength"),
                probability=record.get("probability"),
                prediction_interval=record.get("prediction_interval"),
                fact_snapshot_digest=record.get("fact_snapshot_digest"),
                counter_evidence=record.get("counter_evidence") or [],
            )
            if record != rebuilt:
                raise ValueError("claim digest or fields do not match")
        elif record_type == "outcome":
            if record.get("schema_version") != OUTCOME_SCHEMA_VERSION:
                raise ValueError("invalid outcome schema")
            _case_id(record.get("case_id"))
            claim_digest = str(record.get("claim_digest") or "")
            if re.fullmatch(r"[0-9a-f]{64}", claim_digest) is None:
                raise ValueError("invalid claim digest")
            status = record.get("status")
            if status not in VALID_OUTCOMES:
                raise ValueError("invalid outcome status")
            if status == "unknown":
                if record.get("observed_at") is not None or record.get("provenance") is not None:
                    raise ValueError("unknown outcome cannot claim an observation")
            elif (
                not isinstance(record.get("observed_at"), str)
                or not record["observed_at"].strip()
                or not isinstance(record.get("provenance"), dict)
                or not record["provenance"]
            ):
                raise ValueError("resolved outcome requires observation provenance")
            core = {key: value for key, value in record.items() if key != "outcome_digest"}
            if record.get("outcome_digest") != canonical_digest(core):
                raise ValueError("outcome digest mismatch")
        else:
            raise ValueError("invalid record type")
    except (TypeError, ValueError) as exc:
        findings.append(
            {"level": "error", "code": "invalid_record", "message": str(exc)}
        )
    return {
        "ok": not findings,
        "findings": findings,
        "codes": [item["code"] for item in findings],
    }


def append_record(path: str | Path, record: dict[str, Any]) -> None:
    """Append an immutable record; identical digests are idempotent."""
    result = validate_record(record)
    if not result["ok"]:
        raise ValueError(json.dumps(result, ensure_ascii=False))
    path = Path(path)
    existing = load_records(path)
    digest_field = "claim_digest" if record["record_type"] == "claim" else "outcome_digest"
    digest = record[digest_field]
    if any(item.get(digest_field) == digest for item in existing):
        return
    if record["record_type"] == "claim" and any(
        item.get("record_type") == "claim" and item.get("case_id") == record["case_id"]
        for item in existing
    ):
        raise ValueError("a different immutable claim already exists for case_id")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.chmod(path, 0o600)
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        os.write(descriptor, line.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def load_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        result = validate_record(record)
        if not result["ok"]:
            raise ValueError(json.dumps(result, ensure_ascii=False))
        records.append(record)
    return records


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    claims = {
        record["claim_digest"]: record
        for record in records
        if record.get("record_type") == "claim"
    }
    outcomes: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.get("record_type") == "outcome":
            outcomes[record["claim_digest"]] = record

    scorable: list[tuple[dict[str, Any], dict[str, Any]]] = []
    unknown = 0
    for digest, claim in claims.items():
        outcome = outcomes.get(digest)
        if outcome is None or outcome.get("status") == "unknown":
            unknown += 1
        elif outcome.get("status") in SCORABLE_OUTCOMES:
            scorable.append((claim, outcome))

    hits = sum(outcome["status"] == "hit" for _claim, outcome in scorable)
    partials = sum(outcome["status"] == "partial" for _claim, outcome in scorable)
    misses = sum(outcome["status"] == "miss" for _claim, outcome in scorable)

    brier_terms: list[float] = []
    interval_scores: dict[str, float] = {}
    for claim, outcome in scorable:
        probability = claim.get("probability")
        observed = outcome.get("observed_value")
        if probability is not None and observed in {0.0, 1.0}:
            brier_terms.append((float(probability) - float(observed)) ** 2)
        interval = claim.get("prediction_interval")
        if interval is not None and isinstance(observed, (int, float)):
            lower, upper = float(interval[0]), float(interval[1])
            value = float(observed)
            # Width plus symmetric miss distance. This is an offline interval
            # diagnostic, never a runtime confidence conversion.
            score = upper - lower
            if value < lower:
                score += 2.0 * (lower - value)
            elif value > upper:
                score += 2.0 * (value - upper)
            interval_scores[claim["case_id"]] = round(score, 4)

    count = len(scorable)
    return {
        "total_claims": len(claims),
        "scorable_claims": count,
        "unknown_outcomes": unknown,
        "hits": hits,
        "partials": partials,
        "misses": misses,
        "hit_rate": round(hits / count, 4) if count else None,
        "partial_rate": round(partials / count, 4) if count else None,
        "brier_score": (
            round(sum(brier_terms) / len(brier_terms), 4) if brier_terms else None
        ),
        "brier_reason": None if brier_terms else "no explicit numeric probabilities",
        "interval_scores": interval_scores,
    }


def summarize_v7_scores(scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize blind scores without turning verbal confidence into odds."""
    valid_results = {"hit", "partial", "miss", "abstain", "unknown"}
    for score in scores:
        if not isinstance(score, dict) or score.get("result") not in valid_results:
            raise ValueError("invalid v7 score record")
    known = [score for score in scores if score["result"] != "unknown"]
    hits = sum(score["result"] == "hit" for score in known)
    misses = sum(score["result"] == "miss" for score in known)
    partials = sum(score["result"] == "partial" for score in known)
    abstentions = sum(score["result"] == "abstain" for score in known)
    directional = hits + misses
    return {
        "total_cases": len(scores),
        "known_outcomes": len(known),
        "unknown_outcomes": len(scores) - len(known),
        "hits": hits,
        "misses": misses,
        "partials": partials,
        "abstentions": abstentions,
        "directional_predictions": directional,
        "directional_coverage": round(directional / len(known), 4) if known else None,
        "directional_accuracy": round(hits / directional, 4) if directional else None,
        "partial_rate": round(partials / len(known), 4) if known else None,
        "abstention_rate": round(abstentions / len(known), 4) if known else None,
        "brier_score": None,
        "brier_reason": "verbal confidence is not a calibrated numeric probability",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("summary", "validate"):
        child = subparsers.add_parser(command)
        child.add_argument("--file", required=True)
    args = parser.parse_args()
    try:
        records = load_records(args.file)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.command == "summary":
        print(json.dumps(summarize_records(records), ensure_ascii=False, indent=2))
        return 0
    findings = [record for record in records if not validate_record(record)["ok"]]
    print(json.dumps({"ok": not findings, "findings": findings}, ensure_ascii=False, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
