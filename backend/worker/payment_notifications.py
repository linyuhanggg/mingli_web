from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.commerce.models import Order, PaymentAttempt
from app.commerce.service import CommerceService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

CommerceServiceFactory = Callable[[AsyncSession], CommerceService]


class PaymentNotificationClock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class InboundPaymentNotification:
    """One fake-channel notification already marked verified or not."""

    order_id: UUID
    attempt_id: UUID
    channel: str
    external_event_id: str
    channel_transaction_id: str | None
    payment_succeeded: bool
    verified: bool


class PaymentNotificationInbox(Protocol):
    """Normalized fake-channel inbox. Live providers stay outside this worker."""

    async def list_notifications(self) -> Sequence[InboundPaymentNotification]: ...


@dataclass(frozen=True, slots=True)
class SystemPaymentNotificationClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class FakePaymentNotificationInbox:
    """In-memory fake-channel notifications. Verification is already decided."""

    notifications: tuple[InboundPaymentNotification, ...] = ()

    async def list_notifications(self) -> tuple[InboundPaymentNotification, ...]:
        return self.notifications


@dataclass(frozen=True, slots=True)
class PaymentNotificationWorkerResult:
    processed_event_ids: tuple[str, ...]
    created_payment_ids: tuple[str, ...]
    replayed_event_ids: tuple[str, ...]
    skipped_unverified_event_ids: tuple[str, ...]
    skipped_unmatched_event_ids: tuple[str, ...]
    processed_at: datetime


@dataclass(slots=True)
class PaymentNotificationWorker:
    """Pull injected already-verified notifications and apply confirm/receipt.

    Issue, refund, and channel reconciliation stay on CommerceService. This
    worker only calls apply_payment_notification for verified inbox items that
    already have a local order and attempt. It never creates missing orders,
    never refunds, and never opens a reconciliation run.
    """

    sessions: async_sessionmaker[AsyncSession]
    inbox: PaymentNotificationInbox
    clock: PaymentNotificationClock = field(default_factory=SystemPaymentNotificationClock)
    service_factory: CommerceServiceFactory = CommerceService

    async def run_once(self) -> PaymentNotificationWorkerResult:
        current = self.clock.now()
        items = tuple(await self.inbox.list_notifications())
        processed: list[str] = []
        created_ids: list[str] = []
        replayed: list[str] = []
        skipped_unverified: list[str] = []
        skipped_unmatched: list[str] = []

        async with self.sessions() as session:
            service = self.service_factory(session)
            for item in items:
                if not item.verified:
                    skipped_unverified.append(item.external_event_id)
                    continue
                order = await session.get(Order, item.order_id)
                attempt = await session.get(PaymentAttempt, item.attempt_id)
                if order is None or attempt is None or attempt.order_id != item.order_id:
                    skipped_unmatched.append(item.external_event_id)
                    continue
                payment, created = await service.apply_payment_notification(
                    order_id=item.order_id,
                    attempt_id=item.attempt_id,
                    channel=item.channel,
                    external_event_id=item.external_event_id,
                    channel_transaction_id=item.channel_transaction_id,
                    payment_succeeded=item.payment_succeeded,
                    verified=True,
                    now=current,
                )
                processed.append(item.external_event_id)
                if created and payment is not None:
                    created_ids.append(str(payment.id))
                else:
                    replayed.append(item.external_event_id)
            await session.commit()

        return PaymentNotificationWorkerResult(
            processed_event_ids=tuple(processed),
            created_payment_ids=tuple(created_ids),
            replayed_event_ids=tuple(replayed),
            skipped_unverified_event_ids=tuple(skipped_unverified),
            skipped_unmatched_event_ids=tuple(skipped_unmatched),
            processed_at=current,
        )
