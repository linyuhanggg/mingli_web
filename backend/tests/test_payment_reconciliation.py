from __future__ import annotations

import pytest
from app.commerce.models import (
    EntitlementEventRecord,
    Payment,
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

        assert "refund_amount_exceeds_payment" in {
            item.discrepancy for item in items
        }
