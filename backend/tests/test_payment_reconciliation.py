from __future__ import annotations

import pytest
from app.commerce.models import (
    EntitlementEventRecord,
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
from app.commerce.service import CommerceError, CommerceService
from app.identity.models import User
from sqlalchemy import func, select


async def product_fixture(session):  # type: ignore[no-untyped-def]
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
        channel="closed",
        channel_sku="bazi-v1",
        price_minor=9900,
        currency="CNY",
        enabled=True,
    )
    session.add(offer)
    await session.flush()
    return user, offer


async def confirm_closed_payment(  # type: ignore[no-untyped-def]
    service: CommerceService,
    user: User,
    offer: ProductOffer,
    *,
    transaction_id: str,
    idempotency_key: str,
    target_ref: str,
) -> Payment:
    order = await service.create_order(
        owner_user_id=user.id,
        offer_id=offer.id,
        purchase_target_ref=target_ref,
    )
    attempt, _ = await service.create_payment_attempt(
        order_id=order.id,
        channel="closed",
        idempotency_key=idempotency_key,
    )
    payment, _ = await service.confirm_payment(
        order_id=order.id,
        attempt_id=attempt.id,
        channel="closed",
        channel_transaction_id=transaction_id,
        verified=True,
    )
    return payment


async def test_verified_payment_notification_is_idempotent_by_event_id(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user, offer = await product_fixture(session)
        service = CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="reading-target-1",
        )
        attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-1",
        )

        payment, created = await service.apply_payment_notification(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            external_event_id="event-1",
            channel_transaction_id="tx-1",
            payment_succeeded=True,
            verified=True,
        )
        replayed, replay_created = await service.apply_payment_notification(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            external_event_id="event-1",
            channel_transaction_id="tx-1",
            payment_succeeded=True,
            verified=True,
        )

        assert payment is not None
        assert created is True
        assert replayed is not None
        assert replayed.id == payment.id
        assert replay_created is False
        assert await session.scalar(select(func.count()).select_from(Payment)) == 1
        assert (
            await session.scalar(select(func.count()).select_from(EntitlementEventRecord))
            == 1
        )
        receipt = await session.scalar(select(PaymentNotificationReceipt))
        assert receipt is not None
        assert receipt.external_event_id == "event-1"
        assert receipt.channel_transaction_id == "tx-1"
        assert receipt.processing_status == "processed"
        assert receipt.payment_id == payment.id
        assert (
            await session.scalar(select(func.count()).select_from(PaymentNotificationReceipt))
            == 1
        )

        with pytest.raises(CommerceError, match="notification event is bound"):
            await service.apply_payment_notification(
                order_id=order.id,
                attempt_id=attempt.id,
                channel="closed",
                external_event_id="event-1",
                channel_transaction_id="tx-2",
                payment_succeeded=True,
                verified=True,
            )


async def test_unverified_payment_notification_is_rejected_without_receipt(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user, offer = await product_fixture(session)
        service = CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="reading-target-1",
        )
        attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-1",
        )

        with pytest.raises(
            CommerceError, match="payment notification verification is required"
        ):
            await service.apply_payment_notification(
                order_id=order.id,
                attempt_id=attempt.id,
                channel="closed",
                external_event_id="event-unverified",
                channel_transaction_id="tx-unverified",
                payment_succeeded=True,
                verified=False,
            )

        with pytest.raises(
            CommerceError, match="successful payment notification needs a transaction id"
        ):
            await service.apply_payment_notification(
                order_id=order.id,
                attempt_id=attempt.id,
                channel="closed",
                external_event_id="event-missing-tx",
                channel_transaction_id=None,
                payment_succeeded=True,
                verified=True,
            )

        assert await session.scalar(select(func.count()).select_from(Payment)) == 0
        assert (
            await session.scalar(select(func.count()).select_from(PaymentNotificationReceipt))
            == 0
        )
        assert (
            await session.scalar(select(func.count()).select_from(EntitlementEventRecord))
            == 0
        )


async def test_verified_failed_payment_notification_is_idempotent_without_grant(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user, offer = await product_fixture(session)
        service = CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="reading-target-1",
        )
        attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-1",
        )

        payment, created = await service.apply_payment_notification(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            external_event_id="event-failed",
            channel_transaction_id=None,
            payment_succeeded=False,
            verified=True,
        )
        replayed, replay_created = await service.apply_payment_notification(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            external_event_id="event-failed",
            channel_transaction_id=None,
            payment_succeeded=False,
            verified=True,
        )

        assert payment is None
        assert created is False
        assert replayed is None
        assert replay_created is False
        assert await session.scalar(select(func.count()).select_from(Payment)) == 0
        assert (
            await session.scalar(select(func.count()).select_from(EntitlementEventRecord))
            == 0
        )
        receipt = await session.scalar(select(PaymentNotificationReceipt))
        assert receipt is not None
        assert receipt.external_event_id == "event-failed"
        assert receipt.provider_status == "pending"
        assert receipt.processing_status == "ignored"
        assert receipt.payment_id is None
        assert (
            await session.scalar(select(func.count()).select_from(PaymentNotificationReceipt))
            == 1
        )

        with pytest.raises(CommerceError, match="notification event is bound"):
            await service.apply_payment_notification(
                order_id=order.id,
                attempt_id=attempt.id,
                channel="closed",
                external_event_id="event-failed",
                channel_transaction_id="tx-late-success",
                payment_succeeded=True,
                verified=True,
            )


async def test_channel_reconciliation_persists_differences_and_refund_exceptions(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user, offer = await product_fixture(session)
        service = CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="reading-target-1",
        )
        attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-1",
        )
        payment, _ = await service.confirm_payment(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            channel_transaction_id="tx-1",
            verified=True,
        )
        refund, _ = await service.refund_payment(
            payment_id=payment.id,
            channel="closed",
            channel_refund_id="refund-1",
            reason="用户撤回",
            verified=True,
        )

        run, items = await service.reconcile_channel(
            channel="closed",
            payments=[
                ChannelPaymentSnapshot(
                    transaction_id="tx-1",
                    status="refunded",
                    amount_minor=9900,
                    currency="CNY",
                ),
                ChannelPaymentSnapshot(
                    transaction_id="tx-remote",
                    status="succeeded",
                    amount_minor=100,
                    currency="CNY",
                ),
            ],
            refunds=[
                ChannelRefundSnapshot(
                    refund_id="refund-1",
                    payment_transaction_id="tx-1",
                    status="succeeded",
                    amount_minor=10000,
                    currency="CNY",
                ),
                ChannelRefundSnapshot(
                    refund_id="refund-unknown",
                    payment_transaction_id="tx-missing",
                    status="succeeded",
                    amount_minor=1,
                    currency="CNY",
                ),
            ],
        )

        discrepancies = {item.discrepancy for item in items}
        assert run.status == "has_differences"
        assert run.difference_count == len(items) - run.matched_count
        assert "refund_amount_exceeds_payment" in discrepancies
        assert "refund_without_payment" in discrepancies
        assert "provider_only" in discrepancies
        assert await session.scalar(select(func.count()).select_from(Refund)) == 1
        persisted_run = await session.get(PaymentReconciliationRun, run.id)
        assert persisted_run is not None
        assert persisted_run.status == "has_differences"
        assert persisted_run.item_count == len(items)
        persisted_items = list(
            await session.scalars(
                select(PaymentReconciliationItem).where(
                    PaymentReconciliationItem.run_id == run.id
                )
            )
        )
        assert {item.discrepancy for item in persisted_items} == discrepancies
        assert refund.channel_refund_id == "refund-1"


async def test_channel_reconciliation_classifies_local_amount_currency_and_status_differences(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user, offer = await product_fixture(session)
        service = CommerceService(session)
        await confirm_closed_payment(
            service,
            user,
            offer,
            transaction_id="tx-local-only",
            idempotency_key="attempt-local-only",
            target_ref="reading-target-local-only",
        )
        await confirm_closed_payment(
            service,
            user,
            offer,
            transaction_id="tx-amount",
            idempotency_key="attempt-amount",
            target_ref="reading-target-amount",
        )
        await confirm_closed_payment(
            service,
            user,
            offer,
            transaction_id="tx-currency",
            idempotency_key="attempt-currency",
            target_ref="reading-target-currency",
        )
        await confirm_closed_payment(
            service,
            user,
            offer,
            transaction_id="tx-status",
            idempotency_key="attempt-status",
            target_ref="reading-target-status",
        )
        matched = await confirm_closed_payment(
            service,
            user,
            offer,
            transaction_id="tx-matched",
            idempotency_key="attempt-matched",
            target_ref="reading-target-matched",
        )

        run, items = await service.reconcile_channel(
            channel="closed",
            payments=[
                ChannelPaymentSnapshot(
                    transaction_id="tx-amount",
                    status="succeeded",
                    amount_minor=100,
                    currency="CNY",
                ),
                ChannelPaymentSnapshot(
                    transaction_id="tx-currency",
                    status="succeeded",
                    amount_minor=matched.amount_minor,
                    currency="USD",
                ),
                ChannelPaymentSnapshot(
                    transaction_id="tx-status",
                    status="failed",
                    amount_minor=matched.amount_minor,
                    currency="CNY",
                ),
                ChannelPaymentSnapshot(
                    transaction_id="tx-matched",
                    status="succeeded",
                    amount_minor=matched.amount_minor,
                    currency="CNY",
                ),
            ],
            refunds=[],
        )

        by_ref = {item.reference: item.discrepancy for item in items}
        assert by_ref["tx-local-only"] == "local_only"
        assert by_ref["tx-amount"] == "amount_mismatch"
        assert by_ref["tx-currency"] == "currency_mismatch"
        assert by_ref["tx-status"] == "status_mismatch"
        assert by_ref["tx-matched"] == "matched"
        assert run.status == "has_differences"
        assert run.matched_count == 1
        assert run.difference_count == 4
        assert run.item_count == 5
        persisted = {
            item.reference: item.discrepancy
            for item in await session.scalars(
                select(PaymentReconciliationItem).where(
                    PaymentReconciliationItem.run_id == run.id
                )
            )
        }
        assert persisted == by_ref


async def test_channel_reconciliation_flags_aggregate_refund_overage(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user, offer = await product_fixture(session)
        service = CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="reading-target-1",
        )
        attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-1",
        )
        payment, _ = await service.confirm_payment(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            channel_transaction_id="tx-1",
            verified=True,
        )

        _, items = await service.reconcile_channel(
            channel="closed",
            payments=[
                ChannelPaymentSnapshot(
                    transaction_id="tx-1",
                    status="succeeded",
                    amount_minor=payment.amount_minor,
                    currency="CNY",
                ),
            ],
            refunds=[
                ChannelRefundSnapshot(
                    refund_id="refund-a",
                    payment_transaction_id="tx-1",
                    status="succeeded",
                    amount_minor=5000,
                    currency="CNY",
                ),
                ChannelRefundSnapshot(
                    refund_id="refund-b",
                    payment_transaction_id="tx-1",
                    status="succeeded",
                    amount_minor=5000,
                    currency="CNY",
                ),
            ],
        )

        overage = [
            item
            for item in items
            if item.discrepancy == "refund_amount_exceeds_payment"
        ]
        assert {item.reference for item in overage} == {"refund-a", "refund-b"}
        assert all(item.kind == "refund" for item in overage)
        assert payment.amount_minor == 9900
