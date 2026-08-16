from __future__ import annotations

from app.admin.models import AdminAuditEvent, StaffUser
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_audit_lists_safe_event_metadata_and_actor(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        session.add(
            AdminAuditEvent(
                staff_user_id=staff.id,
                actor_session_id=None,
                action="catalog.version.published",
                event_metadata={
                    "reason": "通过商品发布检查",
                    "target_id": "version-1",
                    "payload": "do-not-expose",
                },
            )
        )
        await session.commit()

    response = await client.get(
        "/api/v1/admin/audit",
        params={"action": "catalog.version.published"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["events"]) == 1
    event = body["events"][0]
    assert event["action"] == "catalog.version.published"
    assert event["actor"] == "ops@example.com"
    assert event["metadata"] == {
        "reason": "通过商品发布检查",
        "target_id": "version-1",
    }
    assert "do-not-expose" not in response.text
    assert response.headers["cache-control"] == "private, no-store, max-age=0"


async def test_admin_audit_is_superadmin_only(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    forbidden = await client.get("/api/v1/admin/audit")
    assert forbidden.status_code == 403
