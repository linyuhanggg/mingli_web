from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.commerce.models import (
    NotificationOutbox,
    ProductFamily,
    ProductOffer,
    ProductVersion,
)
from app.commerce.service import CommerceError, CommerceService
from app.identity.models import User
from app.identity.policy import CURRENT_POLICY_VERSION
from app.referrals.models import ReferralRewardReservation
from app.referrals.policy import ReferralState
from app.referrals.service import ReferralService
from sqlalchemy import select


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


async def test_order_payment_ledger_and_refund_are_idempotent(database) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user, offer = await product_fixture(session)
        service = CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="reading-target-1",
        )
        first_attempt, created = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-1",
        )
        assert created is True

        replayed_attempt, created = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-1",
        )
        assert replayed_attempt.id == first_attempt.id
        assert created is False

        with pytest.raises(CommerceError, match="verification"):
            await service.confirm_payment(
                order_id=order.id,
                attempt_id=first_attempt.id,
                channel="closed",
                channel_transaction_id="tx-1",
                verified=False,
            )
        payment, created = await service.confirm_payment(
            order_id=order.id,
            attempt_id=first_attempt.id,
            channel="closed",
            channel_transaction_id="tx-1",
            verified=True,
        )
        assert created is True
        replayed_payment, created = await service.confirm_payment(
            order_id=order.id,
            attempt_id=first_attempt.id,
            channel="closed",
            channel_transaction_id="tx-1",
            verified=True,
        )
        assert replayed_payment.id == payment.id
        assert created is False

        projection = await service.ledger.project(
            entitlement_id=f"order:{order.id}",
            owner_user_id=user.id,
        )
        assert projection.available == 1
        await service.append_entitlement_event(
            owner_user_id=user.id,
            entitlement_id=f"order:{order.id}",
            kind="RESERVE",
            quantity=1,
            source_type="reading",
            source_ref="reading-1",
        )
        await service.append_entitlement_event(
            owner_user_id=user.id,
            entitlement_id=f"order:{order.id}",
            kind="CONSUME",
            quantity=1,
            source_type="reading",
            source_ref="reading-consume-1",
        )
        refund, created = await service.refund_payment(
            payment_id=payment.id,
            channel="closed",
            channel_refund_id="refund-1",
            reason="用户撤回",
            verified=True,
        )
        assert refund.status == "confirmed"
        assert created is True
        replayed_refund, created = await service.refund_payment(
            payment_id=payment.id,
            channel="closed",
            channel_refund_id="refund-1",
            reason="用户撤回",
            verified=True,
        )
        assert replayed_refund.id == refund.id
        assert created is False
        projection = await service.ledger.project(
            entitlement_id=f"order:{order.id}",
            owner_user_id=user.id,
        )
        assert projection.reversed == 1


async def test_confirmed_payment_commits_bound_referral_reward_once(database) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    async with database.sessions() as session:
        referred, offer = await product_fixture(session)
        inviter = User()
        session.add(inviter)
        await session.flush()

        referral = ReferralService(session)
        campaign = await referral.create_campaign(
            campaign_key="payment-trigger",
            version="v1",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=2),
            total_limit=10,
        )
        await referral.configure_reward_slot(
            campaign_id=campaign.id,
            product_version_id=offer.product_version_id,
            slot="inviter_reward",
            total_limit=10,
            quantity=2,
        )
        await referral.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        code = await referral.create_code(
            campaign_id=campaign.id,
            code="PAYMENT-TRIGGER-1",
            inviter_user_id=inviter.id,
        )
        await referral.record_temporary_attribution(
            campaign_id=campaign.id,
            code=code.code,
            visitor_key="payment-trigger-visitor",
            now=now,
        )
        attribution = await referral.lock_attribution(
            campaign_id=campaign.id,
            code=code.code,
            visitor_key="payment-trigger-visitor",
            referred_user_id=referred.id,
            now=now,
        )

        commerce = CommerceService(session)
        order = await commerce.create_order(
            owner_user_id=referred.id,
            offer_id=offer.id,
            purchase_target_ref="payment-trigger-target",
        )
        attempt, _ = await commerce.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-trigger-attempt",
            referral_attribution_id=attribution.id,
            now=now,
        )
        reservation = await session.scalar(
            select(ReferralRewardReservation).where(
                ReferralRewardReservation.payment_attempt_id == attempt.id,
            )
        )
        assert reservation is not None
        replayed_attempt, attempt_created = await commerce.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-trigger-attempt",
            referral_attribution_id=attribution.id,
            now=now,
        )
        assert replayed_attempt.id == attempt.id
        assert attempt_created is False

        payment, created = await commerce.confirm_payment(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            channel_transaction_id="payment-trigger-transaction",
            verified=True,
            now=now,
        )
        assert created is True

        committed_notifications = list(
            await session.scalars(
                select(NotificationOutbox).where(
                    NotificationOutbox.kind == "referral.reward.committed",
                )
            )
        )
        assert len(committed_notifications) == 2
        assert all(
            set(item.payload) == {"state", "channel"}
            and "amount_minor" not in item.payload
            and "channel_transaction_id" not in item.payload
            for item in committed_notifications
        )

        with pytest.raises(CommerceError, match="refund confirmation"):
            await commerce.refund_payment(
                payment_id=payment.id,
                channel="closed",
                channel_refund_id="payment-trigger-refund-without-confirmation",
                reason="平台终止活动",
                verified=True,
            )

        confirmation, confirmation_created = await referral.confirm_refund(
            payment_id=payment.id,
            user_id=referred.id,
            policy_version=CURRENT_POLICY_VERSION,
        )
        assert confirmation_created is True
        assert confirmation.payment_id == payment.id
        assert confirmation.campaign_version_id == campaign.id
        assert confirmation.product_version_id == offer.product_version_id
        assert confirmation.policy_version == CURRENT_POLICY_VERSION

        stored = await session.get(ReferralRewardReservation, reservation.id)
        assert stored is not None
        assert stored.status == "committed"
        events = await commerce.ledger.find_events_by_source(
            source_type="referral",
            source_ref=str(reservation.id),
        )
        assert len(events) == 1
        assert events[0].kind == "GRANT"
        projection = await commerce.ledger.project(
            entitlement_id=f"referral:{reservation.id}",
            owner_user_id=inviter.id,
        )
        assert projection.available == 2

        replayed, created = await commerce.confirm_payment(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            channel_transaction_id="payment-trigger-transaction",
            verified=True,
        )
        assert replayed.id == payment.id
        assert created is False
        replayed_events = await commerce.ledger.find_events_by_source(
            source_type="referral",
            source_ref=str(reservation.id),
        )
        assert len(replayed_events) == 1

        await commerce.append_entitlement_event(
            owner_user_id=inviter.id,
            entitlement_id=f"referral:{reservation.id}",
            kind="RESERVE",
            quantity=1,
            source_type="referral-test",
            source_ref="payment-trigger-referral-reserve",
        )
        await commerce.append_entitlement_event(
            owner_user_id=inviter.id,
            entitlement_id=f"referral:{reservation.id}",
            kind="CONSUME",
            quantity=1,
            source_type="referral-test",
            source_ref="payment-trigger-referral-consume",
        )
        refund, refund_created = await commerce.refund_payment(
            payment_id=payment.id,
            channel="closed",
            channel_refund_id="payment-trigger-refund",
            reason="平台终止活动",
            verified=True,
            referral_refund_confirmation_id=confirmation.id,
        )
        assert refund_created is True
        stored = await session.get(ReferralRewardReservation, reservation.id)
        assert stored is not None
        assert stored.status == "reversed"
        reverse_events = await commerce.ledger.find_events_by_source(
            source_type="referral_refund",
            source_ref=f"{refund.id}:reverse",
        )
        assert len(reverse_events) == 1
        assert reverse_events[0].kind == "REVERSE"
        expire_events = await commerce.ledger.find_events_by_source(
            source_type="referral_refund",
            source_ref=f"{refund.id}:expire",
        )
        assert len(expire_events) == 1
        assert expire_events[0].kind == "EXPIRE"
        refunded_notifications = list(
            await session.scalars(
                select(NotificationOutbox).where(
                    NotificationOutbox.kind == "referral.reward.refunded",
                )
            )
        )
        assert len(refunded_notifications) == 2


async def test_failed_payment_notification_releases_referral_reward_slot(
    database,
) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    async with database.sessions() as session:
        referred, offer = await product_fixture(session)
        inviter = User()
        session.add(inviter)
        await session.flush()

        referral = ReferralService(session)
        campaign = await referral.create_campaign(
            campaign_key="payment-release",
            version="v1",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=2),
            total_limit=10,
        )
        await referral.configure_reward_slot(
            campaign_id=campaign.id,
            product_version_id=offer.product_version_id,
            slot="inviter_reward",
            total_limit=10,
            quantity=1,
        )
        await referral.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        code = await referral.create_code(
            campaign_id=campaign.id,
            code="PAYMENT-RELEASE-1",
            inviter_user_id=inviter.id,
        )
        await referral.record_temporary_attribution(
            campaign_id=campaign.id,
            code=code.code,
            visitor_key="payment-release-visitor",
            now=now,
        )
        attribution = await referral.lock_attribution(
            campaign_id=campaign.id,
            code=code.code,
            visitor_key="payment-release-visitor",
            referred_user_id=referred.id,
            now=now,
        )

        commerce = CommerceService(session)
        order = await commerce.create_order(
            owner_user_id=referred.id,
            offer_id=offer.id,
            purchase_target_ref="payment-release-target",
        )
        attempt, created = await commerce.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-release-attempt",
            referral_attribution_id=attribution.id,
            now=now,
        )
        assert created is True
        reservation = await session.scalar(
            select(ReferralRewardReservation).where(
                ReferralRewardReservation.payment_attempt_id == attempt.id,
            )
        )
        assert reservation is not None
        assert reservation.status == "reserved"

        payment, notification_created = await commerce.apply_payment_notification(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            external_event_id="payment-release-event",
            channel_transaction_id=None,
            payment_succeeded=False,
            verified=True,
        )
        assert payment is None
        assert notification_created is False
        await session.refresh(reservation)
        assert reservation.status == "released"
        assert await session.scalar(select(ReferralRewardReservation).where(
            ReferralRewardReservation.payment_attempt_id == attempt.id,
            ReferralRewardReservation.status == "reserved",
        )) is None


async def test_payment_confirmation_requires_attempt_channel_match(database) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user, offer = await product_fixture(session)
        service = CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="reading-target-channel-boundary",
        )
        attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-channel-boundary",
        )

        with pytest.raises(CommerceError, match="channel"):
            await service.confirm_payment(
                order_id=order.id,
                attempt_id=attempt.id,
                channel="different-channel",
                channel_transaction_id="tx-channel-boundary",
                verified=True,
            )

        assert order.status == "payment_pending"
        assert attempt.status == "pending"


async def test_payment_attempt_cannot_be_confirmed_with_second_transaction(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user, offer = await product_fixture(session)
        service = CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="reading-target-single-confirmation",
        )
        attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-single-confirmation",
        )
        await service.confirm_payment(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            channel_transaction_id="tx-first-confirmation",
            verified=True,
        )

        with pytest.raises(CommerceError, match="already confirmed"):
            await service.confirm_payment(
                order_id=order.id,
                attempt_id=attempt.id,
                channel="closed",
                channel_transaction_id="tx-second-confirmation",
                verified=True,
            )

        projection = await service.ledger.project(
            entitlement_id=f"order:{order.id}",
            owner_user_id=user.id,
        )
        assert projection.granted == 1


async def test_paid_order_rejects_a_late_payment_attempt(database) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user, offer = await product_fixture(session)
        service = CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="reading-target-paid-order-boundary",
        )
        first_attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-first-late-boundary",
        )
        second_attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="payment-attempt-second-late-boundary",
        )
        await service.confirm_payment(
            order_id=order.id,
            attempt_id=first_attempt.id,
            channel="closed",
            channel_transaction_id="tx-first-late-boundary",
            verified=True,
        )

        with pytest.raises(CommerceError, match="already paid"):
            await service.confirm_payment(
                order_id=order.id,
                attempt_id=second_attempt.id,
                channel="closed",
                channel_transaction_id="tx-second-late-boundary",
                verified=True,
            )

        projection = await service.ledger.project(
            entitlement_id=f"order:{order.id}",
            owner_user_id=user.id,
        )
        assert projection.granted == 1


async def test_refund_reference_cannot_be_replayed_for_another_payment(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        first_user, first_offer = await product_fixture(session)
        service = CommerceService(session)
        first_order = await service.create_order(
            owner_user_id=first_user.id,
            offer_id=first_offer.id,
            purchase_target_ref="reading-target-first-refund",
        )
        first_attempt, _ = await service.create_payment_attempt(
            order_id=first_order.id,
            channel="closed",
            idempotency_key="payment-attempt-first-refund",
        )
        first_payment, _ = await service.confirm_payment(
            order_id=first_order.id,
            attempt_id=first_attempt.id,
            channel="closed",
            channel_transaction_id="tx-first-refund",
            verified=True,
        )
        first_refund, _ = await service.refund_payment(
            payment_id=first_payment.id,
            channel="closed",
            channel_refund_id="refund-reference-boundary",
            reason="用户撤回",
            verified=True,
        )

        second_user = User()
        second_family = ProductFamily(key="bazi-second-refund", label="八字深读")
        session.add_all([second_user, second_family])
        await session.flush()
        second_product = ProductVersion(
            family_id=second_family.id,
            version="v1",
            price_minor=9900,
            currency="CNY",
            contract_version="reading-document-v1",
            status="active",
        )
        session.add(second_product)
        await session.flush()
        second_offer = ProductOffer(
            product_version_id=second_product.id,
            channel="closed",
            channel_sku="bazi-second-refund-v1",
            price_minor=9900,
            currency="CNY",
            enabled=True,
        )
        session.add(second_offer)
        await session.flush()
        second_order = await service.create_order(
            owner_user_id=second_user.id,
            offer_id=second_offer.id,
            purchase_target_ref="reading-target-second-refund",
        )
        second_attempt, _ = await service.create_payment_attempt(
            order_id=second_order.id,
            channel="closed",
            idempotency_key="payment-attempt-second-refund",
        )
        second_payment, _ = await service.confirm_payment(
            order_id=second_order.id,
            attempt_id=second_attempt.id,
            channel="closed",
            channel_transaction_id="tx-second-refund",
            verified=True,
        )

        with pytest.raises(CommerceError, match="bound"):
            await service.refund_payment(
                payment_id=second_payment.id,
                channel="closed",
                channel_refund_id="refund-reference-boundary",
                reason="错误回调",
                verified=True,
            )

        assert first_refund.payment_id == first_payment.id


async def test_notification_outbox_deduplicates_and_claims(database) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = CommerceService(session)
        item, created = await service.enqueue_notification(
            owner_user_id=user.id,
            kind="account.closed",
            dedupe_key="account.closed:user-1",
            payload={"message": "closed"},
        )
        assert created is True
        replayed, created = await service.enqueue_notification(
            owner_user_id=user.id,
            kind="account.closed",
            dedupe_key="account.closed:user-1",
            payload={"message": "different"},
        )
        assert replayed.id == item.id
        assert created is False
        claimed = await service.claim_notifications()
        assert [row.id for row in claimed] == [item.id]
        await service.mark_notification_sent(item.id)
        stored = await session.get(NotificationOutbox, item.id)
        assert stored is not None
        assert stored.status == "sent"


async def test_notification_preferences_gate_external_outbox_channels(database) -> None:  # type: ignore[no-untyped-def]
    from app.commerce.models import NotificationPreference

    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = CommerceService(session)

        defaults = await service.get_notification_preferences(user.id)
        assert defaults.in_app_enabled is True
        assert defaults.email_enabled is False
        assert defaults.sms_enabled is False

        suppressed, created = await service.enqueue_notification(
            owner_user_id=user.id,
            kind="reading.accepted",
            dedupe_key="reading.accepted:email:1",
            payload={"message": "accepted"},
            channel="email",
        )
        assert suppressed is None
        assert created is False

        updated = await service.update_notification_preferences(
            user.id,
            in_app_enabled=True,
            email_enabled=True,
            sms_enabled=False,
        )
        assert updated.email_enabled is True
        item, created = await service.enqueue_notification(
            owner_user_id=user.id,
            kind="reading.accepted",
            dedupe_key="reading.accepted:email:1",
            payload={"message": "accepted"},
            channel="email",
        )
        assert item is not None
        assert item.payload["channel"] == "email"
        assert created is True
        stored = await session.scalar(
            select(NotificationPreference).where(NotificationPreference.user_id == user.id)
        )
        assert stored is not None
        assert stored.email_enabled is True
