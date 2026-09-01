from __future__ import annotations

import copy
import hashlib
import json

from app.charts.contracts import (
    LIFE_KLINE_ALGORITHM_GAP_MINIMUM_IMPLEMENTATION_SLICE,
    LIFE_KLINE_ALGORITHM_GAP_MISSING_INPUTS,
    LIFE_KLINE_ALGORITHM_GAP_MISSING_SEMANTICS,
    LIFE_KLINE_ALGORITHM_GAP_REQUIRED_VERSIONED_FIELDS,
    LIFE_KLINE_CANDIDATE_TIME_AXES,
    parse_view_model,
)
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
            "missing_inputs": list(LIFE_KLINE_ALGORITHM_GAP_MISSING_INPUTS),
            "missing_semantics": list(LIFE_KLINE_ALGORITHM_GAP_MISSING_SEMANTICS),
            "required_versioned_fields": list(
                LIFE_KLINE_ALGORITHM_GAP_REQUIRED_VERSIONED_FIELDS
            ),
            "minimum_implementation_slice": list(
                LIFE_KLINE_ALGORITHM_GAP_MINIMUM_IMPLEMENTATION_SLICE
            ),
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
    assert (
        view_model.algorithm_gap.missing_inputs
        == LIFE_KLINE_ALGORITHM_GAP_MISSING_INPUTS
    )
    assert (
        view_model.algorithm_gap.missing_semantics
        == LIFE_KLINE_ALGORITHM_GAP_MISSING_SEMANTICS
    )
    assert (
        view_model.algorithm_gap.required_versioned_fields
        == LIFE_KLINE_ALGORITHM_GAP_REQUIRED_VERSIONED_FIELDS
    )
    assert (
        view_model.algorithm_gap.minimum_implementation_slice
        == LIFE_KLINE_ALGORITHM_GAP_MINIMUM_IMPLEMENTATION_SLICE
    )
    assert view_model.identity.cache_identity == fact["identity"]["cache_identity"]
    assert view_model.candidate_time_axes == LIFE_KLINE_CANDIDATE_TIME_AXES
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


def test_rejects_forged_cache_identity() -> None:
    forged = _runtime_life_kline_fact()
    forged["identity"]["cache_identity"] = "0" * 64
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=forged),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_stale_cache_identity_after_identity_field_change() -> None:
    stale = _runtime_life_kline_fact()
    # Keep the previously bound digest while swapping a bound identity field.
    stale["identity"]["source_fact_digest"] = "d" * 64
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=stale),
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


def test_rejects_empty_algorithm_gap_lists() -> None:
    emptied = _runtime_life_kline_fact()
    emptied["algorithm_gap"]["missing_inputs"] = []
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=emptied),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_empty_string_in_algorithm_gap_lists() -> None:
    blank = _runtime_life_kline_fact()
    blank["algorithm_gap"]["missing_semantics"] = [
        "measure_unit_and_range",
        "",
        "cross_period_comparability",
        "open_and_close_sampling_points",
        "high_and_low_intra_period_resolution",
        "flat_direction_threshold",
        "missing_observation_policy",
    ]
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=blank),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_removed_algorithm_gap_item() -> None:
    removed = _runtime_life_kline_fact()
    removed["algorithm_gap"]["required_versioned_fields"] = list(
        LIFE_KLINE_ALGORITHM_GAP_REQUIRED_VERSIONED_FIELDS[:-1]
    )
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=removed),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_appended_algorithm_gap_item() -> None:
    appended = _runtime_life_kline_fact()
    appended["algorithm_gap"]["minimum_implementation_slice"] = [
        *LIFE_KLINE_ALGORITHM_GAP_MINIMUM_IMPLEMENTATION_SLICE,
        "extra_host_invented_step",
    ]
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=appended),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_substituted_algorithm_gap_item() -> None:
    substituted = _runtime_life_kline_fact()
    substituted["algorithm_gap"]["missing_inputs"] = [
        "versioned_comparable_measure_definition",
        "host_substituted_corpus",
    ]
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=substituted),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_mutated_time_axis_unit() -> None:
    mutated = _runtime_life_kline_fact()
    mutated["candidate_time_axes"][0]["unit"] = "tampered_unit"
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=mutated),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_mutated_time_axis_source_schema_version() -> None:
    mutated = _runtime_life_kline_fact()
    mutated["candidate_time_axes"][1]["source_schema_version"] = "tampered-schema-v9"
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=mutated),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_mutated_time_axis_source_path() -> None:
    mutated = _runtime_life_kline_fact()
    mutated["candidate_time_axes"][2]["source_path"] = "tampered.path[]"
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=mutated),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_removed_time_axis() -> None:
    removed = _runtime_life_kline_fact()
    removed["candidate_time_axes"] = removed["candidate_time_axes"][:-1]
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=removed),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_appended_time_axis() -> None:
    appended = _runtime_life_kline_fact()
    appended["candidate_time_axes"] = [
        *appended["candidate_time_axes"],
        {
            "kind": "civil_day",
            "unit": "civil_day",
            "source_schema_version": "mingli-bazi-fact-v1",
            "source_path": "fact_extension.facts.day_layers",
            "role": "temporal_key_only",
            "series_ready": False,
        },
    ]
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=appended),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_reordered_time_axes() -> None:
    reordered = _runtime_life_kline_fact()
    axes = list(reordered["candidate_time_axes"])
    axes[0], axes[1] = axes[1], axes[0]
    reordered["candidate_time_axes"] = axes
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=reordered),
            product_id="life-kline-series",
        )
        is None
    )


def test_rejects_substituted_time_axis_kind() -> None:
    substituted = _runtime_life_kline_fact()
    # Keep other fields of the first axis but replace kind with another frozen kind.
    substituted["candidate_time_axes"][0]["kind"] = "gregorian_year"
    assert (
        project_runtime_view_model(
            _life_kline_brief(fact_value=substituted),
            product_id="life-kline-series",
        )
        is None
    )
