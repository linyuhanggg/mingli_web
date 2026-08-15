from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.commerce.models import NotificationOutbox
from app.commerce.service import CommerceError, CommerceService
from app.identity.models import User

BASE_TIME = datetime(2026, 8, 14, 5, 0, tzinfo=UTC)


async def _seed_notification(database: Any, *, available_at: datetime = BASE_TIME) -> Any:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        item, created = await CommerceService(session).enqueue_notification(
            owner_user_id=user.id,
            kind="reading.accepted",
            dedupe_key=f"reading.accepted:{user.id}",
            payload={"message": "已完成"},
            available_at=available_at,
        )
        assert item is not None
        assert created is True
        await session.commit()
        return item.id


async def test_notification_claim_failure_retries_then_reaches_terminal_failed(
    database: Any,
) -> None:
    notification_id = await _seed_notification(database)

    async with database.sessions() as session:
        service = CommerceService(session)
        claimed = await service.claim_notifications(
            now=BASE_TIME,
            lease_seconds=10,
        )
        assert [item.id for item in claimed] == [notification_id]
        assert claimed[0].attempt_count == 1
        claim_token = claimed[0].processing_token
        assert claim_token
        await session.commit()

    async with database.sessions() as session:
        service = CommerceService(session)
        retrying = await service.mark_notification_failed(
            notification_id,
            "provider unavailable",
            now=BASE_TIME,
            retry_delay_seconds=30,
            max_attempts=2,
            claim_token=claim_token,
        )
        assert retrying is True
        await session.commit()

    async with database.sessions() as session:
        service = CommerceService(session)
        assert await service.claim_notifications(
            now=BASE_TIME + timedelta(seconds=29),
        ) == []
        claimed = await service.claim_notifications(
            now=BASE_TIME + timedelta(seconds=30),
        )
        assert len(claimed) == 1
        assert claimed[0].attempt_count == 2
        second_token = claimed[0].processing_token
        assert second_token
        retrying = await service.mark_notification_failed(
            notification_id,
            "provider unavailable again",
            now=BASE_TIME + timedelta(seconds=30),
            retry_delay_seconds=30,
            max_attempts=2,
            claim_token=second_token,
        )
        assert retrying is False
        await session.commit()

    async with database.sessions() as session:
        stored = await session.get(NotificationOutbox, notification_id)
        assert stored is not None
        assert stored.status == "failed"
        assert stored.attempt_count == 2
        assert stored.last_error == "provider unavailable again"


async def test_notification_claim_lease_fences_stale_sender(database: Any) -> None:
    notification_id = await _seed_notification(database)

    async with database.sessions() as session:
        first = await CommerceService(session).claim_notifications(
            now=BASE_TIME,
            lease_seconds=1,
        )
        first_token = first[0].processing_token
        assert first_token
        await session.commit()

    async with database.sessions() as session:
        second = await CommerceService(session).claim_notifications(
            now=BASE_TIME + timedelta(seconds=2),
            lease_seconds=10,
        )
        second_token = second[0].processing_token
        assert second_token and second_token != first_token
        await session.commit()

    async with database.sessions() as session:
        with pytest.raises(CommerceError, match="claim token"):
            await CommerceService(session).mark_notification_sent(
                notification_id,
                claim_token=first_token,
            )
        await CommerceService(session).mark_notification_sent(
            notification_id,
            claim_token=second_token,
            now=BASE_TIME + timedelta(seconds=2),
        )
        await session.commit()

    async with database.sessions() as session:
        stored = await session.get(NotificationOutbox, notification_id)
        assert stored is not None
        assert stored.status == "sent"
        assert stored.processing_token is None


async def test_notification_worker_sends_one_claimed_item(database: Any) -> None:
    notification_id = await _seed_notification(database)
    from worker.notifications import NotificationWorker

    delivered: list[str] = []

    class Sender:
        async def send(self, item: NotificationOutbox) -> None:
            delivered.append(str(item.id))

    class Clock:
        def now(self) -> datetime:
            return BASE_TIME

    worker = NotificationWorker(
        sessions=database.sessions,
        sender=Sender(),
        clock=Clock(),
        lease_seconds=30,
    )
    assert await worker.run_once() is True
    assert delivered == [str(notification_id)]

    async with database.sessions() as session:
        stored = await session.get(NotificationOutbox, notification_id)
        assert stored is not None
        assert stored.status == "sent"


async def test_notification_worker_returns_failed_delivery_to_retry_queue(
    database: Any,
) -> None:
    notification_id = await _seed_notification(database)
    from worker.notifications import NotificationWorker

    class Sender:
        fail = True

        async def send(self, item: NotificationOutbox) -> None:
            del item
            if self.fail:
                raise RuntimeError("smtp unavailable")

    class Clock:
        def now(self) -> datetime:
            return BASE_TIME

    sender = Sender()
    worker = NotificationWorker(
        sessions=database.sessions,
        sender=sender,
        clock=Clock(),
        lease_seconds=30,
        retry_delay_seconds=0,
        max_attempts=2,
    )
    assert await worker.run_once() is True
    async with database.sessions() as session:
        stored = await session.get(NotificationOutbox, notification_id)
        assert stored is not None
        assert stored.status == "pending"
        assert stored.last_error == "smtp unavailable"

    sender.fail = False
    assert await worker.run_once() is True
    async with database.sessions() as session:
        stored = await session.get(NotificationOutbox, notification_id)
        assert stored is not None
        assert stored.status == "sent"
