"""Bazi FactContract: Provider-owned fact validation for the bazi system.

Moved verbatim from ``adapter_validate.py`` (the compatibility facade) so the
bazi domain rules live in a Provider-owned module. The independent oracle
(sexagenary recomputation of luck direction and the ten-step sequence) stays
self-contained here: it must never import the generating adapter
(``bazi_calc``), so the validator cannot "prove itself".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from evidence_contract import canonical_digest

from fact_contracts.common import (
    CanonicalFactsError,
    EngineProvenance,
    FactContract,
    canonical_json_snapshot,
)
from fact_contracts.common import finding as _finding
from fact_contracts.common import valid_text as _valid_text


@dataclass(frozen=True)
class BaziCanonicalFacts:
    """Nominal, immutable Bazi facts at the Engine Adapter boundary."""

    provenance: EngineProvenance
    _payload_json: str = field(repr=False)

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        provenance: EngineProvenance,
    ) -> "BaziCanonicalFacts":
        snapshot = canonical_json_snapshot(payload)
        if snapshot.get("schema_version") != "mingli-bazi-fact-v1":
            raise CanonicalFactsError("invalid Bazi Canonical Facts schema")
        adapter = snapshot.get("adapter")
        calendar = snapshot.get("calendar_normalization")
        if not isinstance(adapter, dict) or not isinstance(calendar, dict):
            raise CanonicalFactsError(
                "Bazi Canonical Facts require adapter and calendar metadata"
            )
        if adapter.get("rule_profile") != provenance.policy_profile:
            raise CanonicalFactsError("Bazi policy provenance mismatch")

        scope = snapshot.get("fact_layer_scope")
        if scope == "natal_static":
            actual_engine = "mingli-bazi-static-facts"
            actual_version = adapter.get("version")
            actual_time_basis = "not_applicable"
        else:
            convention = calendar.get("calendar_convention")
            time_basis = calendar.get("time_basis")
            if not isinstance(convention, dict) or not isinstance(time_basis, dict):
                raise CanonicalFactsError(
                    "Bazi timed facts require engine and time-basis metadata"
                )
            actual_engine = convention.get("engine")
            actual_version = convention.get("engine_version")
            actual_time_basis = time_basis.get("policy")

        if (
            actual_engine != provenance.engine_id
            or actual_version != provenance.engine_version
            or actual_time_basis != provenance.time_basis
        ):
            raise CanonicalFactsError("Bazi engine provenance mismatch")
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

_MONTH_ORDER_STATES = {
    "木": {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"},
    "火": {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"},
    "土": {"土": "旺", "金": "相", "火": "休", "木": "囚", "水": "死"},
    "金": {"金": "旺", "水": "相", "土": "休", "火": "囚", "木": "死"},
    "水": {"水": "旺", "木": "相", "金": "休", "土": "囚", "火": "死"},
}


def _validate_bazi_month_order_adjudication(
    candidates: dict[str, Any],
) -> list[dict[str, str]]:
    strength = (
        candidates.get("strength")
        if isinstance(candidates.get("strength"), dict)
        else {}
    )
    adjudication = (
        strength.get("month_order_adjudication")
        if isinstance(strength.get("month_order_adjudication"), dict)
        else {}
    )
    source = (
        adjudication.get("source_ref")
        if isinstance(adjudication.get("source_ref"), dict)
        else {}
    )
    day_element = strength.get("day_element")
    command_element = strength.get("month_command_element")
    expected_state = (
        _MONTH_ORDER_STATES.get(str(command_element), {}).get(str(day_element))
    )
    unresolved = adjudication.get("unresolved_checks")
    valid = (
        expected_state is not None
        and strength.get("seasonal_state") == expected_state
        and strength.get("seasonal_state_source_rule_id")
        == "bazi/sanming-tonghui#R-02-04"
        and adjudication.get("status") == "adjudicated_month_order_state"
        and adjudication.get("decision_scope")
        == "bazi_month_order_seasonal_state"
        and adjudication.get("day_master_element") == day_element
        and adjudication.get("month_command_element") == command_element
        and adjudication.get("seasonal_state") == expected_state
        and adjudication.get("whole_chart_strength_verdict") is None
        and adjudication.get("useful_god_verdict") is None
        and source.get("pack") == "bazi/sanming-tonghui"
        and source.get("rule_id") == "R-02-04"
        and source.get("source_anchor")
        == "references/books/bazi/sanming-tonghui/rules.md#R-02-04"
        and source.get("verification_status") == "verified"
        and _valid_text(source.get("binding_digest"))
        and isinstance(unresolved, list)
        and bool(unresolved)
        and all(_valid_text(item) for item in unresolved)
    )
    if valid:
        return []
    return [_finding(
        "bazi_month_order_adjudication_invalid",
        "The Bazi month-order state must remain source-bound and must not become a whole-chart strength verdict",
    )]



def _validate_bazi_root_support_adjudication(
    candidates: dict[str, Any],
) -> list[dict[str, str]]:
    strength = (
        candidates.get("strength")
        if isinstance(candidates.get("strength"), dict)
        else {}
    )
    adjudication = (
        strength.get("day_master_root_support_adjudication")
        if isinstance(strength.get("day_master_root_support_adjudication"), dict)
        else {}
    )
    source = (
        adjudication.get("source_ref")
        if isinstance(adjudication.get("source_ref"), dict)
        else {}
    )
    unresolved = adjudication.get("unresolved_checks")
    blockers = adjudication.get("regime_blockers")
    all_counts = adjudication.get("all_element_occurrences")
    root_positions = adjudication.get("same_element_root_positions")
    resource_positions = adjudication.get("resource_branch_positions")
    common = (
        adjudication.get("decision_scope")
        == "bazi_day_master_root_support_evidence"
        and adjudication.get("day_master_element") == strength.get("day_element")
        and adjudication.get("month_command_element")
        == strength.get("month_command_element")
        and adjudication.get("seasonal_state") == strength.get("seasonal_state")
        and adjudication.get("same_element_occurrences")
        == strength.get("same_element_occurrences")
        and adjudication.get("resource_element") == strength.get("resource_element")
        and adjudication.get("resource_occurrences")
        == strength.get("resource_occurrences")
        and adjudication.get("whole_chart_strength_verdict") is None
        and adjudication.get("useful_god_verdict") is None
        and source.get("pack") == "bazi/sanming-tonghui"
        and source.get("rule_id") == "R-02-04"
        and source.get("source_anchor")
        == "references/books/bazi/sanming-tonghui/rules.md#R-02-04"
        and source.get("verification_status") == "verified"
        and _valid_text(source.get("binding_digest"))
        and isinstance(unresolved, list)
        and bool(unresolved)
        and all(_valid_text(item) for item in unresolved)
        and isinstance(blockers, list)
        and all(_valid_text(item) for item in blockers)
        and isinstance(all_counts, dict)
        and isinstance(root_positions, list)
        and all(_valid_text(item) for item in root_positions)
        and isinstance(resource_positions, list)
        and all(_valid_text(item) for item in resource_positions)
        and _valid_text(adjudication.get("month_command_support_or_drain"))
        and isinstance(adjudication.get("visible_support_role_count"), int)
        and isinstance(adjudication.get("visible_pressure_role_count"), int)
    )
    adjudicated = (
        common
        and adjudication.get("status") == "adjudicated_root_support_evidence"
        and blockers == []
    )
    refused = (
        common
        and adjudication.get("status")
        == "refused_following_or_transformation_regime"
        and bool(blockers)
    )
    if adjudicated or refused:
        return []
    return [_finding(
        "bazi_root_support_adjudication_invalid",
        "The Bazi root-support evidence must stay source-bound and must not become a whole-chart strength verdict",
    )]


def _validate_bazi_pattern_adjudication(
    candidates: dict[str, Any],
) -> list[dict[str, str]]:
    reasoning_tools = candidates.get("reasoning_tools")
    if not isinstance(reasoning_tools, dict):
        return [_finding(
            "bazi_pattern_adjudication_missing",
            "Bazi output must expose the verified Ziping month-pattern adjudication",
        )]
    tool = reasoning_tools.get("ziping_month_pattern_adjudication")
    if not isinstance(tool, dict):
        return [_finding(
            "bazi_pattern_adjudication_missing",
            "Bazi output must expose the verified Ziping month-pattern adjudication",
        )]
    payload = {key: value for key, value in tool.items() if key != "tool_digest"}
    source_refs = tool.get("source_refs")
    source = (
        source_refs[0]
        if isinstance(source_refs, list)
        and len(source_refs) == 1
        and isinstance(source_refs[0], dict)
        else {}
    )
    result = tool.get("output") if isinstance(tool.get("output"), dict) else {}
    structure = (
        candidates.get("structure")
        if isinstance(candidates.get("structure"), dict)
        else {}
    )
    month_role = structure.get("month_main_qi_ten_god")
    is_exception = month_role in {"比肩", "劫财"}
    expected_status = (
        "exception_requires_external_selection"
        if is_exception
        else "adjudicated_pattern_entry"
    )
    expected_entry = None if is_exception else month_role
    expected_label = "建禄月劫分支" if is_exception else f"{month_role}格入口"
    digest = tool.get("tool_digest")
    valid = (
        tool.get("tool_id") == "bazi.tool.ziping_month_pattern_adjudication"
        and tool.get("tool_kind") == "source_bound_pattern_entry_adjudication"
        and isinstance(digest, str)
        and digest == canonical_digest(payload)
        and source.get("pack") == "bazi/ziping-zhenquan"
        and source.get("rule_id") == "ZPR-01"
        and source.get("verification_status") == "verified"
        and _valid_text(source.get("binding_digest"))
        and result.get("decision_scope")
        == "ziping_month_command_pattern_entry"
        and result.get("month_main_qi_ten_god") == month_role
        and result.get("status") == expected_status
        and result.get("pattern_entry") == expected_entry
        and result.get("pattern_label") == expected_label
        and result.get("hard_verdict") is None
        and isinstance(result.get("unresolved_checks"), list)
        and bool(result.get("unresolved_checks"))
    )
    if not valid:
        return [_finding(
            "bazi_pattern_adjudication_invalid",
            "The Ziping month-pattern adjudication must remain source-bound and scope-limited",
        )]
    return []


def _validate_bazi_tiaohou_adjudication(
    candidates: dict[str, Any],
) -> list[dict[str, str]]:
    reasoning_tools = candidates.get("reasoning_tools")
    tool = (
        reasoning_tools.get("tiaohou_candidates")
        if isinstance(reasoning_tools, dict)
        else None
    )
    if not isinstance(tool, dict):
        return [_finding(
            "bazi_tiaohou_adjudication_invalid",
            "Bazi output must expose a source-status-aware Tiaohou decision",
        )]
    payload = {key: value for key, value in tool.items() if key != "tool_digest"}
    digest = tool.get("tool_digest")
    source_refs = tool.get("source_refs")
    source = (
        source_refs[0]
        if isinstance(source_refs, list)
        and len(source_refs) == 1
        and isinstance(source_refs[0], dict)
        else {}
    )
    result = tool.get("output") if isinstance(tool.get("output"), dict) else {}
    verification_status = source.get("verification_status")
    priority_stems = result.get("priority_stems")
    matches = result.get("matches")
    verified_shape = (
        verification_status == "verified"
        and result.get("status") == "adjudicated_seasonal_priority"
        and isinstance(priority_stems, list)
        and bool(priority_stems)
        and all(_valid_text(item) for item in priority_stems)
        and isinstance(matches, list)
    )
    inactive_shape = (
        verification_status == "inactive_unverified"
        and result.get("status") == "unavailable_unverified_rule"
        and priority_stems == []
        and matches == []
    )
    valid = (
        tool.get("tool_id") == "bazi.tool.tiaohou_candidates"
        and isinstance(digest, str)
        and digest == canonical_digest(payload)
        and source.get("pack") == "bazi/qiongtong-baojian"
        and _valid_text(source.get("rule_id"))
        and _valid_text(source.get("binding_digest"))
        and result.get("verification_status") == verification_status
        and result.get("hard_verdict") is None
        and (verified_shape or inactive_shape)
    )
    if not valid:
        return [_finding(
            "bazi_tiaohou_adjudication_invalid",
            "Tiaohou output must apply only verified rules and suppress inactive priorities",
        )]
    return []


def _validate_bazi_conflict_arbitration(
    candidates: dict[str, Any],
) -> list[dict[str, str]]:
    """Require BZ-05 to preserve verified layers without choosing among them."""

    reasoning_tools = candidates.get("reasoning_tools")
    if not isinstance(reasoning_tools, dict):
        reasoning_tools = {}
    tool = reasoning_tools.get("conflict_arbitration")
    pattern = reasoning_tools.get("ziping_month_pattern_adjudication")
    strength = reasoning_tools.get("strength_evidence")
    tiaohou = reasoning_tools.get("tiaohou_candidates")
    if not all(isinstance(item, dict) for item in (tool, pattern, strength, tiaohou)):
        return [_finding(
            "bazi_conflict_arbitration_invalid",
            "Bazi conflict arbitration must fail closed over three source-bound sibling layers",
        )]
    assert isinstance(tool, dict)
    assert isinstance(pattern, dict)
    assert isinstance(strength, dict)
    assert isinstance(tiaohou, dict)

    pattern_output = pattern.get("output")
    strength_output = strength.get("output")
    tiaohou_output = tiaohou.get("output")
    if not all(
        isinstance(item, dict)
        for item in (pattern_output, strength_output, tiaohou_output)
    ):
        return [_finding(
            "bazi_conflict_arbitration_invalid",
            "Bazi conflict arbitration must fail closed over three source-bound sibling layers",
        )]
    assert isinstance(pattern_output, dict)
    assert isinstance(strength_output, dict)
    assert isinstance(tiaohou_output, dict)

    def verified_binding(source: Any) -> bool:
        required_keys = {
            "pack",
            "rule_id",
            "source_anchor",
            "verification_status",
            "binding_digest",
        }
        return (
            isinstance(source, dict)
            and set(source) == required_keys
            and source.get("verification_status") == "verified"
            and all(_valid_text(source.get(key)) for key in required_keys)
        )

    pattern_sources = pattern.get("source_refs")
    tiaohou_sources = tiaohou.get("source_refs")
    root_support = strength_output.get("day_master_root_support_adjudication")
    sibling_bindings = [
        pattern_sources[0]
        if isinstance(pattern_sources, list) and len(pattern_sources) == 1
        else None,
        root_support.get("source_ref") if isinstance(root_support, dict) else None,
        tiaohou_sources[0]
        if isinstance(tiaohou_sources, list) and len(tiaohou_sources) == 1
        else None,
    ]
    expected_source_refs = [
        source for source in sibling_bindings if verified_binding(source)
    ]
    expected_layers = {
        "pattern_layer": pattern_output,
        "strength_flow_layer": strength_output,
        "tiaohou_layer": tiaohou_output,
    }
    expected_fact_refs = [
        {
            "path": (
                "$.output.interpretive_candidates.reasoning_tools."
                "ziping_month_pattern_adjudication"
            ),
            "value": {
                "tool_digest": pattern.get("tool_digest"),
                "output": pattern_output,
            },
        },
        {
            "path": (
                "$.output.interpretive_candidates.reasoning_tools."
                "strength_evidence"
            ),
            "value": {
                "tool_digest": strength.get("tool_digest"),
                "output": strength_output,
            },
        },
        {
            "path": (
                "$.output.interpretive_candidates.reasoning_tools."
                "tiaohou_candidates"
            ),
            "value": {
                "tool_digest": tiaohou.get("tool_digest"),
                "output": tiaohou_output,
            },
        },
    ]
    result = tool.get("output") if isinstance(tool.get("output"), dict) else {}
    requested_domains = result.get("requested_domains")
    domains_valid = (
        isinstance(requested_domains, list)
        and all(
            isinstance(domain, str)
            and _valid_text(domain)
            and domain == domain.strip().lower()
            for domain in requested_domains
        )
        and len(requested_domains) == len(set(requested_domains))
    )
    expected_checks = ["verified cross-layer priority rule is unavailable"]
    if domains_valid and requested_domains:
        expected_checks.extend(
            f"{domain} cannot uniquely map to a lineage focus"
            for domain in requested_domains
        )
    else:
        expected_checks.append(
            "question domain is absent and cannot uniquely map to a lineage focus"
        )
    expected_result_keys = {
        "policy_id",
        "policy_anchor",
        "policy_status",
        "status",
        "requested_domains",
        "focus",
        "selected_primary_view",
        "preserved_disagreements",
        "downgraded_layers",
        "layers",
        "unresolved_required_rule",
        "unresolved_checks",
        "hard_verdict",
    }
    payload = {key: value for key, value in tool.items() if key != "tool_digest"}
    digest = tool.get("tool_digest")
    valid = (
        set(tool)
        == {
            "schema_version",
            "tool_id",
            "tool_kind",
            "confidence_bucket",
            "confidence_ceiling",
            "visibility_class",
            "fact_refs",
            "source_refs",
            "output",
            "caveats",
            "tool_digest",
        }
        and tool.get("schema_version") == "mingli-bazi-reasoning-tool-v2"
        and tool.get("tool_id") == "bazi.tool.conflict_arbitration"
        and tool.get("tool_kind") == "decision_stack_conflict_policy"
        and tool.get("confidence_bucket") == "low"
        and tool.get("confidence_ceiling") == "low"
        and tool.get("visibility_class") == "on_demand"
        and isinstance(digest, str)
        and digest == canonical_digest(payload)
        and tool.get("fact_refs") == expected_fact_refs
        and bool(expected_source_refs)
        and tool.get("source_refs") == expected_source_refs
        and all(verified_binding(source) for source in expected_source_refs)
        and all(source.get("rule_id") != "DR-02-06" for source in expected_source_refs)
        and set(result) == expected_result_keys
        and result.get("policy_id") == "bazi.question-focus-routing-v1"
        and result.get("policy_anchor")
        == "references/matrices/bazi-core-decision-stack.md#3-冲突裁判"
        and result.get("policy_status")
        == "product_contract_not_classical_verdict"
        and result.get("status")
        == "unresolved_unverified_cross_layer_arbitrator"
        and domains_valid
        and result.get("focus") is None
        and result.get("selected_primary_view") is None
        and result.get("preserved_disagreements")
        == [
            {
                "between": ["pattern_layer", "strength_flow_layer"],
                "policy": "preserve_both_views",
            },
            {
                "between": ["tiaohou_layer", "strength_flow_layer"],
                "policy": "preserve_both_views",
            },
        ]
        and result.get("downgraded_layers") == []
        and result.get("layers") == expected_layers
        and result.get("unresolved_required_rule")
        == {
            "pack": "bazi/ditiansui-chanwei",
            "rule_id": "DR-02-06",
            "source_anchor": (
                "references/books/bazi/ditiansui-chanwei/"
                "rules.md#DR-02-06"
            ),
            "verification_status": "pending_verification",
        }
        and result.get("unresolved_checks") == expected_checks
        and result.get("hard_verdict") is None
        and isinstance(tool.get("caveats"), list)
        and bool(tool.get("caveats"))
        and all(_valid_text(item) for item in tool["caveats"])
    )
    if valid:
        return []
    return [_finding(
        "bazi_conflict_arbitration_invalid",
        "Bazi conflict arbitration must mirror verified sibling bindings and fail closed without a verified cross-layer priority rule",
    )]


def _validate_bazi_v51_output(output: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    patterns = output.get("source_conditioned_patterns")
    if not isinstance(patterns, list):
        findings.append(_finding(
            "bazi_source_patterns_missing",
            "Bazi output must expose source-conditioned pattern matches as a list",
        ))
    else:
        required = (
            "rule_id",
            "local_rule_id",
            "title",
            "source_pack",
            "source_anchor",
            "status",
            "fact_paths",
            "predicate_audit",
        )
        for index, pattern in enumerate(patterns):
            if not isinstance(pattern, dict):
                findings.append(_finding(
                    "bazi_source_pattern_invalid",
                    f"source_conditioned_patterns[{index}] must be an object",
                ))
                continue
            if any(
                not _valid_text(pattern.get(field))
                for field in required[:6]
            ):
                findings.append(_finding(
                    "bazi_source_pattern_invalid",
                    f"source_conditioned_patterns[{index}] has invalid identity fields",
                ))
            if pattern.get("status") != "predicate_matched_not_verdict":
                findings.append(_finding(
                    "bazi_source_pattern_invalid",
                    f"source_conditioned_patterns[{index}] must not be a verdict",
                ))
            for field in required[6:]:
                value = pattern.get(field)
                if not isinstance(value, list) or not value or not all(
                    _valid_text(item) for item in value
                ):
                    findings.append(_finding(
                        "bazi_source_pattern_invalid",
                        f"source_conditioned_patterns[{index}].{field} must be non-empty text",
                    ))
            if "verdict" in pattern:
                findings.append(_finding(
                    "bazi_source_pattern_invalid",
                    f"source_conditioned_patterns[{index}] must not contain verdict",
                ))
    candidates = (
        output.get("interpretive_candidates")
        if isinstance(output.get("interpretive_candidates"), dict)
        else {}
    )
    required_candidates = {
        "strength": "evidence_only",
        "structure": "candidate_only",
        "following_and_transformation": "requires_classical_adjudication",
    }
    for key, status in required_candidates.items():
        item = candidates.get(key) if isinstance(candidates.get(key), dict) else {}
        if item.get("status") != status or item.get("hard_verdict") is not None:
            findings.append(_finding(
                f"bazi_invalid_interpretive_candidate:{key}",
                f"Bazi {key} must remain a non-verdict fact candidate",
            ))
    findings.extend(_validate_bazi_pattern_adjudication(candidates))
    findings.extend(_validate_bazi_tiaohou_adjudication(candidates))
    findings.extend(_validate_bazi_conflict_arbitration(candidates))
    findings.extend(_validate_bazi_month_order_adjudication(candidates))
    findings.extend(_validate_bazi_root_support_adjudication(candidates))
    strength = candidates.get("strength") if isinstance(candidates.get("strength"), dict) else {}
    if strength.get("seasonal_state") not in {"旺", "相", "休", "囚", "死"}:
        findings.append(_finding(
            "bazi_strength_seasonal_state_missing",
            "Bazi strength evidence must expose the month-order seasonal state",
        ))
    if not _valid_text(strength.get("seasonal_state_source_rule_id")):
        findings.append(_finding(
            "bazi_strength_seasonal_source_missing",
            "Bazi strength evidence must bind the month-order source rule",
        ))
    signals = candidates.get("salience_signals")
    if signals is not None:
        if not isinstance(signals, list):
            findings.append(_finding(
                "bazi_invalid_salience_signal",
                "Bazi salience signals must be a list of mechanical candidates",
            ))
        else:
            seen_signal_ids: set[str] = set()
            for item in signals:
                entry = item if isinstance(item, dict) else {}
                signal_id = entry.get("signal_id")
                basis = entry.get("basis")
                valid = (
                    _valid_text(signal_id)
                    and signal_id not in seen_signal_ids
                    and entry.get("status") == "mechanical_candidate"
                    and isinstance(basis, dict)
                    and bool(basis)
                    and entry.get("hard_verdict") is None
                    and _valid_text(entry.get("boundary"))
                )
                if _valid_text(signal_id):
                    seen_signal_ids.add(str(signal_id))
                if not valid:
                    findings.append(_finding(
                        "bazi_invalid_salience_signal",
                        "Every Bazi salience signal must stay a uniquely identified mechanical candidate",
                    ))
    auxiliary = (
        output.get("shensha_auxiliary")
        if isinstance(output.get("shensha_auxiliary"), dict)
        else {}
    )
    cannot_override = set(auxiliary.get("cannot_override") or ())
    required_precedence = {
        "month_command",
        "structure",
        "strength",
        "tiaohou",
        "ten_gods",
        "luck_cycles",
        "transit_facts",
    }
    if (
        auxiliary.get("status") != "calculated_auxiliary_layer"
        or auxiliary.get("precedence") != "auxiliary_only"
        or auxiliary.get("may_override") != []
        or not required_precedence.issubset(cannot_override)
    ):
        findings.append(_finding(
            "bazi_invalid_shensha_precedence",
            "Bazi Shensha facts must be calculated in a non-overriding auxiliary layer",
        ))
    for item in auxiliary.get("calculated_items") or ():
        if (
            not isinstance(item, dict)
            or item.get("source_dependency_id")
            != "bazi.shensha.yima-taohua-auxiliary"
        ):
            findings.append(_finding(
                "bazi_unbound_shensha_item",
                "Every calculated Bazi Shensha item must bind the audited dependency",
            ))
    return findings


BAZI_PARTIAL_LUCK_TIMING_FIELDS = (
    "start_age",
    "start_age_years",
    "end_age_years",
    "approximate_start_datetime",
    "boundary_term",
    "start_age_rule",
    "interval_days",
    "calendar_year_mapping",
    "active_cycle",
    "precise_timing",
)
BAZI_PARTIAL_FACT_STATUS = "validated_user_provided_four_pillars"
BAZI_PARTIAL_FACT_SCOPE = "natal_static"
BAZI_PARTIAL_INPUT_MODE = "supplied_four_pillars"
BAZI_PARTIAL_RULE_PROFILE = "supplied-four-pillars/static-ziping-v1"
BAZI_PARTIAL_DIRECTION_RULE = "阳年男/阴年女顺，阴年男/阳年女逆；阴阳取年干"
BAZI_PARTIAL_SEQUENCED_KEYS = {
    "status",
    "direction",
    "direction_rule",
    "cycles",
    "unavailable",
}
BAZI_PARTIAL_GENDERLESS_KEYS = {"status", "cycles", "unavailable"}
BAZI_PARTIAL_TIMING_UNAVAILABLE = (
    "start_age",
    "calendar_year_mapping",
    "active_cycle",
    "precise_timing",
)
BAZI_PARTIAL_GENDERLESS_UNAVAILABLE = (
    "direction",
    "sequence",
) + BAZI_PARTIAL_TIMING_UNAVAILABLE
BAZI_PARTIAL_BLOCKED_CAPABILITIES = {
    "annual_or_monthly_timing",
    "birth_calendar_verification",
    "luck_cycle_timing",
    "true_solar_time_verification",
}
BAZI_SALIENCE_SIGNAL_KEYS = {
    "signal_id",
    "status",
    "basis",
    "hard_verdict",
    "boundary",
}
BAZI_SALIENCE_BASIS_RESERVED_KEYS = {
    "confidence",
    "hard_verdict",
    "probability",
    "score",
}
_BAZI_ORACLE_STEMS = "甲乙丙丁戊己庚辛壬癸"
_BAZI_ORACLE_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
_BAZI_ORACLE_JIAZI = tuple(
    _BAZI_ORACLE_STEMS[index % 10] + _BAZI_ORACLE_BRANCHES[index % 12]
    for index in range(60)
)
_BAZI_PILLAR_POSITIONS = {"year", "month", "day", "hour"}
_BAZI_GROWTH_STAGES = ("长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养")
_BAZI_GROWTH_STAGE_START = {
    "甲": 11,
    "丙": 2,
    "戊": 2,
    "庚": 5,
    "壬": 8,
    "乙": 6,
    "丁": 9,
    "己": 9,
    "辛": 0,
    "癸": 3,
}


def _bazi_salience_basis_has_reserved_metadata(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(set(value) & BAZI_SALIENCE_BASIS_RESERVED_KEYS) or any(
            _bazi_salience_basis_has_reserved_metadata(item)
            for item in value.values()
        )
    if isinstance(value, list):
        return any(
            _bazi_salience_basis_has_reserved_metadata(item)
            for item in value
        )
    return False


def _validate_bazi_growth_stages(output: dict[str, Any]) -> list[dict[str, str]]:
    """Independently recompute the visible-stem 十二长生 positions."""

    raw_pillars = output.get("four_pillars")
    raw_stages = output.get("twelve_growth_stages")
    if not isinstance(raw_pillars, dict) or not isinstance(raw_stages, dict):
        return [_finding(
            "bazi_growth_stages_missing",
            "Bazi output must expose four pillars and twelve_growth_stages",
        )]
    findings: list[dict[str, str]] = []
    for position in _BAZI_PILLAR_POSITIONS:
        pillar = raw_pillars.get(position)
        item = raw_stages.get(position)
        if (
            not isinstance(pillar, str)
            or len(pillar) != 2
            or pillar[0] not in _BAZI_ORACLE_STEMS
            or pillar[1] not in _BAZI_ORACLE_BRANCHES
            or not isinstance(item, dict)
        ):
            findings.append(_finding(
                "bazi_growth_stage_invalid",
                f"twelve_growth_stages[{position}] has an invalid shape",
            ))
            continue
        stem, branch = pillar
        start = _BAZI_GROWTH_STAGE_START[stem]
        branch_index = _BAZI_ORACLE_BRANCHES.index(branch)
        yang = _BAZI_ORACLE_STEMS.index(stem) % 2 == 0
        stage_index = (
            (branch_index - start) % 12
            if yang
            else (start - branch_index) % 12
        )
        expected = {
            "position": position,
            "stem": stem,
            "branch": branch,
            "stage": _BAZI_GROWTH_STAGES[stage_index],
            "stage_index": stage_index + 1,
            "direction": "forward" if yang else "reverse",
            "source_dependency_id": "bazi.chart.twelve-growth-stages-v1",
        }
        if any(item.get(key) != value for key, value in expected.items()):
            findings.append(_finding(
                "bazi_growth_stage_recompute_mismatch",
                f"twelve_growth_stages[{position}] disagrees with the independent Di Shi oracle",
            ))
        if not _valid_text(item.get("boundary")):
            findings.append(_finding(
                "bazi_growth_stage_boundary_missing",
                f"twelve_growth_stages[{position}] must declare its non-verdict boundary",
            ))
    if set(raw_stages) != _BAZI_PILLAR_POSITIONS:
        findings.append(_finding(
            "bazi_growth_stage_invalid_keys",
            "twelve_growth_stages must contain exactly the four pillar positions",
        ))
    return findings


def _validate_bazi_xunkong(output: dict[str, Any]) -> list[dict[str, str]]:
    """Independently recompute the day-pillar ten-day xun void branches."""

    raw_pillars = output.get("four_pillars")
    raw_xunkong = output.get("xunkong")
    if not isinstance(raw_pillars, dict) or not isinstance(raw_xunkong, dict):
        return [_finding(
            "bazi_xunkong_missing",
            "Bazi output must expose four pillars and xunkong",
        )]
    day_pillar = raw_pillars.get("day")
    if not isinstance(day_pillar, str) or day_pillar not in _BAZI_ORACLE_JIAZI:
        return [_finding(
            "bazi_xunkong_invalid_day_pillar",
            "Bazi xunkong requires a valid day sexagenary pillar",
        )]
    day_index = _BAZI_ORACLE_JIAZI.index(day_pillar)
    xun_start = _BAZI_ORACLE_JIAZI[(day_index // 10) * 10]
    branch_index = _BAZI_ORACLE_BRANCHES.index(xun_start[1])
    expected_branches = [
        _BAZI_ORACLE_BRANCHES[(branch_index + offset) % 12]
        for offset in (10, 11)
    ]
    expected = {
        "day_pillar": day_pillar,
        "xun": xun_start,
        "branches": expected_branches,
        "source_dependency_id": "bazi.chart.xunkong-sexagenary-v1",
    }
    findings: list[dict[str, str]] = []
    if any(raw_xunkong.get(key) != value for key, value in expected.items()):
        findings.append(_finding(
            "bazi_xunkong_recompute_mismatch",
            "xunkong disagrees with the independent sexagenary xun oracle",
        ))
    branches = raw_xunkong.get("branches")
    if (
        not isinstance(branches, list)
        or len(branches) != 2
        or any(branch not in _BAZI_ORACLE_BRANCHES for branch in branches)
        or len(set(branches)) != 2
    ):
        findings.append(_finding(
            "bazi_xunkong_invalid_branches",
            "xunkong.branches must contain two distinct earthly branches",
        ))
    if not _valid_text(raw_xunkong.get("boundary")):
        findings.append(_finding(
            "bazi_xunkong_boundary_missing",
            "xunkong must declare its non-verdict boundary",
        ))
    return findings


def _validate_bazi_san_yuan(output: dict[str, Any]) -> list[dict[str, str]]:
    """Independently recompute the recovered engine's three-palace facts."""

    raw_pillars = output.get("four_pillars")
    raw_san_yuan = output.get("san_yuan")
    if not isinstance(raw_pillars, dict) or not isinstance(raw_san_yuan, dict):
        return [_finding(
            "bazi_san_yuan_missing",
            "Bazi output must expose four pillars and san_yuan",
        )]
    required = {"year", "month", "hour"}
    if any(
        not isinstance(raw_pillars.get(position), str)
        or len(raw_pillars[position]) != 2
        for position in required
    ):
        return [_finding(
            "bazi_san_yuan_invalid_pillars",
            "Bazi san_yuan requires year, month and hour pillars",
        )]
    stems = _BAZI_ORACLE_STEMS
    branches = _BAZI_ORACLE_BRANCHES
    month_branches = "寅卯辰巳午未申酉戌亥子丑"
    year_stem = raw_pillars["year"][0]
    month_stem = raw_pillars["month"][0]
    month_branch = raw_pillars["month"][1]
    hour_branch = raw_pillars["hour"][1]
    if any(
        stem not in stems for stem in (year_stem, month_stem)
    ) or any(
        branch not in branches for branch in (month_branch, hour_branch)
    ):
        return [_finding(
            "bazi_san_yuan_invalid_pillars",
            "Bazi san_yuan contains an invalid stem or branch",
        )]
    month_index = month_branches.index(month_branch) + 1
    hour_index = month_branches.index(hour_branch) + 1
    ming_offset = month_index + hour_index
    ming_offset = (26 if ming_offset >= 14 else 14) - ming_offset
    shen_offset = month_index + hour_index
    if shen_offset > 12:
        shen_offset -= 12
    year_stem_index = stems.index(year_stem)

    def palace_stem(offset: int) -> str:
        gan_index = (year_stem_index + 1) * 2 + offset
        while gan_index > 10:
            gan_index -= 10
        return stems[gan_index - 1]

    expected = {
        "tai_yuan": stems[(stems.index(month_stem) + 1) % 10]
        + branches[(branches.index(month_branch) + 3) % 12],
        "ming_gong": palace_stem(ming_offset) + month_branches[ming_offset - 1],
        "shen_gong": palace_stem(shen_offset) + month_branches[shen_offset - 1],
        "source": "lunar-typescript-auxiliary",
        "source_dependency_id": "bazi.chart.san-yuan-lunar-typescript-v1",
    }
    findings: list[dict[str, str]] = []
    if any(raw_san_yuan.get(key) != value for key, value in expected.items()):
        findings.append(_finding(
            "bazi_san_yuan_recompute_mismatch",
            "san_yuan disagrees with the independent three-palace oracle",
        ))
    for key in ("tai_yuan", "ming_gong", "shen_gong", "source", "source_dependency_id", "boundary"):
        if not _valid_text(raw_san_yuan.get(key)):
            findings.append(_finding(
                "bazi_san_yuan_invalid_shape",
                f"san_yuan.{key} must be non-empty text",
            ))
    return findings


def _bazi_unique_text_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and bool(item) for item in value)
        and len(value) == len(set(value))
    )


def _bazi_partial_luck_oracle(
    pillars: dict[str, str],
    gender: str,
) -> tuple[bool, list[str]]:
    """Independently recompute direction and the ten-step sequence.

    The oracle re-derives the declared convention from its own tables so a
    corrupted or forged adapter payload cannot validate against itself.
    """

    jiazi = [
        _BAZI_ORACLE_STEMS[index % 10] + _BAZI_ORACLE_BRANCHES[index % 12]
        for index in range(60)
    ]
    yang_year = _BAZI_ORACLE_STEMS.index(pillars["year"][0]) % 2 == 0
    forward = (gender == "male" and yang_year) or (
        gender == "female" and not yang_year
    )
    month_index = jiazi.index(pillars["month"])
    direction = 1 if forward else -1
    sequence = [
        jiazi[(month_index + direction * step) % 60] for step in range(1, 11)
    ]
    return forward, sequence


def _validate_bazi_supplied_salience(
    output: dict[str, Any],
) -> list[dict[str, str]]:
    candidates = output.get("interpretive_candidates")
    candidates = candidates if isinstance(candidates, dict) else {}
    signals = candidates.get("salience_signals")
    if not isinstance(signals, list):
        return [_finding(
            "bazi_missing_salience_signals",
            "A supplied-pillars chart must publish its mechanical salience signals",
        )]
    findings: list[dict[str, str]] = []
    seen_signal_ids: set[str] = set()
    for item in signals:
        entry = item if isinstance(item, dict) else {}
        signal_id = entry.get("signal_id")
        basis = entry.get("basis")
        valid = (
            set(entry) == BAZI_SALIENCE_SIGNAL_KEYS
            and _valid_text(signal_id)
            and signal_id not in seen_signal_ids
            and entry.get("status") == "mechanical_candidate"
            and isinstance(basis, dict)
            and bool(basis)
            and not _bazi_salience_basis_has_reserved_metadata(basis)
            and entry.get("hard_verdict") is None
            and _valid_text(entry.get("boundary"))
        )
        if _valid_text(signal_id):
            seen_signal_ids.add(str(signal_id))
        if not valid:
            findings.append(_finding(
                "bazi_invalid_salience_signal",
                "Every Bazi salience signal must stay a uniquely identified mechanical candidate without verdicts or scores",
            ))
    return findings


def _validate_bazi_supplied_pillar_luck(
    payload: dict[str, Any],
    output: dict[str, Any],
) -> list[dict[str, str]]:
    """Fail-closed schema for supplied-pillars partial luck layers."""

    findings: list[dict[str, str]] = []
    luck = output.get("luck_cycles")
    if not isinstance(luck, dict):
        return [_finding(
            "bazi_partial_luck_missing",
            "A supplied-pillars chart must publish its partial luck layer",
        )]
    input_block = (
        payload.get("input")
        if isinstance(payload.get("input"), dict)
        else {}
    )
    adapter = (
        payload.get("adapter")
        if isinstance(payload.get("adapter"), dict)
        else {}
    )
    if (
        payload.get("fact_layer_status") != BAZI_PARTIAL_FACT_STATUS
        or payload.get("fact_layer_scope") != BAZI_PARTIAL_FACT_SCOPE
        or input_block.get("mode") != BAZI_PARTIAL_INPUT_MODE
        or adapter.get("rule_profile") != BAZI_PARTIAL_RULE_PROFILE
    ):
        findings.append(_finding(
            "bazi_partial_luck_invalid_input",
            "Supplied four-pillar facts require matching status, scope, input mode, and adapter profile",
        ))
    normalized = (
        input_block.get("normalized_input")
        if isinstance(input_block.get("normalized_input"), dict)
        else {}
    )
    gender = normalized.get("gender")
    pillars = normalized.get("pillars")
    valid_gender = gender is None or (
        isinstance(gender, str) and gender in {"male", "female"}
    )
    valid_pillars = (
        isinstance(pillars, dict)
        and set(pillars) == _BAZI_PILLAR_POSITIONS
        and all(
            isinstance(value, str) and value in _BAZI_ORACLE_JIAZI
            for value in pillars.values()
        )
    )
    if not valid_gender or not valid_pillars:
        return [_finding(
            "bazi_partial_luck_invalid_input",
            "A supplied-pillars chart requires four valid normalized Jiazi pillars and an optional normalized male/female gender",
        )]
    output_pillars = output.get("four_pillars")
    calendar = payload.get("calendar_normalization")
    calendar_pillars = (
        calendar.get("ganzhi") if isinstance(calendar, dict) else None
    )
    if output_pillars != pillars or calendar_pillars != pillars:
        findings.append(_finding(
            "bazi_partial_luck_input_output_mismatch",
            "The calculated and calendar four pillars must match the validated normalized input",
        ))
    has_gender = gender in {"male", "female"}
    status = luck.get("status")
    expected_status = (
        "sequence_only" if has_gender else "not_calculated_missing_gender"
    )
    if status != expected_status:
        findings.append(_finding(
            "bazi_partial_luck_invalid_shape",
            "A supplied-pillars luck layer may only carry its declared partial status",
        ))
    expected_keys = (
        BAZI_PARTIAL_SEQUENCED_KEYS if has_gender else BAZI_PARTIAL_GENDERLESS_KEYS
    )
    missing_keys = expected_keys - set(luck)
    extra_keys = set(luck) - expected_keys
    timing_keys = extra_keys & set(BAZI_PARTIAL_LUCK_TIMING_FIELDS)
    if timing_keys:
        findings.append(_finding(
            "bazi_partial_luck_fabricated_timing",
            "A partial luck layer must not fabricate start ages, calendar mappings, or timing",
        ))
    if missing_keys or extra_keys - timing_keys:
        findings.append(_finding(
            "bazi_partial_luck_invalid_shape",
            "A partial luck layer must carry exactly its declared fields",
        ))
    expected_unavailable = set(
        BAZI_PARTIAL_TIMING_UNAVAILABLE
        if has_gender
        else BAZI_PARTIAL_GENDERLESS_UNAVAILABLE
    )
    unavailable = luck.get("unavailable")
    if (
        not _bazi_unique_text_list(unavailable)
        or set(unavailable) != expected_unavailable
    ):
        findings.append(_finding(
            "bazi_partial_luck_invalid_shape",
            "A partial luck layer must declare exactly its unavailable scopes",
        ))
    cycles = luck.get("cycles")
    cycles_list = cycles if isinstance(cycles, list) else []
    cycle_timing_tainted = any(
        isinstance(cycle, dict)
        and any(field in cycle for field in BAZI_PARTIAL_LUCK_TIMING_FIELDS)
        for cycle in cycles_list
    )
    if cycle_timing_tainted:
        findings.append(_finding(
            "bazi_partial_luck_fabricated_timing",
            "A partial luck layer must not fabricate start ages, calendar mappings, or timing",
        ))
    if not has_gender:
        if not isinstance(cycles, list) or cycles != [] or "direction" in luck:
            findings.append(_finding(
                "bazi_partial_luck_invalid_shape",
                "A missing-gender luck layer must stay empty",
            ))
    else:
        shape_ok = (
            isinstance(cycles, list)
            and len(cycles_list) == 10
            and all(
                isinstance(cycle, dict)
                and set(cycle) == {"sequence", "pillar"}
                and type(cycle.get("sequence")) is int
                and cycle.get("sequence") == index
                and _valid_text(cycle.get("pillar"))
                for index, cycle in enumerate(cycles_list, start=1)
            )
        )
        if not shape_ok and not cycle_timing_tainted:
            findings.append(_finding(
                "bazi_partial_luck_invalid_shape",
                "A sequence-only luck layer needs exactly ten sequence/pillar steps",
            ))
        if shape_ok:
            forward, expected_sequence = _bazi_partial_luck_oracle(pillars, gender)
            expected_direction = "forward" if forward else "reverse"
            if (
                luck.get("direction") != expected_direction
                or luck.get("direction_rule") != BAZI_PARTIAL_DIRECTION_RULE
                or [cycle["pillar"] for cycle in cycles_list] != expected_sequence
            ):
                findings.append(_finding(
                    "bazi_partial_luck_recompute_mismatch",
                    "The partial luck sequence disagrees with the declared direction convention recomputed from the supplied pillars",
                ))
    capabilities = (
        payload.get("capabilities")
        if isinstance(payload.get("capabilities"), dict)
        else {}
    )
    allowed_value = capabilities.get("allowed")
    blocked_value = capabilities.get("blocked")
    capability_lists_valid = (
        _bazi_unique_text_list(allowed_value)
        and _bazi_unique_text_list(blocked_value)
    )
    allowed = set(allowed_value) if capability_lists_valid else set()
    blocked = set(blocked_value) if capability_lists_valid else set()
    expected_allowed = {"static_natal_interpretation"}
    if has_gender:
        expected_allowed.add("luck_cycle_sequence")
    if (
        not capability_lists_valid
        or allowed != expected_allowed
        or blocked != BAZI_PARTIAL_BLOCKED_CAPABILITIES
        or bool(allowed & blocked)
    ):
        findings.append(_finding(
            "bazi_partial_luck_capability_mismatch",
            "A supplied-pillars payload must expose exactly its partial capability state",
        ))
    return findings


def _validate_bazi_partial_luck(
    payload: dict[str, Any],
    output: dict[str, Any],
) -> list[dict[str, str]]:
    """Enforce the supplied-pillars luck scopes: sequence yes, timing never.

    Supplied-pillars payloads validate fail-closed against an exact closed
    schema plus an independent recompute oracle. Other bazi payloads keep
    the permissive shape check so legacy hand-built fixtures stay readable.
    """

    input_block = payload.get("input")
    input_mode = (
        input_block.get("mode") if isinstance(input_block, dict) else None
    )
    adapter = payload.get("adapter")
    rule_profile = (
        adapter.get("rule_profile") if isinstance(adapter, dict) else None
    )
    luck = output.get("luck_cycles")
    luck_status = luck.get("status") if isinstance(luck, dict) else None
    supplied_markers = (
        payload.get("fact_layer_status") == BAZI_PARTIAL_FACT_STATUS,
        payload.get("fact_layer_scope") == BAZI_PARTIAL_FACT_SCOPE,
        input_mode == BAZI_PARTIAL_INPUT_MODE,
        rule_profile == BAZI_PARTIAL_RULE_PROFILE,
        isinstance(luck_status, str)
        and luck_status in {"sequence_only", "not_calculated_missing_gender"},
    )
    if any(supplied_markers):
        findings = _validate_bazi_supplied_pillar_luck(payload, output)
        findings.extend(_validate_bazi_supplied_salience(output))
        return findings

    findings: list[dict[str, str]] = []
    if not isinstance(luck, dict):
        return findings
    status = luck.get("status")
    if status not in {"sequence_only", "not_calculated_missing_gender"}:
        return findings
    cycles = luck.get("cycles")
    unavailable = luck.get("unavailable")
    if status == "sequence_only":
        valid_cycles = (
            isinstance(cycles, list)
            and len(cycles) == 10
            and all(
                isinstance(cycle, dict)
                and set(cycle) == {"sequence", "pillar"}
                and cycle.get("sequence") == index
                and _valid_text(cycle.get("pillar"))
                for index, cycle in enumerate(cycles, start=1)
            )
        )
        required_unavailable = {
            "start_age",
            "calendar_year_mapping",
            "active_cycle",
            "precise_timing",
        }
        if (
            luck.get("direction") not in {"forward", "reverse"}
            or not _valid_text(luck.get("direction_rule"))
            or not valid_cycles
            or not isinstance(unavailable, list)
            or not required_unavailable.issubset(set(unavailable))
        ):
            findings.append(_finding(
                "bazi_partial_luck_invalid_shape",
                "A sequence-only luck layer needs direction, the declared rule, ten sequence/pillar steps, and explicit unavailable scopes",
            ))
    else:
        required_unavailable = {
            "direction",
            "sequence",
            "start_age",
            "calendar_year_mapping",
            "active_cycle",
            "precise_timing",
        }
        if (
            cycles != []
            or "direction" in luck
            or not isinstance(unavailable, list)
            or not required_unavailable.issubset(set(unavailable))
        ):
            findings.append(_finding(
                "bazi_partial_luck_invalid_shape",
                "A missing-gender luck layer must stay empty with explicit unavailable scopes",
            ))
    fabricated = any(
        field in luck for field in BAZI_PARTIAL_LUCK_TIMING_FIELDS
    ) or any(
        isinstance(cycle, dict)
        and any(field in cycle for field in BAZI_PARTIAL_LUCK_TIMING_FIELDS)
        for cycle in (cycles if isinstance(cycles, list) else ())
    )
    if fabricated:
        findings.append(_finding(
            "bazi_partial_luck_fabricated_timing",
            "A partial luck layer must not fabricate start ages, calendar mappings, or timing",
        ))
    capabilities = (
        payload.get("capabilities")
        if isinstance(payload.get("capabilities"), dict)
        else {}
    )
    if "luck_cycle_timing" not in (capabilities.get("blocked") or ()):
        findings.append(_finding(
            "bazi_partial_luck_unblocked_timing",
            "A partial luck payload must keep luck_cycle_timing blocked",
        ))
    return findings


BAZI_STATIC_SCOPE = "natal_static"
BAZI_CONFLICT_FACT_STATUS = "conflict_birth_data_vs_supplied_pillars"


class BaziFactContract(FactContract):
    """Fact contract for the bazi Provider (manifest ``fact_contract``)."""

    contract_id = "bazi.supplied-and-computed.v1"
    replaces_legacy_validation = True
    canonical_facts_type = BaziCanonicalFacts

    #: Required output ids owned by the bazi fact contract. Frozen from the
    #: legacy facade table so migrating changes nothing about the report.
    required_output_ids_full = (
        "four_pillars",
        "hidden_stems",
        "ten_gods",
        "nayin",
        "twelve_growth_stages",
        "xunkong",
        "san_yuan",
        "month_command",
        "seasonal_profile",
        "tiaohou_markers",
        "interpretive_candidates",
        "shensha_auxiliary",
        "luck_cycles",
    )

    def required_output_ids(
        self,
        payload: dict[str, Any],
        base_required: tuple[str, ...],
    ) -> tuple[str, ...]:
        del base_required  # the contract owns its own required set
        if payload.get("fact_layer_scope") == BAZI_STATIC_SCOPE:
            return tuple(
                key for key in self.required_output_ids_full if key != "luck_cycles"
            )
        return tuple(self.required_output_ids_full)

    def required_calendar_keys(
        self,
        payload: dict[str, Any],
        base_required: tuple[str, ...],
    ) -> tuple[str, ...]:
        if payload.get("fact_layer_scope") == BAZI_STATIC_SCOPE:
            return ("status", "ganzhi")
        return tuple(base_required)

    def validate_conflict_state(
        self,
        payload: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Payload-level checks that must run even when output is empty.

        The legacy facade reported the birth-data/pillars conflict
        unconditionally; keeping it outside the output-gated
        ``validate_output`` preserves that behavior.
        """
        findings: list[dict[str, str]] = []
        if payload.get("fact_layer_status") == BAZI_CONFLICT_FACT_STATUS:
            findings.append(_finding(
                "conflicting_bazi_facts",
                "Birth-data calculation conflicts with the supplied four"
                " pillars",
            ))
        return findings

    def validate_output(
        self,
        payload: dict[str, Any],
        output: dict[str, Any],
    ) -> list[dict[str, str]]:
        findings: list[dict[str, str]] = []
        findings.extend(_validate_bazi_v51_output(output))
        findings.extend(_validate_bazi_growth_stages(output))
        findings.extend(_validate_bazi_xunkong(output))
        findings.extend(_validate_bazi_san_yuan(output))
        findings.extend(_validate_bazi_partial_luck(payload, output))
        return findings
