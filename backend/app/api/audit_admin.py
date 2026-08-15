"""Read-only, redacted Admin audit history."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.api.admin import require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.commerce.schemas import AdminAuditEventResponse, AdminAuditEventsResponse

router = APIRouter(prefix="/admin/audit", tags=["Admin Audit"])

_SAFE_METADATA_KEYS = frozenset(
    {
        "action",
        "attempt_count",
        "channel",
        "content_key",
        "difference_count",
        "enabled",
        "entitlement_id",
        "family_id",
        "key",
        "notification_id",
        "owner_user_id",
        "provider",
        "reason",
        "revision",
        "revoked_count",
        "role",
        "run_id",
        "source_ref",
        "status",
        "state",
        "target_id",
        "target_ref",
        "version",
        "locale",
    }
)


def _require_audit_reader(staff: StaffUser) -> None:
    if staff.role != "superadmin":
        raise ApiProblem(status=403, title="Audit reader permission required")


def _safe_metadata(value: dict[str, Any]) -> dict[str, str | int | bool | None]:
    safe: dict[str, str | int | bool | None] = {}
    for key, item in value.items():
        if key not in _SAFE_METADATA_KEYS:
            continue
        if item is None or isinstance(item, (bool, int, str)):
            safe[key] = item
    return safe


@router.get(
    "",
    operation_id="listAdminAuditEvents",
    response_model=AdminAuditEventsResponse,
)
async def list_admin_audit_events(
    response: Response,
    action: str | None = Query(default=None, min_length=1, max_length=120),
    staff_user_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminAuditEventsResponse:
    _require_audit_reader(principal[1])
    statement = (
        select(AdminAuditEvent, StaffUser.email)
        .outerjoin(StaffUser, StaffUser.id == AdminAuditEvent.staff_user_id)
        .order_by(desc(AdminAuditEvent.created_at), desc(AdminAuditEvent.id))
        .limit(limit)
    )
    if action is not None:
        statement = statement.where(AdminAuditEvent.action == action)
    if staff_user_id is not None:
        statement = statement.where(AdminAuditEvent.staff_user_id == staff_user_id)
    rows = (await session.execute(statement)).all()
    mark_private(response)
    return AdminAuditEventsResponse(
        events=[
            AdminAuditEventResponse(
                id=event.id,
                action=event.action,
                actor=actor_email or "已撤销员工",
                metadata=_safe_metadata(event.event_metadata),
                created_at=event.created_at,
            )
            for event, actor_email in rows
        ]
    )
