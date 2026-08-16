"""Superadmin-only notification delivery operations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.api.admin import require_staff_csrf, require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.commerce.models import NotificationOutbox
from app.commerce.schemas import (
    AdminNotificationResponse,
    AdminNotificationRetryRequest,
    AdminNotificationsResponse,
)
from app.commerce.service import CommerceError, CommerceService

router = APIRouter(prefix="/admin/notifications", tags=["Admin Notifications"])


def _require_notification_operator(staff: StaffUser) -> None:
    if staff.role != "superadmin":
        raise ApiProblem(status=403, title="Notification operator permission required")


def _reason(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ApiProblem(status=400, title="Notification operation reason is required")
    return normalized


def _channel(item: NotificationOutbox) -> str | None:
    value: Any = item.payload.get("channel")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _response(item: NotificationOutbox) -> AdminNotificationResponse:
    return AdminNotificationResponse(
        id=item.id,
        owner_user_id=item.owner_user_id,
        kind=item.kind,
        dedupe_key=item.dedupe_key,
        channel=_channel(item),
        status=item.status,
        available_at=item.available_at,
        attempt_count=item.attempt_count,
        processing_until=item.processing_until,
        sent_at=item.sent_at,
        last_error=item.last_error,
    )


@router.get(
    "",
    operation_id="listAdminNotifications",
    response_model=AdminNotificationsResponse,
)
async def list_admin_notifications(
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminNotificationsResponse:
    _require_notification_operator(principal[1])
    items = list(
        await session.scalars(
            select(NotificationOutbox)
            .order_by(desc(NotificationOutbox.available_at), desc(NotificationOutbox.id))
            .limit(100)
        )
    )
    mark_private(response)
    return AdminNotificationsResponse(notifications=[_response(item) for item in items])


@router.post(
    "/{notification_id}/retry",
    operation_id="retryAdminNotification",
    response_model=AdminNotificationResponse,
)
async def retry_admin_notification(
    notification_id: UUID,
    payload: AdminNotificationRetryRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminNotificationResponse:
    staff_session, staff = principal
    _require_notification_operator(staff)
    try:
        item = await CommerceService(session).retry_notification(notification_id)
    except CommerceError as error:
        detail = str(error)
        raise ApiProblem(
            status=404 if detail == "notification not found" else 409,
            title=(
                "Notification not found"
                if detail == "notification not found"
                else "Notification cannot be retried"
            ),
            detail=detail,
        ) from error
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action="notification.retry",
            event_metadata={
                "reason": _reason(payload.reason),
                "notification_id": str(item.id),
                "attempt_count": item.attempt_count,
            },
        )
    )
    await session.commit()
    mark_private(response)
    return _response(item)
