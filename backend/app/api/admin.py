"""Staff admin HTTP surface."""

from __future__ import annotations

import hmac
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.cookies import (
    ADMIN_CSRF_COOKIE,
    ADMIN_SESSION_COOKIE,
    clear_admin_cookies,
    set_admin_cookies,
)
from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.admin.repository import AdminRepository
from app.admin.schemas import (
    AdminLoginRequest,
    AdminMeResponse,
    AdminOverviewResponse,
    AdminSessionResponse,
)
from app.admin.service import AdminAuthError, AdminAuthService, build_overview
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.api.rate_guard import check_rate_limiter
from app.commerce.models import EntitlementEventRecord
from app.commerce.schemas import (
    AdminEntitlementAdjustmentRequest,
    AdminEntitlementAdjustmentResponse,
    AdminEntitlementEventResponse,
    AdminEntitlementEventsResponse,
)
from app.commerce.service import CommerceError, CommerceService
from app.config import Settings
from app.identity.security import hash_token
from app.privacy.models import AccountClosureRequest
from app.privacy.schemas import ClosureListResponse, ClosureResponse
from app.privacy.service import (
    ClosureAlreadyExecutedError,
    ClosureNotFoundError,
    ClosureNotReadyError,
    DataRightsService,
)
from app.readings.rate_limit import WindowRateLimiter

router = APIRouter(prefix="/admin", tags=["Admin Auth"])


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _auth_service(request: Request, session: AsyncSession) -> AdminAuthService:
    settings = _settings(request)
    bootstrap_password = (
        settings.admin_bootstrap_password.get_secret_value()
        if settings.admin_bootstrap_password is not None
        else None
    )
    return AdminAuthService(
        AdminRepository(session),
        session_hours=settings.admin_session_hours,
        bootstrap_email=settings.admin_bootstrap_email,
        bootstrap_password=bootstrap_password,
        allow_bootstrap=settings.environment in {"local", "test"},
    )


def _login_limiter(request: Request) -> WindowRateLimiter:
    limiter = getattr(request.app.state, "admin_login_rate_limiter", None)
    if limiter is None:
        settings = _settings(request)
        limiter = WindowRateLimiter(
            limit=settings.admin_login_rate_limit,
            window_seconds=settings.admin_login_rate_window_seconds,
        )
        request.app.state.admin_login_rate_limiter = limiter
    return limiter


async def require_staff_session(
    request: Request,
    session: AsyncSession = Depends(database_session),
) -> tuple[StaffSession, StaffUser]:
    token = request.cookies.get(ADMIN_SESSION_COOKIE)
    if not token:
        raise ApiProblem(status=401, title="Staff authentication required")
    now = datetime.now(UTC)
    repository = AdminRepository(session)
    staff_session = await repository.get_active_session(hash_token(token), now)
    if staff_session is None:
        raise ApiProblem(status=401, title="Staff authentication required")
    staff = await repository.get_staff(staff_session.staff_user_id)
    if staff is None or staff.status != "active":
        raise ApiProblem(status=401, title="Staff authentication required")
    staff_session.last_seen_at = now
    return staff_session, staff


async def require_staff_csrf(
    request: Request,
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> tuple[StaffSession, StaffUser]:
    staff_session, staff = principal
    cookie_token = request.cookies.get(ADMIN_CSRF_COOKIE)
    header_token = request.headers.get("x-csrf-token")
    if not cookie_token or not header_token:
        raise ApiProblem(status=403, title="CSRF validation failed")
    if not hmac.compare_digest(cookie_token, header_token):
        raise ApiProblem(status=403, title="CSRF validation failed")
    if not hmac.compare_digest(staff_session.csrf_token_hash, hash_token(cookie_token)):
        raise ApiProblem(status=403, title="CSRF validation failed")
    return staff_session, staff


@router.post(
    "/auth/login",
    operation_id="adminLogin",
    response_model=AdminSessionResponse,
)
async def admin_login(
    request: Request,
    response: Response,
    payload: AdminLoginRequest,
    session: AsyncSession = Depends(database_session),
) -> AdminSessionResponse:
    settings = _settings(request)
    limiter = _login_limiter(request)
    # Use email as bucket key; do not reveal whether the account exists.
    check_rate_limiter(
        limiter=limiter,
        key=payload.email.strip().lower(),
        title="Too many login attempts; please wait and retry",
    )
    try:
        created = await _auth_service(request, session).login(
            str(payload.email),
            payload.password,
        )
    except AdminAuthError as error:
        raise ApiProblem(status=401, title="Invalid email or password") from error
    await session.commit()
    set_admin_cookies(
        response,
        settings=settings,
        session_token=created.token,
        csrf_token=created.csrf_token,
        expires_at=created.expires_at,
    )
    mark_private(response)
    return AdminSessionResponse(
        staff_id=created.staff.id,
        session_id=created.session_id,
        role=created.staff.role,
        display_name=created.staff.display_name,
        expires_at=created.expires_at,
        csrf_token=created.csrf_token,
    )


@router.post(
    "/auth/logout",
    operation_id="adminLogout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> None:
    staff_session, _staff = principal
    await _auth_service(request, session).logout(staff_session)
    await session.commit()
    clear_admin_cookies(response, settings=_settings(request))
    mark_private(response)


@router.get(
    "/me",
    operation_id="adminMe",
    response_model=AdminMeResponse,
    tags=["Admin Auth"],
)
async def admin_me(
    response: Response,
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminMeResponse:
    staff_session, staff = principal
    mark_private(response)
    return AdminMeResponse(
        staff_id=staff.id,
        role=staff.role,
        email=staff.email,
        display_name=staff.display_name,
        session_id=staff_session.id,
        expires_at=staff_session.expires_at,
    )


@router.get(
    "/overview",
    operation_id="adminOverview",
    response_model=AdminOverviewResponse,
    tags=["Admin Ops"],
)
async def admin_overview(
    response: Response,
    session: AsyncSession = Depends(database_session),
    _principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminOverviewResponse:
    mark_private(response)
    return await build_overview(session)


def _require_entitlement_operator(staff: StaffUser) -> None:
    if staff.role not in {"finance", "ops", "superadmin"}:
        raise ApiProblem(status=403, title="Entitlement operator permission required")


def _entitlement_event_response(
    event: EntitlementEventRecord,
) -> AdminEntitlementEventResponse:
    return AdminEntitlementEventResponse(
        id=event.id,
        owner_user_id=event.owner_user_id,
        entitlement_id=event.entitlement_id,
        kind=event.kind,
        quantity=event.quantity,
        source_type=event.source_type,
        source_ref=event.source_ref,
        target_ref=event.target_ref,
        created_at=event.created_at,
    )


def _commerce_problem(error: CommerceError) -> ApiProblem:
    detail = str(error)
    return ApiProblem(
        status=404 if detail == "owner user not found" else 409,
        title=(
            "Owner user not found"
            if detail == "owner user not found"
            else "Invalid entitlement adjustment"
        ),
        detail=detail,
    )


@router.get(
    "/entitlements/events/recent",
    operation_id="listRecentAdminEntitlementEvents",
    response_model=AdminEntitlementEventsResponse,
    tags=["Admin Entitlements"],
)
async def list_recent_admin_entitlement_events(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminEntitlementEventsResponse:
    _require_entitlement_operator(principal[1])
    events = list(
        await session.scalars(
            select(EntitlementEventRecord)
            .order_by(desc(EntitlementEventRecord.created_at), desc(EntitlementEventRecord.id))
            .limit(limit)
        )
    )
    mark_private(response)
    return AdminEntitlementEventsResponse(
        events=[_entitlement_event_response(event) for event in events]
    )


@router.get(
    "/entitlements/events",
    operation_id="listAdminEntitlementEvents",
    response_model=AdminEntitlementEventsResponse,
    tags=["Admin Entitlements"],
)
async def list_admin_entitlement_events(
    response: Response,
    owner_user_id: UUID,
    entitlement_id: str | None = None,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminEntitlementEventsResponse:
    _require_entitlement_operator(principal[1])
    events = await CommerceService(session).ledger.list_events(
        owner_user_id=owner_user_id,
        entitlement_id=entitlement_id,
    )
    await session.commit()
    mark_private(response)
    return AdminEntitlementEventsResponse(
        events=[_entitlement_event_response(event) for event in events]
    )


@router.post(
    "/entitlements/events",
    operation_id="adjustAdminEntitlement",
    response_model=AdminEntitlementAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Admin Entitlements"],
)
async def adjust_admin_entitlement(
    response: Response,
    payload: AdminEntitlementAdjustmentRequest,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminEntitlementAdjustmentResponse:
    staff_session, staff = principal
    _require_entitlement_operator(staff)
    try:
        event, created = await CommerceService(session).adjust_entitlement_as_staff(
            owner_user_id=payload.owner_user_id,
            entitlement_id=payload.entitlement_id,
            action=payload.action,
            quantity=payload.quantity,
            reason=payload.reason,
            source_ref=payload.source_ref,
            target_ref=payload.target_ref,
            actor_staff_user_id=staff.id,
            actor_session_id=staff_session.id,
        )
    except CommerceError as error:
        raise _commerce_problem(error) from error
    await session.commit()
    mark_private(response)
    if not created:
        response.status_code = status.HTTP_200_OK
    return AdminEntitlementAdjustmentResponse(
        event=_entitlement_event_response(event),
        created=created,
    )


def _require_privacy_operator(staff: StaffUser) -> None:
    if staff.role not in {"ops", "superadmin"}:
        raise ApiProblem(status=403, title="Privacy operator permission required")


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


@router.get(
    "/privacy/closures",
    operation_id="listAccountClosures",
    response_model=ClosureListResponse,
    tags=["Admin Privacy"],
)
async def list_account_closures(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> ClosureListResponse:
    _require_privacy_operator(principal[1])
    closures = await DataRightsService(
        session, _settings(request)
    ).list_pending_closures()
    mark_private(response)
    return ClosureListResponse(closures=[_closure_response(item) for item in closures])


@router.post(
    "/privacy/closures/{closure_id}/execute",
    operation_id="executeAccountClosure",
    response_model=ClosureResponse,
    tags=["Admin Privacy"],
)
async def execute_account_closure(
    request: Request,
    response: Response,
    closure_id: UUID,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> ClosureResponse:
    actor_session, actor = principal
    _require_privacy_operator(actor)
    try:
        closure = await DataRightsService(
            session, _settings(request)
        ).execute_closure(closure_id)
    except ClosureNotFoundError as error:
        raise ApiProblem(status=404, title="Account closure not found") from error
    except (ClosureNotReadyError, ClosureAlreadyExecutedError) as error:
        raise ApiProblem(status=409, title="Account closure is not ready") from error
    session.add(
        AdminAuditEvent(
            staff_user_id=actor.id,
            actor_session_id=actor_session.id,
            action="privacy.closure.execute",
            event_metadata={
                "target_id": str(closure.user_id),
                "status": closure.status,
            },
        )
    )
    await session.commit()
    mark_private(response)
    return _closure_response(closure)
