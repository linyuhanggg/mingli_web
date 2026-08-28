"""Ziwei source-pattern integrity validation.

The adapter emits matched classical rule predicates as evidence bindings, not
as verdicts.  This Provider-owned contract independently rebuilds those
bindings from the checked runtime evidence index and the payload's calculated
facts.  It deliberately does not import or call the Ziwei generator.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from reading_engine import evidence_rules
from reading_engine.contracts import FactRef

from fact_contracts.common import (
    CanonicalFactsError,
    CanonicalFactsFieldClosure,
    EngineProvenance,
    FactContract,
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
)


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
        snapshot = canonical_json_snapshot(
            payload,
            field_closure=_ZIWEI_CANONICAL_FIELDS,
        )
        if snapshot.get("schema_version") != "mingli-ziwei-fact-v1":
            raise CanonicalFactsError("invalid Ziwei Canonical Facts schema")
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
