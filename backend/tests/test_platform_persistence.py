from datetime import UTC, datetime, timedelta

import pytest
from app.admin.models import StaffUser
from app.content.models import ContentRevisionRecord
from app.identity.models import User
from app.referrals.models import (
    ReferralAttribution,
    ReferralCampaignVersion,
    ReferralCode,
    ReferralRewardReservation,
    ReferralTemporaryAttribution,
)
from sqlalchemy.exc import IntegrityError


@pytest.mark.asyncio
async def test_referral_facts_persist_with_global_referred_user_lock(database) -> None:  # type: ignore[no-untyped-def]
    now = datetime(2026, 8, 13, tzinfo=UTC)
    inviter = User()
    referred = User()
    campaign = ReferralCampaignVersion(
        campaign_key="spring",
        version="v1",
        state="active",
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1),
    )
    async with database.sessions() as session:
        session.add_all([inviter, referred, campaign])
        await session.flush()
        code = ReferralCode(
            campaign_version_id=campaign.id,
            code="SPRING-1",
            inviter_user_id=inviter.id,
        )
        session.add(code)
        await session.flush()
        session.add(
            ReferralTemporaryAttribution(
                campaign_version_id=campaign.id,
                code_id=code.id,
                visitor_key_hash="a" * 64,
                inviter_user_id=inviter.id,
                expires_at=now + timedelta(days=30),
                last_seen_at=now,
            )
        )
        attribution = ReferralAttribution(
            campaign_version_id=campaign.id,
            code_id=code.id,
            referred_user_id=referred.id,
            inviter_user_id=inviter.id,
            locked_at=now,
        )
        session.add(attribution)
        await session.flush()
        session.add(
            ReferralRewardReservation(
                campaign_version_id=campaign.id,
                attribution_id=attribution.id,
                referred_user_id=referred.id,
                inviter_user_id=inviter.id,
                quantity=1,
                reserved_at=now,
            )
        )
        await session.commit()

        session.add(
            ReferralAttribution(
                campaign_version_id=campaign.id,
                code_id=code.id,
                referred_user_id=referred.id,
                inviter_user_id=inviter.id,
                locked_at=now,
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()


@pytest.mark.asyncio
async def test_content_revision_key_locale_and_revision_are_unique(database) -> None:  # type: ignore[no-untyped-def]
    staff = StaffUser(
        email="editor@example.com",
        password_hash="test-only",
        display_name="编辑",
        role="ops",
    )
    async with database.sessions() as session:
        session.add(staff)
        await session.flush()
        session.add(
            ContentRevisionRecord(
                content_key="home.hero",
                locale="zh-CN",
                revision=1,
                state="published",
                body="第一版",
                author_ref="staff-1",
                author_staff_user_id=staff.id,
            )
        )
        await session.commit()
        session.add(
            ContentRevisionRecord(
                content_key="home.hero",
                locale="zh-CN",
                revision=1,
                state="draft",
                body="重复版本",
                author_ref="staff-1",
                author_staff_user_id=staff.id,
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
