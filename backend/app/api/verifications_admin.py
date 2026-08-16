"""Read-only Admin metadata for verification and report feedback events."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import StaffSession, StaffUser
from app.admin.schemas import (
    AdminVerificationEventResponse,
    AdminVerificationEventsResponse,
)
from app.api.admin import require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.readings.models import (
    ClaimVerificationEvent,
    ReadingVerification,
    ReportFeedback,
)

router = APIRouter(prefix="/admin/verifications", tags=["Admin Readings"])


def _require_read_access(staff: StaffUser) -> None:
    if staff.role not in {"support", "ops", "superadmin"}:
        raise ApiProblem(status=403, title="Verification read permission required")


@router.get(
    "",
    operation_id="listAdminVerificationEvents",
    response_model=AdminVerificationEventsResponse,
)
async def list_admin_verification_events(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminVerificationEventsResponse:
    _require_read_access(principal[1])
    reading_events = list(
        await session.scalars(
            select(ReadingVerification)
            .order_by(ReadingVerification.created_at.desc())
            .limit(limit)
        )
    )
    claim_events = list(
        await session.scalars(
            select(ClaimVerificationEvent)
            .order_by(ClaimVerificationEvent.created_at.desc())
            .limit(limit)
        )
    )
    feedback_events = list(
        await session.scalars(
            select(ReportFeedback)
            .order_by(ReportFeedback.created_at.desc())
            .limit(limit)
        )
    )
    events: list[tuple[datetime, AdminVerificationEventResponse]] = [
        (
            item.created_at,
            AdminVerificationEventResponse(
                id=item.id,
                source="reading",
                reading_version_id=item.reading_version_id,
                claim_id=None,
                outcome=item.outcome,
                actor_ref="user-feedback",
                created_at=item.created_at,
            ),
        )
        for item in reading_events
    ]
    events.extend(
        (
            item.created_at,
            AdminVerificationEventResponse(
                id=item.id,
                source="claim",
                reading_version_id=item.reading_version_id,
                claim_id=item.claim_id,
                outcome=item.outcome,
                actor_ref=item.actor_ref,
                created_at=item.created_at,
            ),
        )
        for item in claim_events
    )
    events.extend(
        (
            item.created_at,
            AdminVerificationEventResponse(
                id=item.id,
                source="feedback",
                reading_version_id=item.reading_version_id,
                claim_id=None,
                outcome=item.outcome,
                actor_ref=item.actor_ref,
                created_at=item.created_at,
            ),
        )
        for item in feedback_events
    )
    events.sort(key=lambda item: item[0], reverse=True)
    mark_private(response)
    return AdminVerificationEventsResponse(events=[item[1] for item in events[:limit]])
