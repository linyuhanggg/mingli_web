from __future__ import annotations

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_sessions_lists_metadata_and_revokes_a_session(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        sessions = list(
            await session.scalars(
                select(StaffSession).where(StaffSession.staff_user_id == staff.id)
            )
        )
        assert len(sessions) == 1
        session_id = sessions[0].id

    listed = await client.get("/api/v1/admin/sessions")
    assert listed.status_code == 200, listed.text
    item = listed.json()["sessions"][0]
    assert item["id"] == str(session_id)
    assert item["actor"] == "ops@example.com"
    assert item["status"] == "active"
    assert "token_hash" not in listed.text
    assert "csrf_token_hash" not in listed.text

    revoked = await client.post(
        f"/api/v1/admin/sessions/{session_id}/revoke",
        headers=headers,
        json={"reason": "撤销异常员工会话"},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "revoked"

    async with database.sessions() as session:
        audits = list(
            await session.scalars(
                select(AdminAuditEvent).where(
                    AdminAuditEvent.action == "staff.session.revoked"
                )
            )
        )
    assert len(audits) == 1
    assert audits[0].event_metadata["reason"] == "撤销异常员工会话"


async def test_admin_sessions_require_superadmin_and_csrf(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        session_row = await session.scalar(
            select(StaffSession).where(StaffSession.staff_user_id == staff.id)
        )
        assert session_row is not None
        staff.role = "support"
        await session.commit()

    assert (await client.get("/api/v1/admin/sessions")).status_code == 403
    missing_csrf = await client.post(
        f"/api/v1/admin/sessions/{session_row.id}/revoke",
        json={"reason": "验证会话强退边界"},
    )
    assert missing_csrf.status_code == 403
    forbidden = await client.post(
        f"/api/v1/admin/sessions/{session_row.id}/revoke",
        headers=headers,
        json={"reason": "验证角色强退边界"},
    )
    assert forbidden.status_code == 403
