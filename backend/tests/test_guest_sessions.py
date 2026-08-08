import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select


def find_cookie(headers: list[str], name: str) -> str:
    return next(header for header in headers if header.startswith(f"{name}="))


async def test_guest_session_uses_opaque_security_cookies(client: AsyncClient) -> None:
    before = datetime.now(UTC)
    response = await client.post("/api/v1/guest-sessions")
    after = datetime.now(UTC)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert (
        before + timedelta(hours=23, minutes=59)
        <= datetime.fromisoformat(body["expires_at"])
        <= after + timedelta(hours=24, seconds=1)
    )
    assert len(body["csrf_token"]) >= 32

    cookies = response.headers.get_list("set-cookie")
    guest_cookie = find_cookie(cookies, "mingli_guest")
    csrf_cookie = find_cookie(cookies, "mingli_csrf")

    assert "HttpOnly" in guest_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "Secure" in guest_cookie
    assert "SameSite=lax" in guest_cookie
    assert "Max-Age=86400" in guest_cookie


async def test_guest_session_persists_only_token_hashes(
    client: AsyncClient,
    database: Any,
) -> None:
    await client.post("/api/v1/guest-sessions")
    raw_guest_token = client.cookies["mingli_guest"]
    raw_csrf_token = client.cookies["mingli_csrf"]

    models = __import__("app.identity.models", fromlist=["GuestSession"])
    async with database.sessions() as session:
        stored = (await session.scalars(select(models.GuestSession))).one()

    assert stored.token_hash == hashlib.sha256(raw_guest_token.encode()).hexdigest()
    assert stored.csrf_token_hash == hashlib.sha256(raw_csrf_token.encode()).hexdigest()
    assert raw_guest_token not in stored.token_hash
    assert raw_csrf_token not in stored.csrf_token_hash


async def test_creating_a_new_guest_session_revokes_the_previous_one(
    client: AsyncClient,
    database: Any,
) -> None:
    first = await client.post("/api/v1/guest-sessions")
    first_token = client.cookies["mingli_guest"]
    second = await client.post("/api/v1/guest-sessions")

    assert first.status_code == 201
    assert second.status_code == 201
    assert client.cookies["mingli_guest"] != first_token

    models = __import__("app.identity.models", fromlist=["GuestSession"])
    async with database.sessions() as session:
        stored = list(await session.scalars(select(models.GuestSession)))

    assert len(stored) == 2
    assert sum(item.revoked_at is not None for item in stored) == 1
