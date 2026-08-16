"""Superadmin-only staff session inventory and revocation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.api.admin import require_staff_csrf, require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.commerce.schemas import (
    AdminSessionRevokeRequest,
    AdminStaffSessionResponse,
    AdminStaffSessionsResponse,
)

router = APIRouter(prefix="/admin/sessions", tags=["Admin Sessions"])


def _require_session_operator(staff: StaffUser) -> None:
    if staff.role != "superadmin":
        raise ApiProblem(status=403, title="Session operator permission required")


def _reason(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ApiProblem(status=400, title="Session operation reason is required")
    return normalized


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _status(item: StaffSession, now: datetime) -> Literal["active", "expired", "revoked"]:
    if item.revoked_at is not None:
        return "revoked"
    if _utc(item.expires_at) <= now:
        return "expired"
    return "active"


def _response(item: StaffSession, actor: str, now: datetime) -> AdminStaffSessionResponse:
    return AdminStaffSessionResponse(
        id=item.id,
        staff_user_id=item.staff_user_id,
        actor=actor,
        status=_status(item, now),
        expires_at=item.expires_at,
        last_seen_at=item.last_seen_at,
        revoked_at=item.revoked_at,
        created_at=item.created_at,
    )


@router.get(
    "",
    operation_id="listAdminStaffSessions",
    response_model=AdminStaffSessionsResponse,
)
async def list_admin_staff_sessions(
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminStaffSessionsResponse:
    _require_session_operator(principal[1])
    rows = (
        await session.execute(
            select(StaffSession, StaffUser.email)
            .join(StaffUser, StaffUser.id == StaffSession.staff_user_id)
            .order_by(desc(StaffSession.last_seen_at), desc(StaffSession.created_at))
            .limit(200)
        )
    ).all()
    now = datetime.now(UTC)
    mark_private(response)
    return AdminStaffSessionsResponse(
        sessions=[_response(item, actor, now) for item, actor in rows]
    )


@router.post(
    "/{session_id}/revoke",
    operation_id="revokeAdminStaffSession",
    response_model=AdminStaffSessionResponse,
)
async def revoke_admin_staff_session(
    session_id: UUID,
    payload: AdminSessionRevokeRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminStaffSessionResponse:
    actor_session, actor = principal
    _require_session_operator(actor)
    target = await session.get(StaffSession, session_id)
    if target is None:
        raise ApiProblem(status=404, title="Staff session not found")
    now = datetime.now(UTC)
    if target.revoked_at is None:
        target.revoked_at = now
        session.add(
            AdminAuditEvent(
                staff_user_id=actor.id,
                actor_session_id=actor_session.id,
                action="staff.session.revoked",
                event_metadata={
                    "reason": _reason(payload.reason),
                    "target_id": str(target.id),
                },
            )
        )
        await session.commit()
        await session.refresh(target)
    mark_private(response)
    target_actor = await session.scalar(
        select(StaffUser.email).where(StaffUser.id == target.staff_user_id)
    )
    return _response(target, target_actor or "已撤销员工", now)
