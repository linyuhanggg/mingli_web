from __future__ import annotations

from uuid import uuid4

from app.admin.models import AdminAuditEvent, StaffUser
from app.commerce.models import NotificationOutbox
from app.identity.models import User
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def _make_superadmin(database) -> NotificationOutbox:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "superadmin"
        user = User()
        session.add(user)
        await session.flush()
        item = NotificationOutbox(
            owner_user_id=user.id,
            kind="reading.accepted",
            dedupe_key=f"notification-{uuid4().hex}",
            payload={"channel": "email", "subject": "隐藏内容"},
            status="failed",
            attempt_count=3,
            last_error="provider timeout",
        )
        session.add(item)
        await session.commit()
        return item


async def test_admin_notifications_lists_without_payload_and_retries_failed_item(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    item = await _make_superadmin(database)

    listed = await client.get("/api/v1/admin/notifications")
    assert listed.status_code == 200, listed.text
    assert listed.json()["notifications"][0]["id"] == str(item.id)
    assert listed.json()["notifications"][0]["channel"] == "email"
    assert "payload" not in listed.json()["notifications"][0]

    retried = await client.post(
        f"/api/v1/admin/notifications/{item.id}/retry",
        headers=headers,
        json={"reason": "供应商恢复，重新投递通知"},
    )
    assert retried.status_code == 200, retried.text
    assert retried.json()["status"] == "pending"
    assert retried.json()["attempt_count"] == 3

    async with database.sessions() as session:
        audits = list(
            await session.scalars(
                select(AdminAuditEvent).where(
                    AdminAuditEvent.action == "notification.retry"
                )
            )
        )
    assert len(audits) == 1
    assert audits[0].event_metadata["reason"] == "供应商恢复，重新投递通知"


async def test_admin_notifications_require_superadmin_and_csrf(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    item = await _make_superadmin(database)
    missing_csrf = await client.post(
        f"/api/v1/admin/notifications/{item.id}/retry",
        json={"reason": "验证通知重试边界"},
    )
    assert missing_csrf.status_code == 403

    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    assert (await client.get("/api/v1/admin/notifications")).status_code == 403
    forbidden = await client.post(
        f"/api/v1/admin/notifications/{item.id}/retry",
        headers=headers,
        json={"reason": "验证通知角色边界"},
    )
    assert forbidden.status_code == 403
