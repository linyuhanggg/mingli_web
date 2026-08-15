from datetime import UTC, datetime, timedelta

import pytest
from app.admin.models import AdminAuditEvent, StaffUser
from app.admin.passwords import hash_password
from app.commerce.models import EntitlementEventRecord
from app.identity.models import User
from app.referrals.models import (
    ReferralAttribution,
    ReferralCampaignVersion,
    ReferralCode,
    ReferralRewardReservation,
)
from app.referrals.policy import ReferralError, ReferralState
from app.referrals.service import ReferralService
from httpx import AsyncClient
from sqlalchemy import select


async def _login(client: AsyncClient, email: str = "ops@example.com") -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={
            "email": email,
            "password": "correct-horse",
        },
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def _make_committed_attribution(database):  # type: ignore[no-untyped-def]
    now = datetime.now(UTC)
    async with database.sessions() as session:
        inviter = User()
        referred = User()
        session.add_all([inviter, referred])
        await session.flush()
        campaign = ReferralCampaignVersion(
            campaign_key="appeal-2026",
            version="v1",
            state="active",
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=30),
            total_limit=10,
            per_inviter_limit=5,
            reward_quantity=2,
            reward_window_seconds=90 * 86400,
        )
        session.add(campaign)
        await session.flush()
        code = ReferralCode(
            campaign_version_id=campaign.id,
            code="APPEAL-ABC",
            inviter_user_id=inviter.id,
            status="active",
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
            quantity=2,
            status="committed",
            reserved_at=now,
            committed_at=now,
        )
        session.add(reservation)
        await session.flush()
        entitlement_id = f"referral:{reservation.id}"
        session.add_all(
            [
                EntitlementEventRecord(
                    entitlement_id=entitlement_id,
                    owner_user_id=inviter.id,
                    kind="GRANT",
                    quantity=2,
                    source_type="referral",
                    source_ref=str(reservation.id),
                    created_at=now,
                ),
                EntitlementEventRecord(
                    entitlement_id=entitlement_id,
                    owner_user_id=inviter.id,
                    kind="RESERVE",
                    quantity=2,
                    source_type="fulfillment",
                    source_ref=f"{reservation.id}:reserve",
                    created_at=now + timedelta(seconds=1),
                ),
                EntitlementEventRecord(
                    entitlement_id=entitlement_id,
                    owner_user_id=inviter.id,
                    kind="CONSUME",
                    quantity=2,
                    source_type="fulfillment",
                    source_ref=f"{reservation.id}:consume",
                    created_at=now + timedelta(seconds=2),
                ),
            ]
        )
        await session.commit()
        return attribution.id, reservation.id, inviter.id, referred.id


async def _add_staff(database, *, email: str) -> None:
    async with database.sessions() as session:
        session.add(
            StaffUser(
                email=email,
                password_hash=hash_password("correct-horse"),
                display_name=email.split("@", 1)[0],
                role="finance",
                status="active",
            )
        )
        await session.commit()


async def test_admin_appeal_records_risk_and_requires_two_distinct_correction_approvals(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    attribution_id, reservation_id, inviter_id, _referred_id = (
        await _make_committed_attribution(database)
    )
    first_headers = await _login(client)

    created = await client.post(
        "/api/v1/admin/appeals",
        headers=first_headers,
        json={
            "attribution_id": str(attribution_id),
            "reason": "客户提供了支付与归因证据，申请复核。",
        },
    )
    assert created.status_code == 201, created.text
    appeal_id = created.json()["id"]
    assert created.json()["status"] == "submitted"

    risk = await client.post(
        f"/api/v1/admin/appeals/{appeal_id}/risk-signals",
        headers=first_headers,
        json={
            "signal_type": "device_overlap",
            "severity": "medium",
            "reason": "设备信号重合，仅作为风险提示。",
        },
    )
    assert risk.status_code == 201, risk.text
    assert risk.json()["signal_type"] == "device_overlap"

    first = await client.post(
        f"/api/v1/admin/appeals/{appeal_id}/decision",
        headers=first_headers,
        json={
            "outcome": "correction",
            "reason": "需要纠正已确认的技术错误。",
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "correction_pending"
    assert first.json()["approval_count"] == 1

    duplicate = await client.post(
        f"/api/v1/admin/appeals/{appeal_id}/decision",
        headers=first_headers,
        json={
            "outcome": "correction",
            "reason": "重复审批不应通过。",
        },
    )
    assert duplicate.status_code == 409, duplicate.text

    await _add_staff(database, email="finance@example.com")
    second_headers = await _login(client, email="finance@example.com")
    second = await client.post(
        f"/api/v1/admin/appeals/{appeal_id}/decision",
        headers=second_headers,
        json={
            "outcome": "correction",
            "reason": "第二位独立审核员确认纠正。",
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "corrected"
    assert second.json()["approval_count"] == 2
    assert second.json()["correction_event_kind"] == "REVERSE"
    assert set(second.json()["participation_restriction_user_ids"]) == {
        str(inviter_id),
        str(_referred_id),
    }

    async with database.sessions() as session:
        events = list(
            await session.scalars(
                select(EntitlementEventRecord).where(
                    EntitlementEventRecord.entitlement_id == f"referral:{reservation_id}"
                )
            )
        )
        assert [event.kind for event in events].count("REVERSE") == 1
        audits = list(
            await session.scalars(
                select(AdminAuditEvent).where(
                    AdminAuditEvent.action.in_(
                        {"referral.appeal.created", "referral.appeal.corrected"}
                    )
                )
            )
        )
    assert {event.action for event in audits} == {
            "referral.appeal.created",
            "referral.appeal.corrected",
        }

    async with database.sessions() as session:
        new_inviter = User()
        session.add(new_inviter)
        await session.flush()
        service = ReferralService(session)
        campaign = await service.create_campaign(
            campaign_key="future-participation",
            version="v1",
            starts_at=datetime.now(UTC) - timedelta(minutes=1),
            ends_at=datetime.now(UTC) + timedelta(days=30),
            total_limit=10,
        )
        await service.set_campaign_state(campaign.id, ReferralState.ACTIVE)
        code = await service.create_code(
            campaign_id=campaign.id,
            code="FUTURE-1",
            inviter_user_id=new_inviter.id,
        )
        await service.record_temporary_attribution(
            campaign_id=campaign.id,
            code=code.code,
            visitor_key="future-participation-visitor",
        )
        with pytest.raises(ReferralError, match="participation is restricted"):
            await service.lock_attribution(
                campaign_id=campaign.id,
                code=code.code,
                visitor_key="future-participation-visitor",
                referred_user_id=inviter_id,
            )


async def test_admin_appeals_read_and_submission_permissions_are_explicit(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    attribution_id, _reservation_id, _inviter_id, _referred_id = (
        await _make_committed_attribution(database)
    )
    headers = await _login(client)

    listed = await client.get("/api/v1/admin/appeals", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["appeals"] == []

    created = await client.post(
        "/api/v1/admin/appeals",
        headers=headers,
        json={"attribution_id": str(attribution_id), "reason": "请复核。"},
    )
    assert created.status_code == 201, created.text

    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    support_list = await client.get("/api/v1/admin/appeals", headers=headers)
    assert support_list.status_code == 200, support_list.text
    assert len(support_list.json()["appeals"]) == 1

    forbidden = await client.post(
        f"/api/v1/admin/appeals/{created.json()['id']}/risk-signals",
        headers=headers,
        json={
            "signal_type": "ip_overlap",
            "severity": "low",
            "reason": "客服不能录入风险结论。",
        },
    )
    assert forbidden.status_code == 403, forbidden.text
