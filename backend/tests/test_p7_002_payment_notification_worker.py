"""P7-002: injectable payment-notification worker applies verified inbox items."""

from __future__ import annotations

import importlib
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.commerce.models import (
    EntitlementEventRecord,
    Order,
    Payment,
    PaymentNotificationReceipt,
    PaymentReconciliationRun,
    ProductFamily,
    ProductOffer,
    ProductVersion,
    Refund,
)
from app.commerce.service import CommerceError, CommerceService
from app.identity.models import User
from sqlalchemy import func, select
from worker.payment_notifications import (
    FakePaymentNotificationInbox,
    InboundPaymentNotification,
    PaymentNotificationWorker,
)

CHANNEL = "closed"
NOW = datetime(2026, 8, 19, 11, 0, tzinfo=UTC)


class FrozenClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def now(self) -> datetime:
        return self.current


@pytest.fixture
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Any:
    for key in [name for name in os.environ if name.startswith("MINGLI_")]:
        monkeypatch.delenv(key, raising=False)
    config = importlib.import_module("app.config")
    return config.Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        otp_adapter="fake",
    )


def _worker(
    database: Any,
    inbox: FakePaymentNotificationInbox,
    *,
    now: datetime = NOW,
    service_factory: Any = CommerceService,
) -> PaymentNotificationWorker:
    return PaymentNotificationWorker(
        sessions=database.sessions,
        inbox=inbox,
        clock=FrozenClock(now),
        service_factory=service_factory,
    )


async def _product(session: Any) -> tuple[User, ProductOffer]:
    user = User()
    family = ProductFamily(key="bazi", label="八字深读")
    session.add_all([user, family])
    await session.flush()
    product = ProductVersion(
        family_id=family.id,
        version="v1",
        price_minor=9900,
        currency="CNY",
        contract_version="reading-document-v1",
        status="active",
    )
    session.add(product)
    await session.flush()
    offer = ProductOffer(
        product_version_id=product.id,
        channel=CHANNEL,
        channel_sku="bazi-v1",
        price_minor=9900,
        currency="CNY",
        enabled=True,
    )
    session.add(offer)
    await session.flush()
    return user, offer


async def _pending_attempt(
    service: CommerceService,
    user: User,
    offer: ProductOffer,
    *,
    target_ref: str,
    idempotency_key: str,
) -> tuple[UUID, UUID]:
    order = await service.create_order(
        owner_user_id=user.id,
        offer_id=offer.id,
        purchase_target_ref=target_ref,
    )
    attempt, created = await service.create_payment_attempt(
        order_id=order.id,
        channel=CHANNEL,
        idempotency_key=idempotency_key,
    )
    assert created is True
    return order.id, attempt.id


async def _counts(session: Any) -> tuple[int, int, int, int, int, int]:
    payments = await session.scalar(select(func.count()).select_from(Payment))
    refunds = await session.scalar(select(func.count()).select_from(Refund))
    grants = await session.scalar(select(func.count()).select_from(EntitlementEventRecord))
    orders = await session.scalar(select(func.count()).select_from(Order))
    receipts = await session.scalar(
        select(func.count()).select_from(PaymentNotificationReceipt)
    )
    runs = await session.scalar(select(func.count()).select_from(PaymentReconciliationRun))
    assert payments is not None
    assert refunds is not None
    assert grants is not None
    assert orders is not None
    assert receipts is not None
    assert runs is not None
    return payments, refunds, grants, orders, receipts, runs


async def test_isolated_settings_are_test_sqlite_memory_fake_otp(
    isolated_settings: Any,
) -> None:
    assert isolated_settings.environment == "test"
    assert isolated_settings.database_url == "sqlite+aiosqlite:///:memory:"
    assert isolated_settings.otp_adapter == "fake"
    leftover = [name for name in os.environ if name.startswith("MINGLI_")]
    assert leftover == []


async def test_run_once_applies_verified_inbox_into_payment(
    database: Any,
    isolated_settings: Any,
) -> None:
    del isolated_settings
    async with database.sessions() as session:
        user, offer = await _product(session)
        service = CommerceService(session)
        order_id, attempt_id = await _pending_attempt(
            service,
            user,
            offer,
            target_ref="reading-notify-1",
            idempotency_key="attempt-notify-1",
        )
        await session.commit()

    inbox = FakePaymentNotificationInbox(
        notifications=(
            InboundPaymentNotification(
                order_id=order_id,
                attempt_id=attempt_id,
                channel=CHANNEL,
                external_event_id="event-1",
                channel_transaction_id="tx-1",
                payment_succeeded=True,
                verified=True,
            ),
        )
    )
    result = await _worker(database, inbox).run_once()

    assert result.processed_event_ids == ("event-1",)
    assert len(result.created_payment_ids) == 1
    assert result.replayed_event_ids == ()
    assert result.skipped_unverified_event_ids == ()
    assert result.skipped_unmatched_event_ids == ()
    assert result.processed_at == NOW

    async with database.sessions() as session:
        payments = list(await session.scalars(select(Payment)))
        assert len(payments) == 1
        payment = payments[0]
        assert str(payment.id) == result.created_payment_ids[0]
        assert payment.channel == CHANNEL
        assert payment.channel_transaction_id == "tx-1"
        assert payment.status == "confirmed"
        assert payment.confirmed_at.replace(tzinfo=UTC) == NOW
        order = await session.get(Order, order_id)
        assert order is not None
        assert order.status == "paid"
        assert order.paid_at.replace(tzinfo=UTC) == NOW
        receipt = await session.scalar(select(PaymentNotificationReceipt))
        assert receipt is not None
        assert receipt.external_event_id == "event-1"
        assert receipt.channel_transaction_id == "tx-1"
        assert receipt.processing_status == "processed"
        assert receipt.payment_id == payment.id
        assert receipt.processed_at is not None
        assert receipt.processed_at.replace(tzinfo=UTC) == NOW
        grants = list(await session.scalars(select(EntitlementEventRecord)))
        assert [row.kind for row in grants] == ["GRANT"]
        assert await session.scalar(select(func.count()).select_from(Refund)) == 0
        assert (
            await session.scalar(select(func.count()).select_from(PaymentReconciliationRun))
            == 0
        )


async def test_run_once_replays_same_event_idempotently(
    database: Any,
    isolated_settings: Any,
) -> None:
    del isolated_settings
    async with database.sessions() as session:
        user, offer = await _product(session)
        service = CommerceService(session)
        order_id, attempt_id = await _pending_attempt(
            service,
            user,
            offer,
            target_ref="reading-notify-replay",
            idempotency_key="attempt-notify-replay",
        )
        await session.commit()

    item = InboundPaymentNotification(
        order_id=order_id,
        attempt_id=attempt_id,
        channel=CHANNEL,
        external_event_id="event-replay",
        channel_transaction_id="tx-replay",
        payment_succeeded=True,
        verified=True,
    )
    inbox = FakePaymentNotificationInbox(notifications=(item,))
    first = await _worker(database, inbox).run_once()
    second = await _worker(database, inbox).run_once()

    assert first.created_payment_ids == second.created_payment_ids or (
        len(first.created_payment_ids) == 1 and second.created_payment_ids == ()
    )
    assert first.processed_event_ids == ("event-replay",)
    assert second.processed_event_ids == ("event-replay",)
    assert second.replayed_event_ids == ("event-replay",)
    assert second.created_payment_ids == ()

    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Payment)) == 1
        assert (
            await session.scalar(select(func.count()).select_from(PaymentNotificationReceipt))
            == 1
        )
        assert (
            await session.scalar(select(func.count()).select_from(EntitlementEventRecord))
            == 1
        )
        payment = await session.scalar(select(Payment))
        assert payment is not None
        assert payment.channel_transaction_id == "tx-replay"
        assert str(payment.id) == first.created_payment_ids[0]


async def test_run_once_skips_unverified_without_payment_or_receipt(
    database: Any,
    isolated_settings: Any,
) -> None:
    del isolated_settings
    async with database.sessions() as session:
        user, offer = await _product(session)
        service = CommerceService(session)
        order_id, attempt_id = await _pending_attempt(
            service,
            user,
            offer,
            target_ref="reading-notify-unverified",
            idempotency_key="attempt-notify-unverified",
        )
        await session.commit()
        before = await _counts(session)

    inbox = FakePaymentNotificationInbox(
        notifications=(
            InboundPaymentNotification(
                order_id=order_id,
                attempt_id=attempt_id,
                channel=CHANNEL,
                external_event_id="event-unverified",
                channel_transaction_id="tx-unverified",
                payment_succeeded=True,
                verified=False,
            ),
        )
    )
    result = await _worker(database, inbox).run_once()

    assert result.processed_event_ids == ()
    assert result.created_payment_ids == ()
    assert result.skipped_unverified_event_ids == ("event-unverified",)
    assert result.replayed_event_ids == ()

    async with database.sessions() as session:
        assert await _counts(session) == before
        order = await session.get(Order, order_id)
        assert order is not None
        assert order.status == "payment_pending"


async def test_run_once_uses_injected_clock_and_inbox(
    database: Any,
    isolated_settings: Any,
) -> None:
    del isolated_settings
    later = datetime(2026, 8, 19, 19, 45, tzinfo=UTC)
    calls: list[tuple[str, bool, datetime | None]] = []

    class RecordingCommerceService(CommerceService):
        async def apply_payment_notification(
            self,
            *,
            order_id: UUID,
            attempt_id: UUID,
            channel: str,
            external_event_id: str,
            channel_transaction_id: str | None,
            payment_succeeded: bool,
            verified: bool,
            now: datetime | None = None,
        ) -> tuple[Payment | None, bool]:
            calls.append((external_event_id, verified, now))
            return await super().apply_payment_notification(
                order_id=order_id,
                attempt_id=attempt_id,
                channel=channel,
                external_event_id=external_event_id,
                channel_transaction_id=channel_transaction_id,
                payment_succeeded=payment_succeeded,
                verified=verified,
                now=now,
            )

    async with database.sessions() as session:
        user, offer = await _product(session)
        service = CommerceService(session)
        order_id, attempt_id = await _pending_attempt(
            service,
            user,
            offer,
            target_ref="reading-notify-clock",
            idempotency_key="attempt-notify-clock",
        )
        await session.commit()

    inbox = FakePaymentNotificationInbox(
        notifications=(
            InboundPaymentNotification(
                order_id=order_id,
                attempt_id=attempt_id,
                channel=CHANNEL,
                external_event_id="event-clock",
                channel_transaction_id="tx-clock",
                payment_succeeded=True,
                verified=True,
            ),
        )
    )
    result = await _worker(
        database,
        inbox,
        now=later,
        service_factory=RecordingCommerceService,
    ).run_once()

    assert result.processed_at == later
    assert calls == [("event-clock", True, later)]
    async with database.sessions() as session:
        payment = await session.scalar(select(Payment))
        assert payment is not None
        assert payment.confirmed_at.replace(tzinfo=UTC) == later
        receipt = await session.scalar(select(PaymentNotificationReceipt))
        assert receipt is not None
        assert receipt.processed_at is not None
        assert receipt.processed_at.replace(tzinfo=UTC) == later


async def test_run_once_does_not_auto_create_or_reverse(
    database: Any,
    isolated_settings: Any,
) -> None:
    del isolated_settings
    orphan_order_id = uuid4()
    orphan_attempt_id = uuid4()

    async with database.sessions() as session:
        user, offer = await _product(session)
        service = CommerceService(session)
        order_id, attempt_id = await _pending_attempt(
            service,
            user,
            offer,
            target_ref="reading-notify-keep",
            idempotency_key="attempt-notify-keep",
        )
        payment, created = await service.apply_payment_notification(
            order_id=order_id,
            attempt_id=attempt_id,
            channel=CHANNEL,
            external_event_id="event-keep",
            channel_transaction_id="tx-keep",
            payment_succeeded=True,
            verified=True,
            now=NOW,
        )
        assert payment is not None
        assert created is True
        await session.commit()
        payment_id = payment.id
        before = await _counts(session)

    inbox = FakePaymentNotificationInbox(
        notifications=(
            InboundPaymentNotification(
                order_id=orphan_order_id,
                attempt_id=orphan_attempt_id,
                channel=CHANNEL,
                external_event_id="event-orphan",
                channel_transaction_id="tx-orphan",
                payment_succeeded=True,
                verified=True,
            ),
            InboundPaymentNotification(
                order_id=order_id,
                attempt_id=attempt_id,
                channel=CHANNEL,
                external_event_id="event-failed-signal",
                channel_transaction_id=None,
                payment_succeeded=False,
                verified=True,
            ),
        )
    )
    result = await _worker(database, inbox).run_once()

    assert result.skipped_unmatched_event_ids == ("event-orphan",)
    assert "event-failed-signal" in result.processed_event_ids
    assert result.created_payment_ids == ()
    assert "event-failed-signal" in result.replayed_event_ids or (
        result.created_payment_ids == ()
    )

    async with database.sessions() as session:
        after = await _counts(session)
        # Orphan skipped: no new Payment. Failed signal may create an ignored
        # receipt but must not create Refund / ReconciliationRun / REVERSE.
        assert after[0] == before[0]  # payments
        assert after[1] == before[1]  # refunds
        assert after[2] == before[2]  # grants
        assert after[3] == before[3]  # orders
        assert after[5] == before[5]  # reconciliation runs
        assert after[4] == before[4] + 1  # ignored receipt only
        stored = await session.get(Payment, payment_id)
        assert stored is not None
        assert stored.status == "confirmed"
        assert stored.channel_transaction_id == "tx-keep"
        grants = list(await session.scalars(select(EntitlementEventRecord)))
        assert [row.kind for row in grants] == ["GRANT"]
        ignored = await session.scalar(
            select(PaymentNotificationReceipt).where(
                PaymentNotificationReceipt.external_event_id == "event-failed-signal"
            )
        )
        assert ignored is not None
        assert ignored.processing_status == "ignored"
        assert ignored.payment_id is None
        assert await session.scalar(select(func.count()).select_from(Refund)) == 0


async def test_run_once_preserves_same_event_different_transaction_rejection(
    database: Any,
    isolated_settings: Any,
) -> None:
    del isolated_settings
    async with database.sessions() as session:
        user, offer = await _product(session)
        service = CommerceService(session)
        order_id, attempt_id = await _pending_attempt(
            service,
            user,
            offer,
            target_ref="reading-notify-bound",
            idempotency_key="attempt-notify-bound",
        )
        await session.commit()

    first_inbox = FakePaymentNotificationInbox(
        notifications=(
            InboundPaymentNotification(
                order_id=order_id,
                attempt_id=attempt_id,
                channel=CHANNEL,
                external_event_id="event-bound",
                channel_transaction_id="tx-first",
                payment_succeeded=True,
                verified=True,
            ),
        )
    )
    first = await _worker(database, first_inbox).run_once()
    assert len(first.created_payment_ids) == 1

    conflict_inbox = FakePaymentNotificationInbox(
        notifications=(
            InboundPaymentNotification(
                order_id=order_id,
                attempt_id=attempt_id,
                channel=CHANNEL,
                external_event_id="event-bound",
                channel_transaction_id="tx-second",
                payment_succeeded=True,
                verified=True,
            ),
        )
    )
    with pytest.raises(CommerceError, match="notification event is bound"):
        await _worker(database, conflict_inbox).run_once()

    async with database.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Payment)) == 1
        assert (
            await session.scalar(select(func.count()).select_from(EntitlementEventRecord))
            == 1
        )
        payment = await session.scalar(select(Payment))
        assert payment is not None
        assert payment.channel_transaction_id == "tx-first"
