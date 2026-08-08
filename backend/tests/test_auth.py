from typing import Any
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select


async def create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def request_otp(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    channel: str = "phone",
    destination: str = "13800138000",
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": channel, "destination": destination},
    )
    assert response.status_code == 202, response.text
    return response.json()


async def verify_otp(
    client: AsyncClient,
    headers: dict[str, str],
    challenge_id: str,
    code: str = "246810",
):  # type: ignore[no-untyped-def]
    return await client.post(
        "/api/v1/auth/otp/verify",
        headers=headers,
        json={"challenge_id": challenge_id, "code": code},
    )


async def login_with_phone(client: AsyncClient) -> tuple[dict[str, Any], dict[str, str]]:
    headers = await create_guest(client)
    challenge = await request_otp(client, headers)
    response = await verify_otp(client, headers, challenge["challenge_id"])
    assert response.status_code == 200, response.text
    return response.json(), {"X-CSRF-Token": response.json()["csrf_token"]}


async def test_verified_phone_otp_creates_user_identity_and_device_session(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)
    challenge = await request_otp(client, headers)

    assert challenge["development_code"] == "246810"
    verified = await verify_otp(client, headers, challenge["challenge_id"])

    assert verified.status_code == 200
    body = verified.json()
    UUID(body["user_id"])
    UUID(body["session_id"])
    session_cookie = next(
        value
        for value in verified.headers.get_list("set-cookie")
        if value.startswith("mingli_session=")
    )
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "Max-Age=2592000" in session_cookie

    account = await client.get("/api/v1/account")
    assert account.status_code == 200
    assert account.json() == {
        "user_id": body["user_id"],
        "identities": [
            {
                "id": account.json()["identities"][0]["id"],
                "provider": "phone",
                "masked_destination": "+86 138****8000",
                "verified_at": account.json()["identities"][0]["verified_at"],
            }
        ],
    }


async def test_repeat_login_resolves_the_same_user(
    client: AsyncClient,
    database: Any,
) -> None:
    first, csrf_headers = await login_with_phone(client)
    logout = await client.post("/api/v1/auth/logout", headers=csrf_headers)
    assert logout.status_code == 204

    second_headers = await create_guest(client)
    challenge = await request_otp(client, second_headers)
    second = await verify_otp(client, second_headers, challenge["challenge_id"])

    assert second.status_code == 200
    assert second.json()["user_id"] == first["user_id"]

    models = __import__("app.identity.models", fromlist=["User", "LoginIdentity", "DeviceSession"])
    async with database.sessions() as session:
        users = list(await session.scalars(select(models.User)))
        identities = list(await session.scalars(select(models.LoginIdentity)))
        device_sessions = list(await session.scalars(select(models.DeviceSession)))

    assert len(users) == 1
    assert len(identities) == 1
    assert len(device_sessions) == 2
    assert sum(item.revoked_at is not None for item in device_sessions) == 1


async def test_email_is_normalized_and_raw_destination_is_not_persisted(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    challenge = await request_otp(
        client,
        headers,
        channel="email",
        destination="  Cherry@Example.COM ",
    )
    response = await verify_otp(client, headers, challenge["challenge_id"])
    assert response.status_code == 200

    models = __import__("app.identity.models", fromlist=["LoginIdentity", "AuditEvent"])
    async with database.sessions() as session:
        identity = (await session.scalars(select(models.LoginIdentity))).one()
        audit = (await session.scalars(select(models.AuditEvent))).one()

    assert identity.provider == "email"
    assert identity.masked_destination == "c***@example.com"
    assert len(identity.provider_subject_hash) == 64
    assert "cherry@example.com" not in identity.provider_subject_hash
    assert "Cherry@Example.COM" not in str(audit.event_metadata)


async def test_invalid_code_does_not_create_a_user(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    challenge = await request_otp(client, headers)
    response = await verify_otp(client, headers, challenge["challenge_id"], "111111")

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid or expired code"

    models = __import__("app.identity.models", fromlist=["User"])
    async with database.sessions() as session:
        users = list(await session.scalars(select(models.User)))
    assert users == []


async def test_request_rate_limit_is_generic(client: AsyncClient) -> None:
    headers = await create_guest(client)
    first = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": "phone", "destination": "13800138000"},
    )
    second = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": "phone", "destination": "13800138000"},
    )

    assert first.status_code == 202
    assert second.status_code == 429
    assert second.json()["title"] == "Please wait before requesting another code"


async def test_logout_revokes_the_current_device_session(
    client: AsyncClient,
) -> None:
    _, csrf_headers = await login_with_phone(client)

    logout = await client.post("/api/v1/auth/logout", headers=csrf_headers)
    account = await client.get("/api/v1/account")

    assert logout.status_code == 204
    assert "Max-Age=0" in "\n".join(logout.headers.get_list("set-cookie"))
    assert account.status_code == 401


async def test_account_requires_a_device_session(client: AsyncClient) -> None:
    response = await client.get("/api/v1/account")

    assert response.status_code == 401
    assert response.json()["title"] == "Authentication required"
