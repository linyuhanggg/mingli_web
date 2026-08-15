"""Public invite projection and guest-session attribution capture."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Path, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import database_session, mark_private, require_guest_csrf
from app.api.errors import ApiProblem
from app.identity.cookies import GUEST_COOKIE, SESSION_COOKIE
from app.identity.models import DeviceSession, GuestSession
from app.identity.repository import IdentityRepository
from app.identity.security import hash_token
from app.referrals.models import (
    ReferralCampaignVersion,
    ReferralCode,
    ReferralRewardReservation,
    ReferralTemporaryAttribution,
)
from app.referrals.policy import ReferralError
from app.referrals.schemas import (
    ReferralAttributionCaptureResponse,
    ReferralPublicResponse,
)
from app.referrals.service import ReferralService, _visitor_hash

router = APIRouter(prefix="/referrals", tags=["Referrals"])


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


async def _public_code(
    session: AsyncSession,
    code: str,
) -> tuple[ReferralCode, ReferralCampaignVersion]:
    found = await session.execute(
        select(ReferralCode, ReferralCampaignVersion)
        .join(
            ReferralCampaignVersion,
            ReferralCampaignVersion.id == ReferralCode.campaign_version_id,
        )
        .where(ReferralCode.code == code, ReferralCode.status == "active")
    )
    row = found.first()
    if row is None:
        raise ApiProblem(status=404, title="Invitation code not found")
    return row[0], row[1]


def _public_status(
    campaign: ReferralCampaignVersion,
    *,
    reserved_count: int,
    now: datetime,
) -> str:
    if campaign.state == "ended" or (
        campaign.ends_at is not None and now >= _as_utc(campaign.ends_at)
    ):
        return "ended"
    if campaign.state == "paused":
        return "paused"
    if campaign.state in {"draft", "scheduled"} or now < _as_utc(campaign.starts_at):
        return "planned"
    if campaign.total_limit is not None and reserved_count >= campaign.total_limit:
        return "full"
    return "active"


async def _active_guest(
    session: AsyncSession,
    token: str | None,
    now: datetime,
) -> GuestSession | None:
    if not token:
        return None
    return await IdentityRepository(session).get_active_guest_session(
        hash_token(token), now
    )


async def _active_device(
    session: AsyncSession,
    token: str | None,
    now: datetime,
) -> DeviceSession | None:
    if not token:
        return None
    return await IdentityRepository(session).get_active_device_session(
        hash_token(token), now
    )


@router.get(
    "/{code}",
    operation_id="getReferralInvite",
    response_model=ReferralPublicResponse,
)
async def get_referral_invite(
    request: Request,
    response: Response,
    code: str = Path(min_length=1, max_length=120),
    session: AsyncSession = Depends(database_session),
) -> ReferralPublicResponse:
    referral_code, campaign = await _public_code(session, code)
    now = datetime.now(UTC)
    reserved_count = await session.scalar(
        select(func.count(ReferralRewardReservation.id)).where(
            ReferralRewardReservation.campaign_version_id == campaign.id,
            ReferralRewardReservation.status.in_(["reserved", "committed"]),
        )
    )
    guest = await _active_guest(session, request.cookies.get(GUEST_COOKIE), now)
    device = await _active_device(session, request.cookies.get(SESSION_COOKIE), now)
    attribution_recorded = False
    if guest is not None:
        attribution_recorded = bool(
            await session.scalar(
                select(ReferralTemporaryAttribution.id).where(
                    ReferralTemporaryAttribution.campaign_version_id == campaign.id,
                    ReferralTemporaryAttribution.code_id == referral_code.id,
                    ReferralTemporaryAttribution.visitor_key_hash
                    == _visitor_hash(str(guest.id)),
                    ReferralTemporaryAttribution.expires_at > now,
                )
            )
        )
    mark_private(response)
    return ReferralPublicResponse(
        code=referral_code.code,
        campaign_key=campaign.campaign_key,
        version=campaign.version,
        status=_public_status(
            campaign,
            reserved_count=int(reserved_count or 0),
            now=now,
        ),
        starts_at=campaign.starts_at,
        ends_at=campaign.ends_at,
        per_inviter_limit=campaign.per_inviter_limit,
        attribution_recorded=attribution_recorded,
        self_invite=False if device is None else device.user_id == referral_code.inviter_user_id,
    )


@router.post(
    "/{code}/attribution",
    operation_id="recordReferralAttribution",
    response_model=ReferralAttributionCaptureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_referral_attribution(
    response: Response,
    code: str = Path(min_length=1, max_length=120),
    session: AsyncSession = Depends(database_session),
    guest_session: GuestSession = Depends(require_guest_csrf),
) -> ReferralAttributionCaptureResponse:
    referral_code, campaign = await _public_code(session, code)
    visitor_hash = _visitor_hash(str(guest_session.id))
    existing = await session.scalar(
        select(ReferralTemporaryAttribution.id).where(
            ReferralTemporaryAttribution.campaign_version_id == campaign.id,
            ReferralTemporaryAttribution.visitor_key_hash == visitor_hash,
        )
    )
    try:
        await ReferralService(session).record_temporary_attribution(
            campaign_id=campaign.id,
            code=referral_code.code,
            visitor_key=str(guest_session.id),
        )
    except ReferralError as error:
        raise ApiProblem(
            status=409,
            title="Invitation is not available",
            detail=str(error),
        ) from error
    await session.commit()
    mark_private(response)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
    return ReferralAttributionCaptureResponse(status="recorded")


@router.delete(
    "/{code}/attribution",
    operation_id="clearReferralAttribution",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_referral_attribution(
    response: Response,
    code: str = Path(min_length=1, max_length=120),
    session: AsyncSession = Depends(database_session),
    guest_session: GuestSession = Depends(require_guest_csrf),
) -> Response:
    await _public_code(session, code)
    await ReferralService(session).clear_temporary_attributions(
        visitor_key=str(guest_session.id)
    )
    await session.commit()
    mark_private(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
