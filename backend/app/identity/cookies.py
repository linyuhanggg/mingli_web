from datetime import datetime

from fastapi import Response

from app.config import Settings

GUEST_COOKIE = "mingli_guest"
SESSION_COOKIE = "mingli_session"
CSRF_COOKIE = "mingli_csrf"


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


def set_guest_cookies(
    response: Response,
    *,
    settings: Settings,
    guest_token: str,
    csrf_token: str,
    expires_at: datetime,
) -> None:
    _set_cookie(
        response,
        key=GUEST_COOKIE,
        value=guest_token,
        httponly=True,
        settings=settings,
        max_age=24 * 60 * 60,
        expires_at=expires_at,
    )
    _set_cookie(
        response,
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        settings=settings,
        max_age=24 * 60 * 60,
        expires_at=expires_at,
    )


def set_device_cookies(
    response: Response,
    *,
    settings: Settings,
    session_token: str,
    csrf_token: str,
    expires_at: datetime,
) -> None:
    max_age = settings.device_session_days * 24 * 60 * 60
    _set_cookie(
        response,
        key=SESSION_COOKIE,
        value=session_token,
        httponly=True,
        settings=settings,
        max_age=max_age,
        expires_at=expires_at,
    )
    _set_cookie(
        response,
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        settings=settings,
        max_age=max_age,
        expires_at=expires_at,
    )


def clear_device_cookies(response: Response, *, settings: Settings) -> None:
    for key in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(
            key=key,
            path="/",
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            httponly=key == SESSION_COOKIE,
            samesite="lax",
        )
