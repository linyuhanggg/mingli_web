"""Redacted Admin reads for referral campaign and reward facts."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.admin.schemas import (
    AdminReferralAttributionResponse,
    AdminReferralCampaignCreateRequest,
    AdminReferralCampaignResponse,
    AdminReferralCampaignStateRequest,
    AdminReferralCodeCreateRequest,
    AdminReferralCodeResponse,
    AdminReferralResponse,
    AdminReferralRewardResponse,
    AdminReferralRewardSlotCreateRequest,
    AdminReferralRewardSlotResponse,
    AdminReferralsResponse,
)
from app.api.admin import require_staff_csrf, require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.referrals.models import (
    ReferralAttribution,
    ReferralCampaignVersion,
    ReferralCode,
    ReferralRewardReservation,
    ReferralRewardSlot,
    ReferralTemporaryAttribution,
)
from app.referrals.policy import ReferralError, ReferralState
from app.referrals.service import ReferralService

router = APIRouter(prefix="/admin/referrals", tags=["Admin Referrals"])


def _require_referral_reader(staff: StaffUser) -> None:
    if staff.role not in {"ops", "superadmin"}:
        raise ApiProblem(status=403, title="Referral reader permission required")


def _require_referral_operator(staff: StaffUser) -> None:
    if staff.role not in {"ops", "superadmin"}:
        raise ApiProblem(status=403, title="Referral operator permission required")


def _reason(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ApiProblem(status=400, title="Referral operation reason is required")
    return normalized


def _referral_problem(error: ReferralError) -> ApiProblem:
    detail = str(error)
    not_found = detail.endswith("not found")
    return ApiProblem(
        status=404 if not_found else 409,
        title="Referral object not found" if not_found else "Invalid referral transition",
        detail=detail,
    )


def _code_response(code: ReferralCode) -> AdminReferralCodeResponse:
    return AdminReferralCodeResponse(
        id=code.id,
        campaign_version_id=code.campaign_version_id,
        code=code.code,
        inviter_user_id=code.inviter_user_id,
        status=code.status,
        created_at=code.created_at,
    )


def _reward_slot_response(slot: ReferralRewardSlot) -> AdminReferralRewardSlotResponse:
    return AdminReferralRewardSlotResponse(
        id=slot.id,
        campaign_version_id=slot.campaign_version_id,
        product_version_id=slot.product_version_id,
        slot_key=slot.slot_key,
        enabled=slot.enabled,
        total_limit=slot.total_limit,
        quantity=slot.quantity,
        created_at=slot.created_at,
    )


async def _campaign_response(
    session: AsyncSession,
    campaign: ReferralCampaignVersion,
) -> AdminReferralCampaignResponse:
    code_count = await session.scalar(
        select(func.count(ReferralCode.id)).where(
            ReferralCode.campaign_version_id == campaign.id
        )
    )
    attribution_count = await session.scalar(
        select(func.count(ReferralAttribution.id)).where(
            ReferralAttribution.campaign_version_id == campaign.id
        )
    )
    temporary_attribution_count = await session.scalar(
        select(func.count(ReferralTemporaryAttribution.id)).where(
            ReferralTemporaryAttribution.campaign_version_id == campaign.id
        )
    )
    reservation_count = await session.scalar(
        select(func.count(ReferralRewardReservation.id)).where(
            ReferralRewardReservation.campaign_version_id == campaign.id
        )
    )
    return AdminReferralCampaignResponse(
        id=campaign.id,
        campaign_key=campaign.campaign_key,
        version=campaign.version,
        state=campaign.state,
        starts_at=campaign.starts_at,
        ends_at=campaign.ends_at,
        total_limit=campaign.total_limit,
        per_inviter_limit=campaign.per_inviter_limit,
        reward_quantity=campaign.reward_quantity,
        reward_window_seconds=campaign.reward_window_seconds,
        code_count=int(code_count or 0),
        temporary_attribution_count=int(temporary_attribution_count or 0),
        attribution_count=int(attribution_count or 0),
        reservation_count=int(reservation_count or 0),
        created_at=campaign.created_at,
    )


@router.post(
    "",
    operation_id="createAdminReferralCampaign",
    response_model=AdminReferralCampaignResponse,
    status_code=201,
)
async def create_admin_referral_campaign(
    payload: AdminReferralCampaignCreateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminReferralCampaignResponse:
    staff_session, staff = principal
    _require_referral_operator(staff)
    try:
        campaign = await ReferralService(session).create_campaign(
            campaign_key=payload.campaign_key,
            version=payload.version,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            total_limit=payload.total_limit,
            per_inviter_limit=payload.per_inviter_limit,
            reward_quantity=payload.reward_quantity,
            reward_window_seconds=payload.reward_window_seconds,
        )
    except ReferralError as error:
        raise _referral_problem(error) from error
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action="referral.campaign.created",
            event_metadata={
                "reason": _reason(payload.reason),
                "campaign_key": campaign.campaign_key,
                "version": campaign.version,
                "target_id": str(campaign.id),
            },
        )
    )
    await session.commit()
    await session.refresh(campaign)
    mark_private(response)
    return await _campaign_response(session, campaign)


@router.post(
    "/{campaign_id}/codes",
    operation_id="createAdminReferralCode",
    response_model=AdminReferralCodeResponse,
    status_code=201,
)
async def create_admin_referral_code(
    campaign_id: UUID,
    payload: AdminReferralCodeCreateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminReferralCodeResponse:
    staff_session, staff = principal
    _require_referral_operator(staff)
    try:
        code = await ReferralService(session).create_code(
            campaign_id=campaign_id,
            code=payload.code,
            inviter_user_id=payload.inviter_user_id,
        )
    except ReferralError as error:
        raise _referral_problem(error) from error
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action="referral.code.created",
            event_metadata={
                "reason": _reason(payload.reason),
                "campaign_id": str(campaign_id),
                "code_id": str(code.id),
                "inviter_user_id": str(code.inviter_user_id),
            },
        )
    )
    await session.commit()
    await session.refresh(code)
    mark_private(response)
    return _code_response(code)


@router.post(
    "/{campaign_id}/reward-slots",
    operation_id="createAdminReferralRewardSlot",
    response_model=AdminReferralRewardSlotResponse,
    status_code=201,
)
async def create_admin_referral_reward_slot(
    campaign_id: UUID,
    payload: AdminReferralRewardSlotCreateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminReferralRewardSlotResponse:
    staff_session, staff = principal
    _require_referral_operator(staff)
    try:
        slot = await ReferralService(session).configure_reward_slot(
            campaign_id=campaign_id,
            product_version_id=payload.product_version_id,
            slot=payload.slot,
            total_limit=payload.total_limit,
            quantity=payload.quantity,
            enabled=payload.enabled,
        )
    except ReferralError as error:
        raise _referral_problem(error) from error
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action="referral.reward_slot.created",
            event_metadata={
                "reason": _reason(payload.reason),
                "campaign_id": str(campaign_id),
                "product_version_id": str(slot.product_version_id),
                "slot": slot.slot_key,
            },
        )
    )
    await session.commit()
    await session.refresh(slot)
    mark_private(response)
    return _reward_slot_response(slot)


@router.post(
    "/{campaign_id}/state",
    operation_id="setAdminReferralCampaignState",
    response_model=AdminReferralCampaignResponse,
)
async def set_admin_referral_campaign_state(
    campaign_id: UUID,
    payload: AdminReferralCampaignStateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminReferralCampaignResponse:
    staff_session, staff = principal
    _require_referral_operator(staff)
    try:
        campaign = await ReferralService(session).set_campaign_state(
            campaign_id,
            ReferralState(payload.state),
        )
    except ReferralError as error:
        raise _referral_problem(error) from error
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action="referral.campaign.state_changed",
            event_metadata={
                "reason": _reason(payload.reason),
                "target_id": str(campaign.id),
                "state": campaign.state,
            },
        )
    )
    await session.commit()
    await session.refresh(campaign)
    mark_private(response)
    return await _campaign_response(session, campaign)


@router.get(
    "",
    operation_id="listAdminReferrals",
    response_model=AdminReferralsResponse,
)
async def list_admin_referrals(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminReferralsResponse:
    _require_referral_reader(principal[1])
    campaigns = list(
        await session.scalars(
            select(ReferralCampaignVersion)
            .order_by(desc(ReferralCampaignVersion.created_at), desc(ReferralCampaignVersion.id))
            .limit(limit)
        )
    )
    mark_private(response)
    return AdminReferralsResponse(
        campaigns=[await _campaign_response(session, item) for item in campaigns]
    )


@router.get(
    "/{campaign_id}",
    operation_id="getAdminReferral",
    response_model=AdminReferralResponse,
)
async def get_admin_referral(
    campaign_id: UUID,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminReferralResponse:
    _require_referral_reader(principal[1])
    campaign = await session.get(ReferralCampaignVersion, campaign_id)
    if campaign is None:
        raise ApiProblem(status=404, title="Referral campaign not found")
    codes = list(
        await session.scalars(
            select(ReferralCode)
            .where(ReferralCode.campaign_version_id == campaign.id)
            .order_by(desc(ReferralCode.created_at), desc(ReferralCode.id))
        )
    )
    attributions = list(
        await session.scalars(
            select(ReferralAttribution)
            .where(ReferralAttribution.campaign_version_id == campaign.id)
            .order_by(desc(ReferralAttribution.locked_at), desc(ReferralAttribution.id))
        )
    )
    rewards = list(
        await session.scalars(
            select(ReferralRewardReservation)
            .where(ReferralRewardReservation.campaign_version_id == campaign.id)
            .order_by(
                desc(ReferralRewardReservation.reserved_at),
                desc(ReferralRewardReservation.id),
            )
        )
    )
    slots = list(
        await session.scalars(
            select(ReferralRewardSlot)
            .where(ReferralRewardSlot.campaign_version_id == campaign.id)
            .order_by(ReferralRewardSlot.product_version_id, ReferralRewardSlot.slot_key)
        )
    )
    mark_private(response)
    return AdminReferralResponse(
        campaign=await _campaign_response(session, campaign),
        codes=[
            AdminReferralCodeResponse(
                id=item.id,
                campaign_version_id=item.campaign_version_id,
                code=item.code,
                inviter_user_id=item.inviter_user_id,
                status=item.status,
                created_at=item.created_at,
            )
            for item in codes
        ],
        attributions=[
            AdminReferralAttributionResponse(
                id=item.id,
                campaign_version_id=item.campaign_version_id,
                code_id=item.code_id,
                referred_user_id=item.referred_user_id,
                inviter_user_id=item.inviter_user_id,
                locked_at=item.locked_at,
                status=item.status,
            )
            for item in attributions
        ],
        slots=[
            AdminReferralRewardSlotResponse(
                id=item.id,
                campaign_version_id=item.campaign_version_id,
                product_version_id=item.product_version_id,
                slot_key=item.slot_key,
                enabled=item.enabled,
                total_limit=item.total_limit,
                quantity=item.quantity,
                created_at=item.created_at,
            )
            for item in slots
        ],
        rewards=[
            AdminReferralRewardResponse(
                id=item.id,
                campaign_version_id=item.campaign_version_id,
                attribution_id=item.attribution_id,
                referred_user_id=item.referred_user_id,
                inviter_user_id=item.inviter_user_id,
                product_version_id=item.product_version_id,
                payment_attempt_id=item.payment_attempt_id,
                quantity=item.quantity,
                status=item.status,
                reserved_at=item.reserved_at,
                committed_at=item.committed_at,
            )
            for item in rewards
        ],
    )
