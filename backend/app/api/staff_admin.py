"""Superadmin-only staff directory and role/status administration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.admin.passwords import hash_password
from app.admin.schemas import (
    AdminStaffCreateRequest,
    AdminStaffListResponse,
    AdminStaffPasswordResetRequest,
    AdminStaffResponse,
    AdminStaffRoleRequest,
    AdminStaffStatusRequest,
    StaffRole,
)
from app.api.admin import require_staff_csrf, require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem

router = APIRouter(prefix="/admin/staff", tags=["Admin Staff"])


def _require_staff_operator(staff: StaffUser) -> None:
    if staff.role != "superadmin":
        raise ApiProblem(status=403, title="Staff operator permission required")


def _reason(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ApiProblem(status=400, title="Staff operation reason is required")
    return normalized


def _response(staff: StaffUser, unrevoked_session_count: int) -> AdminStaffResponse:
    return AdminStaffResponse(
        id=staff.id,
        email=staff.email,
        display_name=staff.display_name,
        role=cast(StaffRole, staff.role),
        status=cast(Literal["active", "suspended"], staff.status),
        created_at=staff.created_at,
        last_login_at=staff.last_login_at,
        unrevoked_session_count=unrevoked_session_count,
    )


async def _unrevoked_session_count(session: AsyncSession, staff_user_id: UUID) -> int:
    sessions = list(
        await session.scalars(
            select(StaffSession).where(StaffSession.staff_user_id == staff_user_id)
        )
    )
    return sum(item.revoked_at is None for item in sessions)


async def _staff_or_404(session: AsyncSession, staff_id: UUID) -> StaffUser:
    staff = await session.get(StaffUser, staff_id)
    if staff is None:
        raise ApiProblem(status=404, title="Staff user not found")
    return staff


def _reject_self(actor: StaffUser, target: StaffUser) -> None:
    if actor.id == target.id:
        raise ApiProblem(status=409, title="Cannot change the current staff account")


async def _revoke_sessions(
    session: AsyncSession,
    *,
    staff_user_id: UUID,
    now: datetime,
) -> int:
    sessions = list(
        await session.scalars(
            select(StaffSession).where(StaffSession.staff_user_id == staff_user_id)
        )
    )
    revoked_count = 0
    for item in sessions:
        if item.revoked_at is None:
            item.revoked_at = now
            revoked_count += 1
    return revoked_count


@router.post(
    "",
    operation_id="createAdminStaff",
    response_model=AdminStaffResponse,
    status_code=201,
)
async def create_admin_staff(
    payload: AdminStaffCreateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminStaffResponse:
    actor_session, actor = principal
    _require_staff_operator(actor)
    reason = _reason(payload.reason)
    email = str(payload.email).strip().lower()
    display_name = payload.display_name.strip()
    if not display_name:
        raise ApiProblem(status=400, title="Staff display name is required")
    existing = await session.scalar(
        select(StaffUser).where(func.lower(StaffUser.email) == email)
    )
    if existing is not None:
        raise ApiProblem(status=409, title="Staff email already exists")

    staff = StaffUser(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=display_name,
        role=payload.role,
        status="active",
    )
    session.add(staff)
    await session.flush()
    session.add(
        AdminAuditEvent(
            staff_user_id=actor.id,
            actor_session_id=actor_session.id,
            action="staff.created",
            event_metadata={
                "reason": reason,
                "role": payload.role,
                "target_id": str(staff.id),
            },
        )
    )
    await session.commit()
    await session.refresh(staff)
    mark_private(response)
    return _response(staff, 0)


@router.get(
    "",
    operation_id="listAdminStaff",
    response_model=AdminStaffListResponse,
)
async def list_admin_staff(
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminStaffListResponse:
    _require_staff_operator(principal[1])
    staff_members = list(
        await session.scalars(select(StaffUser).order_by(StaffUser.email).limit(200))
    )
    result = [
        _response(item, await _unrevoked_session_count(session, item.id))
        for item in staff_members
    ]
    mark_private(response)
    return AdminStaffListResponse(staff=result)


@router.post(
    "/{staff_id}/status",
    operation_id="updateAdminStaffStatus",
    response_model=AdminStaffResponse,
)
async def update_admin_staff_status(
    staff_id: UUID,
    payload: AdminStaffStatusRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminStaffResponse:
    actor_session, actor = principal
    _require_staff_operator(actor)
    target = await _staff_or_404(session, staff_id)
    _reject_self(actor, target)
    reason = _reason(payload.reason)
    now = datetime.now(UTC)
    revoked_count = 0
    if target.status != payload.status:
        target.status = payload.status
        if payload.status == "suspended":
            revoked_count = await _revoke_sessions(
                session,
                staff_user_id=target.id,
                now=now,
            )
        session.add(
            AdminAuditEvent(
                staff_user_id=actor.id,
                actor_session_id=actor_session.id,
                action="staff.status.updated",
                event_metadata={
                    "reason": reason,
                    "status": payload.status,
                    "target_id": str(target.id),
                    "revoked_count": revoked_count,
                },
            )
        )
        await session.commit()
        await session.refresh(target)
    mark_private(response)
    return _response(target, await _unrevoked_session_count(session, target.id))


@router.post(
    "/{staff_id}/role",
    operation_id="updateAdminStaffRole",
    response_model=AdminStaffResponse,
)
async def update_admin_staff_role(
    staff_id: UUID,
    payload: AdminStaffRoleRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminStaffResponse:
    actor_session, actor = principal
    _require_staff_operator(actor)
    target = await _staff_or_404(session, staff_id)
    _reject_self(actor, target)
    reason = _reason(payload.reason)
    now = datetime.now(UTC)
    revoked_count = 0
    if target.role != payload.role:
        target.role = payload.role
        revoked_count = await _revoke_sessions(
            session,
            staff_user_id=target.id,
            now=now,
        )
        session.add(
            AdminAuditEvent(
                staff_user_id=actor.id,
                actor_session_id=actor_session.id,
                action="staff.role.updated",
                event_metadata={
                    "reason": reason,
                    "role": payload.role,
                    "target_id": str(target.id),
                    "revoked_count": revoked_count,
                },
            )
        )
        await session.commit()
        await session.refresh(target)
    mark_private(response)
    return _response(target, await _unrevoked_session_count(session, target.id))


@router.post(
    "/{staff_id}/password-reset",
    operation_id="resetAdminStaffPassword",
    response_model=AdminStaffResponse,
)
async def reset_admin_staff_password(
    staff_id: UUID,
    payload: AdminStaffPasswordResetRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminStaffResponse:
    actor_session, actor = principal
    _require_staff_operator(actor)
    target = await _staff_or_404(session, staff_id)
    _reject_self(actor, target)
    reason = _reason(payload.reason)
    target.password_hash = hash_password(payload.password)
    revoked_count = await _revoke_sessions(
        session,
        staff_user_id=target.id,
        now=datetime.now(UTC),
    )
    session.add(
        AdminAuditEvent(
            staff_user_id=actor.id,
            actor_session_id=actor_session.id,
            action="staff.password.reset",
            event_metadata={
                "reason": reason,
                "target_id": str(target.id),
                "revoked_count": revoked_count,
            },
        )
    )
    await session.commit()
    await session.refresh(target)
    mark_private(response)
    return _response(target, await _unrevoked_session_count(session, target.id))
