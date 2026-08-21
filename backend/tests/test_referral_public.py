from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from app.identity.models import User
from app.referrals.models import (
    ReferralAttribution,
    ReferralCampaignVersion,
    ReferralCode,
    ReferralTemporaryAttribution,
)
from app.referrals.policy import ReferralError, ReferralState
from app.referrals.service import ReferralService
from httpx import AsyncClient
from sqlalchemy import func, select


async def _active_campaign(database, *, code: str = "PUBLIC-1"):
    now = datetime.now(UTC).replace(microsecond=0)
    async with database.sessions() as session:
        inviter = User()
        session.add(inviter)
        await session.flush()
        service = ReferralService(session)
        campaign = await service.create_campaign(
            campaign_key="public-invite",
            version="v1",
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=1),
            total_limit=10,
        )
        await service.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        referral_code = await service.create_code(
            campaign_id=campaign.id,
            code=code,
            inviter_user_id=inviter.id,
        )
        await session.commit()
        return campaign.id, referral_code.code, inviter.id


async def test_referral_service_locks_last_valid_invitation_and_can_clear(database) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 14, 6, 0, tzinfo=UTC)
    async with database.sessions() as session:
        inviter = User()
        first_inviter = User()
        referred = User()
        session.add_all([inviter, first_inviter, referred])
        await session.flush()
        service = ReferralService(session)
        first_campaign = await service.create_campaign(
            campaign_key="first-invite",
            version="v1",
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=1),
            total_limit=10,
        )
        second_campaign = await service.create_campaign(
            campaign_key="second-invite",
            version="v1",
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=1),
            total_limit=10,
        )
        await service.set_campaign_state(first_campaign.id, ReferralState.ACTIVE)
        await service.set_campaign_state(second_campaign.id, ReferralState.ACTIVE)
        first_code = await service.create_code(
            campaign_id=first_campaign.id,
            code="FIRST-1",
            inviter_user_id=first_inviter.id,
        )
        second_code = await service.create_code(
            campaign_id=second_campaign.id,
            code="SECOND-1",
            inviter_user_id=inviter.id,
        )
        visitor_key = "guest-session-id"
        await service.record_temporary_attribution(
            campaign_id=first_campaign.id,
            code=first_code.code,
            visitor_key=visitor_key,
            now=now,
        )
        await service.record_temporary_attribution(
            campaign_id=second_campaign.id,
            code=second_code.code,
            visitor_key=visitor_key,
            now=now + timedelta(seconds=1),
        )

        attribution = await service.lock_latest_attribution(
            visitor_key=visitor_key,
            referred_user_id=referred.id,
            now=now + timedelta(seconds=2),
        )

        assert attribution is not None
        assert attribution.code_id == second_code.id
        assert await session.scalar(
            select(func.count(ReferralTemporaryAttribution.id)).where(
                ReferralTemporaryAttribution.visitor_key_hash.is_not(None)
            )
        ) == 2

        await service.clear_temporary_attributions(visitor_key=visitor_key)
        assert await session.scalar(
            select(func.count(ReferralTemporaryAttribution.id)).where(
                ReferralTemporaryAttribution.visitor_key_hash.is_not(None)
            )
        ) == 0


async def test_referral_service_does_not_lock_self_invitation(database) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 14, 6, 0, tzinfo=UTC)
    async with database.sessions() as session:
        inviter = User()
        session.add(inviter)
        await session.flush()
        service = ReferralService(session)
        campaign = await service.create_campaign(
            campaign_key="self-invite",
            version="v1",
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=1),
            total_limit=10,
        )
        await service.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        code = await service.create_code(
            campaign_id=campaign.id,
            code="SELF-1",
            inviter_user_id=inviter.id,
        )
        await service.record_temporary_attribution(
            campaign_id=campaign.id,
            code=code.code,
            visitor_key="self-visitor",
            now=now,
        )

        with pytest.raises(ReferralError, match="self referral"):
            await service.lock_latest_attribution(
                visitor_key="self-visitor",
                referred_user_id=inviter.id,
                now=now,
            )


async def test_public_referral_endpoint_records_replaces_and_clears_guest_attribution(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    _campaign_id, code, inviter_id = await _active_campaign(database)

    public = await client.get(f"/api/v1/referrals/{code}")
    assert public.status_code == 200, public.text
    assert public.headers["cache-control"] == "private, no-store, max-age=0"
    assert public.json()["status"] == "active"
    assert public.json()["attribution_recorded"] is False
    assert str(inviter_id) not in public.text

    guest = await client.post("/api/v1/guest-sessions")
    assert guest.status_code == 201, guest.text
    csrf = guest.json()["csrf_token"]
    recorded = await client.post(
        f"/api/v1/referrals/{code}/attribution",
        headers={"X-CSRF-Token": csrf},
    )
    assert recorded.status_code == 201, recorded.text
    assert recorded.json() == {"status": "recorded"}

    replayed = await client.post(
        f"/api/v1/referrals/{code}/attribution",
        headers={"X-CSRF-Token": csrf},
    )
    assert replayed.status_code == 200, replayed.text
    async with database.sessions() as session:
        assert await session.scalar(select(func.count(ReferralTemporaryAttribution.id))) == 1

    refreshed = await client.get(f"/api/v1/referrals/{code}")
    assert refreshed.json()["attribution_recorded"] is True

    cleared = await client.delete(
        f"/api/v1/referrals/{code}/attribution",
        headers={"X-CSRF-Token": csrf},
    )
    assert cleared.status_code == 204, cleared.text
    cleared_again = await client.delete(
        f"/api/v1/referrals/{code}/attribution",
        headers={"X-CSRF-Token": csrf},
    )
    assert cleared_again.status_code == 204, cleared_again.text
    async with database.sessions() as session:
        assert await session.scalar(select(func.count(ReferralTemporaryAttribution.id))) == 0


async def test_public_referral_endpoint_rejects_unknown_or_inactive_codes(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    unknown = await client.get("/api/v1/referrals/UNKNOWN")
    assert unknown.status_code == 404

    now = datetime.now(UTC).replace(microsecond=0)
    async with database.sessions() as session:
        inviter = User()
        campaign = ReferralCampaignVersion(
            campaign_key="paused-invite",
            version="v1",
            state="paused",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=1),
            total_limit=10,
        )
        session.add_all([inviter, campaign])
        await session.flush()
        session.add(
            ReferralCode(
                campaign_version_id=campaign.id,
                code="PAUSED-1",
                inviter_user_id=inviter.id,
            )
        )
        await session.commit()

    paused = await client.get("/api/v1/referrals/PAUSED-1")
    assert paused.status_code == 200, paused.text
    assert paused.json()["status"] == "paused"
    guest = await client.post("/api/v1/guest-sessions")
    recorded = await client.post(
        "/api/v1/referrals/PAUSED-1/attribution",
        headers={"X-CSRF-Token": guest.json()["csrf_token"]},
    )
    assert recorded.status_code == 409


async def test_new_otp_user_locks_last_invitation_in_same_guest_session(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    _campaign_id, code, _inviter_id = await _active_campaign(database, code="REGISTER-1")
    guest = await client.post("/api/v1/guest-sessions")
    csrf = guest.json()["csrf_token"]
    captured = await client.post(
        f"/api/v1/referrals/{code}/attribution",
        headers={"X-CSRF-Token": csrf},
    )
    assert captured.status_code == 201, captured.text
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers={"X-CSRF-Token": csrf},
        json={"channel": "email", "destination": "referral-new@example.com"},
    )
    assert requested.status_code == 202, requested.text
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers={"X-CSRF-Token": csrf},
        json={"challenge_id": requested.json()["challenge_id"], "code": "246810"},
    )
    assert verified.status_code == 200, verified.text
    user_id = UUID(verified.json()["user_id"])

    async with database.sessions() as session:
        attribution = await session.scalar(
            select(ReferralAttribution).where(
                ReferralAttribution.referred_user_id == user_id,
            )
        )
        assert attribution is not None
        assert attribution.status == "locked"


async def test_existing_account_does_not_lock_a_new_invitation_and_self_is_visible(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    guest = await client.post("/api/v1/guest-sessions")
    csrf = guest.json()["csrf_token"]
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers={"X-CSRF-Token": csrf},
        json={"channel": "email", "destination": "existing-referral@example.com"},
    )
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers={"X-CSRF-Token": csrf},
        json={"challenge_id": requested.json()["challenge_id"], "code": "246810"},
    )
    assert verified.status_code == 200, verified.text
    owner_id = UUID(verified.json()["user_id"])
    from app.identity.policy import CURRENT_POLICY_VERSION

    for policy_key in ("privacy", "terms"):
        accepted = await client.post(
            "/api/v1/auth/consents",
            headers={"X-CSRF-Token": verified.json()["csrf_token"]},
            json={
                "policy_key": policy_key,
                "policy_version": CURRENT_POLICY_VERSION,
                "context": "reaccept",
            },
        )
        assert accepted.status_code == 201, accepted.text

    now = datetime.now(UTC).replace(microsecond=0)
    async with database.sessions() as session:
        service = ReferralService(session)
        campaign = await service.create_campaign(
            campaign_key="existing-account-invite",
            version="v1",
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=1),
            total_limit=10,
        )
        await service.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        code = await service.create_code(
            campaign_id=campaign.id,
            code="EXISTING-1",
            inviter_user_id=owner_id,
        )
        await session.commit()

    new_guest = await client.post("/api/v1/guest-sessions")
    new_csrf = new_guest.json()["csrf_token"]
    captured = await client.post(
        f"/api/v1/referrals/{code.code}/attribution",
        headers={"X-CSRF-Token": new_csrf},
    )
    assert captured.status_code == 201, captured.text
    self_view = await client.get(f"/api/v1/referrals/{code.code}")
    assert self_view.json()["self_invite"] is True

    requested_again = await client.post(
        "/api/v1/auth/otp/request",
        headers={"X-CSRF-Token": new_csrf},
        json={"channel": "email", "destination": "existing-referral@example.com"},
    )
    verified_again = await client.post(
        "/api/v1/auth/otp/verify",
        headers={"X-CSRF-Token": new_csrf},
        json={
            "challenge_id": requested_again.json()["challenge_id"],
            "code": "246810",
        },
    )
    assert verified_again.status_code == 200, verified_again.text
    async with database.sessions() as session:
        assert await session.scalar(select(ReferralAttribution.id)) is None
