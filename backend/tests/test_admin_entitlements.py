from __future__ import annotations

from uuid import uuid4

from app.admin.models import AdminAuditEvent, StaffUser
from app.commerce.models import EntitlementEventRecord
from app.commerce.service import CommerceService
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


async def test_admin_entitlement_adjustment_is_idempotent_and_audited(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    owner_id = uuid4()
    async with database.sessions() as session:
        session.add(User(id=owner_id))
        await session.commit()

    headers = await _admin_headers(client)
    grant_payload = {
        "owner_user_id": str(owner_id),
        "entitlement_id": "manual:case-1",
        "action": "grant",
        "quantity": 2,
        "reason": "客服补发体验次数",
        "source_ref": "case-1-grant",
        "target_ref": "support-case-1",
    }
    granted = await client.post(
        "/api/v1/admin/entitlements/events",
        headers=headers,
        json=grant_payload,
    )
    assert granted.status_code == 201, granted.text
    assert granted.json()["event"]["kind"] == "GRANT"
    assert granted.json()["created"] is True

    replayed = await client.post(
        "/api/v1/admin/entitlements/events",
        headers=headers,
        json=grant_payload,
    )
    assert replayed.status_code == 200, replayed.text
    assert replayed.json()["event"]["id"] == granted.json()["event"]["id"]
    assert replayed.json()["created"] is False

    revoked = await client.post(
        "/api/v1/admin/entitlements/events",
        headers=headers,
        json={
            **grant_payload,
            "action": "revoke",
            "quantity": 1,
            "reason": "客服撤回多发次数",
            "source_ref": "case-1-revoke",
        },
    )
    assert revoked.status_code == 201, revoked.text
    assert revoked.json()["event"]["kind"] == "EXPIRE"

    events = await client.get(
        "/api/v1/admin/entitlements/events",
        params={"owner_user_id": str(owner_id)},
    )
    assert events.status_code == 200, events.text
    assert [item["kind"] for item in events.json()["events"]] == ["EXPIRE", "GRANT"]

    async with database.sessions() as session:
        stored_events = list(
            await session.scalars(
                select(EntitlementEventRecord).where(
                    EntitlementEventRecord.owner_user_id == owner_id
                )
            )
        )
        assert len(stored_events) == 2
        audit_rows = list(
            await session.scalars(
                select(AdminAuditEvent).where(
                    AdminAuditEvent.action == "entitlement.adjusted"
                )
            )
        )
        assert len(audit_rows) == 2
        assert {row.event_metadata["action"] for row in audit_rows} == {"grant", "revoke"}
    assert all(row.event_metadata["reason"] for row in audit_rows)


async def test_admin_recent_entitlements_lists_real_events_without_owner_filter(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        owner = User()
        session.add(owner)
        await session.flush()
        session.add(
            EntitlementEventRecord(
                owner_user_id=owner.id,
                entitlement_id="order:recent-1",
                kind="GRANT",
                quantity=2,
                source_type="test",
                source_ref="recent-grant-1",
                target_ref="reading-1",
            )
        )
        await session.commit()

    await _admin_headers(client)
    response = await client.get("/api/v1/admin/entitlements/events/recent")

    assert response.status_code == 200, response.text
    assert response.json()["events"][0]["entitlement_id"] == "order:recent-1"
    assert response.json()["events"][0]["owner_user_id"] == str(owner.id)


async def test_admin_recent_entitlements_forbids_support(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    response = await client.get(
        "/api/v1/admin/entitlements/events/recent",
        headers=headers,
    )

    assert response.status_code == 403


async def test_admin_entitlement_mutation_requires_csrf_and_operator_role(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    owner_id = uuid4()
    async with database.sessions() as session:
        session.add(User(id=owner_id))
        await session.commit()

    headers = await _admin_headers(client)
    missing_csrf = await client.post(
        "/api/v1/admin/entitlements/events",
        json={
            "owner_user_id": str(owner_id),
            "entitlement_id": "manual:case-2",
            "action": "grant",
            "quantity": 1,
            "reason": "补偿",
            "source_ref": "case-2-grant",
        },
    )
    assert missing_csrf.status_code == 403

    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    forbidden = await client.post(
        "/api/v1/admin/entitlements/events",
        headers=headers,
        json={
            "owner_user_id": str(owner_id),
            "entitlement_id": "manual:case-2",
            "action": "grant",
            "quantity": 1,
            "reason": "补偿",
            "source_ref": "case-2-grant",
        },
    )
    assert forbidden.status_code == 403


async def test_admin_entitlement_revoke_follows_ledger_state_and_compensation_is_separate(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    owner_id = uuid4()
    async with database.sessions() as session:
        session.add(User(id=owner_id))
        await session.commit()

    headers = await _admin_headers(client)
    for entitlement_id, reserve_kind, expected_revoke_kind in (
        ("manual:reserved", "RESERVE", "RELEASE"),
        ("manual:consumed", "CONSUME", "REVERSE"),
    ):
        granted = await client.post(
            "/api/v1/admin/entitlements/events",
            headers=headers,
            json={
                "owner_user_id": str(owner_id),
                "entitlement_id": entitlement_id,
                "action": "grant",
                "reason": "测试生命周期",
                "source_ref": f"{entitlement_id}:grant",
            },
        )
        assert granted.status_code == 201, granted.text
        async with database.sessions() as session:
            commerce = CommerceService(session)
            await commerce.append_entitlement_event(
                owner_user_id=owner_id,
                entitlement_id=entitlement_id,
                kind="RESERVE",
                quantity=1,
                source_type="test",
                source_ref=f"{entitlement_id}:reserve",
            )
            if reserve_kind == "CONSUME":
                await commerce.append_entitlement_event(
                    owner_user_id=owner_id,
                    entitlement_id=entitlement_id,
                    kind="CONSUME",
                    quantity=1,
                    source_type="test",
                    source_ref=f"{entitlement_id}:consume",
                )
            await session.commit()

        revoked = await client.post(
            "/api/v1/admin/entitlements/events",
            headers=headers,
            json={
                "owner_user_id": str(owner_id),
                "entitlement_id": entitlement_id,
                "action": "revoke",
                "reason": "测试撤回",
                "source_ref": f"{entitlement_id}:revoke",
            },
        )
        assert revoked.status_code == 201, revoked.text
        assert revoked.json()["event"]["kind"] == expected_revoke_kind

    compensated = await client.post(
        "/api/v1/admin/entitlements/events",
        headers=headers,
        json={
            "owner_user_id": str(owner_id),
            "entitlement_id": "manual:compensation-1",
            "action": "compensate",
            "reason": "服务补偿",
            "source_ref": "compensation-1",
            "target_ref": "reading-1",
        },
    )
    assert compensated.status_code == 201, compensated.text
    assert compensated.json()["event"]["source_type"] == "admin_compensation"
