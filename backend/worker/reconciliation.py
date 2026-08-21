from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.commerce.reconciliation import ChannelPaymentSnapshot, ChannelRefundSnapshot
from app.commerce.service import CommerceService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

CommerceServiceFactory = Callable[[AsyncSession], CommerceService]


class ReconciliationClock(Protocol):
    def now(self) -> datetime: ...


class ChannelReceiptSource(Protocol):
    """Normalized fake-channel facts. Live providers stay outside this worker."""

    async def list_payments(self) -> Sequence[ChannelPaymentSnapshot]: ...

    async def list_refunds(self) -> Sequence[ChannelRefundSnapshot]: ...


@dataclass(frozen=True, slots=True)
class SystemReconciliationClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class FakeChannelReceipts:
    """In-memory fake channel receipts already used by local reconciliation."""

    payments: tuple[ChannelPaymentSnapshot, ...] = ()
    refunds: tuple[ChannelRefundSnapshot, ...] = ()

    async def list_payments(self) -> tuple[ChannelPaymentSnapshot, ...]:
        return self.payments

    async def list_refunds(self) -> tuple[ChannelRefundSnapshot, ...]:
        return self.refunds


@dataclass(frozen=True, slots=True)
class ReconciliationWorkerResult:
    run_id: UUID
    channel: str
    status: str
    item_count: int
    matched_count: int
    difference_count: int
    discrepancies: tuple[str, ...]


@dataclass(slots=True)
class ReconciliationWorker:
    """Pull injected channel receipts, classify diffs, persist one batch.

    Issue, confirm, refund, and ledger repair stay on CommerceService. This
    worker only calls reconcile_channel with the injected receipts and clock.
    It never creates payments, never refunds, and never appends GRANT/REVERSE.
    """

    sessions: async_sessionmaker[AsyncSession]
    source: ChannelReceiptSource
    channel: str
    clock: ReconciliationClock = field(default_factory=SystemReconciliationClock)
    service_factory: CommerceServiceFactory = CommerceService

    def __post_init__(self) -> None:
        if not self.channel.strip():
            raise ValueError("reconciliation channel is required")

    async def run_once(self) -> ReconciliationWorkerResult:
        current = self.clock.now()
        payments = tuple(await self.source.list_payments())
        refunds = tuple(await self.source.list_refunds())
        async with self.sessions() as session:
            service = self.service_factory(session)
            run, items = await service.reconcile_channel(
                channel=self.channel,
                payments=payments,
                refunds=refunds,
                run_at=current,
            )
            result = ReconciliationWorkerResult(
                run_id=run.id,
                channel=run.channel,
                status=run.status,
                item_count=run.item_count,
                matched_count=run.matched_count,
                difference_count=run.difference_count,
                discrepancies=tuple(item.discrepancy for item in items),
            )
            await session.commit()
        return result
