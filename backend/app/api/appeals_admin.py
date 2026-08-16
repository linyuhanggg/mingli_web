"""Admin referral appeal intake, risk signals, and two-person corrections."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.admin.schemas import (
    AdminReferralAppealApprovalResponse,
    AdminReferralAppealCreateRequest,
    AdminReferralAppealDecisionRequest,
    AdminReferralAppealResponse,
    AdminReferralAppealsResponse,
    AdminReferralRiskSignalRequest,
    AdminReferralRiskSignalResponse,
)
from app.api.admin import require_staff_csrf, require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.commerce.models import EntitlementEventRecord
from app.commerce.service import CommerceError, CommerceService
from app.referrals.models import (
    ReferralAppeal,
    ReferralAppealApproval,
    ReferralAttribution,
    ReferralParticipationRestriction,
    ReferralRewardReservation,
    ReferralRiskSignal,
)
from app.referrals.service import ReferralService

router = APIRouter(prefix="/admin/appeals", tags=["Admin Referral Appeals"])

_READER_ROLES = {"support", "finance", "ops", "superadmin"}
_SUBMITTER_ROLES = {"support", "superadmin"}
_RISK_WRITER_ROLES = {"ops", "superadmin"}
_DECISION_ROLES = {"finance", "superadmin"}


def _require_role(staff: StaffUser, allowed: set[str], title: str) -> None:
    if staff.role not in allowed:
        raise ApiProblem(status=403, title=title)


def _reason(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ApiProblem(status=400, title="Appeal operation reason is required")
    return normalized


async def _get_appeal(session: AsyncSession, appeal_id: UUID) -> ReferralAppeal:
    appeal = await session.get(ReferralAppeal, appeal_id)
    if appeal is None:
        raise ApiProblem(status=404, title="Referral appeal not found")
    return appeal


async def _correction_event(
    session: AsyncSession,
    appeal_id: UUID,
) -> EntitlementEventRecord | None:
    event: EntitlementEventRecord | None = await session.scalar(
        select(EntitlementEventRecord)
        .where(
            EntitlementEventRecord.source_type == "admin_revoke",
            EntitlementEventRecord.source_ref == f"referral-appeal:{appeal_id}:correction",
        )
        .order_by(desc(EntitlementEventRecord.created_at), desc(EntitlementEventRecord.id))
    )
    return event


async def _response(
    session: AsyncSession,
    appeal: ReferralAppeal,
) -> AdminReferralAppealResponse:
    attribution = await session.get(ReferralAttribution, appeal.attribution_id)
    if attribution is None:
        raise ApiProblem(status=409, title="Referral attribution is no longer available")
    signals = list(
        await session.scalars(
            select(ReferralRiskSignal)
            .where(ReferralRiskSignal.appeal_id == appeal.id)
            .order_by(ReferralRiskSignal.created_at, ReferralRiskSignal.id)
        )
    )
    approvals = list(
        await session.scalars(
            select(ReferralAppealApproval)
            .where(ReferralAppealApproval.appeal_id == appeal.id)
            .order_by(ReferralAppealApproval.created_at, ReferralAppealApproval.id)
        )
    )
    correction_event = await _correction_event(session, appeal.id)
    restricted_user_ids = list(
        await session.scalars(
            select(ReferralParticipationRestriction.user_id).where(
                ReferralParticipationRestriction.user_id.in_(
                    [attribution.inviter_user_id, attribution.referred_user_id]
                )
            )
        )
    )
    return AdminReferralAppealResponse(
        id=appeal.id,
        attribution_id=appeal.attribution_id,
        requester_user_id=appeal.requester_user_id,
        inviter_user_id=attribution.inviter_user_id,
        status=appeal.status,
        reason=appeal.reason,
        decision_reason=appeal.decision_reason,
        created_at=appeal.created_at,
        decided_at=appeal.decided_at,
        approval_count=len(approvals),
        risk_signals=[
            AdminReferralRiskSignalResponse(
                id=item.id,
                signal_type=item.signal_type,
                severity=item.severity,
                reason=item.reason,
                created_by_staff_user_id=item.created_by_staff_user_id,
                created_at=item.created_at,
            )
            for item in signals
        ],
        approvals=[
            AdminReferralAppealApprovalResponse(
                id=item.id,
                staff_user_id=item.staff_user_id,
                reason=item.reason,
                created_at=item.created_at,
            )
            for item in approvals
        ],
        correction_event_id=correction_event.id if correction_event is not None else None,
        correction_event_kind=correction_event.kind if correction_event is not None else None,
        participation_restriction_user_ids=restricted_user_ids,
    )


@router.get(
    "",
    operation_id="listAdminReferralAppeals",
    response_model=AdminReferralAppealsResponse,
)
async def list_admin_referral_appeals(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminReferralAppealsResponse:
    _require_role(principal[1], _READER_ROLES, "Referral appeal reader permission required")
    appeals = list(
        await session.scalars(
            select(ReferralAppeal)
            .order_by(desc(ReferralAppeal.created_at), desc(ReferralAppeal.id))
            .limit(limit)
        )
    )
    mark_private(response)
    return AdminReferralAppealsResponse(
        appeals=[await _response(session, appeal) for appeal in appeals]
    )


@router.post(
    "",
    operation_id="createAdminReferralAppeal",
    response_model=AdminReferralAppealResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_referral_appeal(
    payload: AdminReferralAppealCreateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminReferralAppealResponse:
    staff_session, staff = principal
    _require_role(staff, _SUBMITTER_ROLES, "Referral appeal submission permission required")
    attribution = await session.get(ReferralAttribution, payload.attribution_id)
    if attribution is None:
        raise ApiProblem(status=404, title="Referral attribution not found")
    existing = await session.scalar(
        select(ReferralAppeal).where(ReferralAppeal.attribution_id == attribution.id)
    )
    if existing is not None:
        raise ApiProblem(status=409, title="Referral attribution already has an appeal")
    appeal = ReferralAppeal(
        attribution_id=attribution.id,
        requester_user_id=attribution.referred_user_id,
        reason=_reason(payload.reason),
        status="submitted",
    )
    session.add(appeal)
    await session.flush()
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action="referral.appeal.created",
            event_metadata={
                "appeal_id": str(appeal.id),
                "attribution_id": str(attribution.id),
            },
        )
    )
    await session.commit()
    await session.refresh(appeal)
    mark_private(response)
    return await _response(session, appeal)


@router.post(
    "/{appeal_id}/risk-signals",
    operation_id="recordAdminReferralRiskSignal",
    response_model=AdminReferralRiskSignalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_admin_referral_risk_signal(
    appeal_id: UUID,
    payload: AdminReferralRiskSignalRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminReferralRiskSignalResponse:
    staff_session, staff = principal
    _require_role(staff, _RISK_WRITER_ROLES, "Referral risk signal permission required")
    appeal = await _get_appeal(session, appeal_id)
    if appeal.status in {"accepted", "rejected", "corrected"}:
        raise ApiProblem(status=409, title="Referral appeal is already decided")
    signal = ReferralRiskSignal(
        appeal_id=appeal.id,
        signal_type=payload.signal_type,
        severity=payload.severity,
        reason=_reason(payload.reason),
        created_by_staff_user_id=staff.id,
    )
    session.add(signal)
    await session.flush()
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action="referral.appeal.risk_signal.recorded",
            event_metadata={
                "appeal_id": str(appeal.id),
                "signal_id": str(signal.id),
                "signal_type": signal.signal_type,
                "severity": signal.severity,
            },
        )
    )
    await session.commit()
    await session.refresh(signal)
    mark_private(response)
    return AdminReferralRiskSignalResponse(
        id=signal.id,
        signal_type=signal.signal_type,
        severity=signal.severity,
        reason=signal.reason,
        created_by_staff_user_id=signal.created_by_staff_user_id,
        created_at=signal.created_at,
    )


@router.post(
    "/{appeal_id}/decision",
    operation_id="decideAdminReferralAppeal",
    response_model=AdminReferralAppealResponse,
)
async def decide_admin_referral_appeal(
    appeal_id: UUID,
    payload: AdminReferralAppealDecisionRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminReferralAppealResponse:
    staff_session, staff = principal
    _require_role(staff, _DECISION_ROLES, "Referral appeal decision permission required")
    appeal = await _get_appeal(session, appeal_id)
    reason = _reason(payload.reason)
    now = datetime.now(UTC)

    if payload.outcome in {"accept", "reject"}:
        if appeal.status != "submitted":
            raise ApiProblem(status=409, title="Referral appeal cannot receive this decision")
        appeal.status = "accepted" if payload.outcome == "accept" else "rejected"
        appeal.decision_reason = reason
        appeal.decided_at = now
        session.add(
            AdminAuditEvent(
                staff_user_id=staff.id,
                actor_session_id=staff_session.id,
                action="referral.appeal.decided",
                event_metadata={
                    "appeal_id": str(appeal.id),
                    "outcome": payload.outcome,
                },
            )
        )
        await session.commit()
        await session.refresh(appeal)
        mark_private(response)
        return await _response(session, appeal)

    if appeal.status not in {"submitted", "correction_pending"}:
        raise ApiProblem(status=409, title="Referral appeal cannot receive a correction")
    existing_approval = await session.scalar(
        select(ReferralAppealApproval).where(
            ReferralAppealApproval.appeal_id == appeal.id,
            ReferralAppealApproval.staff_user_id == staff.id,
        )
    )
    if existing_approval is not None:
        raise ApiProblem(status=409, title="The same staff member cannot approve twice")
    approval = ReferralAppealApproval(
        appeal_id=appeal.id,
        staff_user_id=staff.id,
        reason=reason,
    )
    session.add(approval)
    appeal.status = "correction_pending"
    appeal.decision_reason = reason
    await session.flush()
    approval_rows = list(
        await session.scalars(
            select(ReferralAppealApproval).where(
                ReferralAppealApproval.appeal_id == appeal.id
            )
        )
    )
    if len(approval_rows) < 2:
        session.add(
            AdminAuditEvent(
                staff_user_id=staff.id,
                actor_session_id=staff_session.id,
                action="referral.appeal.approval.recorded",
                event_metadata={
                    "appeal_id": str(appeal.id),
                    "approval_count": len(approval_rows),
                },
            )
        )
        await session.commit()
        await session.refresh(appeal)
        mark_private(response)
        return await _response(session, appeal)

    attribution = await session.get(ReferralAttribution, appeal.attribution_id)
    if attribution is None:
        raise ApiProblem(status=409, title="Referral attribution is no longer available")
    reservation = await session.scalar(
        select(ReferralRewardReservation).where(
            ReferralRewardReservation.attribution_id == attribution.id
        )
    )
    if reservation is None or reservation.status != "committed":
        raise ApiProblem(
            status=409,
            title="A committed referral reward is required before correction",
        )
    source_ref = f"referral-appeal:{appeal.id}:correction"
    try:
        event, _created = await CommerceService(session).adjust_entitlement_as_staff(
            owner_user_id=reservation.inviter_user_id,
            entitlement_id=f"referral:{reservation.id}",
            action="revoke",
            quantity=reservation.quantity,
            reason=reason,
            source_ref=source_ref,
            target_ref=str(attribution.id),
            actor_staff_user_id=staff.id,
            actor_session_id=staff_session.id,
        )
    except CommerceError as error:
        raise ApiProblem(
            status=409,
            title="Referral correction cannot be applied",
            detail=str(error),
        ) from error
    appeal.status = "corrected"
    appeal.decided_at = now
    referral_service = ReferralService(session)
    await referral_service.restrict_future_participation(
        user_id=attribution.inviter_user_id,
        source_appeal_id=appeal.id,
        reason=reason,
        created_by_staff_user_id=staff.id,
    )
    await referral_service.restrict_future_participation(
        user_id=attribution.referred_user_id,
        source_appeal_id=appeal.id,
        reason=reason,
        created_by_staff_user_id=staff.id,
    )
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action="referral.appeal.corrected",
            event_metadata={
                "appeal_id": str(appeal.id),
                "approval_count": len(approval_rows),
                "event_id": str(event.id),
                "event_kind": event.kind,
            },
        )
    )
    await session.commit()
    await session.refresh(appeal)
    mark_private(response)
    return await _response(session, appeal)
