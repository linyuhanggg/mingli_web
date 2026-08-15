from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.admin.models import StaffUser
from app.commerce.models import ProductFamily, ProductOffer, ProductVersion
from app.commerce.service import CommerceService
from app.identity.models import User
from app.identity.policy import CURRENT_POLICY_VERSION
from app.referrals.models import (
    ReferralAttribution,
    ReferralCampaignVersion,
    ReferralCode,
    ReferralRefundConfirmation,
    ReferralRewardReservation,
)
from app.referrals.service import ReferralService
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_commerce_read_lists_order_payment_and_refund_facts(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    await _admin_headers(client)
    async with database.sessions() as session:
        user = User()
        family = ProductFamily(key="admin-read-bazi", label="八字深读")
        session.add_all([user, family])
        await session.flush()
        version = ProductVersion(
            family_id=family.id,
            version="v1",
            price_minor=9900,
            currency="CNY",
            contract_version="reading-document-v1",
            status="active",
        )
        session.add(version)
        await session.flush()
        offer = ProductOffer(
            product_version_id=version.id,
            channel="closed",
            channel_sku="admin-read-bazi-v1",
            price_minor=9900,
            currency="CNY",
            enabled=True,
        )
        session.add(offer)
        await session.flush()
        service = CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="admin-read-target",
        )
        attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="admin-read-attempt",
        )
        payment, _ = await service.confirm_payment(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            channel_transaction_id="admin-read-tx",
            verified=True,
        )
        accepted_at = datetime(2026, 8, 14, 8, 30, tzinfo=UTC)
        campaign = ReferralCampaignVersion(
            campaign_key="admin-read-referral",
            version="v1",
            state="active",
            starts_at=accepted_at - timedelta(days=1),
            ends_at=accepted_at + timedelta(days=30),
            total_limit=10,
            per_inviter_limit=10,
            reward_quantity=1,
            reward_window_seconds=90 * 86400,
        )
        session.add(campaign)
        await session.flush()
        code = ReferralCode(
            campaign_version_id=campaign.id,
            code="ADMIN-READ-REFERRAL",
            inviter_user_id=user.id,
        )
        session.add(code)
        await session.flush()
        attribution = ReferralAttribution(
            campaign_version_id=campaign.id,
            code_id=code.id,
            referred_user_id=user.id,
            inviter_user_id=user.id,
            locked_at=accepted_at,
        )
        session.add(attribution)
        await session.flush()
        reservation = ReferralRewardReservation(
            campaign_version_id=campaign.id,
            attribution_id=attribution.id,
            referred_user_id=user.id,
            inviter_user_id=user.id,
            product_version_id=version.id,
            payment_attempt_id=attempt.id,
            quantity=1,
            status="reserved",
            reserved_at=accepted_at,
        )
        session.add(reservation)
        await session.flush()
        await ReferralService(session).commit_reward(reservation.id, now=accepted_at)
        confirmation = ReferralRefundConfirmation(
            order_id=order.id,
            payment_id=payment.id,
            reservation_id=reservation.id,
            campaign_version_id=campaign.id,
            product_version_id=version.id,
            user_id=user.id,
            policy_version=CURRENT_POLICY_VERSION,
            accepted_at=accepted_at,
        )
        session.add(confirmation)
        await session.flush()
        refund, _ = await service.refund_payment(
            payment_id=payment.id,
            channel="closed",
            channel_refund_id="admin-read-refund",
            reason="测试退款事实",
            verified=True,
            referral_refund_confirmation_id=confirmation.id,
        )
        await session.commit()

    orders = await client.get("/api/v1/admin/commerce/orders")
    payments = await client.get("/api/v1/admin/commerce/payments")
    refunds = await client.get("/api/v1/admin/commerce/refunds")
    assert orders.status_code == 200, orders.text
    assert payments.status_code == 200, payments.text
    assert refunds.status_code == 200, refunds.text
    assert orders.json()["orders"][0]["id"] == str(order.id)
    assert orders.json()["orders"][0]["status"] == "refunded"
    assert payments.json()["payments"][0]["channel_transaction_id"] == "admin-read-tx"
    assert refunds.json()["refunds"][0]["id"] == str(refund.id)
    assert refunds.json()["refunds"][0]["referral_confirmation_id"] == str(confirmation.id)
    assert (
        refunds.json()["refunds"][0]["referral_confirmation_policy_version"]
        == CURRENT_POLICY_VERSION
    )
    confirmation_at = datetime.fromisoformat(
        refunds.json()["refunds"][0]["referral_confirmation_at"]
    ).replace(tzinfo=UTC)
    assert confirmation_at == accepted_at
    assert "idempotency_key_hash" not in orders.text


async def test_admin_commerce_read_forbids_support(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    response = await client.get("/api/v1/admin/commerce/orders", headers=headers)

    assert response.status_code == 403
