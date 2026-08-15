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


async def test_admin_reconciliation_runs_a_normalized_snapshot_and_lists_differences(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    payload = {
        "channel": "closed",
        "reason": "核对测试渠道到账事实",
        "payments": [
            {
                "transaction_id": "tx-remote",
                "status": "succeeded",
                "amount_minor": 100,
                "currency": "cny",
            }
        ],
        "refunds": [],
    }

    created = await client.post(
        "/api/v1/admin/reconciliation/runs",
        headers=headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["channel"] == "closed"
    assert body["status"] == "has_differences"
    assert body["difference_count"] == 1
    assert body["items"][0]["discrepancy"] == "provider_only"
    assert created.headers["cache-control"] == "private, no-store, max-age=0"

    listed = await client.get("/api/v1/admin/reconciliation")
    assert listed.status_code == 200, listed.text
    assert listed.json()["runs"][0]["id"] == body["id"]
    detail = await client.get(f"/api/v1/admin/reconciliation/runs/{body['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["items"][0]["reference"] == "tx-remote"

    async with database.sessions() as session:
        audits = list(
            await session.scalars(
                select(AdminAuditEvent).where(
                    AdminAuditEvent.action == "payment.reconciliation.run"
                )
            )
        )
    assert len(audits) == 1
    assert audits[0].event_metadata["reason"] == "核对测试渠道到账事实"


async def test_admin_reconciliation_requires_csrf_and_finance_operator(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    await _admin_headers(client)
    payload = {"channel": "closed", "reason": "验证对账写入边界"}
    missing_csrf = await client.post(
        "/api/v1/admin/reconciliation/runs",
        json=payload,
    )
    assert missing_csrf.status_code == 403

    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    forbidden = await client.get("/api/v1/admin/reconciliation")
    assert forbidden.status_code == 403
    forbidden_write = await client.post(
        "/api/v1/admin/reconciliation/runs",
        headers=headers,
        json=payload,
    )
    assert forbidden_write.status_code == 403
