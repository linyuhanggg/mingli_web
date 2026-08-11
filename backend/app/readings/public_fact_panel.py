from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.readings.runtime_contracts import ReadingBrief

# Runtime projects caller inputs as fact:{subject}/input/{field_id}.
# No raw caller input may leave the private result API; only derived facts do.
_SENSITIVE_INPUT_FIELDS = frozenset(
    {
        "birth_datetime",
        "birth_time",
        "birth_datetime_or_four_pillars",
        "datetime",
    }
)
_INPUT_FIELD_REF = re.compile(r"/input/([^/]+)$")
_ISO_DATE_TIME = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
)
_BIRTH_LABEL = re.compile(r"(出生时间|出生时刻|birth[_\s-]?date(?:time)?|birth[_\s-]?time)", re.I)


def _field_id_from_ref(ref: object) -> str | None:
    if not isinstance(ref, str):
        return None
    match = _INPUT_FIELD_REF.search(ref)
    if match is None:
        return None
    return match.group(1)


def _value_has_raw_datetime(value: object) -> bool:
    if isinstance(value, str):
        return _ISO_DATE_TIME.search(value) is not None
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if (
                (key_text in _SENSITIVE_INPUT_FIELDS or key_text.startswith("birth"))
                and isinstance(item, str)
                and _ISO_DATE_TIME.search(item)
            ):
                return True
            if _value_has_raw_datetime(item):
                return True
    if isinstance(value, (list, tuple)):
        return any(_value_has_raw_datetime(item) for item in value)
    return False


def is_sensitive_public_fact(fact: Mapping[str, object]) -> bool:
    """Return True when a brief fact must not be exposed on the public result API."""
    ref = fact.get("ref")
    field_id = _field_id_from_ref(ref)
    if field_id is not None:
        return True
    display = fact.get("display_text")
    display_text = display if isinstance(display, str) else ""
    if _BIRTH_LABEL.search(display_text) and _ISO_DATE_TIME.search(display_text):
        return True
    value = fact.get("value")
    return bool(
        isinstance(ref, str) and "birth" in ref and _value_has_raw_datetime(value)
    )


def _filter_ref_list(values: object, removed: set[str]) -> list[str]:
    if not isinstance(values, list):
        return []
    kept: list[str] = []
    for item in values:
        if isinstance(item, str) and item not in removed:
            kept.append(item)
    return kept


def project_public_fact_panel(
    brief: ReadingBrief | Mapping[str, object] | None,
) -> dict[str, Any] | None:
    """Project a stored ReadingBrief into an API-safe fact panel.

    Internal brief storage and Guard inputs stay untouched; only the outbound
    result payload is filtered.
    """
    if brief is None:
        return None
    payload = brief.to_dict() if isinstance(brief, ReadingBrief) else dict(brief)
    facts = payload.get("facts")
    if not isinstance(facts, list):
        return payload

    kept_facts: list[dict[str, Any]] = []
    removed_refs: set[str] = set()
    for item in facts:
        if not isinstance(item, Mapping):
            continue
        if is_sensitive_public_fact(item):
            ref = item.get("ref")
            if isinstance(ref, str):
                removed_refs.add(ref)
            continue
        kept_facts.append(dict(item))
    payload["facts"] = kept_facts

    if removed_refs:
        scopes = payload.get("claim_scopes")
        if isinstance(scopes, list):
            cleaned_scopes: list[dict[str, Any]] = []
            for scope in scopes:
                if not isinstance(scope, Mapping):
                    continue
                next_scope = dict(scope)
                next_scope["fact_refs"] = _filter_ref_list(scope.get("fact_refs"), removed_refs)
                cleaned_scopes.append(next_scope)
            payload["claim_scopes"] = cleaned_scopes

        findings = payload.get("findings")
        if isinstance(findings, list):
            cleaned_findings: list[dict[str, Any]] = []
            for finding in findings:
                if not isinstance(finding, Mapping):
                    continue
                next_finding = dict(finding)
                next_finding["fact_refs"] = _filter_ref_list(
                    finding.get("fact_refs"),
                    removed_refs,
                )
                cleaned_findings.append(next_finding)
            payload["findings"] = cleaned_findings

        evidence = payload.get("evidence")
        if isinstance(evidence, list):
            cleaned_evidence: list[dict[str, Any]] = []
            for item in evidence:
                if not isinstance(item, Mapping):
                    continue
                next_item = dict(item)
                next_item["supports_fact_refs"] = _filter_ref_list(
                    item.get("supports_fact_refs"),
                    removed_refs,
                )
                cleaned_evidence.append(next_item)
            payload["evidence"] = cleaned_evidence

    return payload
