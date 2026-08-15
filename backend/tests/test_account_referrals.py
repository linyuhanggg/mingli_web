from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from httpx import AsyncClient


async def _create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def _login(client: AsyncClient, guest_headers: dict[str, str]) -> dict[str, str]:
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=guest_headers,
        json={"channel": "email", "destination": "referrals@example.com"},
    )
    assert requested.status_code == 202, requested.text
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers=guest_headers,
        json={"challenge_id": requested.json()["challenge_id"], "code": "246810"},
    )
    assert verified.status_code == 200, verified.text
    return {"X-CSRF-Token": verified.json()["csrf_token"]}


async def test_account_referrals_return_only_current_user_progress(
    client: AsyncClient,
    database: Any,
) -> None:
    guest_headers = await _create_guest(client)
    await _login(client, guest_headers)
    account = await client.get("/api/v1/account")
    assert account.status_code == 200, account.text
    owner_id = UUID(account.json()["user_id"])

    from app.identity.models import User
    from app.referrals.models import (
        ReferralAttribution,
        ReferralCampaignVersion,
        ReferralCode,
        ReferralRewardReservation,
    )

    now = datetime(2026, 8, 14, 5, 0, tzinfo=UTC)
    async with database.sessions() as session:
        referred = User()
        other_inviter = User()
        session.add_all([referred, other_inviter])
        await session.flush()

        campaign = ReferralCampaignVersion(
            campaign_key="account-view",
            version="v1",
            state="active",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=7),
            total_limit=100,
            per_inviter_limit=10,
        )
        other_campaign = ReferralCampaignVersion(
            campaign_key="other-view",
            version="v1",
            state="active",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=7),
            total_limit=100,
            per_inviter_limit=10,
        )
        session.add_all([campaign, other_campaign])
        await session.flush()

        code = ReferralCode(
            campaign_version_id=campaign.id,
            code="MY-CODE",
            inviter_user_id=owner_id,
        )
        other_code = ReferralCode(
            campaign_version_id=other_campaign.id,
            code="OTHER-CODE",
            inviter_user_id=other_inviter.id,
        )
        session.add_all([code, other_code])
        await session.flush()
        attribution = ReferralAttribution(
            campaign_version_id=campaign.id,
            code_id=code.id,
            referred_user_id=referred.id,
            inviter_user_id=owner_id,
            locked_at=now,
            status="locked",
        )
        session.add(attribution)
        await session.flush()
        reward = ReferralRewardReservation(
            campaign_version_id=campaign.id,
            attribution_id=attribution.id,
            referred_user_id=referred.id,
            inviter_user_id=owner_id,
            quantity=3,
            status="committed",
            reserved_at=now,
            committed_at=now + timedelta(hours=1),
        )
        session.add(reward)
        await session.commit()

    listed = await client.get("/api/v1/account/referrals")
    assert listed.status_code == 200, listed.text
    assert listed.headers["cache-control"] == "private, no-store, max-age=0"
    body = listed.json()
    assert len(body["campaigns"]) == 1
    item = body["campaigns"][0]
    assert item["campaign_key"] == "account-view"
    assert item["state"] == "active"
    assert item["codes"] == ["MY-CODE"]
    assert item["invited_count"] == 1
    assert item["my_attribution_stage"] is None
    assert item["rewards"][0]["status"] == "committed"
    assert set(item["rewards"][0]) == {"status", "occurred_at"}
    assert "OTHER-CODE" not in listed.text
    assert str(owner_id) not in listed.text
    assert str(referred.id) not in listed.text
    assert "quantity" not in listed.text
    assert "payment_attempt_id" not in listed.text


async def test_account_referrals_require_a_verified_device(client: AsyncClient) -> None:
    response = await client.get("/api/v1/account/referrals")
    assert response.status_code == 401
