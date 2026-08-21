"""Cheap fail-closed checks shared by exhaustive provider audits."""

from __future__ import annotations

from typing import Any

from reading_engine.providers import PROVIDER_CAPABILITIES


def provider_preflight_failure(
    *,
    system: str,
    schema_version: str,
    provider_class: type,
    expected_mode: str,
    expected_provider_id: str | None = None,
    expected_provider_version: str | None = None,
) -> dict[str, Any] | None:
    findings: list[str] = []
    if (
        expected_provider_id is not None
        and expected_provider_version is not None
        and (
            provider_class.provider_id != expected_provider_id
            or provider_class.provider_version != expected_provider_version
        )
    ):
        findings.append(f"{system} provider identity drift")
    capability = PROVIDER_CAPABILITIES.get(system)
    if capability is None or capability.mode != expected_mode:
        findings.append(
            f"{system} provider capability mode is not {expected_mode}"
        )
    if not findings:
        return None
    return {
        "schema_version": schema_version,
        "system": system,
        "status": "fail",
        "provider_ready": False,
        "provider": {
            "provider_id": provider_class.provider_id,
            "provider_version": provider_class.provider_version,
            "capability_mode": capability.mode if capability is not None else None,
        },
        "counts": {},
        "route_owned_case_ids": [],
        "boundary_categories": [],
        "findings": findings,
    }
