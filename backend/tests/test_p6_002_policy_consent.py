from typing import Any
from uuid import UUID

from app.commerce.models import Order
from app.identity.models import ConsentRecord
from app.identity.policy import CURRENT_POLICY_VERSION
from httpx import AsyncClient
from sqlalchemy import func, select
from tests.test_public_bazi_checkout_api import _seed_target


async def _create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def _otp_login(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    destination: str,
) -> dict[str, Any]:
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": "email", "destination": destination},
    )
    assert requested.status_code == 202, requested.text
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers=headers,
        json={"challenge_id": requested.json()["challenge_id"], "code": "246810"},
    )
    return {
        "status_code": verified.status_code,
        "body": verified.json(),
        "challenge_id": requested.json()["challenge_id"],
        "response": verified,
    }


async def _record_consents(
    client: AsyncClient,
    csrf_token: str,
    *,
    context: str,
    policy_version: str = CURRENT_POLICY_VERSION,
) -> list[Any]:
    recorded = []
    for policy_key in ("privacy", "terms"):
        response = await client.post(
            "/api/v1/auth/consents",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "policy_key": policy_key,
                "policy_version": policy_version,
                "context": context,
            },
        )
        recorded.append(response)
    return recorded


async def test_purchase_consent_is_written_and_required_for_checkout(
    client: AsyncClient,
    database: Any,
) -> None:
    guest = await _create_guest(client)
    logged_in = await _otp_login(client, guest, destination="p6-002-purchase@example.com")
    assert logged_in["status_code"] == 200, logged_in["response"].text
    user_id = UUID(logged_in["body"]["user_id"])
    headers = {"X-CSRF-Token": logged_in["body"]["csrf_token"]}
    target = await _seed_target(database, owner_user_id=user_id)

    missing = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "p6-002-missing-purchase"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert missing.status_code == 400, missing.text
    assert missing.json()["title"] == "Policy version is not current"
    async with database.sessions() as session:
        assert await session.scalar(select(func.count(Order.id))) == 0
        assert await session.scalar(select(func.count(ConsentRecord.id))) == 0

    written = await _record_consents(client, headers["X-CSRF-Token"], context="purchase")
    assert [item.status_code for item in written] == [201, 201]
    assert {item.json()["policy_key"] for item in written} == {"privacy", "terms"}
    assert {item.json()["policy_version"] for item in written} == {CURRENT_POLICY_VERSION}
    assert {item.json()["context"] for item in written} == {"purchase"}

    async with database.sessions() as session:
        records = list(await session.scalars(select(ConsentRecord)))
    assert {record.policy_key for record in records} == {"privacy", "terms"}
    assert {record.policy_version for record in records} == {CURRENT_POLICY_VERSION}
    assert {record.context for record in records} == {"purchase"}
    assert {str(record.user_id) for record in records} == {str(user_id)}

    created = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "p6-002-with-purchase"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert created.status_code == 201, created.text
    async with database.sessions() as session:
        assert await session.scalar(select(func.count(Order.id))) == 1


async def test_stale_policy_rejects_password_login_otp_login_and_checkout(
    client: AsyncClient,
    database: Any,
    monkeypatch: Any,
) -> None:
    guest = await _create_guest(client)
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=guest,
        json={"channel": "email", "destination": "p6-002-stale@example.com"},
    )
    assert requested.status_code == 202, requested.text
    registered = await client.post(
        "/api/v1/auth/register",
        headers=guest,
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": "246810",
            "password": "correct-password",
            "policy_version": CURRENT_POLICY_VERSION,
        },
    )
    assert registered.status_code == 200, registered.text
    headers = {"X-CSRF-Token": registered.json()["csrf_token"]}
    user_id = UUID(registered.json()["user_id"])
    written = await _record_consents(client, headers["X-CSRF-Token"], context="purchase")
    assert [item.status_code for item in written] == [201, 201]
    target = await _seed_target(database, owner_user_id=user_id)

    current = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "p6-002-stale-before"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert current.status_code == 201, current.text

    import app.identity.policy as policy_module

    monkeypatch.setattr(policy_module, "CURRENT_POLICY_VERSION", "development-preview-v0.2")

    expired_checkout = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "p6-002-stale-after"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert expired_checkout.status_code == 400, expired_checkout.text
    assert expired_checkout.json()["title"] == "Policy version is not current"

    await client.post("/api/v1/auth/logout", headers=headers)

    password_guest = await _create_guest(client)
    password_login = await client.post(
        "/api/v1/auth/password/login",
        headers=password_guest,
        json={
            "channel": "email",
            "destination": "p6-002-stale@example.com",
            "password": "correct-password",
        },
    )
    assert password_login.status_code == 400, password_login.text
    assert password_login.json()["title"] == "Policy version is not current"

    otp_guest = await _create_guest(client)
    otp_attempt = await _otp_login(client, otp_guest, destination="p6-002-stale@example.com")
    assert otp_attempt["status_code"] == 400, otp_attempt["response"].text
    assert otp_attempt["body"]["title"] == "Policy version is not current"

    retry = await client.post(
        "/api/v1/auth/otp/verify",
        headers=otp_guest,
        json={"challenge_id": otp_attempt["challenge_id"], "code": "246810"},
    )
    assert retry.status_code == 400, retry.text
    assert retry.json()["title"] == "Policy version is not current"
