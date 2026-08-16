from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from app.admin.models import AdminAuditEvent
from httpx import AsyncClient
from sqlalchemy import select


async def create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def login(client: AsyncClient, headers: dict[str, str]) -> dict[str, str]:
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": "email", "destination": "privacy@example.com"},
    )
    assert requested.status_code == 202, requested.text
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers=headers,
        json={"challenge_id": requested.json()["challenge_id"], "code": "246810"},
    )
    assert verified.status_code == 200, verified.text
    return {"X-CSRF-Token": verified.json()["csrf_token"]}


async def create_profile(client: AsyncClient, headers: dict[str, str]) -> str:
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "隐私测试"},
    )
    assert draft.status_code == 201, draft.text
    confirmed = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市朝阳区",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "longitude": 116.4074,
            "latitude": 39.9042,
            "coordinate_source": "user_confirmed",
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    return confirmed.json()["profile_id"]


async def test_account_export_and_single_profile_delete(
    client: AsyncClient,
) -> None:
    guest_headers = await create_guest(client)
    profile_id = await create_profile(client, guest_headers)
    device_headers = await login(client, guest_headers)

    exported = await client.get("/api/v1/account/export")
    assert exported.status_code == 200, exported.text
    assert exported.headers["cache-control"] == "private, no-store, max-age=0"
    payload = exported.json()["payload"]
    assert payload["user"]["status"] == "active"
    assert payload["profiles"][0]["payload"]["location"] == "北京市朝阳区"
    assert payload["notification_preferences"] == {
        "in_app_enabled": True,
        "email_enabled": False,
        "sms_enabled": False,
    }
    assert "payload_ciphertext" not in exported.text

    deleted = await client.delete(
        f"/api/v1/profiles/{profile_id}",
        headers=device_headers,
    )
    assert deleted.status_code == 204, deleted.text
    profiles = await client.get("/api/v1/profiles")
    assert profiles.status_code == 200
    assert profiles.json() == {"profiles": []}


async def test_account_notification_preferences_are_private_and_updateable(
    client: AsyncClient,
) -> None:
    guest_headers = await create_guest(client)
    device_headers = await login(client, guest_headers)

    defaults = await client.get("/api/v1/account/notification-preferences")
    assert defaults.status_code == 200, defaults.text
    assert defaults.headers["cache-control"] == "private, no-store, max-age=0"
    assert defaults.json() == {
        "in_app_enabled": True,
        "email_enabled": False,
        "sms_enabled": False,
    }

    updated = await client.put(
        "/api/v1/account/notification-preferences",
        headers=device_headers,
        json={
            "in_app_enabled": True,
            "email_enabled": True,
            "sms_enabled": False,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["email_enabled"] is True

    exported = await client.get("/api/v1/account/export")
    assert exported.status_code == 200, exported.text
    assert exported.json()["payload"]["notification_preferences"] == {
        "in_app_enabled": True,
        "email_enabled": True,
        "sms_enabled": False,
    }


async def test_revoke_all_sessions_revokes_current_device(
    client: AsyncClient,
    database: Any,
) -> None:
    guest_headers = await create_guest(client)
    device_headers = await login(client, guest_headers)

    revoked = await client.post(
        "/api/v1/auth/sessions/revoke-all",
        headers=device_headers,
    )
    assert revoked.status_code == 204, revoked.text
    account = await client.get("/api/v1/account")
    assert account.status_code == 401

    from app.identity.models import DeviceSession

    async with database.sessions() as session:
        sessions = list(await session.scalars(select(DeviceSession)))
    assert sessions
    assert all(item.revoked_at is not None for item in sessions)


async def test_closure_is_idempotent_reversible_and_admin_executable(
    client: AsyncClient,
    database: Any,
) -> None:
    guest_headers = await create_guest(client)
    device_headers = await login(client, guest_headers)

    requested = await client.post(
        "/api/v1/account/closure",
        headers=device_headers,
    )
    assert requested.status_code == 201, requested.text
    closure_id = requested.json()["closure_id"]
    replayed = await client.post(
        "/api/v1/account/closure",
        headers=device_headers,
    )
    assert replayed.status_code == 200
    assert replayed.json()["closure_id"] == closure_id

    cancelled = await client.delete(
        "/api/v1/account/closure",
        headers=device_headers,
    )
    assert cancelled.status_code == 204, cancelled.text
    assert (await client.get("/api/v1/account/closure")).json() is None

    requested_again = await client.post(
        "/api/v1/account/closure",
        headers=device_headers,
    )
    assert requested_again.status_code == 201
    closure_id = UUID(requested_again.json()["closure_id"])

    from app.privacy.models import AccountClosureRequest

    async with database.sessions() as session:
        closure = await session.get(AccountClosureRequest, closure_id)
        assert closure is not None
        closure.cancel_until = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()

    admin_login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert admin_login.status_code == 200, admin_login.text
    admin_headers = {"X-CSRF-Token": admin_login.json()["csrf_token"]}
    queue = await client.get(
        "/api/v1/admin/privacy/closures",
    )
    assert queue.status_code == 200, queue.text
    assert queue.json()["closures"][0]["closure_id"] == str(closure_id)

    executed = await client.post(
        f"/api/v1/admin/privacy/closures/{closure_id}/execute",
        headers=admin_headers,
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["status"] == "executed"
    async with database.sessions() as session:
        audit = await session.scalar(
            select(AdminAuditEvent).where(
                AdminAuditEvent.action == "privacy.closure.execute"
            )
        )
    assert audit is not None
    assert audit.event_metadata["target_id"] == executed.json()["user_id"]
    account = await client.get("/api/v1/account")
    assert account.status_code == 401


@pytest.mark.asyncio
async def test_closure_cannot_execute_before_cancel_window(
    client: AsyncClient,
) -> None:
    guest_headers = await create_guest(client)
    device_headers = await login(client, guest_headers)
    requested = await client.post(
        "/api/v1/account/closure",
        headers=device_headers,
    )
    assert requested.status_code == 201
    admin_login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert admin_login.status_code == 200
    admin_headers = {"X-CSRF-Token": admin_login.json()["csrf_token"]}
    response = await client.post(
        f"/api/v1/admin/privacy/closures/{requested.json()['closure_id']}/execute",
        headers=admin_headers,
    )
    assert response.status_code == 409
