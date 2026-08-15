from datetime import UTC, datetime, timedelta

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.admin.passwords import hash_password, verify_password
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_staff_lists_and_updates_status_and_role(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    now = datetime.now(UTC)
    async with database.sessions() as session:
        target = StaffUser(
            email="analyst@example.com",
            password_hash="not-returned",
            display_name="分析员工",
            role="support",
            status="active",
        )
        session.add(target)
        await session.flush()
        session.add(
            StaffSession(
                staff_user_id=target.id,
                token_hash="target-token-hash",
                csrf_token_hash="target-csrf-hash",
                expires_at=now + timedelta(hours=4),
                last_seen_at=now,
            )
        )
        await session.commit()
        target_id = target.id

    listed = await client.get("/api/v1/admin/staff")
    assert listed.status_code == 200, listed.text
    item = next(item for item in listed.json()["staff"] if item["id"] == str(target_id))
    assert item["email"] == "analyst@example.com"
    assert item["role"] == "support"
    assert item["status"] == "active"
    assert item["unrevoked_session_count"] == 1
    assert "password_hash" not in listed.text

    suspended = await client.post(
        f"/api/v1/admin/staff/{target_id}/status",
        headers=headers,
        json={"status": "suspended", "reason": "员工离岗，立即停用"},
    )
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["status"] == "suspended"

    async with database.sessions() as session:
        target_row = await session.get(StaffUser, target_id)
        target_session = await session.scalar(
            select(StaffSession).where(StaffSession.staff_user_id == target_id)
        )
        assert target_row is not None
        assert target_session is not None
        assert target_row.status == "suspended"
        assert target_session.revoked_at is not None

    reactivated = await client.post(
        f"/api/v1/admin/staff/{target_id}/status",
        headers=headers,
        json={"status": "active", "reason": "员工恢复值班"},
    )
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["status"] == "active"

    role_changed = await client.post(
        f"/api/v1/admin/staff/{target_id}/role",
        headers=headers,
        json={"role": "finance", "reason": "调整职责范围"},
    )
    assert role_changed.status_code == 200, role_changed.text
    assert role_changed.json()["role"] == "finance"

    async with database.sessions() as session:
        actions = list(
            await session.scalars(
                select(AdminAuditEvent.action).where(
                    AdminAuditEvent.staff_user_id == (await session.scalar(
                        select(StaffUser.id).where(StaffUser.email == "ops@example.com")
                    ))
                )
            )
        )
    assert "staff.status.updated" in actions
    assert "staff.role.updated" in actions


async def test_admin_staff_forbids_support_and_self_lockout(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff_id = staff.id
        staff.role = "support"
        await session.commit()

    assert (await client.get("/api/v1/admin/staff")).status_code == 403
    create_payload = {
        "email": "new-support@example.com",
        "display_name": "新客服",
        "role": "support",
        "password": "initial-password-123",
        "reason": "补充客服排班",
    }
    missing_csrf = await client.post(
        "/api/v1/admin/staff",
        json=create_payload,
    )
    assert missing_csrf.status_code == 403
    create_forbidden = await client.post(
        "/api/v1/admin/staff",
        headers=headers,
        json=create_payload,
    )
    assert create_forbidden.status_code == 403
    forbidden = await client.post(
        f"/api/v1/admin/staff/{staff_id}/status",
        headers=headers,
        json={"status": "suspended", "reason": "不能自锁"},
    )
    assert forbidden.status_code == 403


async def test_admin_staff_resets_password_without_echoing_secret(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        target = StaffUser(
            email="reset@example.com",
            password_hash=hash_password("old-password"),
            display_name="待重置员工",
            role="ops",
            status="active",
        )
        session.add(target)
        await session.commit()
        target_id = target.id

    reset = await client.post(
        f"/api/v1/admin/staff/{target_id}/password-reset",
        headers=headers,
        json={"password": "new-password-123", "reason": "员工请求重置密码"},
    )
    assert reset.status_code == 200, reset.text
    assert "new-password-123" not in reset.text

    async with database.sessions() as session:
        target_row = await session.get(StaffUser, target_id)
        audit = await session.scalar(
            select(AdminAuditEvent).where(AdminAuditEvent.action == "staff.password.reset")
        )
        assert target_row is not None
        assert verify_password("new-password-123", target_row.password_hash)
        assert audit is not None
        assert "password" not in audit.event_metadata


async def test_admin_staff_creates_hashed_account_and_rejects_duplicate_email(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    payload = {
        "email": "new-operator@example.com",
        "display_name": "新运营",
        "role": "ops",
        "password": "initial-password-123",
        "reason": "补充运营值班",
    }

    created = await client.post(
        "/api/v1/admin/staff",
        headers=headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    assert created.json()["email"] == payload["email"]
    assert created.json()["role"] == payload["role"]
    assert "password" not in created.json()
    assert "password_hash" not in created.text

    duplicate = await client.post(
        "/api/v1/admin/staff",
        headers=headers,
        json=payload,
    )
    assert duplicate.status_code == 409, duplicate.text

    async with database.sessions() as session:
        staff_rows = list(
            await session.scalars(
                select(StaffUser).where(StaffUser.email == payload["email"])
            )
        )
        audit = await session.scalar(
            select(AdminAuditEvent).where(AdminAuditEvent.action == "staff.created")
        )
        assert len(staff_rows) == 1
        assert verify_password(payload["password"], staff_rows[0].password_hash)
        assert audit is not None
        assert payload["password"] not in str(audit.event_metadata)
