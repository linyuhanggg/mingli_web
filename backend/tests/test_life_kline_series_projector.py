from __future__ import annotations

import copy
import hashlib
import json

from app.charts.contracts import parse_view_model
from app.charts.projectors import project_runtime_view_model


def _digest(payload: dict[str, object]) -> str:
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _runtime_life_kline_fact(
    *,
    subject_ref: str = "profile-version:test",
) -> dict[str, object]:
    identity = {
        "subject_ref": subject_ref,
        "profile_version_id": subject_ref,
        "runtime_release": "mingli-master/5.1",
        "runtime_source_commit": "a" * 40,
        "runtime_manifest_digest": "b" * 64,
        "source_fact_digest": "c" * 64,
    }
    cache_identity = _digest(
        {
            "schema_version": "mingli-life-kline-facts-v1",
            "contract_version": "life-kline-authority-v1",
            **identity,
        }
    )
    return {
        "schema_version": "mingli-life-kline-facts-v1",
        "contract_version": "life-kline-authority-v1",
        "status": "unavailable_algorithm_gap",
        "identity": {**identity, "cache_identity": cache_identity},
        "audited_source_contracts": [
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
        ],
        "candidate_time_axes": [
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
        ],
        "value_axis": {
            "available": False,
            "measure_id": None,
            "unit": None,
            "range": None,
            "comparability_key": None,
            "unavailable_reason": "missing_versioned_comparable_measure",
        },
        "candles": {
            "available": False,
            "field_set": None,
            "sampling_rule_id": None,
            "sampling_rule_version": None,
            "unavailable_reason": "missing_versioned_candle_sampling_semantics",
        },
        "change": {
            "available": False,
            "direction_rule_id": None,
            "delta_unit": None,
            "unavailable_reason": "missing_authoritative_close_values",
        },
        "series": [],
        "algorithm_gap": {
            "gap_id": "life-kline.comparable-measure-and-candle-sampling.v1",
            "user_input_can_resolve": False,
            "missing_inputs": [
                "versioned_comparable_measure_definition",
                "calibration_and_validation_corpus",
            ],
            "missing_semantics": [
                "measure_unit_and_range",
                "measure_polarity",
                "cross_period_comparability",
                "open_and_close_sampling_points",
                "high_and_low_intra_period_resolution",
                "flat_direction_threshold",
                "missing_observation_policy",
            ],
            "required_versioned_fields": [
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
            ],
            "minimum_implementation_slice": [
                "freeze_one_comparable_measure_and_its_evidence_authority",
                "implement_the_measure_as_a_deterministic_versioned_pure_function",
                "freeze_candle_sampling_semantics_or_remove_ohlc_from_the_product_contract",
                "derive_direction_and_delta_only_from_authoritative_close_values",
                "validate_boundaries_missingness_idempotency_and_calibration_before_ready",
            ],
        },
    }


def _life_kline_brief(
    *,
    object_id: str = "life_kline",
    fact_value: dict[str, object] | None = None,
    subject_ref: str = "profile-version:test",
) -> dict[str, object]:
    facts: list[dict[str, object]] = [
        {
            "ref": f"fact:{subject_ref}/input/birth_datetime",
            "subject_ref": subject_ref,
            "kind_id": "kind.fact",
            "value": "1994-04-30T05:55:00+08:00",
            "display_text": "出生时间",
        }
    ]
    if fact_value is not None:
        facts.append(
            {
                "ref": f"fact:{subject_ref}/calculated/bazi/life_kline",
                "subject_ref": subject_ref,
                "kind_id": "kind.fact",
                "value": fact_value,
                "display_text": "人生K线权威事实",
            }
        )
    return {
        "question": "请展示人生K线",
        "vocabulary": [],
        "facts": facts,
        "evidence": [],
        "findings": [],
        "claim_scopes": [],
        "limits": [],
        "prior_answer": None,
        "request_view": {
            "subject_refs": [subject_ref],
            "capability_ids": ["bazi"],
            "object_id": object_id,
            "dimension_ids": ["overview"],
            "horizon": {"kind_id": "life", "start": None, "end": None},
        },
    }


def test_projects_exact_unavailable_life_kline_series_without_ohlc() -> None:
    fact = _runtime_life_kline_fact()
    view_model = project_runtime_view_model(
        _life_kline_brief(fact_value=fact),
        product_id="life-kline-series",
    )

    assert view_model is not None
    assert view_model.schema_version == "life-kline-series/v1"
    assert view_model.status == "unavailable_algorithm_gap"
    assert view_model.series == ()
    assert view_model.value_axis.available is False
    assert view_model.candles.available is False
    assert view_model.change.available is False
    assert view_model.algorithm_gap.user_input_can_resolve is False
    assert view_model.identity.cache_identity == fact["identity"]["cache_identity"]
    assert all(axis.series_ready is False for axis in view_model.candidate_time_axes)
    parsed = parse_view_model(view_model.model_dump(mode="json"))
    assert parsed.schema_version == "life-kline-series/v1"


def test_life_kline_projection_is_idempotent_for_same_runtime_identity() -> None:
    fact = _runtime_life_kline_fact()
    first = project_runtime_view_model(
        _life_kline_brief(fact_value=fact),
        product_id="life-kline-series",
    )
    second = project_runtime_view_model(
        _life_kline_brief(fact_value=copy.deepcopy(fact)),
        product_id="life-kline-series",
    )

    assert first is not None and second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_rejects_natal_object_as_life_kline_series() -> None:
    assert (
        project_runtime_view_model(
            _life_kline_brief(
                object_id="natal",
                fact_value=_runtime_life_kline_fact(),
            ),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_missing_life_kline_fact() -> None:
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=None),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_host_fabricated_ohlc_or_ready_status() -> None:
    fabricated = _runtime_life_kline_fact()
    fabricated["series"] = [
        {
            "open": 10,
            "high": 20,
            "low": 5,
            "close": 15,
            "direction": "up",
            "delta": 5,
        }
    ]
    fabricated["status"] = "ready"
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=fabricated),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_cross_profile_identity_mismatch() -> None:
    mismatched = _runtime_life_kline_fact(subject_ref="profile-version:other")
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=mismatched),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_user_resolvable_gap_flag() -> None:
    resolvable = _runtime_life_kline_fact()
    resolvable["algorithm_gap"]["user_input_can_resolve"] = True
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=resolvable),
            product_id="life-kline-series",
        )
        is None
    )
