from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

from app.readings.narrative_contracts import (
    NarrativeCandidate,
    OutputContract,
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


class NarrativeGuard:
    """Validates reference closure and product bounds without judging prose semantics."""

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
        scopes = {
            (item["subject_ref"], item["dimension_id"]): item for item in payload["claim_scopes"]
        }
        subjects = {item["subject_ref"] for item in [*payload["facts"], *payload["findings"]]} | {
            subject for subject, _dimension in scopes
        }
        dimensions = {dimension for _subject, dimension in scopes}
        brief_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        if not contract.min_blocks <= len(parsed.blocks) <= contract.max_blocks:
            _add_error(errors, "block_count_out_of_range")
        if len("\n\n".join(block.text for block in parsed.blocks)) > (contract.max_output_chars):
            _add_error(errors, "output_too_long")
        block_ids = [block.block_id for block in parsed.blocks]
        if len(set(block_ids)) != len(block_ids):
            _add_error(errors, "duplicate_block_id")

        covered_dimensions: set[str] = set()
        covered_limits: set[str] = set()
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
                if block.claim_kind_id not in scope["allowed_kind_ids"]:
                    _add_error(errors, "kind_not_allowed")
                if _certainty_exceeds(
                    block.certainty_id,
                    scope["certainty_ceiling_id"],
                ):
                    _add_error(errors, "certainty_exceeded")
                if not set(block.fact_refs).issubset(scope["fact_refs"]):
                    _add_error(errors, "scope_mismatch")
                if not set(block.evidence_refs).issubset(scope["evidence_refs"]):
                    _add_error(errors, "scope_mismatch")

            for fact in known_facts:
                if fact is not None and fact["subject_ref"] != block.subject_ref:
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
                if (
                    limit is not None
                    and limit["scope_refs"]
                    and block.subject_ref not in limit["scope_refs"]
                ):
                    _add_error(errors, "scope_mismatch")

            if contains_internal_identifier(block.text):
                _add_error(errors, "internal_identifier_visible")
            if _PROBABILITY.search(block.text):
                _add_error(errors, "uncalibrated_probability")
            if _GUARANTEE.search(block.text):
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
