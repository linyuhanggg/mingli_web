from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.commerce.models import Order, PaymentAttempt, ProductFamily, ProductVersion
from app.identity.models import User
from app.referrals.models import (
    ReferralAttribution,
    ReferralCampaignVersion,
    ReferralCode,
    ReferralRewardReservation,
)
from app.referrals.policy import ReferralError, ReferralState
from app.referrals.service import ReferralService
from sqlalchemy import select


async def test_persistent_referral_lifecycle_locks_once_and_expires_reward(
    database,
) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    async with database.sessions() as session:
        inviter = User()
        referred = User()
        session.add_all([inviter, referred])
        family = ProductFamily(key="lifecycle-reading", label="生命周期深读")
        session.add(family)
        await session.flush()
        product = ProductVersion(
            family_id=family.id,
            version="v1",
            price_minor=9900,
            currency="CNY",
            contract_version="contract-v1",
            status="active",
        )
        session.add(product)
        await session.flush()
        service = ReferralService(session)
        campaign = await service.create_campaign(
            campaign_key="summer",
            version="v1",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=1),
            total_limit=2,
            per_inviter_limit=1,
            reward_quantity=2,
            reward_window_seconds=90,
        )
        await service.configure_reward_slot(
            campaign_id=campaign.id,
            product_version_id=product.id,
            slot="inviter_reward",
            total_limit=2,
            quantity=2,
        )
        await service.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        code = await service.create_code(
            campaign_id=campaign.id,
            code="SUMMER-1",
            inviter_user_id=inviter.id,
        )
        await service.record_temporary_attribution(
            campaign_id=campaign.id,
            code=code.code,
            visitor_key="visitor-1",
            now=now,
        )
        attribution = await service.lock_attribution(
            campaign_id=campaign.id,
            code=code.code,
            visitor_key="visitor-1",
            referred_user_id=referred.id,
            now=now,
        )
        reservation = await service.reserve_reward(
            attribution_id=attribution.id,
            product_version_id=product.id,
            now=now,
        )
        replayed = await service.reserve_reward(
            attribution_id=attribution.id,
            product_version_id=product.id,
            now=now,
        )
        assert replayed.id == reservation.id
        await service.commit_reward(reservation.id, now=now)
        projection = await service.commerce.ledger.project(
            entitlement_id=f"referral:{reservation.id}",
            owner_user_id=inviter.id,
        )
        assert projection.available == 2
        await service.commerce.append_entitlement_event(
            owner_user_id=inviter.id,
            entitlement_id=f"referral:{reservation.id}",
            kind="RESERVE",
            quantity=1,
            source_type="referral-test",
            source_ref="referral-test-reserve",
        )
        await service.commerce.append_entitlement_event(
            owner_user_id=inviter.id,
            entitlement_id=f"referral:{reservation.id}",
            kind="CONSUME",
            quantity=1,
            source_type="referral-test",
            source_ref="referral-test-consume",
        )
        assert await service.expire_rewards(now=now + timedelta(seconds=91)) == 1
        projection = await service.commerce.ledger.project(
            entitlement_id=f"referral:{reservation.id}",
            owner_user_id=inviter.id,
        )
        assert projection.consumed == 1
        assert projection.expired == 1


async def test_referral_rejects_invalid_visitor_and_self_referral(database) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    async with database.sessions() as session:
        inviter = User()
        session.add(inviter)
        await session.flush()
        service = ReferralService(session)
        campaign = await service.create_campaign(
            campaign_key="invite",
            version="v1",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=1),
            total_limit=10,
        )
        await service.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        code = await service.create_code(
            campaign_id=campaign.id,
            code="INVITE-1",
            inviter_user_id=inviter.id,
        )
        with pytest.raises(ReferralError, match="self referral"):
            await service.lock_attribution(
                campaign_id=campaign.id,
                code=code.code,
                visitor_key="not-recorded",
                referred_user_id=inviter.id,
                now=now,
            )


async def test_campaign_requires_positive_total_limit_and_valid_window(database) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    async with database.sessions() as session:
        service = ReferralService(session)
        with pytest.raises(ReferralError, match="total limit"):
            await service.create_campaign(
                campaign_key="unbounded",
                version="v1",
                starts_at=now,
                ends_at=now + timedelta(days=1),
            )

        with pytest.raises(ReferralError, match="campaign window"):
            await service.create_campaign(
                campaign_key="backwards",
                version="v1",
                starts_at=now + timedelta(days=1),
                ends_at=now,
                total_limit=10,
            )


async def test_temporary_attribution_expires_at_campaign_end(database) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    campaign_end = now + timedelta(hours=2)
    async with database.sessions() as session:
        inviter = User()
        session.add(inviter)
        await session.flush()
        service = ReferralService(session)
        campaign = await service.create_campaign(
            campaign_key="short-window",
            version="v1",
            starts_at=now - timedelta(minutes=1),
            ends_at=campaign_end,
            total_limit=10,
        )
        await service.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        code = await service.create_code(
            campaign_id=campaign.id,
            code="SHORT-1",
            inviter_user_id=inviter.id,
        )

        attribution = await service.record_temporary_attribution(
            campaign_id=campaign.id,
            code=code.code,
            visitor_key="short-window-visitor",
            now=now,
        )

        assert attribution.expires_at == campaign_end


async def test_ended_campaign_cannot_be_reopened(database) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    async with database.sessions() as session:
        service = ReferralService(session)
        campaign = await service.create_campaign(
            campaign_key="terminal",
            version="v1",
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=1),
            total_limit=10,
        )
        await service.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        await service.set_campaign_state(campaign.id, ReferralState.ENDED)

        with pytest.raises(ReferralError, match="invalid campaign state transition"):
            await service.set_campaign_state(campaign.id, ReferralState.ACTIVE)


async def test_payment_confirmation_after_campaign_end_releases_reserved_reward(
    database,
) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    async with database.sessions() as session:
        inviter = User()
        referred = User()
        campaign = ReferralCampaignVersion(
            campaign_key="late-payment",
            version="v1",
            state=ReferralState.ACTIVE,
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=1),
            total_limit=10,
        )
        session.add_all([inviter, referred, campaign])
        await session.flush()
        code = ReferralCode(
            campaign_version_id=campaign.id,
            code="LATE-PAYMENT-1",
            inviter_user_id=inviter.id,
        )
        session.add(code)
        await session.flush()
        attribution = ReferralAttribution(
            campaign_version_id=campaign.id,
            code_id=code.id,
            referred_user_id=referred.id,
            inviter_user_id=inviter.id,
            locked_at=now,
            status="locked",
        )
        session.add(attribution)
        await session.flush()
        reservation = ReferralRewardReservation(
            campaign_version_id=campaign.id,
            attribution_id=attribution.id,
            referred_user_id=referred.id,
            inviter_user_id=inviter.id,
            quantity=1,
            status="reserved",
            reserved_at=now,
        )
        session.add(reservation)
        await session.flush()

        campaign.state = ReferralState.ENDED
        result = await ReferralService(session).commit_reward(
            reservation.id,
            now=now + timedelta(days=2),
        )

        assert result.status == "released"
        assert await session.scalar(
            select(ReferralRewardReservation).where(
                ReferralRewardReservation.id == reservation.id,
                ReferralRewardReservation.status == "committed",
            )
        ) is None


async def test_reward_slots_bind_reservations_to_product_payment_and_release_capacity(
    database,
) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    async with database.sessions() as session:
        inviter = User()
        referred = User()
        second_referred = User()
        session.add_all([inviter, referred, second_referred])
        family = ProductFamily(key="deep-reading", label="深读")
        session.add(family)
        await session.flush()
        product = ProductVersion(
            family_id=family.id,
            version="v1",
            price_minor=9900,
            currency="CNY",
            contract_version="contract-v1",
            status="active",
        )
        session.add(product)
        await session.flush()

        service = ReferralService(session)
        campaign = await service.create_campaign(
            campaign_key="product-slot",
            version="v1",
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=1),
            total_limit=2,
        )
        await service.configure_reward_slot(
            campaign_id=campaign.id,
            product_version_id=product.id,
            slot="inviter_reward",
            total_limit=1,
            quantity=1,
        )
        await service.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        code = await service.create_code(
            campaign_id=campaign.id,
            code="PRODUCT-SLOT-1",
            inviter_user_id=inviter.id,
        )

        async def payment_for(owner_id):  # type: ignore[no-untyped-def]
            order = Order(
                owner_user_id=owner_id,
                product_version_id=product.id,
                purchase_target_ref=f"target:{owner_id}",
                amount_minor=product.price_minor,
                currency=product.currency,
                status="payment_pending",
            )
            session.add(order)
            await session.flush()
            attempt = PaymentAttempt(
                order_id=order.id,
                channel="test",
                idempotency_key_hash=uuid4().hex,
                status="pending",
            )
            session.add(attempt)
            await session.flush()
            return attempt

        for visitor, user in (("slot-visitor-1", referred), ("slot-visitor-2", second_referred)):
            await service.record_temporary_attribution(
                campaign_id=campaign.id,
                code=code.code,
                visitor_key=visitor,
                now=now,
            )
            await service.lock_attribution(
                campaign_id=campaign.id,
                code=code.code,
                visitor_key=visitor,
                referred_user_id=user.id,
                now=now,
            )

        first_attempt = await payment_for(referred.id)
        first_attribution = await session.scalar(
            select(ReferralAttribution).where(
                ReferralAttribution.referred_user_id == referred.id,
            )
        )
        assert first_attribution is not None
        first = await service.reserve_reward_for_payment(
            attribution_id=first_attribution.id,
            payment_attempt_id=first_attempt.id,
            now=now,
        )

        assert first.product_version_id == product.id
        assert first.payment_attempt_id == first_attempt.id

        second_attempt = await payment_for(second_referred.id)
        second_attribution = await session.scalar(
            select(ReferralAttribution).where(
                ReferralAttribution.referred_user_id == second_referred.id,
            )
        )
        assert second_attribution is not None
        with pytest.raises(ReferralError, match="product reward limit"):
            await service.reserve_reward_for_payment(
                attribution_id=second_attribution.id,
                payment_attempt_id=second_attempt.id,
                now=now,
            )

        await service.release_reward_for_payment(payment_attempt_id=first_attempt.id)
        released = await service.reserve_reward_for_payment(
            attribution_id=second_attribution.id,
            payment_attempt_id=second_attempt.id,
            now=now,
        )
        assert released.status == "reserved"
