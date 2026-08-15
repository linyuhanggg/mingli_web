from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

LedgerEventKind = Literal[
    "GRANT",
    "RESERVE",
    "CONSUME",
    "RELEASE",
    "REVERSE",
    "EXPIRE",
]


class LedgerError(ValueError):
    """The append-only entitlement lifecycle would become invalid."""


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    event_id: UUID
    entitlement_id: str
    kind: LedgerEventKind
    quantity: int
    source: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class EntitlementProjection:
    entitlement_id: str
    granted: int
    reserved: int
    consumed: int
    released: int
    reversed: int
    expired: int

    @property
    def available(self) -> int:
        # REVERSE records a refund/compensation fact for an already consumed
        # unit; it must not make the projected available balance negative.
        return self.granted - self.reserved - self.consumed - self.expired


class EntitlementLedger:
    """In-memory reference implementation of the append-only ledger contract.

    The database implementation must persist the same event semantics. No caller
    receives a mutable balance field; every projection is derived from events.
    """

    def __init__(self) -> None:
        self._events: list[LedgerEvent] = []
        self._event_ids: set[UUID] = set()

    @property
    def events(self) -> tuple[LedgerEvent, ...]:
        return tuple(self._events)

    def append(self, event: LedgerEvent) -> None:
        if event.event_id in self._event_ids:
            raise LedgerError("event already appended")
        if event.quantity <= 0:
            raise LedgerError("event quantity must be positive")
        projection = self.project(event.entitlement_id)
        if event.kind == "GRANT":
            if projection.granted > 0:
                raise LedgerError("entitlement already granted")
        elif projection.granted == 0:
            raise LedgerError("grant is required before lifecycle events")
        elif event.kind == "RESERVE":
            if event.quantity > projection.available:
                raise LedgerError("reserve exceeds available units")
        elif event.kind == "CONSUME":
            if event.quantity > projection.reserved:
                raise LedgerError("consume requires reserved units")
        elif event.kind == "RELEASE":
            if event.quantity > projection.reserved:
                raise LedgerError("release exceeds reserved units")
        elif event.kind == "REVERSE":
            reversible = projection.consumed - projection.reversed
            if event.quantity > reversible:
                raise LedgerError("reverse exceeds consumed units")
        elif event.kind == "EXPIRE":
            if projection.reserved:
                raise LedgerError("expire requires no reserved units")
            expirable = (
                projection.granted
                - projection.consumed
                - projection.reversed
                - projection.expired
            )
            if event.quantity > expirable:
                raise LedgerError("expire exceeds remaining units")
        else:
            raise LedgerError(f"unsupported ledger event: {event.kind!r}")
        self._events.append(event)
        self._event_ids.add(event.event_id)

    def project(self, entitlement_id: str) -> EntitlementProjection:
        totals = {
            "granted": 0,
            "reserved": 0,
            "consumed": 0,
            "released": 0,
            "reversed": 0,
            "expired": 0,
        }
        for event in self._events:
            if event.entitlement_id != entitlement_id:
                continue
            if event.kind == "GRANT":
                totals["granted"] += event.quantity
            elif event.kind == "RESERVE":
                totals["reserved"] += event.quantity
            elif event.kind == "CONSUME":
                totals["reserved"] -= event.quantity
                totals["consumed"] += event.quantity
            elif event.kind == "RELEASE":
                totals["reserved"] -= event.quantity
                totals["released"] += event.quantity
            elif event.kind == "REVERSE":
                totals["reversed"] += event.quantity
            elif event.kind == "EXPIRE":
                totals["expired"] += event.quantity
        return EntitlementProjection(entitlement_id=entitlement_id, **totals)
