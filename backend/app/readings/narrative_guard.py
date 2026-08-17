from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from app.readings.narrative_contracts import (
    NarrativeCandidate,
    OutputContract,
    merge_claim_scopes,
)
from app.readings.output_contracts import resolve_output_contract
from app.readings.runtime_contracts import (
    ContractValidationError,
    ReadingBrief,
)

_INTERNAL_IDENTIFIER = re.compile(
    r"(?:state_token|fact:|finding:|evidence:|subject:|schema|prompt|provider)",
    re.IGNORECASE,
)
_PROBABILITY = re.compile(r"%|百分之")
_GUARANTEE = re.compile(r"保证|必然|一定会|肯定会")
_SPECIFIC_DATE = re.compile(r"\b\d{4}(?:-|/|年)\d{1,2}(?:-|/|月)\d{1,2}日?\b")
_SPECIFIC_MONEY = re.compile(r"\b\d+(?:\.\d+)?\s*(?:元|块|万元|人民币|美元)\b")
_CERTAINTY_RANK = {
    "certainty.possible": 1,
    "certainty.tendency": 2,
    "certainty.strong": 3,
    "certainty.certain": 4,
}
_BAZI_DEEP_OUTPUT_CONTRACT_ID = "bazi-deep-output-v1"
_BAZI_DEEP_TEXT_NOT_GROUNDED = "bazi_deep_text_not_grounded"
_BAZI_DEEP_DUPLICATE_SOURCE = "bazi_deep_duplicate_source"


@dataclass(frozen=True, slots=True)
class GuardResult:
    passed: bool
    errors: tuple[str, ...]


def contains_internal_identifier(text: str) -> bool:
    return _INTERNAL_IDENTIFIER.search(text) is not None


def _add_error(errors: list[str], code: str) -> None:
    if code not in errors:
        errors.append(code)


def _candidate_from_value(
    value: NarrativeCandidate | Mapping[str, object],
) -> NarrativeCandidate | None:
    if isinstance(value, NarrativeCandidate):
        return value
    try:
        return NarrativeCandidate.from_dict(value)
    except (ContractValidationError, KeyError, TypeError, ValueError):
        return None


def _certainty_exceeds(value: str, ceiling: str) -> bool:
    if value == ceiling:
        return False
    value_rank = _CERTAINTY_RANK.get(value)
    ceiling_rank = _CERTAINTY_RANK.get(ceiling)
    if value_rank is None or ceiling_rank is None:
        return True
    return value_rank > ceiling_rank


def _text_matches_public_source(text: str, source: object) -> bool:
    return isinstance(source, str) and text == source


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_refs(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    refs = tuple(value)
    if not all(_non_empty_text(ref) for ref in refs):
        return None
    return cast(tuple[str, ...], refs)


def _is_verified_exact_evidence(item: object) -> bool:
    if not isinstance(item, Mapping):
        return False
    ref = item.get("ref")
    evidence_ref = item.get("evidence_ref")
    source_title = item.get("source_title")
    locator = item.get("locator")
    excerpt = item.get("excerpt")
    verbatim_excerpt = item.get("verbatim_excerpt")
    if (
        not _non_empty_text(ref)
        or evidence_ref != ref
        or item.get("verification_status") != "verified_exact"
        or not _non_empty_text(item.get("rule_id"))
        or not _non_empty_text(source_title)
        or not _non_empty_text(locator)
        or not _non_empty_text(verbatim_excerpt)
        or excerpt != verbatim_excerpt
    ):
        return False
    supports = _string_refs(item.get("supports_fact_refs"))
    citations = item.get("verbatim_citations")
    if not supports or not isinstance(citations, (list, tuple)) or not citations:
        return False
    for citation in citations:
        if not isinstance(citation, Mapping):
            return False
        if (
            citation.get("verification_status") != "verified_exact"
            or not _non_empty_text(citation.get("source_title"))
            or not _non_empty_text(citation.get("locator"))
            or not _non_empty_text(citation.get("verbatim_excerpt"))
        ):
            return False
    first = citations[0]
    return all(
        (
            first.get("source_title") == source_title,
            first.get("locator") == locator,
            first.get("verbatim_excerpt") == verbatim_excerpt,
        )
    )


def _is_audited_public_finding(
    finding: object,
    evidence: Mapping[str, object],
) -> bool:
    if not isinstance(finding, Mapping) or finding.get("support_mode") != "exact":
        return False
    fact_refs = _string_refs(finding.get("fact_refs"))
    evidence_refs = _string_refs(finding.get("evidence_refs"))
    if not fact_refs or not evidence_refs:
        return False
    fact_ref_set = set(fact_refs)
    for evidence_ref in evidence_refs:
        item = evidence.get(evidence_ref)
        if not _is_verified_exact_evidence(item):
            return False
        assert isinstance(item, Mapping)
        supports = _string_refs(item.get("supports_fact_refs"))
        if not supports or not set(supports).issubset(fact_ref_set):
            return False
    return True


class NarrativeGuard:
    """Validate reference closure and product bounds.

    ``bazi-deep-output-v1`` additionally uses a P0 extractive text contract:
    each block must exactly copy a directly referenced public fact, Runtime
    claim unit, or limit.
    This mechanical equality check is not general semantic entailment; other
    output contracts keep the reference-closure behavior below.
    """

    def validate(
        self,
        candidate: NarrativeCandidate | Mapping[str, object],
        brief: ReadingBrief,
        output_contract: str | OutputContract,
    ) -> GuardResult:
        parsed = _candidate_from_value(candidate)
        if parsed is None:
            return GuardResult(passed=False, errors=("schema_invalid",))

        contract = resolve_output_contract(output_contract)
        payload = brief.to_dict()
        errors: list[str] = []
        facts = {item["ref"]: item for item in payload["facts"]}
        evidence = {item["ref"]: item for item in payload["evidence"]}
        findings = {item["ref"]: item for item in payload["findings"]}
        limits = {item["kind_id"]: item for item in payload["limits"]}
        scopes = merge_claim_scopes(payload)
        subjects = {item["subject_ref"] for item in [*payload["facts"], *payload["findings"]]} | {
            subject for subject, _dimension in scopes
        }
        dimensions = {dimension for _subject, dimension in scopes}
        brief_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        is_bazi_deep = contract.contract_id == _BAZI_DEEP_OUTPUT_CONTRACT_ID

        if not contract.min_blocks <= len(parsed.blocks) <= contract.max_blocks:
            _add_error(errors, "block_count_out_of_range")
        if len("\n\n".join(block.text for block in parsed.blocks)) > (contract.max_output_chars):
            _add_error(errors, "output_too_long")
        block_ids = [block.block_id for block in parsed.blocks]
        if len(set(block_ids)) != len(block_ids):
            _add_error(errors, "duplicate_block_id")

        covered_dimensions: set[str] = set()
        covered_limits: set[str] = set()
        used_bazi_source_refs: set[str] = set()
        used_bazi_texts: set[str] = set()
        for block in parsed.blocks:
            covered_dimensions.add(block.dimension_id)
            covered_limits.update(block.limit_kind_ids)
            if block.subject_ref not in subjects:
                _add_error(errors, "unknown_subject_ref")
            if block.dimension_id not in dimensions:
                _add_error(errors, "unknown_dimension")

            known_facts = [facts.get(ref) for ref in block.fact_refs]
            known_findings = [findings.get(ref) for ref in block.finding_refs]
            known_evidence = [evidence.get(ref) for ref in block.evidence_refs]
            known_limits = [limits.get(ref) for ref in block.limit_kind_ids]
            matched_fact_refs = {
                ref
                for ref, fact in zip(block.fact_refs, known_facts, strict=True)
                if fact is not None
                and _text_matches_public_source(block.text, fact["display_text"])
            }
            matched_finding_refs = {
                ref
                for ref, finding in zip(block.finding_refs, known_findings, strict=True)
                if _is_audited_public_finding(finding, evidence)
                and isinstance(finding, Mapping)
                and _text_matches_public_source(
                    block.text,
                    finding.get("public_text"),
                )
            }
            matched_limit_refs = {
                ref
                for ref, limit in zip(block.limit_kind_ids, known_limits, strict=True)
                if limit is not None
                and _text_matches_public_source(block.text, limit["public_text"])
            }
            grounded_in_limit = bool(matched_limit_refs)
            bazi_source_refs = {
                *(f"fact:{ref}" for ref in matched_fact_refs),
                *(f"finding:{ref}" for ref in matched_finding_refs),
                *(f"limit:{ref}" for ref in matched_limit_refs),
            }
            if is_bazi_deep:
                if not bazi_source_refs:
                    _add_error(errors, _BAZI_DEEP_TEXT_NOT_GROUNDED)
                elif (
                    block.text in used_bazi_texts
                    or bool(bazi_source_refs & used_bazi_source_refs)
                ):
                    _add_error(errors, _BAZI_DEEP_DUPLICATE_SOURCE)
                else:
                    used_bazi_texts.add(block.text)
                    used_bazi_source_refs.update(bazi_source_refs)
            relationship_scope_fact_refs: frozenset[str] = frozenset()
            if any(item is None for item in known_facts):
                _add_error(errors, "unknown_fact_ref")
            if any(item is None for item in known_findings):
                _add_error(errors, "unknown_finding_ref")
            if any(item is None for item in known_evidence):
                _add_error(errors, "unknown_evidence_ref")
            if any(item is None for item in known_limits):
                _add_error(errors, "unknown_limit_ref")

            scope = scopes.get((block.subject_ref, block.dimension_id))
            if scope is None:
                _add_error(errors, "scope_mismatch")
            else:
                allowed_kind_ids = cast(tuple[str, ...], scope["allowed_kind_ids"])
                certainty_ceiling_id = cast(str, scope["certainty_ceiling_id"])
                fact_refs = cast(tuple[str, ...], scope["fact_refs"])
                evidence_refs = cast(tuple[str, ...], scope["evidence_refs"])
                relationship_scope_fact_refs = frozenset(fact_refs)
                if block.claim_kind_id not in allowed_kind_ids:
                    _add_error(errors, "kind_not_allowed")
                if _certainty_exceeds(
                    block.certainty_id,
                    certainty_ceiling_id,
                ):
                    _add_error(errors, "certainty_exceeded")
                if not set(block.fact_refs).issubset(fact_refs):
                    _add_error(errors, "scope_mismatch")
                if not set(block.evidence_refs).issubset(evidence_refs):
                    _add_error(errors, "scope_mismatch")

            for fact in known_facts:
                # A relationship claim is deliberately a cross-subject block.
                # It may cite the other subject's source fact only when that
                # exact ref was published in the relationship scope; ordinary
                # single-subject dimensions stay strict.
                if (
                    fact is not None
                    and fact["subject_ref"] != block.subject_ref
                    and not (
                        block.dimension_id == "relationship"
                        and fact["ref"] in relationship_scope_fact_refs
                    )
                ):
                    _add_error(errors, "scope_mismatch")
            for item in known_evidence:
                if item is not None and not (
                    set(item["supports_fact_refs"]) & set(block.fact_refs)
                ):
                    _add_error(errors, "scope_mismatch")
            for finding in known_findings:
                if finding is None:
                    continue
                if (
                    finding["subject_ref"] != block.subject_ref
                    or block.dimension_id not in finding["dimension_ids"]
                    or not set(finding["fact_refs"]).issubset(block.fact_refs)
                    or not set(finding["evidence_refs"]).issubset(block.evidence_refs)
                    or not set(finding["limit_kind_ids"]).issubset(block.limit_kind_ids)
                ):
                    _add_error(errors, "scope_mismatch")
            for limit in known_limits:
                scope_refs = (
                    cast(tuple[str, ...], limit["scope_refs"])
                    if limit is not None
                    else ()
                )
                if (
                    limit is not None
                    and scope_refs
                    and block.subject_ref not in scope_refs
                    and block.dimension_id not in scope_refs
                ):
                    _add_error(errors, "scope_mismatch")

            if contains_internal_identifier(block.text):
                _add_error(errors, "internal_identifier_visible")
            if _PROBABILITY.search(block.text):
                _add_error(errors, "uncalibrated_probability")
            if _GUARANTEE.search(block.text) and not (is_bazi_deep and grounded_in_limit):
                _add_error(errors, "unsupported_guarantee")
            specific_values = [
                *(match.group(0) for match in _SPECIFIC_DATE.finditer(block.text)),
                *(match.group(0) for match in _SPECIFIC_MONEY.finditer(block.text)),
            ]
            if any(value not in brief_text for value in specific_values):
                _add_error(errors, "invented_specific")

        if not set(contract.required_dimension_ids).issubset(covered_dimensions):
            _add_error(errors, "required_dimension_missing")
        if not set(contract.required_limit_kind_ids).issubset(covered_limits):
            _add_error(errors, "required_limit_missing")
        return GuardResult(passed=not errors, errors=tuple(errors))
