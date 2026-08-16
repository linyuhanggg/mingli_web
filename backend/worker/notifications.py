from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.commerce.models import NotificationOutbox
from app.commerce.service import CommerceService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class NotificationSender(Protocol):
    async def send(self, item: NotificationOutbox) -> None: ...


class NotificationClock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class SystemNotificationClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(slots=True)
class NotificationWorker:
    """Deliver one outbox item through an injected channel adapter.

    Provider credentials and channel-specific delivery remain outside this
    worker. The worker only owns claim fencing, bounded retries, and terminal
    failure state transitions.
    """

    sessions: async_sessionmaker[AsyncSession]
    sender: NotificationSender
    clock: NotificationClock = field(default_factory=SystemNotificationClock)
    lease_seconds: int = 300
    retry_delay_seconds: float = 60.0
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if self.lease_seconds < 1:
            raise ValueError("notification lease must be positive")
        if self.retry_delay_seconds < 0:
            raise ValueError("notification retry delay cannot be negative")
        if self.max_attempts < 1:
            raise ValueError("notification max attempts must be positive")

    async def run_once(self) -> bool:
        current = self.clock.now()
        async with self.sessions() as session:
            service = CommerceService(session)
            claimed = await service.claim_notifications(
                limit=1,
                now=current,
                lease_seconds=self.lease_seconds,
            )
            if not claimed:
                await session.rollback()
                return False
            item = claimed[0]
            claim_token = item.processing_token
            if claim_token is None:
                raise RuntimeError("claimed notification has no fencing token")
            await session.commit()

        try:
            await self.sender.send(item)
        except Exception as error:
            async with self.sessions() as session:
                await CommerceService(session).mark_notification_failed(
                    item.id,
                    str(error),
                    now=self.clock.now(),
                    retry_delay_seconds=self.retry_delay_seconds,
                    max_attempts=self.max_attempts,
                    claim_token=claim_token,
                )
                await session.commit()
            return True

        async with self.sessions() as session:
            await CommerceService(session).mark_notification_sent(
                item.id,
                now=self.clock.now(),
                claim_token=claim_token,
            )
            await session.commit()
        return True
