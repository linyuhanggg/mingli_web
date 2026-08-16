from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    database_session,
    mark_private,
    require_device_csrf,
    require_device_session,
)
from app.api.errors import ApiProblem
from app.commerce.models import NotificationOutbox, NotificationPreference
from app.commerce.notifications import project_in_app_notification
from app.commerce.schemas import (
    AccountNotification,
    AccountNotificationsReadAllResponse,
    AccountNotificationsResponse,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
)
from app.commerce.service import CommerceError, CommerceService
from app.identity.models import DeviceSession
from app.identity.repository import IdentityRepository
from app.identity.schemas import AccountResponse, LoginIdentitySummary
from app.privacy.models import AccountClosureRequest
from app.privacy.schemas import ClosureResponse, DataExportResponse
from app.privacy.service import (
    ClosureNotFoundError,
    ClosureNotReadyError,
    DataRightsService,
)

router = APIRouter(tags=["Identity"])


@router.get("/account", operation_id="getAccount", response_model=AccountResponse)
async def get_account(
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
) -> AccountResponse:
    repository = IdentityRepository(session)
    user = await repository.get_user(device_session.user_id)
    if user is None or user.status != "active":
        raise ApiProblem(status=401, title="Authentication required")
    identities = await repository.list_identities(user.id)
    mark_private(response)
    return AccountResponse(
        user_id=user.id,
        identities=[LoginIdentitySummary.model_validate(identity) for identity in identities],
    )


@router.get(
    "/account/export",
    operation_id="exportAccountData",
    response_model=DataExportResponse,
)
async def export_account_data(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
) -> DataExportResponse:
    try:
        payload = await DataRightsService(
            session, request.app.state.settings
        ).export_user(device_session.user_id)
    except ClosureNotFoundError as error:
        raise ApiProblem(status=401, title="Authentication required") from error
    mark_private(response)
    return DataExportResponse(
        generated_at=datetime.fromisoformat(str(payload["generated_at"])),
        user_id=device_session.user_id,
        payload=payload,
    )


@router.get(
    "/account/notifications",
    operation_id="listAccountNotifications",
    response_model=AccountNotificationsResponse,
)
async def list_account_notifications(
    response: Response,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
) -> AccountNotificationsResponse:
    items, unread_count = await CommerceService(session).list_account_notifications(
        device_session.user_id,
        unread_only=unread_only,
        limit=limit,
    )
    mark_private(response)
    return AccountNotificationsResponse(
        notifications=[_account_notification_response(item) for item in items],
        unread_count=unread_count,
    )


@router.post(
    "/account/notifications/read-all",
    operation_id="markAllAccountNotificationsRead",
    response_model=AccountNotificationsReadAllResponse,
)
async def mark_all_account_notifications_read(
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_csrf),
) -> AccountNotificationsReadAllResponse:
    unread_count = await CommerceService(session).mark_all_account_notifications_read(
        device_session.user_id
    )
    await session.commit()
    mark_private(response)
    return AccountNotificationsReadAllResponse(unread_count=unread_count)


@router.post(
    "/account/notifications/{notification_id}/read",
    operation_id="markAccountNotificationRead",
    response_model=AccountNotification,
)
async def mark_account_notification_read(
    notification_id: UUID,
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_csrf),
) -> AccountNotification:
    try:
        item = await CommerceService(session).mark_account_notification_read(
            device_session.user_id,
            notification_id,
        )
    except CommerceError as error:
        raise ApiProblem(status=404, title="Notification not found") from error
    await session.commit()
    mark_private(response)
    return _account_notification_response(item)


@router.delete(
    "/account/notifications/{notification_id}",
    operation_id="deleteAccountNotification",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_account_notification(
    notification_id: UUID,
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_csrf),
) -> None:
    try:
        await CommerceService(session).delete_account_notification(
            device_session.user_id,
            notification_id,
        )
    except CommerceError as error:
        raise ApiProblem(status=404, title="Notification not found") from error
    await session.commit()
    mark_private(response)


def _account_notification_response(item: NotificationOutbox) -> AccountNotification:
    projection = project_in_app_notification(item)
    if projection is None:
        raise ApiProblem(status=404, title="Notification not found")
    return AccountNotification(
        id=item.id,
        title=projection.title,
        summary=projection.summary,
        available_at=item.available_at,
        read_at=item.read_at,
        target_href=projection.target_href,
    )


@router.get(
    "/account/notification-preferences",
    operation_id="getNotificationPreferences",
    response_model=NotificationPreferencesResponse,
)
async def get_notification_preferences(
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
) -> NotificationPreferencesResponse:
    preference = await CommerceService(session).get_notification_preferences(
        device_session.user_id
    )
    await session.commit()
    mark_private(response)
    return _notification_preferences_response(preference)


@router.put(
    "/account/notification-preferences",
    operation_id="updateNotificationPreferences",
    response_model=NotificationPreferencesResponse,
)
async def update_notification_preferences(
    payload: NotificationPreferencesRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_csrf),
) -> NotificationPreferencesResponse:
    preference = await CommerceService(session).update_notification_preferences(
        device_session.user_id,
        in_app_enabled=payload.in_app_enabled,
        email_enabled=payload.email_enabled,
        sms_enabled=payload.sms_enabled,
    )
    await session.commit()
    mark_private(response)
    return _notification_preferences_response(preference)


@router.get(
    "/account/closure",
    operation_id="getAccountClosure",
    response_model=ClosureResponse | None,
)
async def get_account_closure(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
) -> ClosureResponse | None:
    closure = await DataRightsService(
        session, request.app.state.settings
    ).active_closure(device_session.user_id)
    mark_private(response)
    return None if closure is None else _closure_response(closure)


@router.post(
    "/account/closure",
    operation_id="requestAccountClosure",
    response_model=ClosureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_account_closure(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_csrf),
) -> ClosureResponse:
    try:
        closure, created = await DataRightsService(
            session, request.app.state.settings
        ).request_closure(device_session.user_id)
    except ClosureNotFoundError as error:
        raise ApiProblem(status=401, title="Authentication required") from error
    await session.commit()
    if not created:
        response.status_code = status.HTTP_200_OK
    mark_private(response)
    return _closure_response(closure)


@router.delete(
    "/account/closure",
    operation_id="cancelAccountClosure",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_account_closure(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_csrf),
) -> None:
    try:
        await DataRightsService(
            session, request.app.state.settings
        ).cancel_closure(device_session.user_id)
    except ClosureNotFoundError as error:
        raise ApiProblem(status=404, title="Active account closure not found") from error
    except ClosureNotReadyError as error:
        raise ApiProblem(status=409, title="Account closure can no longer be cancelled") from error
    await session.commit()
    mark_private(response)


def _closure_response(closure: AccountClosureRequest) -> ClosureResponse:
    return ClosureResponse(
        closure_id=closure.id,
        user_id=closure.user_id,
        status=closure.status,
        requested_at=closure.requested_at,
        cancel_until=closure.cancel_until,
        cancelled_at=closure.cancelled_at,
        executed_at=closure.executed_at,
    )


def _notification_preferences_response(
    preference: NotificationPreference,
) -> NotificationPreferencesResponse:
    return NotificationPreferencesResponse(
        in_app_enabled=preference.in_app_enabled,
        email_enabled=preference.email_enabled,
        sms_enabled=preference.sms_enabled,
    )
