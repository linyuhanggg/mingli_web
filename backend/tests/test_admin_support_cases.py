from __future__ import annotations

from uuid import uuid4

import pytest
from app.admin.models import AdminAuditEvent, StaffUser
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


async def test_support_case_application_is_persisted_and_audited(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    owner_id = uuid4()
    async with database.sessions() as session:
        session.add(User(id=owner_id))
        await session.commit()

    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    created = await client.post(
        "/api/v1/admin/support-cases",
        headers=headers,
        json={
            "owner_user_id": str(owner_id),
            "subject_ref": "reading:version-1",
            "category": "delivery",
            "summary": "用户反馈报告未显示",
            "reason": "记录客服请求并交由运营处理",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "open"
    assert body["category"] == "delivery"
    assert body["owner_user_id"] == str(owner_id)
    assert "password" not in created.text

    listed = await client.get("/api/v1/admin/support-cases", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["cases"][0]["id"] == body["id"]
    assert listed.json()["cases"][0]["summary"] == "用户反馈报告未显示"

    async with database.sessions() as session:
        events = list(
            await session.scalars(
                select(AdminAuditEvent).where(
                    AdminAuditEvent.action == "support_case.created"
                )
            )
        )
        assert len(events) == 1
        assert events[0].event_metadata["case_id"] == body["id"]
        assert events[0].event_metadata["category"] == "delivery"
        assert "summary" not in events[0].event_metadata


async def test_support_cases_are_readable_by_finance_but_only_support_or_superadmin_can_submit(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "finance"
        await session.commit()

    listed = await client.get("/api/v1/admin/support-cases", headers=headers)
    assert listed.status_code == 200, listed.text

    forbidden = await client.post(
        "/api/v1/admin/support-cases",
        headers=headers,
        json={
            "subject_ref": "user:case-1",
            "category": "account",
            "summary": "需要人工核实",
            "reason": "财务不应提交客服案件",
        },
    )
    assert forbidden.status_code == 403, forbidden.text


async def test_support_case_submission_requires_csrf_and_rejects_unknown_owner(
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

    payload = {
        "owner_user_id": str(uuid4()),
        "subject_ref": "user:unknown",
        "category": "account",
        "summary": "用户请求人工协助",
        "reason": "记录未找到用户的客服请求",
    }
    missing_csrf = await client.post("/api/v1/admin/support-cases", json=payload)
    assert missing_csrf.status_code == 403

    unknown_owner = await client.post(
        "/api/v1/admin/support-cases",
        headers=headers,
        json=payload,
    )
    assert unknown_owner.status_code == 404, unknown_owner.text


@pytest.mark.parametrize(
    "category",
    ["profile_correction", "algorithm_review", "after_sales", "compensation"],
)
async def test_support_case_accepts_operational_queue_categories(
    client: AsyncClient,
    database,
    category: str,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    response = await client.post(
        "/api/v1/admin/support-cases",
        headers=headers,
        json={
            "subject_ref": "subject:version-1",
            "category": category,
            "summary": f"申请{category}",
            "reason": "按案件类型进入对应运营队列",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["category"] == category
