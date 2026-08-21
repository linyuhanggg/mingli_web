#!/usr/bin/env python3
"""Offline sidecar: freeze Mingli claims before outcomes, then score later."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "mingli-frozen-prediction-v1"
SCORE_SCHEMA_VERSION = "mingli-blind-score-v1"
MC_SCHEMA_VERSION = "mingli-frozen-mc-prediction-v1"
MC_SCORE_SCHEMA_VERSION = "mingli-blind-mc-score-v1"
VERDICTS = {"support", "oppose", "mixed", "underdetermined"}
CONFIDENCE_BUCKETS = {"low", "medium", "high"}
FORBIDDEN_PREDICTION_KEYS = {
    "actual",
    "actual_result",
    "answer",
    "correct_option",
    "ground_truth",
    "label_after",
    "observed_outcome",
    "outcome",
    "result_after",
}
CASE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


class PredictionConflictError(ValueError):
    """Raised when a frozen case is presented with a different prediction."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _find_forbidden_key(value: Any, path: str = "$") -> str | None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key).strip().lower()
            child_path = f"{path}.{raw_key}"
            if key in FORBIDDEN_PREDICTION_KEYS:
                return child_path
            found = _find_forbidden_key(child, child_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_forbidden_key(child, f"{path}[{index}]")
            if found:
                return found
    return None


def _validate_case_input(case_input: dict[str, Any]) -> str:
    if not isinstance(case_input, dict):
        raise TypeError("prediction input must be a JSON object")
    leak_path = _find_forbidden_key(case_input)
    if leak_path:
        raise ValueError(f"outcome-like field is forbidden in prediction input: {leak_path}")
    case_id = str(case_input.get("case_id") or "")
    if not CASE_ID_RE.fullmatch(case_id):
        raise ValueError("case_id must be a safe lowercase identifier")
    if not isinstance(case_input.get("question"), str) or not case_input["question"].strip():
        raise ValueError("prediction input requires a non-empty question")
    if not isinstance(case_input.get("fact_snapshot"), dict):
        raise ValueError("prediction input requires a fact_snapshot object")
    return case_id


def _inference_view(inference: dict[str, Any], case_id: str) -> dict[str, Any]:
    if not isinstance(inference, dict):
        raise TypeError("inference must be a JSON object")
    leak_path = _find_forbidden_key(inference)
    if leak_path:
        raise ValueError(f"outcome-like field is forbidden in inference: {leak_path}")
    if inference.get("schema_version") == "mingli-inference-artifact-v1":
        # The v7 inference artifact belongs to the retired reading pipeline;
        # the ledger no longer accepts it, and Git history keeps the schema.
        raise ValueError("retired v7 inference artifact schema is not accepted")
    if inference.get("case_id") != case_id:
        raise ValueError("inference case_id does not match prediction input")
    if inference.get("verdict") not in VERDICTS:
        raise ValueError("inference verdict is invalid")
    if inference.get("confidence_bucket") not in CONFIDENCE_BUCKETS:
        raise ValueError("inference confidence_bucket is invalid")
    for field in ("decisive_activation_ids", "counter_evidence_ids"):
        values = inference.get(field)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError(f"inference {field} must be a list of strings")
    return {
        "schema_version": inference.get("schema_version"),
        "verdict": inference["verdict"],
        "confidence_bucket": inference["confidence_bucket"],
        "decisive_activation_ids": list(inference["decisive_activation_ids"]),
        "counter_evidence_ids": list(inference["counter_evidence_ids"]),
        "inference_digest": canonical_digest(inference),
    }


def _prediction_record(
    case_input: dict[str, Any],
    inference: dict[str, Any],
) -> dict[str, Any]:
    case_id = _validate_case_input(case_input)
    view = _inference_view(inference, case_id)
    prediction = {
        "schema_version": view["schema_version"],
        "verdict": view["verdict"],
        "confidence_bucket": view["confidence_bucket"],
        "decisive_activation_ids": list(view["decisive_activation_ids"]),
        "counter_evidence_ids": list(view["counter_evidence_ids"]),
        "inference_artifact_digest": view["inference_digest"],
    }
    record = {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "system": case_input.get("system"),
        "question_digest": canonical_digest(case_input["question"]),
        "facts_digest": canonical_digest(case_input["fact_snapshot"]),
        "input_digest": canonical_digest(case_input),
        "inference_digest": view["inference_digest"],
        "prediction_text": str(
            inference.get("prediction_text") or view["verdict"]
        ),
        "published_at": str(case_input.get("published_at") or "not-recorded"),
        "resolution_window": str(
            case_input.get("resolution_window") or "not-recorded"
        ),
        "method": str(
            case_input.get("method")
            or inference.get("schema_version")
            or "structured-inference"
        ),
        "source_references": list(
            case_input.get("source_references")
            or view["decisive_activation_ids"]
        ),
        "prediction": prediction,
    }
    record["prediction_digest"] = canonical_digest(record)
    return record


def _validate_record(record: dict[str, Any]) -> None:
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid frozen prediction schema")
    digest = record.get("prediction_digest")
    payload = {key: value for key, value in record.items() if key != "prediction_digest"}
    if not isinstance(digest, str) or digest != canonical_digest(payload):
        raise ValueError("frozen prediction digest mismatch")


class PredictionStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, case_id: str) -> Path:
        if not CASE_ID_RE.fullmatch(case_id):
            raise ValueError("case_id must be a safe lowercase identifier")
        return self.root / f"{case_id}.prediction.json"

    def freeze(
        self,
        case_input: dict[str, Any],
        inference: dict[str, Any],
    ) -> dict[str, Any]:
        expected = _prediction_record(case_input, inference)
        path = self._path(expected["case_id"])
        if path.exists():
            existing = self.load(expected["case_id"])
            if existing != expected:
                raise PredictionConflictError(
                    "prediction already frozen for the same case; polarity or evidence cannot change"
                )
            return existing

        self.root.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(expected, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=self.root,
            prefix=f".{expected['case_id']}.",
            suffix=".tmp",
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)
        return expected

    def load(self, case_id: str) -> dict[str, Any]:
        path = self._path(case_id)
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError("frozen prediction must be a JSON object")
        _validate_record(record)
        return record

    def score(
        self,
        frozen_prediction: dict[str, Any],
        case_outcome: dict[str, Any] | None,
    ) -> dict[str, Any]:
        _validate_record(frozen_prediction)
        if case_outcome is None:
            score = {
                "schema_version": SCORE_SCHEMA_VERSION,
                "case_id": frozen_prediction["case_id"],
                "prediction_digest": frozen_prediction["prediction_digest"],
                "predicted_polarity": frozen_prediction["prediction"]["verdict"],
                "observed_polarity": None,
                "result": "unknown",
                "observed_at": None,
                "outcome_provenance": None,
                "outcome_digest": None,
            }
            score["score_digest"] = canonical_digest(score)
            return score
        if not isinstance(case_outcome, dict):
            raise TypeError("case outcome must be a JSON object")
        if case_outcome.get("case_id") != frozen_prediction.get("case_id"):
            raise ValueError("outcome case_id does not match frozen prediction")
        outcome = case_outcome.get("outcome")
        if not isinstance(outcome, dict):
            raise ValueError("case outcome requires an outcome object")
        expected_polarity = outcome.get("scoring_polarity")
        if outcome.get("status") == "unknown":
            return self.score(frozen_prediction, None)
        if expected_polarity not in {"support", "oppose"}:
            raise ValueError("outcome scoring_polarity must be support or oppose")

        predicted = frozen_prediction["prediction"]["verdict"]
        if predicted == "underdetermined":
            result = "abstain"
        elif predicted == "mixed":
            result = "partial"
        elif predicted == expected_polarity:
            result = "hit"
        else:
            result = "miss"
        score = {
            "schema_version": SCORE_SCHEMA_VERSION,
            "case_id": frozen_prediction["case_id"],
            "prediction_digest": frozen_prediction["prediction_digest"],
            "predicted_polarity": predicted,
            "observed_polarity": expected_polarity,
            "result": result,
            "observed_at": outcome.get("observed_at"),
            "outcome_provenance": case_outcome.get("provenance"),
            "outcome_digest": canonical_digest(case_outcome),
        }
        score["score_digest"] = canonical_digest(score)
        return score


def _validate_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name} must be a SHA-256 digest")


def _mc_option_letters(case_input: dict[str, Any]) -> set[str]:
    options = case_input.get("options")
    if not isinstance(options, list) or len(options) < 2:
        raise ValueError("multiple-choice input requires options")
    letters: set[str] = set()
    for index, option in enumerate(options):
        if not isinstance(option, str):
            raise ValueError("multiple-choice options must be strings")
        match = re.match(r"\s*([A-Za-z])(?=[^A-Za-z]|$)", option)
        label = (
            match.group(1).upper()
            if match is not None
            else chr(ord("A") + index)
        )
        if label in letters:
            raise ValueError("multiple-choice options require unique letter labels")
        letters.add(label)
    return letters


def _validate_mc_record(record: dict[str, Any]) -> None:
    if record.get("schema_version") != MC_SCHEMA_VERSION:
        raise ValueError("invalid frozen multiple-choice prediction schema")
    digest = record.get("prediction_digest")
    payload = {key: value for key, value in record.items() if key != "prediction_digest"}
    if not isinstance(digest, str) or digest != canonical_digest(payload):
        raise ValueError("frozen multiple-choice prediction digest mismatch")


class MultipleChoicePredictionStore:
    """Immutable blind store for answer-isolated multiple-choice diagnostics."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, case_id: str) -> Path:
        if not CASE_ID_RE.fullmatch(case_id):
            raise ValueError("case_id must be a safe lowercase identifier")
        return self.root / f"{case_id}.mc-prediction.json"

    def freeze(
        self,
        case_input: dict[str, Any],
        *,
        inference_digest: str,
        prompt_digest: str,
        prediction: dict[str, Any],
        method: str | None = None,
        model_id: str | None = None,
    ) -> dict[str, Any]:
        case_id = _validate_case_input(case_input)
        allowed_choices = _mc_option_letters(case_input)
        _validate_sha256("inference_digest", inference_digest)
        _validate_sha256("prompt_digest", prompt_digest)
        resolved_method = method or model_id
        if not isinstance(resolved_method, str) or not resolved_method.strip():
            raise ValueError("multiple-choice prediction requires a method")
        if not isinstance(prediction, dict):
            raise TypeError("multiple-choice prediction must be an object")
        leak_path = _find_forbidden_key(prediction)
        if leak_path:
            raise ValueError(f"outcome-like field is forbidden in prediction: {leak_path}")
        choice = prediction.get("choice")
        if choice not in allowed_choices | {"ABSTAIN"}:
            raise ValueError("multiple-choice prediction choice is invalid")
        confidence = prediction.get("confidence_bucket")
        if confidence not in CONFIDENCE_BUCKETS:
            raise ValueError("multiple-choice confidence_bucket is invalid")
        reason = prediction.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("multiple-choice prediction requires a reason")
        activation_ids = prediction.get("used_activation_ids")
        if not isinstance(activation_ids, list) or not all(
            isinstance(item, str) for item in activation_ids
        ):
            raise ValueError("multiple-choice used_activation_ids must be strings")
        rule_ids = prediction.get("used_rule_ids") or []
        if not isinstance(rule_ids, list) or not all(
            isinstance(item, str) for item in rule_ids
        ):
            raise ValueError("multiple-choice used_rule_ids must be strings")

        record = {
            "schema_version": MC_SCHEMA_VERSION,
            "case_id": case_id,
            "system": case_input.get("system"),
            "question_digest": canonical_digest(case_input["question"]),
            "facts_digest": canonical_digest(case_input["fact_snapshot"]),
            "input_digest": canonical_digest(case_input),
            "inference_digest": inference_digest,
            "prompt_digest": prompt_digest,
            "method": resolved_method.strip(),
            "prediction": {
                "choice": choice,
                "confidence_bucket": confidence,
                "reason": reason.strip(),
                "used_activation_ids": list(activation_ids),
                "used_rule_ids": list(rule_ids),
            },
        }
        record["prediction_digest"] = canonical_digest(record)
        path = self._path(case_id)
        if path.exists():
            existing = self.load(case_id)
            if existing != record:
                raise PredictionConflictError(
                    "multiple-choice prediction already frozen for the same case"
                )
            return existing

        self.root.mkdir(parents=True, exist_ok=True)
        rendered = json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.root,
            prefix=f".{case_id}.",
            suffix=".tmp",
            text=True,
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)
        return record

    def load(self, case_id: str) -> dict[str, Any]:
        record = json.loads(self._path(case_id).read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError("frozen multiple-choice prediction must be an object")
        _validate_mc_record(record)
        return record

    def score(
        self,
        frozen_prediction: dict[str, Any],
        case_outcome: dict[str, Any],
    ) -> dict[str, Any]:
        _validate_mc_record(frozen_prediction)
        if not isinstance(case_outcome, dict):
            raise TypeError("multiple-choice outcome must be an object")
        if case_outcome.get("case_id") != frozen_prediction.get("case_id"):
            raise ValueError("outcome case_id does not match frozen prediction")
        correct = case_outcome.get("correct_option")
        if not isinstance(correct, str) or re.fullmatch(r"[A-Z]", correct) is None:
            raise ValueError("multiple-choice outcome requires correct_option")
        predicted = frozen_prediction["prediction"]["choice"]
        result = "abstain" if predicted == "ABSTAIN" else "hit" if predicted == correct else "miss"
        score = {
            "schema_version": MC_SCORE_SCHEMA_VERSION,
            "case_id": frozen_prediction["case_id"],
            "prediction_digest": frozen_prediction["prediction_digest"],
            "predicted_option": predicted,
            "correct_option": correct,
            "result": result,
            "outcome_digest": canonical_digest(case_outcome),
        }
        score["score_digest"] = canonical_digest(score)
        return score
