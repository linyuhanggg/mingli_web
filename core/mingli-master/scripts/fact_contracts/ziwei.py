"""Ziwei source-pattern integrity validation.

The adapter emits matched classical rule predicates as evidence bindings, not
as verdicts.  This Provider-owned contract independently rebuilds those
bindings from the checked runtime evidence index and the payload's calculated
facts.  It deliberately does not import or call the Ziwei generator.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from reading_engine import evidence_rules
from reading_engine.contracts import FactRef

from fact_contracts.common import (
    COMMON_CANONICAL_OBJECT_FIELDS,
    CanonicalFactsError,
    CanonicalFactsFieldClosure,
    EngineProvenance,
    FactContract,
    canonical_object_fields,
    canonical_json_snapshot,
)
from fact_contracts.common import finding as _finding


_ZIWEI_CANONICAL_FIELDS = CanonicalFactsFieldClosure(
    root_fields=frozenset(
        {
            "adapter",
            "calendar_normalization",
            "capabilities",
            "fact_layer_scope",
            "fact_layer_status",
            "input",
            "natal_fact_digest",
            "output",
            "schema_version",
            "source_lineage",
            "system",
            "trace",
            "warnings",
        }
    ),
    output_fields=frozenset(
        {
            "chart_convention",
            "chinese_date",
            "fact_layer_separation",
            "five_elements_class",
            "interpretation_status",
            "interpretive_candidates",
            "lunar_date_display",
            "major_limit_direction",
            "major_limit_sequence",
            "major_limit_starting_age",
            "major_limits",
            "ming_shen",
            "natal_transformation_facts",
            "palace_facts",
            "palaces",
            "sihua",
            "solar_date",
            "source_conditioned_patterns",
            "source_lineage",
            "source_roles",
            "star_facts",
            "stars",
            "time",
            "time_range",
            "transformation_layers",
        }
    ),
    nested_object_fields=(
        COMMON_CANONICAL_OBJECT_FIELDS
        + canonical_object_fields(
            (
                "adapter",
                "dependency engine_contract generated_at license_status name "
                "rule_profile runtime version",
            ),
            ("adapter/dependency", "name provenance version"),
            (
                "adapter/engine_contract",
                "artifact_sha256 config fix_leap license license_sha256 name "
                "source_dependency_ids version",
            ),
            (
                "adapter/engine_contract/config",
                "ageDivide algorithm dayDivide horoscopeDivide yearDivide",
            ),
            ("input", "missing_or_ambiguous normalized_input raw_user_input"),
            (
                "input/normalized_input",
                "civil_datetime coordinate_source effective_datetime gender "
                "hour_branch_policy latitude location longitude time_basis_policy "
                "timezone zi_hour_policy ziwei_engine_input",
            ),
            (
                "input/normalized_input/ziwei_engine_input",
                "day_divide fix_leap solar_date time_index",
            ),
            (
                "input/raw_user_input",
                "civil_datetime coordinate_source gender latitude location longitude "
                "time_basis_policy timezone zi_hour_policy",
            ),
            (
                "output/chart_convention",
                "age_divide algorithm day_divide engine fix_leap horoscope_divide "
                "major_limit_direction_rule source_dependency_ids time_index year_divide",
            ),
            ("output/chart_convention/engine", "name version"),
            ("output/fact_layer_separation", "calculation interpretation"),
            (
                "output/interpretive_candidates",
                "boundary evaluated_rules hard_verdict life_palace matched_rules "
                "requires_classical_adjudication san_fang_si_zheng schema_version "
                "source_dependency_ids source_rules status transformation_facts",
            ),
            (
                "output/interpretive_candidates/evaluated_rules/*",
                "details hard_verdict id matched name predicate source_anchor "
                "source_dependency_id source_pack status verification_status",
            ),
            (
                "output/interpretive_candidates/evaluated_rules/*/details",
                "assistant_stars emperor_stars matched matched_palaces matched_stars "
                "palace required_stars scope triad_palaces",
            ),
            (
                "output/interpretive_candidates/life_palace",
                "adjective_stars branch brightness index major_stars minor_stars "
                "palace role",
            ),
            (
                "output/interpretive_candidates/life_palace/brightness/*",
                "brightness star",
            ),
            (
                "output/interpretive_candidates/matched_rules/*",
                "details hard_verdict id matched name predicate source_anchor "
                "source_dependency_id source_pack status verification_status",
            ),
            (
                "output/interpretive_candidates/matched_rules/*/details",
                "assistant_stars emperor_stars matched matched_palaces matched_stars "
                "palace required_stars scope triad_palaces",
            ),
            (
                "output/interpretive_candidates/san_fang_si_zheng/*",
                "adjective_stars branch brightness index major_stars minor_stars "
                "palace role",
            ),
            (
                "output/interpretive_candidates/san_fang_si_zheng/*/brightness/*",
                "brightness star",
            ),
            (
                "output/interpretive_candidates/source_rules/*",
                "pack procedure_id role rule_ids verification_status",
            ),
            (
                "output/interpretive_candidates/transformation_facts/*",
                "palace palace_branch scope source_dependency_id star transformation",
            ),
            (
                "output/major_limit_direction",
                "direction gender source_dependency_id year_polarity year_stem",
            ),
            (
                "output/major_limit_sequence/*",
                "age_end age_start direction earthlyBranch heavenlyStem palace "
                "palace_branch palace_index range sequence source_dependency_id",
            ),
            (
                "output/major_limits/*",
                "age_end age_start direction earthlyBranch heavenlyStem palace "
                "palace_branch palace_index range sequence source_dependency_id",
            ),
            ("output/ming_shen", "body_star ming_branch shen_branch soul_star"),
            (
                "output/natal_transformation_facts/*",
                "palace palace_branch scope source_dependency_id star transformation",
            ),
            (
                "output/palace_facts/*",
                "adjectiveStars ages boshi12 changsheng12 decadal earthlyBranch "
                "heavenlyStem index isBodyPalace isOriginalPalace jiangqian12 "
                "majorStars minorStars name suiqian12",
            ),
            (
                "output/palace_facts/*/adjectiveStars/*",
                "brightness mutagen name scope type",
            ),
            (
                "output/palace_facts/*/decadal",
                "earthlyBranch heavenlyStem range",
            ),
            (
                "output/palace_facts/*/majorStars/*",
                "brightness mutagen name scope type",
            ),
            (
                "output/palace_facts/*/minorStars/*",
                "brightness mutagen name scope type",
            ),
            (
                "output/palaces/*",
                "adjectiveStars ages boshi12 changsheng12 decadal earthlyBranch "
                "heavenlyStem index isBodyPalace isOriginalPalace jiangqian12 "
                "majorStars minorStars name suiqian12",
            ),
            (
                "output/palaces/*/adjectiveStars/*",
                "brightness mutagen name scope type",
            ),
            ("output/palaces/*/decadal", "earthlyBranch heavenlyStem range"),
            (
                "output/palaces/*/majorStars/*",
                "brightness mutagen name scope type",
            ),
            (
                "output/palaces/*/minorStars/*",
                "brightness mutagen name scope type",
            ),
            ("output/sihua/*", "mutagen palace star"),
            (
                "output/source_conditioned_patterns/*",
                "fact_paths local_rule_id predicate_audit rule_id source_anchor "
                "source_dependency_id source_pack status title",
            ),
            (
                "output/source_lineage",
                "calculation commentary_only interpretation",
            ),
            (
                "output/source_lineage/calculation/*",
                "pack role source_dependency_ids",
            ),
            (
                "output/source_lineage/commentary_only/*",
                "calculation_authority pack role",
            ),
            (
                "output/source_lineage/interpretation/*",
                "calculation_authority pack role",
            ),
            (
                "output/source_roles",
                "calculation_primary classical_adjudication "
                "late_observational_commentary",
            ),
            (
                "output/star_facts/*",
                "brightness mutagen name palace palace_branch palace_index scope type",
            ),
            (
                "output/stars/*",
                "brightness mutagen name palace palace_branch palace_index scope type",
            ),
            ("output/transformation_layers", "natal"),
            (
                "output/transformation_layers/natal/*",
                "palace palace_branch scope source_dependency_id star transformation",
            ),
            ("source_lineage", "calculation commentary_only interpretation"),
            (
                "source_lineage/calculation/*",
                "pack role source_dependency_ids",
            ),
            (
                "source_lineage/commentary_only/*",
                "calculation_authority pack role",
            ),
            (
                "source_lineage/interpretation/*",
                "calculation_authority pack role",
            ),
        )
    ),
)


_ZIWEI_ENGINE_ID = "iztro"
_ZIWEI_ENGINE_VERSION = "2.5.8"
_ZIWEI_POLICY_PROFILE = "iztro-default-v2.5.8/fix-leap/zh-CN"
_ZIWEI_TIME_BASES = frozenset(
    {
        "civil",
        "longitude_mean_solar-v1",
        "local_apparent_solar-v1",
    }
)
_TEMPORAL_LAYER_FIELDS = (
    "active_natal_palace earthlyBranch fact_layer heavenlyStem index mutagen "
    "name palaceNames palace_assignments palace_facts star_facts stars "
    "transformation_facts yearlyDecStar"
)
_TEMPORAL_STAR_FIELDS = "name scope type"
_TEMPORAL_PALACE_FIELDS = (
    "dynamic_stars index natal_branch natal_palace temporal_palace"
)
_TEMPORAL_ASSIGNMENT_FIELDS = (
    "chart_palace dynamic_stars index natal_branch natal_palace temporal_palace"
)
_TEMPORAL_STAR_FACT_FIELDS = (
    "name natal_branch natal_palace palace palace_branch palace_index scope "
    "temporal_palace type"
)
_TEMPORAL_TRANSFORMATION_FIELDS = (
    "effect natal_palaces palace palace_branch scope source_dependency_id star "
    "transformation"
)


def _temporal_layer_field_rules(
    *prefixes: str,
) -> tuple[tuple[tuple[str, ...], frozenset[str]], ...]:
    rules: list[tuple[str, str]] = []
    for prefix in prefixes:
        rules.extend(
            (
                (prefix, _TEMPORAL_LAYER_FIELDS),
                (f"{prefix}/stars/*/*", _TEMPORAL_STAR_FIELDS),
                (f"{prefix}/yearlyDecStar", "jiangqian12 suiqian12"),
                (f"{prefix}/palace_facts/*", _TEMPORAL_PALACE_FIELDS),
                (
                    f"{prefix}/palace_facts/*/dynamic_stars/*",
                    _TEMPORAL_STAR_FIELDS,
                ),
                (
                    f"{prefix}/palace_assignments/*",
                    _TEMPORAL_ASSIGNMENT_FIELDS,
                ),
                (
                    f"{prefix}/palace_assignments/*/dynamic_stars/*",
                    _TEMPORAL_STAR_FIELDS,
                ),
                (
                    f"{prefix}/palace_assignments/*/chart_palace",
                    "branch name",
                ),
                (f"{prefix}/star_facts/*", _TEMPORAL_STAR_FACT_FIELDS),
                (
                    f"{prefix}/transformation_facts/*",
                    _TEMPORAL_TRANSFORMATION_FIELDS,
                ),
                (f"{prefix}/active_natal_palace", "branch index name"),
            )
        )
    return canonical_object_fields(*rules)


def _source_lineage_field_rules(
    prefix: str,
) -> tuple[tuple[tuple[str, ...], frozenset[str]], ...]:
    return canonical_object_fields(
        (prefix, "calculation commentary_only interpretation"),
        (f"{prefix}/calculation/*", "pack role source_dependency_ids"),
        (
            f"{prefix}/commentary_only/*",
            "calculation_authority pack role",
        ),
        (
            f"{prefix}/interpretation/*",
            "calculation_authority pack role",
        ),
    )


_ZIWEI_TEMPORAL_CANONICAL_FIELDS = CanonicalFactsFieldClosure(
    root_fields=frozenset({"output"}),
    output_fields=frozenset(
        {
            "active_major_limit",
            "active_major_limit_segments",
            "annual_layers",
            "calendar_coverage",
            "fact_layer_separation",
            "interpretation_status",
            "monthly_layers",
            "natal_fact_digest",
            "rule_trace",
            "schema_version",
            "source_lineage",
            "source_roles",
        }
    ),
    nested_object_fields=(
        _temporal_layer_field_rules(
            "output/active_major_limit",
            "output/active_major_limit_segments/*/major_limit",
            "output/annual_layers/*/value/liu_nian",
            "output/annual_layers/*/value/segments/*/liu_nian",
            "output/monthly_layers/*/value/liu_yue",
            "output/monthly_layers/*/value/segments/*/liu_yue",
        )
        + canonical_object_fields(
            (
                "output/active_major_limit_segments/*",
                "end_exclusive major_limit start_inclusive "
                "transformation_facts transformations",
            ),
            (
                "output/active_major_limit_segments/*/transformation_facts/*",
                _TEMPORAL_TRANSFORMATION_FIELDS,
            ),
            ("output/annual_layers/*", "key value"),
            (
                "output/annual_layers/*/value",
                "coverage_end_exclusive coverage_start liu_nian "
                "representative_scope segments transformations year",
            ),
            (
                "output/annual_layers/*/value/segments/*",
                "end_exclusive liu_nian start_inclusive "
                "transformation_facts transformations",
            ),
            (
                "output/annual_layers/*/value/segments/*/transformation_facts/*",
                _TEMPORAL_TRANSFORMATION_FIELDS,
            ),
            ("output/monthly_layers/*", "key value"),
            (
                "output/monthly_layers/*/value",
                "liu_yue month representative_scope segments transformations year",
            ),
            (
                "output/monthly_layers/*/value/segments/*",
                "end_exclusive liu_yue start_inclusive "
                "transformation_facts transformations",
            ),
            (
                "output/monthly_layers/*/value/segments/*/transformation_facts/*",
                _TEMPORAL_TRANSFORMATION_FIELDS,
            ),
            (
                "output/calendar_coverage",
                "age_divide end_exclusive horoscope_divide requested_target_date "
                "start_inclusive status",
            ),
            (
                "output/fact_layer_separation",
                "calculation classical_interpretation late_observation",
            ),
            (
                "output/source_roles",
                "calculation_primary classical_adjudication "
                "late_observational_commentary",
            ),
            (
                "output/rule_trace/*",
                "dependency operation rule_id source_dependency_id",
            ),
            ("output/rule_trace/*/dependency", "name version"),
        )
        + _source_lineage_field_rules("output/source_lineage")
    ),
)


_ZIWEI_TARGET_CANONICAL_FIELDS = CanonicalFactsFieldClosure(
    root_fields=frozenset({"output"}),
    output_fields=frozenset(
        {
            "annual",
            "boundary_profile",
            "interpretation_status",
            "major_limit",
            "monthly",
            "natal_fact_digest",
            "schema_version",
            "source_lineage",
            "source_roles",
            "target_date",
            "transformation_layers",
        }
    ),
    nested_object_fields=(
        _temporal_layer_field_rules(
            "output/major_limit",
            "output/annual",
            "output/monthly",
        )
        + canonical_object_fields(
            (
                "output/boundary_profile",
                "age_divide day_divide horoscope_divide",
            ),
            (
                "output/source_roles",
                "calculation_primary classical_adjudication "
                "late_observational_commentary",
            ),
            ("output/transformation_layers", "annual major_limit monthly"),
            (
                "output/transformation_layers/annual/*",
                _TEMPORAL_TRANSFORMATION_FIELDS,
            ),
            (
                "output/transformation_layers/major_limit/*",
                _TEMPORAL_TRANSFORMATION_FIELDS,
            ),
            (
                "output/transformation_layers/monthly/*",
                _TEMPORAL_TRANSFORMATION_FIELDS,
            ),
        )
        + _source_lineage_field_rules("output/source_lineage")
    ),
)


def _snapshot_temporal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if type(payload) is not dict:
        raise CanonicalFactsError("Ziwei temporal Canonical Facts must be an object")
    transformed = dict(payload)
    for field, key_pattern in (
        ("annual_layers", r"(?:18|19|20|21)\d{2}"),
        ("monthly_layers", r"(?:18|19|20|21)\d{2}-(?:0[1-9]|1[0-2])"),
    ):
        mapping = transformed.get(field)
        if type(mapping) is not dict:
            raise CanonicalFactsError(
                f"Ziwei temporal Canonical Facts require {field}"
            )
        rows: list[dict[str, Any]] = []
        for key, value in mapping.items():
            if type(key) is not str or re.fullmatch(key_pattern, key) is None:
                raise CanonicalFactsError(
                    f"Ziwei temporal Canonical Facts contain an invalid {field} key"
                )
            rows.append({"key": key, "value": value})
        transformed[field] = rows

    snapshot = canonical_json_snapshot(
        {"output": transformed},
        field_closure=_ZIWEI_TEMPORAL_CANONICAL_FIELDS,
    )["output"]
    for field in ("annual_layers", "monthly_layers"):
        snapshot[field] = {
            row["key"]: row["value"] for row in snapshot[field]
        }
    return snapshot


def _snapshot_target_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if type(payload) is not dict:
        raise CanonicalFactsError("Ziwei target Canonical Facts must be an object")
    return canonical_json_snapshot(
        {"output": payload},
        field_closure=_ZIWEI_TARGET_CANONICAL_FIELDS,
    )["output"]


def _validate_temporal_provenance(
    snapshot: dict[str, Any],
    provenance: EngineProvenance,
) -> None:
    if (
        provenance.engine_id != _ZIWEI_ENGINE_ID
        or provenance.engine_version != _ZIWEI_ENGINE_VERSION
        or provenance.policy_profile != _ZIWEI_POLICY_PROFILE
        or provenance.time_basis not in _ZIWEI_TIME_BASES
    ):
        raise CanonicalFactsError("Ziwei temporal engine provenance mismatch")
    natal_digest = snapshot.get("natal_fact_digest")
    if (
        type(natal_digest) is not str
        or re.fullmatch(r"[0-9a-f]{64}", natal_digest) is None
    ):
        raise CanonicalFactsError("Ziwei temporal facts require a natal digest")
    if snapshot.get("schema_version") != "mingli-ziwei-temporal-fact-v1":
        return
    traces = snapshot.get("rule_trace")
    if type(traces) is not list or len(traces) != 1:
        raise CanonicalFactsError("Ziwei temporal facts require one engine trace")
    trace = traces[0]
    dependency = trace.get("dependency") if type(trace) is dict else None
    if (
        type(dependency) is not dict
        or dependency.get("name") != provenance.engine_id
        or dependency.get("version") != provenance.engine_version
        or trace.get("rule_id") != "ziwei.iztro-horoscope-v2.5.8"
        or trace.get("source_dependency_id")
        != "ziwei.iztro.decadal-year-month-horoscope"
    ):
        raise CanonicalFactsError("Ziwei temporal engine trace mismatch")


@dataclass(frozen=True)
class ZiweiCanonicalFacts:
    """Nominal, immutable Ziwei facts at the Engine Adapter boundary."""

    provenance: EngineProvenance
    _payload_json: str = field(repr=False)

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        provenance: EngineProvenance,
    ) -> "ZiweiCanonicalFacts":
        schema_version = (
            payload.get("schema_version") if type(payload) is dict else None
        )
        if schema_version == "mingli-ziwei-fact-v1":
            snapshot = canonical_json_snapshot(
                payload,
                field_closure=_ZIWEI_CANONICAL_FIELDS,
            )
            adapter = snapshot.get("adapter")
            calendar = snapshot.get("calendar_normalization")
            if not isinstance(adapter, dict) or not isinstance(calendar, dict):
                raise CanonicalFactsError(
                    "Ziwei Canonical Facts require adapter and calendar metadata"
                )
            engine = adapter.get("engine_contract")
            time_basis = calendar.get("time_basis")
            if not isinstance(engine, dict) or not isinstance(time_basis, dict):
                raise CanonicalFactsError(
                    "Ziwei Canonical Facts require engine and time-basis metadata"
                )
            if (
                engine.get("name") != provenance.engine_id
                or engine.get("version") != provenance.engine_version
                or adapter.get("rule_profile") != provenance.policy_profile
                or time_basis.get("policy") != provenance.time_basis
            ):
                raise CanonicalFactsError("Ziwei engine provenance mismatch")
        elif schema_version == "mingli-ziwei-temporal-fact-v1":
            snapshot = _snapshot_temporal_payload(payload)
            _validate_temporal_provenance(snapshot, provenance)
        elif schema_version == "mingli-ziwei-target-fact-v1":
            snapshot = _snapshot_target_payload(payload)
            _validate_temporal_provenance(snapshot, provenance)
            target_date_text = snapshot.get("target_date")
            if (
                type(target_date_text) is not str
                or re.fullmatch(r"\d{4}-\d{2}-\d{2}", target_date_text) is None
            ):
                raise CanonicalFactsError(
                    "Ziwei target facts require an ISO target date"
                )
            try:
                target_date = date.fromisoformat(target_date_text)
            except ValueError as exc:
                raise CanonicalFactsError(
                    "Ziwei target facts require an ISO target date"
                ) from exc
            if not 1800 <= target_date.year <= 2199:
                raise CanonicalFactsError(
                    "Ziwei target facts require a supported target date"
                )
        else:
            raise CanonicalFactsError("invalid Ziwei Canonical Facts schema")
        return cls(
            provenance=provenance,
            _payload_json=json.dumps(
                snapshot,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)


_CALCULATED_STATUS = "calculated_ziwei_chart_from_birth_datetime"
_BINDING_FIELDS = (
    "rule_id",
    "local_rule_id",
    "title",
    "source_pack",
    "source_anchor",
    "fact_paths",
    "predicate_audit",
)


def _escape_fact_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _fact_leaves(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    """Yield the Runtime fact-index paths without using generator helpers."""

    if isinstance(value, Mapping) and value:
        for key in sorted(value, key=str):
            token = _escape_fact_token(str(key))
            yield from _fact_leaves(value[key], f"{path}/{token}")
        return
    if isinstance(value, (list, tuple)) and value:
        for index, item in enumerate(value):
            yield from _fact_leaves(item, f"{path}/{index}")
        return
    yield path or "/", value


def _fact_refs(
    payload: dict[str, Any], output: dict[str, Any]
) -> tuple[FactRef, ...]:
    """Rebuild the pre-binding fact view used for applicability matching."""

    fact_output = dict(output)
    # A source binding can never prove itself.  The generator matched against
    # this field while it was still empty; the contract recreates that view.
    fact_output["source_conditioned_patterns"] = []
    calendar = payload.get("calendar_normalization")
    indexed = {
        "chart_facts": {
            "calendar_normalization": (
                calendar if isinstance(calendar, dict) else {}
            ),
            "output": fact_output,
        }
    }
    return tuple(
        FactRef(
            fact_id=f"fact:{path}",
            path=path,
            value=value,
            provider_id="ziwei.source-pattern-integrity",
            provider_version="1",
            reading_id="",
            version=1,
        )
        for path, value in _fact_leaves(indexed)
    )


def _expected_bindings(
    payload: dict[str, Any], output: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return canonical matched bindings from verified Runtime rules."""

    fact_refs = _fact_refs(payload, output)
    bindings: list[dict[str, Any]] = []
    for rule in evidence_rules.production_evidence_rules():
        if (
            rule.system != "ziwei"
            or not rule.runtime_active
            or rule.classical_binding_status != "verified"
        ):
            continue
        matched, fact_paths, predicate_audit = evidence_rules.match_rule(
            rule, fact_refs
        )
        if not matched:
            continue
        bindings.append(
            {
                "rule_id": rule.rule_id,
                "local_rule_id": rule.local_rule_id,
                "title": rule.title,
                "source_pack": rule.source_pack,
                "source_anchor": rule.source_anchor,
                "fact_paths": list(fact_paths),
                "predicate_audit": list(predicate_audit),
            }
        )
    return sorted(bindings, key=lambda item: str(item["rule_id"]))


def _observed_bindings(patterns: Any) -> list[dict[str, Any]] | None:
    if not isinstance(patterns, list):
        return None
    projected: list[dict[str, Any]] = []
    for pattern in patterns:
        if not isinstance(pattern, dict):
            return None
        projected.append(
            {field: pattern.get(field) for field in _BINDING_FIELDS}
        )
    return projected


class ZiweiFactContract(FactContract):
    """Verify source-conditioned rule bindings independently of generation."""

    contract_id = "ziwei.source-pattern-integrity-v1"
    canonical_facts_type = ZiweiCanonicalFacts

    def validate_output(
        self,
        payload: dict[str, Any],
        output: dict[str, Any],
    ) -> list[dict[str, str]]:
        if payload.get("fact_layer_status") != _CALCULATED_STATUS:
            return []
        observed = _observed_bindings(
            output.get("source_conditioned_patterns")
        )
        expected = _expected_bindings(payload, output)
        if observed == expected:
            return []
        return [
            _finding(
                "ziwei_source_pattern_binding_invalid",
                "Ziwei source-conditioned patterns must match the"
                " runtime-active, classically verified rule bindings",
            )
        ]


__all__ = ["ZiweiCanonicalFacts", "ZiweiFactContract"]
