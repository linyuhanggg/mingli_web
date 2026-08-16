from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.commerce.ledger import EntitlementLedger, LedgerError, LedgerEvent


def event(kind: str, quantity: int, *, entitlement_id: str = "ent-1") -> LedgerEvent:
    return LedgerEvent(
        event_id=uuid4(),
        entitlement_id=entitlement_id,
        kind=kind,  # type: ignore[arg-type]
        quantity=quantity,
        source="test",
        occurred_at=datetime.now(UTC),
    )


def test_ledger_projects_append_only_lifecycle_without_negative_available_units() -> None:
    ledger = EntitlementLedger()

    ledger.append(event("GRANT", 2))
    ledger.append(event("RESERVE", 1))
    ledger.append(event("CONSUME", 1))
    ledger.append(event("GRANT", 1, entitlement_id="ent-2"))
    ledger.append(event("RESERVE", 1, entitlement_id="ent-2"))
    ledger.append(event("CONSUME", 1, entitlement_id="ent-2"))
    ledger.append(event("REVERSE", 1, entitlement_id="ent-2"))

    projection = ledger.project("ent-1")
    assert projection.granted == 2
    assert projection.reserved == 0
    assert projection.consumed == 1
    assert projection.available == 1
    assert ledger.project("ent-2").available == 0


def test_ledger_rejects_consume_before_reserve_and_duplicate_event() -> None:
    ledger = EntitlementLedger()
    grant = event("GRANT", 1)
    ledger.append(grant)

    with pytest.raises(LedgerError, match="consume requires reserved units"):
        ledger.append(event("CONSUME", 1))

    with pytest.raises(LedgerError, match="event already appended"):
        ledger.append(grant)


def test_ledger_rejects_overrelease_overreserve_and_expire_with_reserved_units() -> None:
    ledger = EntitlementLedger()
    ledger.append(event("GRANT", 1))
    ledger.append(event("RESERVE", 1))

    with pytest.raises(LedgerError, match="reserve exceeds available units"):
        ledger.append(event("RESERVE", 1))
    with pytest.raises(LedgerError, match="expire requires no reserved units"):
        ledger.append(event("EXPIRE", 1))
    with pytest.raises(LedgerError, match="release exceeds reserved units"):
        ledger.append(event("RELEASE", 2))
