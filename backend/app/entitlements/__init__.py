"""Dogfood-era capability grants (not a commercial entitlement ledger)."""

from app.entitlements.service import (
    PAID_READING_CAPABILITIES,
    EntitlementDeniedError,
    EntitlementService,
    paid_capability_for_action,
)

__all__ = [
    "PAID_READING_CAPABILITIES",
    "EntitlementDeniedError",
    "EntitlementService",
    "paid_capability_for_action",
]
