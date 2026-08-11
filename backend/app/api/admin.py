"""Staff admin HTTP surface."""

from __future__ import annotations

import hmac
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.cookies import (
    ADMIN_CSRF_COOKIE,
    ADMIN_SESSION_COOKIE,
    clear_admin_cookies,
    set_admin_cookies,
)
from app.admin.models import StaffSession, StaffUser
from app.admin.repository import AdminRepository
from app.admin.schemas import (
    AdminLoginRequest,
    AdminMeResponse,
    AdminOverviewResponse,
    AdminSessionResponse,
)
from app.admin.service import AdminAuthError, AdminAuthService, build_stub_overview
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.api.rate_guard import check_rate_limiter
from app.config import Settings
from app.identity.security import hash_token
from app.readings.rate_limit import WindowRateLimiter

router = APIRouter(prefix="/admin", tags=["Admin Auth"])


def _settings(request: Request) -> Settings:
    return request.app.state.settings


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
        role=created.staff.role,  # type: ignore[arg-type]
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
        role=staff.role,  # type: ignore[arg-type]
        email=staff.email,  # type: ignore[arg-type]
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
    _principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminOverviewResponse:
    mark_private(response)
    return build_stub_overview()
