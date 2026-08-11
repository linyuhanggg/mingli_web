"""Admin-only cookie helpers. Separate from C-end identity cookies."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Response

from app.config import Settings

ADMIN_SESSION_COOKIE = "mingli_admin_session"
ADMIN_CSRF_COOKIE = "mingli_admin_csrf"


def _set_cookie(
    response: Response,
    *,
    key: str,
    value: str,
    httponly: bool,
    settings: Settings,
    max_age: int,
    expires_at: datetime,
) -> None:
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        expires=expires_at,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=httponly,
        samesite="lax",
    )


def set_admin_cookies(
    response: Response,
    *,
    settings: Settings,
    session_token: str,
    csrf_token: str,
    expires_at: datetime,
) -> None:
    remaining = int((expires_at - datetime.now(UTC)).total_seconds())
    max_age = max(remaining, 60)
    _set_cookie(
        response,
        key=ADMIN_SESSION_COOKIE,
        value=session_token,
        httponly=True,
        settings=settings,
        max_age=max_age,
        expires_at=expires_at,
    )
    _set_cookie(
        response,
        key=ADMIN_CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        settings=settings,
        max_age=max_age,
        expires_at=expires_at,
    )


def clear_admin_cookies(response: Response, *, settings: Settings) -> None:
    for key, httponly in (
        (ADMIN_SESSION_COOKIE, True),
        (ADMIN_CSRF_COOKIE, False),
    ):
        response.delete_cookie(
            key=key,
            path="/",
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            httponly=httponly,
            samesite="lax",
        )
