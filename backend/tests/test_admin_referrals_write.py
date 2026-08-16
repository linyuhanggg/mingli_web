from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.admin.models import AdminAuditEvent, StaffUser
from app.commerce.models import ProductFamily, ProductVersion
from app.identity.models import User
from app.referrals.models import ReferralCampaignVersion, ReferralRewardSlot
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={
            "email": "ops@example.com",
            "password": "correct-horse",
        },
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_ops_can_create_referral_campaign_with_audited_reason(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    now = datetime.now(UTC)

    response = await client.post(
        "/api/v1/admin/referrals",
        headers=headers,
        json={
            "campaign_key": "spring-2027",
            "version": "v1",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=30)).isoformat(),
            "total_limit": 100,
            "per_inviter_limit": 10,
            "reward_quantity": 1,
            "reward_window_seconds": 90 * 86400,
            "reason": "运营配置春季邀请活动。",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["campaign_key"] == "spring-2027"
    assert body["state"] == "draft"
    assert body["total_limit"] == 100

    async with database.sessions() as session:
        campaign = await session.scalar(
            select(ReferralCampaignVersion).where(
                ReferralCampaignVersion.id == UUID(body["id"])
            )
        )
        assert campaign is not None
        audit = await session.scalar(
            select(AdminAuditEvent).where(
                AdminAuditEvent.action == "referral.campaign.created"
            )
        )
        assert audit is not None
        assert audit.event_metadata["reason"] == "运营配置春季邀请活动。"
        assert audit.event_metadata["campaign_key"] == "spring-2027"


async def test_support_cannot_create_referral_campaign(
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

    now = datetime.now(UTC)
    response = await client.post(
        "/api/v1/admin/referrals",
        headers=headers,
        json={
            "campaign_key": "support-must-not-write",
            "version": "v1",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=1)).isoformat(),
            "total_limit": 10,
            "reason": "客服不应配置活动。",
        },
    )

    assert response.status_code == 403


async def test_referral_campaign_version_is_unique_for_operator_retries(
    client: AsyncClient,
) -> None:
    headers = await _admin_headers(client)
    now = datetime.now(UTC)
    payload = {
        "campaign_key": "retry-safe-campaign",
        "version": "v1",
        "starts_at": now.isoformat(),
        "ends_at": (now + timedelta(days=30)).isoformat(),
        "total_limit": 10,
        "reason": "验证活动版本重复提交边界。",
    }

    first = await client.post("/api/v1/admin/referrals", headers=headers, json=payload)
    assert first.status_code == 201, first.text
    duplicate = await client.post("/api/v1/admin/referrals", headers=headers, json=payload)

    assert duplicate.status_code == 409, duplicate.text
    assert duplicate.json()["detail"] == "campaign version already exists"


async def test_ops_can_add_a_code_for_an_active_inviter(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    now = datetime.now(UTC)
    campaign_response = await client.post(
        "/api/v1/admin/referrals",
        headers=headers,
        json={
            "campaign_key": "code-campaign",
            "version": "v1",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=30)).isoformat(),
            "total_limit": 10,
            "reason": "创建活动后配置活动码。",
        },
    )
    assert campaign_response.status_code == 201, campaign_response.text

    async with database.sessions() as session:
        inviter = User()
        session.add(inviter)
        await session.commit()
        inviter_id = inviter.id

    response = await client.post(
        f"/api/v1/admin/referrals/{campaign_response.json()['id']}/codes",
        headers=headers,
        json={
            "code": "CODE-2027",
            "inviter_user_id": str(inviter_id),
            "reason": "为活动配置公开邀请码。",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["code"] == "CODE-2027"
    assert response.json()["inviter_user_id"] == str(inviter_id)


async def test_referral_code_rejects_unknown_inviter_deterministically(
    client: AsyncClient,
) -> None:
    headers = await _admin_headers(client)
    now = datetime.now(UTC)
    campaign_response = await client.post(
        "/api/v1/admin/referrals",
        headers=headers,
        json={
            "campaign_key": "invalid-inviter-campaign",
            "version": "v1",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=30)).isoformat(),
            "total_limit": 10,
            "reason": "准备验证邀请人拒绝规则。",
        },
    )
    assert campaign_response.status_code == 201, campaign_response.text

    response = await client.post(
        f"/api/v1/admin/referrals/{campaign_response.json()['id']}/codes",
        headers=headers,
        json={
            "code": "INVALID-INVITER",
            "inviter_user_id": str(uuid4()),
            "reason": "拒绝不存在的邀请人。",
        },
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "inviter user not found"


async def test_ops_can_configure_a_product_reward_slot(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    now = datetime.now(UTC)
    campaign_response = await client.post(
        "/api/v1/admin/referrals",
        headers=headers,
        json={
            "campaign_key": "slot-campaign",
            "version": "v1",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=30)).isoformat(),
            "total_limit": 10,
            "reason": "为活动配置商品奖励槽。",
        },
    )
    assert campaign_response.status_code == 201, campaign_response.text

    async with database.sessions() as session:
        family = ProductFamily(key="slot-product", label="邀请奖励商品")
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
        await session.commit()
        product_id = product.id

    response = await client.post(
        f"/api/v1/admin/referrals/{campaign_response.json()['id']}/reward-slots",
        headers=headers,
        json={
            "product_version_id": str(product_id),
            "slot": "inviter_reward",
            "total_limit": 5,
            "quantity": 2,
            "enabled": True,
            "reason": "绑定真实商品的邀请人奖励。",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["product_version_id"] == str(product_id)
    assert response.json()["quantity"] == 2

    async with database.sessions() as session:
        slot = await session.scalar(
            select(ReferralRewardSlot).where(
                ReferralRewardSlot.id == UUID(response.json()["id"])
            )
        )
        assert slot is not None


async def test_ops_can_change_campaign_state_through_the_state_machine(
    client: AsyncClient,
) -> None:
    headers = await _admin_headers(client)
    now = datetime.now(UTC)
    campaign_response = await client.post(
        "/api/v1/admin/referrals",
        headers=headers,
        json={
            "campaign_key": "state-campaign",
            "version": "v1",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=30)).isoformat(),
            "total_limit": 10,
            "reason": "创建活动后推进活动状态。",
        },
    )
    assert campaign_response.status_code == 201, campaign_response.text

    response = await client.post(
        f"/api/v1/admin/referrals/{campaign_response.json()['id']}/state",
        headers=headers,
        json={
            "state": "active",
            "reason": "运营确认活动窗口后启用。",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["state"] == "active"
