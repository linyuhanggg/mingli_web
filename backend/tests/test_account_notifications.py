from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient


async def _create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def _login(client: AsyncClient, guest_headers: dict[str, str]) -> dict[str, str]:
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=guest_headers,
        json={"channel": "email", "destination": "notifications@example.com"},
    )
    assert requested.status_code == 202, requested.text
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers=guest_headers,
        json={"challenge_id": requested.json()["challenge_id"], "code": "246810"},
    )
    assert verified.status_code == 200, verified.text
    return {"X-CSRF-Token": verified.json()["csrf_token"]}


async def _notification(
    database: Any,
    *,
    owner_user_id: UUID,
    channel: str = "in_app",
    kind: str = "referral.reward.committed",
    secret: str = "must-not-leave-the-outbox",
) -> UUID:
    from app.commerce.models import NotificationOutbox

    async with database.sessions() as session:
        item = NotificationOutbox(
            owner_user_id=owner_user_id,
            kind=kind,
            dedupe_key=f"notification:{uuid4().hex}",
            payload={"channel": channel, "state": "committed", "secret": secret},
            status="sent",
            available_at=datetime(2026, 8, 14, 5, 0, tzinfo=UTC),
        )
        session.add(item)
        await session.commit()
        return item.id


async def test_account_notifications_are_private_and_project_only_in_app_facts(
    client: AsyncClient,
    database: Any,
) -> None:
    guest_headers = await _create_guest(client)
    await _login(client, guest_headers)
    account = await client.get("/api/v1/account")
    assert account.status_code == 200, account.text
    owner_user_id = UUID(account.json()["user_id"])

    from app.identity.models import User

    async with database.sessions() as session:
        other_user = User()
        session.add(other_user)
        await session.flush()
        other_user_id = other_user.id
        await session.commit()

    current_id = await _notification(database, owner_user_id=owner_user_id)
    await _notification(database, owner_user_id=owner_user_id, channel="email")
    await _notification(database, owner_user_id=other_user_id)

    listed = await client.get("/api/v1/account/notifications")
    assert listed.status_code == 200, listed.text
    assert listed.headers["cache-control"] == "private, no-store, max-age=0"
    body = listed.json()
    assert body["unread_count"] == 1
    assert [item["id"] for item in body["notifications"]] == [str(current_id)]
    item = body["notifications"][0]
    assert set(item) == {
        "id",
        "title",
        "summary",
        "available_at",
        "read_at",
        "target_href",
    }
    assert item["title"] == "邀请奖励已确认"
    assert item["target_href"] == "/account/invitations"
    assert item["read_at"] is None
    assert "secret" not in listed.text
    assert "payload" not in listed.text
    assert "owner_user_id" not in listed.text
    assert "referral.reward.committed" not in listed.text

    unread = await client.get("/api/v1/account/notifications?unread_only=true")
    assert unread.status_code == 200
    assert len(unread.json()["notifications"]) == 1


async def test_account_notifications_support_read_all_read_one_and_owned_soft_delete(
    client: AsyncClient,
    database: Any,
) -> None:
    guest_headers = await _create_guest(client)
    device_headers = await _login(client, guest_headers)
    account = await client.get("/api/v1/account")
    owner_user_id = UUID(account.json()["user_id"])

    from app.identity.models import User

    async with database.sessions() as session:
        other_user = User()
        session.add(other_user)
        await session.flush()
        other_user_id = other_user.id
        await session.commit()

    first_id = await _notification(database, owner_user_id=owner_user_id)
    second_id = await _notification(database, owner_user_id=owner_user_id)
    other_id = await _notification(database, owner_user_id=other_user_id)

    marked = await client.post(
        f"/api/v1/account/notifications/{first_id}/read",
        headers=device_headers,
    )
    assert marked.status_code == 200, marked.text
    assert marked.json()["read_at"] is not None

    unread = await client.get("/api/v1/account/notifications?unread_only=true")
    assert [item["id"] for item in unread.json()["notifications"]] == [str(second_id)]
    assert unread.json()["unread_count"] == 1

    read_all = await client.post(
        "/api/v1/account/notifications/read-all",
        headers=device_headers,
    )
    assert read_all.status_code == 200, read_all.text
    assert read_all.json() == {"unread_count": 0}

    deleted = await client.delete(
        f"/api/v1/account/notifications/{first_id}",
        headers=device_headers,
    )
    assert deleted.status_code == 204, deleted.text
    cross_user_delete = await client.delete(
        f"/api/v1/account/notifications/{other_id}",
        headers=device_headers,
    )
    assert cross_user_delete.status_code == 404, cross_user_delete.text

    remaining = await client.get("/api/v1/account/notifications")
    assert [item["id"] for item in remaining.json()["notifications"]] == [str(second_id)]
    assert remaining.json()["notifications"][0]["read_at"] is not None


async def test_account_notifications_require_a_verified_device(client: AsyncClient) -> None:
    response = await client.get("/api/v1/account/notifications")
    assert response.status_code == 401
