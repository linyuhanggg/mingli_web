"""Fail-closed Runtime authority contract for the life K-line product.

The current Runtime can calculate ordered Bazi luck/transit facts, but it has
no versioned, empirically calibrated, cross-period numeric measure.  A candle
series would therefore be fabricated.  This module makes that absence a
deterministic Runtime fact instead of leaving a host to infer or fill values.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "mingli-life-kline-facts-v1"
CONTRACT_VERSION = "life-kline-authority-v1"
STATUS = "unavailable_algorithm_gap"
GAP_ID = "life-kline.comparable-measure-and-candle-sampling.v1"

VALUE_AXIS_UNAVAILABLE_REASON = "missing_versioned_comparable_measure"
CANDLE_UNAVAILABLE_REASON = "missing_versioned_candle_sampling_semantics"
CHANGE_UNAVAILABLE_REASON = "missing_authoritative_close_values"

_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

_RELEASE_MANIFEST = ".mingli-release-manifest.json"
_RELEASE_VERSION = "release/version.json"

_AUDITED_SOURCE_CONTRACTS = (
    {
        "schema_version": "mingli-bazi-fact-v1",
        "authority_scope": "luck_cycle_and_transit_time_facts",
        "comparable_numeric_measure_available": False,
    },
    {
        "schema_version": "mingli-near-time-fortune-v2",
        "authority_scope": "major_luck_year_month_day_mechanism_stack",
        "comparable_numeric_measure_available": False,
    },
)

_CANDIDATE_TIME_AXES = (
    {
        "kind": "major_luck",
        "unit": "age_years",
        "source_schema_version": "mingli-bazi-fact-v1",
        "source_path": "output.luck_cycles.cycles[]",
        "role": "temporal_key_only",
        "series_ready": False,
    },
    {
        "kind": "gregorian_year",
        "unit": "calendar_year",
        "source_schema_version": "mingli-bazi-fact-v1",
        "source_path": "fact_extension.facts.year_layers",
        "role": "temporal_key_only",
        "series_ready": False,
    },
    {
        "kind": "gregorian_month",
        "unit": "calendar_month",
        "source_schema_version": "mingli-bazi-fact-v1",
        "source_path": "fact_extension.facts.month_layers",
        "role": "temporal_key_only",
        "series_ready": False,
    },
    {
        "kind": "civil_day",
        "unit": "civil_day",
        "source_schema_version": "mingli-bazi-fact-v1",
        "source_path": "fact_extension.facts.day_layers",
        "role": "temporal_key_only",
        "series_ready": False,
    },
)

_MISSING_INPUTS = (
    "versioned_comparable_measure_definition",
    "calibration_and_validation_corpus",
)

_MISSING_SEMANTICS = (
    "measure_unit_and_range",
    "measure_polarity",
    "cross_period_comparability",
    "open_and_close_sampling_points",
    "high_and_low_intra_period_resolution",
    "flat_direction_threshold",
    "missing_observation_policy",
)

_REQUIRED_VERSIONED_FIELDS = (
    "measure.id",
    "measure.version",
    "measure.unit",
    "measure.range",
    "measure.polarity",
    "sampling.rule_id",
    "sampling.rule_version",
    "comparability.key",
    "series[].fact_refs",
    "meta.profile_version_id",
    "meta.reading_document_version",
    "meta.runtime_release",
    "meta.runtime_manifest_digest",
    "meta.source_fact_digest",
)

_MINIMUM_IMPLEMENTATION_SLICE = (
    "freeze_one_comparable_measure_and_its_evidence_authority",
    "implement_the_measure_as_a_deterministic_versioned_pure_function",
    "freeze_candle_sampling_semantics_or_remove_ohlc_from_the_product_contract",
    "derive_direction_and_delta_only_from_authoritative_close_values",
    "validate_boundaries_missingness_idempotency_and_calibration_before_ready",
)


class LifeKlineContractError(ValueError):
    """The payload is not the exact fail-closed v1 authority contract."""


def load_runtime_release_identity(skill_root: str | Path) -> dict[str, str]:
    """Read the immutable identity carried by one signed Runtime release.

    The portable adapter runs from a materialized release whose root contains
    both the canonical version file and the signed release manifest.  Reading
    those files keeps release identity inside the Runtime boundary; a host
    cannot provide a source commit or substitute its own digest.
    """

    root = Path(skill_root).resolve()
    release_dir = root / "release"
    version_path = root / _RELEASE_VERSION
    manifest_path = root / _RELEASE_MANIFEST
    if (
        release_dir.is_symlink()
        or version_path.is_symlink()
        or manifest_path.is_symlink()
        or not version_path.is_file()
        or not manifest_path.is_file()
    ):
        raise LifeKlineContractError(
            "signed Runtime release identity is unavailable"
        )
    try:
        version_bytes = version_path.read_bytes()
        version_payload = json.loads(version_bytes)
        manifest_bytes = manifest_path.read_bytes()
        manifest_payload = json.loads(manifest_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifeKlineContractError(
            "signed Runtime release identity is unavailable"
        ) from exc
    if not isinstance(version_payload, Mapping) or not isinstance(
        manifest_payload, Mapping
    ):
        raise LifeKlineContractError(
            "signed Runtime release identity must be JSON objects"
        )
    release_name = version_payload.get("name")
    release_version = version_payload.get("version")
    if (
        manifest_payload.get("schema_version") != 3
        or not isinstance(manifest_payload.get("release"), str)
        or not str(manifest_payload["release"]).strip()
    ):
        raise LifeKlineContractError("signed Runtime release manifest is invalid")
    release_files = manifest_payload.get("files")
    expected_version_digest = (
        release_files.get(_RELEASE_VERSION)
        if isinstance(release_files, Mapping)
        else None
    )
    if (
        not isinstance(expected_version_digest, str)
        or _SHA256_RE.fullmatch(expected_version_digest) is None
        or hashlib.sha256(version_bytes).hexdigest() != expected_version_digest
    ):
        raise LifeKlineContractError(
            "Runtime version is not bound by the signed release manifest"
        )
    return {
        "runtime_release": (
            f"{_opaque_id(release_name, 'release.name')}/"
            f"{_opaque_id(release_version, 'release.version')}"
        ),
        "runtime_source_commit": _source_commit(
            manifest_payload.get("source_commit")
        ),
        "runtime_manifest_digest": hashlib.sha256(manifest_bytes).hexdigest(),
    }


def _opaque_id(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _OPAQUE_ID_RE.fullmatch(value) is None:
        raise LifeKlineContractError(f"{field_name} must be an opaque identifier")
    return value


def _digest(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise LifeKlineContractError(f"{field_name} must be a lowercase SHA-256")
    return value


def _source_commit(value: object) -> str:
    if not isinstance(value, str) or _SOURCE_COMMIT_RE.fullmatch(value) is None:
        raise LifeKlineContractError(
            "runtime_source_commit must be a lowercase 40-character Git SHA"
        )
    return value


def _canonical_digest(payload: Mapping[str, object]) -> str:
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def build_unavailable_life_kline_facts(
    *,
    subject_ref: str,
    profile_version_id: str,
    runtime_release: str,
    runtime_source_commit: str,
    runtime_manifest_digest: str,
    source_fact_digest: str,
) -> dict[str, Any]:
    """Build the only truthful v1 result for the current Runtime.

    The identity inputs are already-authoritative opaque values supplied by
    the Runtime host.  They are bound into ``cache_identity``.  No clock,
    randomness, environment state, chart counts, or interpretation is read.
    """

    identity = {
        "subject_ref": _opaque_id(subject_ref, "subject_ref"),
        "profile_version_id": _opaque_id(
            profile_version_id,
            "profile_version_id",
        ),
        "runtime_release": _opaque_id(runtime_release, "runtime_release"),
        "runtime_source_commit": _source_commit(runtime_source_commit),
        "runtime_manifest_digest": _digest(
            runtime_manifest_digest,
            "runtime_manifest_digest",
        ),
        "source_fact_digest": _digest(source_fact_digest, "source_fact_digest"),
    }
    cache_identity = _canonical_digest(
        {
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            **identity,
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "status": STATUS,
        "identity": {**identity, "cache_identity": cache_identity},
        "audited_source_contracts": [
            dict(item) for item in _AUDITED_SOURCE_CONTRACTS
        ],
        "candidate_time_axes": [dict(item) for item in _CANDIDATE_TIME_AXES],
        "value_axis": {
            "available": False,
            "measure_id": None,
            "unit": None,
            "range": None,
            "comparability_key": None,
            "unavailable_reason": VALUE_AXIS_UNAVAILABLE_REASON,
        },
        "candles": {
            "available": False,
            "field_set": None,
            "sampling_rule_id": None,
            "sampling_rule_version": None,
            "unavailable_reason": CANDLE_UNAVAILABLE_REASON,
        },
        "change": {
            "available": False,
            "direction_rule_id": None,
            "delta_unit": None,
            "unavailable_reason": CHANGE_UNAVAILABLE_REASON,
        },
        "series": [],
        "algorithm_gap": {
            "gap_id": GAP_ID,
            "user_input_can_resolve": False,
            "missing_inputs": list(_MISSING_INPUTS),
            "missing_semantics": list(_MISSING_SEMANTICS),
            "required_versioned_fields": list(_REQUIRED_VERSIONED_FIELDS),
            "minimum_implementation_slice": list(_MINIMUM_IMPLEMENTATION_SLICE),
        },
    }


def validate_life_kline_facts(payload: Mapping[str, object]) -> None:
    """Reject any value that is not the exact current fail-closed payload."""

    if not isinstance(payload, Mapping):
        raise LifeKlineContractError("life K-line facts must be a JSON object")
    identity = payload.get("identity")
    if not isinstance(identity, Mapping):
        raise LifeKlineContractError("life K-line identity is missing")
    try:
        expected = build_unavailable_life_kline_facts(
            subject_ref=identity["subject_ref"],  # type: ignore[arg-type]
            profile_version_id=identity["profile_version_id"],  # type: ignore[arg-type]
            runtime_release=identity["runtime_release"],  # type: ignore[arg-type]
            runtime_source_commit=identity[
                "runtime_source_commit"
            ],  # type: ignore[arg-type]
            runtime_manifest_digest=identity[
                "runtime_manifest_digest"
            ],  # type: ignore[arg-type]
            source_fact_digest=identity["source_fact_digest"],  # type: ignore[arg-type]
        )
    except KeyError as exc:
        raise LifeKlineContractError(
            f"life K-line identity is missing {exc.args[0]}"
        ) from None
    if payload != expected:
        raise LifeKlineContractError(
            "life K-line facts differ from the exact fail-closed v1 contract"
        )


__all__ = [
    "CANDLE_UNAVAILABLE_REASON",
    "CHANGE_UNAVAILABLE_REASON",
    "CONTRACT_VERSION",
    "GAP_ID",
    "LifeKlineContractError",
    "SCHEMA_VERSION",
    "STATUS",
    "VALUE_AXIS_UNAVAILABLE_REASON",
    "build_unavailable_life_kline_facts",
    "load_runtime_release_identity",
    "validate_life_kline_facts",
]
