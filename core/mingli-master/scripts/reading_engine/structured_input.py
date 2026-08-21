"""One validator and normalizer for every user-supplied Tier-B chart."""

from __future__ import annotations

import copy
from typing import Any

import adapter_validate
import structured_chart_adapter


def _expected_route(system: str) -> tuple[str, str | None]:
    requested = str(system or "").strip().lower()
    return structured_chart_adapter.ROUTE_ALIASES.get(
        requested,
        (requested, None),
    )


def _route_matches(system: str, facts: dict[str, Any]) -> bool:
    expected_system, expected_subsystem = _expected_route(system)
    if facts.get("system") != expected_system:
        return False
    return (
        expected_subsystem is None
        or facts.get("subsystem") == expected_subsystem
    )


def normalize_structured_chart(system: str, raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or not raw:
        raise ValueError("complete user-provided chart is required")
    adapter = raw.get("adapter") if isinstance(raw.get("adapter"), dict) else {}
    if adapter.get("name") == structured_chart_adapter.ADAPTER_NAME:
        facts = copy.deepcopy(raw)
        expected_system, _ = _expected_route(system)
        validation = adapter_validate.validate_payload(expected_system, facts)
        if not validation["ok"]:
            raise ValueError(
                "invalid structured chart: "
                + ", ".join(item["code"] for item in validation["findings"])
            )
    else:
        facts = structured_chart_adapter.build_payload(system, copy.deepcopy(raw))
    if not _route_matches(system, facts):
        raise ValueError(
            "structured chart system or subsystem does not match the requested route"
        )
    return facts


def has_complete_structured_chart(system: str, raw: dict[str, Any]) -> bool:
    try:
        normalize_structured_chart(system, raw)
    except (KeyError, TypeError, ValueError):
        return False
    return True


__all__ = [
    "has_complete_structured_chart",
    "normalize_structured_chart",
]
