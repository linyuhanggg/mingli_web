import hmac
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiProblem
from app.identity.cookies import CSRF_COOKIE, GUEST_COOKIE, SESSION_COOKIE
from app.identity.models import DeviceSession, GuestSession
from app.identity.repository import IdentityRepository
from app.identity.security import hash_token


async def database_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def _valid_double_submit(request: Request) -> tuple[str, str] | None:
    cookie_token = request.cookies.get(CSRF_COOKIE)
    header_token = request.headers.get("x-csrf-token")
    if not cookie_token or not header_token:
        return None
    if not hmac.compare_digest(cookie_token, header_token):
        return None
    return cookie_token, hash_token(cookie_token)


async def require_guest_csrf(
    request: Request,
    session: AsyncSession = Depends(database_session),
) -> GuestSession:
    guest_token = request.cookies.get(GUEST_COOKIE)
    csrf = _valid_double_submit(request)
    if not guest_token or csrf is None:
        raise ApiProblem(status=403, title="CSRF validation failed")

    _, csrf_hash = csrf
    guest = await IdentityRepository(session).get_active_guest_session(
        hash_token(guest_token), datetime.now(UTC)
    )
    if guest is None or not hmac.compare_digest(guest.csrf_token_hash, csrf_hash):
        raise ApiProblem(status=403, title="CSRF validation failed")
    return guest


async def require_guest_session(
    request: Request,
    session: AsyncSession = Depends(database_session),
) -> GuestSession:
    guest_token = request.cookies.get(GUEST_COOKIE)
    if not guest_token:
        raise ApiProblem(status=401, title="Guest session required")
    guest = await IdentityRepository(session).get_active_guest_session(
        hash_token(guest_token), datetime.now(UTC)
    )
    if guest is None:
        raise ApiProblem(status=401, title="Guest session required")
    return guest


async def require_device_session(
    request: Request,
    session: AsyncSession = Depends(database_session),
) -> DeviceSession:
    session_token = request.cookies.get(SESSION_COOKIE)
    if not session_token:
        raise ApiProblem(status=401, title="Authentication required")
    device_session = await IdentityRepository(session).get_active_device_session(
        hash_token(session_token), datetime.now(UTC)
    )
    if device_session is None:
        raise ApiProblem(status=401, title="Authentication required")
    return device_session


@dataclass(frozen=True, slots=True)
class Owner:
    kind: Literal["user", "guest"]
    id: UUID
    csrf_token_hash: str


async def require_owner(
    request: Request,
    session: AsyncSession = Depends(database_session),
) -> Owner:
    if request.cookies.get(SESSION_COOKIE) is not None:
        device_session = await require_device_session(request, session)
        return Owner(
            kind="user",
            id=device_session.user_id,
            csrf_token_hash=device_session.csrf_token_hash,
        )
    guest = await require_guest_session(request, session)
    return Owner(
        kind="guest",
        id=guest.id,
        csrf_token_hash=guest.csrf_token_hash,
    )


async def require_device_csrf(
    request: Request,
    device_session: DeviceSession = Depends(require_device_session),
) -> DeviceSession:
    csrf = _valid_double_submit(request)
    if csrf is None or not hmac.compare_digest(device_session.csrf_token_hash, csrf[1]):
        raise ApiProblem(status=403, title="CSRF validation failed")
    return device_session


async def require_owner_csrf(
    request: Request,
    owner: Owner = Depends(require_owner),
) -> Owner:
    csrf = _valid_double_submit(request)
    if csrf is None or not hmac.compare_digest(owner.csrf_token_hash, csrf[1]):
        raise ApiProblem(status=403, title="CSRF validation failed")
    return owner


def mark_private(response: Response) -> None:
    """Phase 2 profile/reading payloads must never be cached or indexed."""
    response.headers["cache-control"] = "private, no-store, max-age=0"
    response.headers["x-robots-tag"] = "noindex, nofollow, noarchive"
