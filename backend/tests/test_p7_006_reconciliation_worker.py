"""P7-006: injectable reconciliation worker classifies diffs and persists batches."""

from __future__ import annotations

import importlib
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import pytest
from app.commerce.models import (
    EntitlementEventRecord,
    Order,
    Payment,
    PaymentNotificationReceipt,
    PaymentReconciliationItem,
    PaymentReconciliationRun,
    ProductFamily,
    ProductOffer,
    ProductVersion,
    Refund,
)
from app.commerce.reconciliation import ChannelPaymentSnapshot, ChannelRefundSnapshot
from app.commerce.service import CommerceService
from app.identity.models import User
from sqlalchemy import func, select
from worker.reconciliation import FakeChannelReceipts, ReconciliationWorker

CHANNEL = "closed"
NOW = datetime(2026, 8, 19, 10, 0, tzinfo=UTC)

# Existing CommerceService discrepancy values. Do not invent new labels.
PAYMENT_DISCREPANCIES = frozenset(
    {
        "matched",
        "local_only",
        "provider_only",
        "amount_mismatch",
        "currency_mismatch",
        "status_mismatch",
    }
)
REFUND_DISCREPANCIES = frozenset(
    {
        "matched",
        "local_only",
        "provider_only",
        "amount_mismatch",
        "currency_mismatch",
        "refund_status_mismatch",
        "refund_without_payment",
        "refund_amount_exceeds_payment",
    }
)
KNOWN_DISCREPANCIES = PAYMENT_DISCREPANCIES | REFUND_DISCREPANCIES


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
    source: FakeChannelReceipts,
    *,
    now: datetime = NOW,
    channel: str = CHANNEL,
    service_factory: Any = CommerceService,
) -> ReconciliationWorker:
    return ReconciliationWorker(
        sessions=database.sessions,
        source=source,
        channel=channel,
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


async def _notify_payment(
    service: CommerceService,
    user: User,
    offer: ProductOffer,
    *,
    transaction_id: str,
    event_id: str,
    target_ref: str,
) -> Payment:
    order = await service.create_order(
        owner_user_id=user.id,
        offer_id=offer.id,
        purchase_target_ref=target_ref,
    )
    attempt, _ = await service.create_payment_attempt(
        order_id=order.id,
        channel=CHANNEL,
        idempotency_key=f"attempt-{transaction_id}",
    )
    payment, created = await service.apply_payment_notification(
        order_id=order.id,
        attempt_id=attempt.id,
        channel=CHANNEL,
        external_event_id=event_id,
        channel_transaction_id=transaction_id,
        payment_succeeded=True,
        verified=True,
    )
    assert payment is not None
    assert created is True
    return payment


async def _counts(session: Any) -> tuple[int, int, int, int, int]:
    payments = await session.scalar(select(func.count()).select_from(Payment))
    refunds = await session.scalar(select(func.count()).select_from(Refund))
    grants = await session.scalar(select(func.count()).select_from(EntitlementEventRecord))
    orders = await session.scalar(select(func.count()).select_from(Order))
    receipts = await session.scalar(
        select(func.count()).select_from(PaymentNotificationReceipt)
    )
    assert payments is not None
    assert refunds is not None
    assert grants is not None
    assert orders is not None
    assert receipts is not None
    return payments, refunds, grants, orders, receipts


async def test_isolated_settings_are_test_sqlite_memory_fake_otp(
    isolated_settings: Any,
) -> None:
    assert isolated_settings.environment == "test"
    assert isolated_settings.database_url == "sqlite+aiosqlite:///:memory:"
    assert isolated_settings.otp_adapter == "fake"
    leftover = [name for name in os.environ if name.startswith("MINGLI_")]
    assert leftover == []


async def test_run_once_pulls_injected_fake_receipts_and_persists_batch(
    database: Any,
    isolated_settings: Any,
) -> None:
    del isolated_settings
    async with database.sessions() as session:
        user, offer = await _product(session)
        service = CommerceService(session)
        matched = await _notify_payment(
            service,
            user,
            offer,
            transaction_id="tx-matched",
            event_id="evt-matched",
            target_ref="reading-matched",
        )
        await _notify_payment(
            service,
            user,
            offer,
            transaction_id="tx-amount",
            event_id="evt-amount",
            target_ref="reading-amount",
        )
        await _notify_payment(
            service,
            user,
            offer,
            transaction_id="tx-local",
            event_id="evt-local",
            target_ref="reading-local",
        )
        await session.commit()
        amount = matched.amount_minor

    source = FakeChannelReceipts(
        payments=(
            ChannelPaymentSnapshot(
                transaction_id="tx-matched",
                status="succeeded",
                amount_minor=amount,
                currency="CNY",
            ),
            ChannelPaymentSnapshot(
                transaction_id="tx-amount",
                status="succeeded",
                amount_minor=100,
                currency="CNY",
            ),
            ChannelPaymentSnapshot(
                transaction_id="tx-remote",
                status="succeeded",
                amount_minor=amount,
                currency="CNY",
            ),
        )
    )
    first = await _worker(database, source).run_once()
    second = await _worker(database, source).run_once()

    assert first.status == "has_differences"
    assert first.item_count == 4
    assert first.matched_count == 1
    assert first.difference_count == 3
    assert first.run_id != second.run_id
    assert set(first.discrepancies) <= KNOWN_DISCREPANCIES
    assert set(first.discrepancies) == {
        "matched",
        "amount_mismatch",
        "provider_only",
        "local_only",
    }

    async with database.sessions() as session:
        stored = await session.get(PaymentReconciliationRun, first.run_id)
        assert stored is not None
        assert stored.run_at.replace(tzinfo=UTC) == NOW
        assert stored.channel == CHANNEL
        assert stored.status == "has_differences"
        items = list(
            await session.scalars(
                select(PaymentReconciliationItem).where(
                    PaymentReconciliationItem.run_id == first.run_id
                )
            )
        )
        by_ref = {item.reference: item.discrepancy for item in items}
        assert by_ref["tx-matched"] == "matched"
        assert by_ref["tx-amount"] == "amount_mismatch"
        assert by_ref["tx-remote"] == "provider_only"
        assert by_ref["tx-local"] == "local_only"
        assert all(item.discrepancy in KNOWN_DISCREPANCIES for item in items)
        later = await session.get(PaymentReconciliationRun, second.run_id)
        assert later is not None
        assert later.id != stored.id
        first_again = await session.get(PaymentReconciliationRun, first.run_id)
        assert first_again is not None
        assert first_again.difference_count == 3


async def test_run_once_does_not_auto_repair_or_reverse(
    database: Any,
    isolated_settings: Any,
) -> None:
    del isolated_settings
    async with database.sessions() as session:
        user, offer = await _product(session)
        service = CommerceService(session)
        payment = await _notify_payment(
            service,
            user,
            offer,
            transaction_id="tx-keep",
            event_id="evt-keep",
            target_ref="reading-keep",
        )
        await session.commit()
        amount = payment.amount_minor
        payment_id = payment.id
        before = await _counts(session)

    source = FakeChannelReceipts(
        payments=(
            ChannelPaymentSnapshot(
                transaction_id="tx-keep",
                status="failed",
                amount_minor=amount,
                currency="CNY",
            ),
            ChannelPaymentSnapshot(
                transaction_id="tx-missing-local",
                status="succeeded",
                amount_minor=amount,
                currency="CNY",
            ),
        ),
        refunds=(
            ChannelRefundSnapshot(
                refund_id="refund-orphan",
                payment_transaction_id="tx-keep",
                status="succeeded",
                amount_minor=amount + 1,
                currency="CNY",
            ),
        ),
    )
    result = await _worker(database, source).run_once()

    assert result.status == "has_differences"
    assert "status_mismatch" in result.discrepancies
    assert "provider_only" in result.discrepancies
    assert "refund_amount_exceeds_payment" in result.discrepancies
    assert set(result.discrepancies) <= KNOWN_DISCREPANCIES

    async with database.sessions() as session:
        after = await _counts(session)
        assert after == before
        stored_payment = await session.get(Payment, payment_id)
        assert stored_payment is not None
        assert stored_payment.status == "confirmed"
        assert stored_payment.channel_transaction_id == "tx-keep"
        grants = list(await session.scalars(select(EntitlementEventRecord)))
        assert [row.kind for row in grants] == ["GRANT"]
        assert await session.scalar(select(func.count()).select_from(Refund)) == 0
        receipts = list(await session.scalars(select(PaymentNotificationReceipt)))
        assert [row.processing_status for row in receipts] == ["processed"]


async def test_run_once_reuses_existing_discrepancy_values(
    database: Any,
    isolated_settings: Any,
) -> None:
    del isolated_settings
    async with database.sessions() as session:
        user, offer = await _product(session)
        service = CommerceService(session)
        currency = await _notify_payment(
            service,
            user,
            offer,
            transaction_id="tx-currency",
            event_id="evt-currency",
            target_ref="reading-currency",
        )
        refunded = await _notify_payment(
            service,
            user,
            offer,
            transaction_id="tx-refunded",
            event_id="evt-refunded",
            target_ref="reading-refunded",
        )
        await service.refund_payment(
            payment_id=refunded.id,
            channel=CHANNEL,
            channel_refund_id="refund-local",
            reason="用户撤回",
            verified=True,
        )
        await session.commit()
        amount = currency.amount_minor

    source = FakeChannelReceipts(
        payments=(
            ChannelPaymentSnapshot(
                transaction_id="tx-currency",
                status="succeeded",
                amount_minor=amount,
                currency="USD",
            ),
            ChannelPaymentSnapshot(
                transaction_id="tx-refunded",
                status="refunded",
                amount_minor=amount,
                currency="CNY",
            ),
        ),
        refunds=(
            ChannelRefundSnapshot(
                refund_id="refund-unknown",
                payment_transaction_id="tx-missing",
                status="succeeded",
                amount_minor=1,
                currency="CNY",
            ),
            ChannelRefundSnapshot(
                refund_id="refund-status",
                payment_transaction_id="tx-refunded",
                status="pending",
                amount_minor=amount,
                currency="CNY",
            ),
        ),
    )
    result = await _worker(database, source).run_once()

    assert set(result.discrepancies) <= KNOWN_DISCREPANCIES
    async with database.sessions() as session:
        items = list(
            await session.scalars(
                select(PaymentReconciliationItem).where(
                    PaymentReconciliationItem.run_id == result.run_id
                )
            )
        )
        by_ref = {item.reference: item.discrepancy for item in items}
        assert by_ref["tx-currency"] == "currency_mismatch"
        assert by_ref["tx-refunded"] == "matched"
        assert by_ref["refund-local"] == "local_only"
        assert by_ref["refund-unknown"] == "refund_without_payment"
        assert by_ref["refund-status"] == "provider_only"
        assert all(item.discrepancy in KNOWN_DISCREPANCIES for item in items)
        assert await session.scalar(select(func.count()).select_from(Refund)) == 1
        refund = await session.scalar(select(Refund))
        assert refund is not None
        assert refund.channel_refund_id == "refund-local"
        assert refund.status == "confirmed"


async def test_run_once_uses_injected_clock_store_and_service(
    database: Any,
    isolated_settings: Any,
) -> None:
    del isolated_settings
    later = datetime(2026, 8, 19, 18, 30, tzinfo=UTC)
    calls: list[tuple[str, datetime | None, int, int]] = []

    class RecordingCommerceService(CommerceService):
        async def reconcile_channel(
            self,
            *,
            channel: str,
            payments: Sequence[ChannelPaymentSnapshot],
            refunds: Sequence[ChannelRefundSnapshot],
            run_at: datetime | None = None,
        ) -> tuple[PaymentReconciliationRun, list[PaymentReconciliationItem]]:
            calls.append((channel, run_at, len(payments), len(refunds)))
            return await super().reconcile_channel(
                channel=channel,
                payments=payments,
                refunds=refunds,
                run_at=run_at,
            )

    source = FakeChannelReceipts(
        payments=(
            ChannelPaymentSnapshot(
                transaction_id="tx-remote-only",
                status="succeeded",
                amount_minor=100,
                currency="CNY",
            ),
        )
    )
    result = await _worker(
        database,
        source,
        now=later,
        channel="closed",
        service_factory=RecordingCommerceService,
    ).run_once()
    assert result.channel == "closed"
    assert result.discrepancies == ("provider_only",)
    assert calls == [("closed", later, 1, 0)]
    async with database.sessions() as session:
        stored = await session.get(PaymentReconciliationRun, result.run_id)
        assert stored is not None
        assert stored.run_at.replace(tzinfo=UTC) == later
        assert stored.item_count == 1
        assert stored.difference_count == 1
