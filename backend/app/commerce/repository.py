from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commerce.ledger import (
    EntitlementLedger,
    EntitlementProjection,
    LedgerEvent,
    LedgerEventKind,
)
from app.commerce.models import EntitlementEventRecord


class CommerceRepository:
    """Persistence adapter for append-only commerce facts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _events(
        self,
        *,
        entitlement_id: str,
        owner_user_id: UUID,
    ) -> list[EntitlementEventRecord]:
        rows = await self.session.scalars(
            select(EntitlementEventRecord)
            .where(
                EntitlementEventRecord.entitlement_id == entitlement_id,
                EntitlementEventRecord.owner_user_id == owner_user_id,
            )
            .order_by(EntitlementEventRecord.created_at, EntitlementEventRecord.id)
        )
        return list(rows)

    async def project(
        self,
        *,
        entitlement_id: str,
        owner_user_id: UUID,
    ) -> EntitlementProjection:
        ledger = EntitlementLedger()
        for row in await self._events(
            entitlement_id=entitlement_id,
            owner_user_id=owner_user_id,
        ):
            ledger.append(
                LedgerEvent(
                    event_id=row.id,
                    entitlement_id=row.entitlement_id,
                    kind=cast(LedgerEventKind, row.kind),
                    quantity=row.quantity,
                    source=row.source_type,
                    occurred_at=row.created_at or datetime.now(UTC),
                )
            )
        return ledger.project(entitlement_id)

    async def find_events_by_source(
        self,
        *,
        source_type: str,
        source_ref: str,
    ) -> list[EntitlementEventRecord]:
        rows = await self.session.scalars(
            select(EntitlementEventRecord)
            .where(
                EntitlementEventRecord.source_type == source_type,
                EntitlementEventRecord.source_ref == source_ref,
            )
            .order_by(EntitlementEventRecord.created_at, EntitlementEventRecord.id)
        )
        return list(rows)

    async def list_events(
        self,
        *,
        owner_user_id: UUID,
        entitlement_id: str | None = None,
        limit: int = 100,
    ) -> list[EntitlementEventRecord]:
        if limit < 1:
            raise ValueError("event limit must be positive")
        statement = select(EntitlementEventRecord).where(
            EntitlementEventRecord.owner_user_id == owner_user_id
        )
        if entitlement_id is not None:
            statement = statement.where(
                EntitlementEventRecord.entitlement_id == entitlement_id
            )
        rows = await self.session.scalars(
            statement
            .order_by(
                EntitlementEventRecord.created_at.desc(),
                EntitlementEventRecord.id.desc(),
            )
            .limit(limit)
        )
        return list(rows)

    async def append_entitlement_event(
        self,
        *,
        entitlement_id: str,
        owner_user_id: UUID,
        kind: LedgerEventKind,
        quantity: int,
        source_type: str,
        source_ref: str,
        target_ref: str | None = None,
        occurred_at: datetime | None = None,
    ) -> EntitlementEventRecord:
        if not source_ref.strip():
            raise ValueError("source_ref is required")
        duplicate = await self.session.scalar(
            select(EntitlementEventRecord.id).where(
                EntitlementEventRecord.owner_user_id == owner_user_id,
                EntitlementEventRecord.source_type == source_type,
                EntitlementEventRecord.source_ref == source_ref,
                EntitlementEventRecord.kind == kind,
            )
        )
        if duplicate is not None:
            raise ValueError("source_ref already recorded")
        happened_at = occurred_at or datetime.now(UTC)
        event = LedgerEvent(
            event_id=uuid4(),
            entitlement_id=entitlement_id,
            kind=kind,
            quantity=quantity,
            source=source_type,
            occurred_at=happened_at,
        )
        ledger = EntitlementLedger()
        for row in await self._events(
            entitlement_id=entitlement_id,
            owner_user_id=owner_user_id,
        ):
            ledger.append(
                LedgerEvent(
                    event_id=row.id,
                    entitlement_id=row.entitlement_id,
                    kind=cast(LedgerEventKind, row.kind),
                    quantity=row.quantity,
                    source=row.source_type,
                    occurred_at=row.created_at or happened_at,
                )
            )
        ledger.append(event)
        record = EntitlementEventRecord(
            id=event.event_id,
            entitlement_id=entitlement_id,
            owner_user_id=owner_user_id,
            kind=kind,
            quantity=quantity,
            source_type=source_type,
            source_ref=source_ref,
            target_ref=target_ref,
            created_at=happened_at,
        )
        self.session.add(record)
        await self.session.flush()
        return record
