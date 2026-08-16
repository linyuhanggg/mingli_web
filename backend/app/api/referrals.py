"""Private account-facing referral progress reads."""

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import database_session, mark_private, require_device_session
from app.identity.models import DeviceSession
from app.referrals.models import (
    ReferralAttribution,
    ReferralCampaignVersion,
    ReferralCode,
    ReferralRewardReservation,
)
from app.referrals.schemas import (
    AccountReferralCampaignResponse,
    AccountReferralRewardResponse,
    AccountReferralsResponse,
)

router = APIRouter(tags=["Identity"])


@router.get(
    "/account/referrals",
    operation_id="listAccountReferrals",
    response_model=AccountReferralsResponse,
)
async def list_account_referrals(
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
) -> AccountReferralsResponse:
    user_id = device_session.user_id
    codes = list(
        await session.scalars(
            select(ReferralCode)
            .where(ReferralCode.inviter_user_id == user_id)
            .order_by(desc(ReferralCode.created_at), desc(ReferralCode.id))
        )
    )
    attributions = list(
        await session.scalars(
            select(ReferralAttribution)
            .where(
                or_(
                    ReferralAttribution.inviter_user_id == user_id,
                    ReferralAttribution.referred_user_id == user_id,
                )
            )
            .order_by(desc(ReferralAttribution.locked_at), desc(ReferralAttribution.id))
        )
    )
    rewards = list(
        await session.scalars(
            select(ReferralRewardReservation)
            .where(
                or_(
                    ReferralRewardReservation.inviter_user_id == user_id,
                    ReferralRewardReservation.referred_user_id == user_id,
                )
            )
            .order_by(
                desc(ReferralRewardReservation.reserved_at),
                desc(ReferralRewardReservation.id),
            )
        )
    )

    campaign_ids: set[UUID] = {
        item.campaign_version_id for item in codes
    }
    campaign_ids.update(item.campaign_version_id for item in attributions)
    campaign_ids.update(item.campaign_version_id for item in rewards)

    campaigns = []
    if campaign_ids:
        campaigns = list(
            await session.scalars(
                select(ReferralCampaignVersion)
                .where(ReferralCampaignVersion.id.in_(campaign_ids))
                .order_by(
                    desc(ReferralCampaignVersion.created_at),
                    desc(ReferralCampaignVersion.id),
                )
            )
        )

    codes_by_campaign: defaultdict[UUID, list[str]] = defaultdict(list)
    for code in codes:
        if code.status == "active":
            codes_by_campaign[code.campaign_version_id].append(code.code)

    invited_by_campaign: defaultdict[UUID, int] = defaultdict(int)
    attribution_by_campaign: dict[UUID, str] = {}
    for attribution in attributions:
        if attribution.inviter_user_id == user_id:
            invited_by_campaign[attribution.campaign_version_id] += 1
        if attribution.referred_user_id == user_id:
            attribution_by_campaign.setdefault(
                attribution.campaign_version_id,
                attribution.status,
            )

    rewards_by_campaign: defaultdict[UUID, list[AccountReferralRewardResponse]] = defaultdict(
        list
    )
    for reward in rewards:
        rewards_by_campaign[reward.campaign_version_id].append(
            AccountReferralRewardResponse(
                status=reward.status,
                occurred_at=reward.committed_at or reward.reserved_at,
            )
        )

    mark_private(response)
    return AccountReferralsResponse(
        campaigns=[
            AccountReferralCampaignResponse(
                campaign_key=campaign.campaign_key,
                version=campaign.version,
                state=campaign.state,
                starts_at=campaign.starts_at,
                ends_at=campaign.ends_at,
                per_inviter_limit=campaign.per_inviter_limit,
                codes=codes_by_campaign[campaign.id],
                invited_count=invited_by_campaign[campaign.id],
                my_attribution_stage=attribution_by_campaign.get(campaign.id),
                rewards=rewards_by_campaign[campaign.id],
            )
            for campaign in campaigns
        ]
    )
