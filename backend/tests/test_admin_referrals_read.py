from datetime import UTC, datetime, timedelta

from app.admin.models import StaffUser
from app.commerce.models import ProductFamily, ProductVersion
from app.identity.models import User
from app.referrals.models import (
    ReferralAttribution,
    ReferralCampaignVersion,
    ReferralCode,
    ReferralRewardReservation,
    ReferralRewardSlot,
    ReferralTemporaryAttribution,
)
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_referrals_reads_campaign_funnel_and_reward_facts(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC)
    async with database.sessions() as session:
        inviter = User()
        referred = User()
        session.add_all([inviter, referred])
        family = ProductFamily(key="admin-referral-reading", label="Admin 邀请深读")
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
        campaign = ReferralCampaignVersion(
            campaign_key="summer-2026",
            version="v1",
            state="active",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=30),
            total_limit=100,
            per_inviter_limit=5,
            reward_quantity=2,
            reward_window_seconds=90 * 86400,
        )
        session.add(campaign)
        await session.flush()
        session.add(
            ReferralRewardSlot(
                campaign_version_id=campaign.id,
                product_version_id=product.id,
                slot_key="inviter_reward",
                enabled=True,
                total_limit=10,
                quantity=2,
            )
        )
        await session.flush()
        code = ReferralCode(
            campaign_version_id=campaign.id,
            code="SUMMER-ABC",
            inviter_user_id=inviter.id,
            status="active",
        )
        session.add(code)
        await session.flush()
        temporary = ReferralTemporaryAttribution(
            campaign_version_id=campaign.id,
            code_id=code.id,
            visitor_key_hash="a" * 64,
            inviter_user_id=inviter.id,
            expires_at=now + timedelta(days=30),
            last_seen_at=now,
        )
        session.add(temporary)
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
            quantity=2,
            status="committed",
            reserved_at=now,
            committed_at=now,
        )
        session.add(reservation)
        await session.commit()

    await _admin_headers(client)
    campaigns = await client.get("/api/v1/admin/referrals")
    assert campaigns.status_code == 200, campaigns.text
    assert campaigns.json()["campaigns"][0]["campaign_key"] == "summer-2026"
    assert campaigns.json()["campaigns"][0]["code_count"] == 1
    assert campaigns.json()["campaigns"][0]["temporary_attribution_count"] == 1
    assert campaigns.json()["campaigns"][0]["attribution_count"] == 1
    assert campaigns.json()["campaigns"][0]["reservation_count"] == 1

    detail = await client.get(f"/api/v1/admin/referrals/{campaign.id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["codes"][0]["code"] == "SUMMER-ABC"
    assert detail.json()["attributions"][0]["status"] == "locked"
    assert detail.json()["rewards"][0]["status"] == "committed"
    assert detail.json()["slots"][0]["product_version_id"] == str(product.id)
    assert detail.json()["rewards"][0]["product_version_id"] is None
    assert detail.json()["rewards"][0]["payment_attempt_id"] is None
    assert "visitor_key_hash" not in detail.text


async def test_admin_referrals_forbids_support(
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

    response = await client.get("/api/v1/admin/referrals", headers=headers)

    assert response.status_code == 403
