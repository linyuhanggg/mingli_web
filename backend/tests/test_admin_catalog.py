from __future__ import annotations

from uuid import uuid4

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


async def test_admin_catalog_can_publish_an_offer_and_records_audit(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)

    family = await client.post(
        "/api/v1/admin/catalog/families",
        headers=headers,
        json={
            "key": "bazi-deep-reading",
            "label": "八字深度解读",
            "reason": "建立正式商品族",
        },
    )
    assert family.status_code == 201, family.text
    family_id = family.json()["id"]

    version = await client.post(
        "/api/v1/admin/catalog/versions",
        headers=headers,
        json={
            "family_id": family_id,
            "version": "v1",
            "price_minor": 9900,
            "currency": "cny",
            "contract_version": "reading-document-v1",
            "follow_up_count": 2,
            "follow_up_window_seconds": 90 * 86400,
            "reason": "建立首个交付版本",
        },
    )
    assert version.status_code == 201, version.text
    version_id = version.json()["id"]

    offer = await client.post(
        "/api/v1/admin/catalog/offers",
        headers=headers,
        json={
            "product_version_id": version_id,
            "channel": "closed",
            "channel_sku": "bazi-deep-reading-v1",
            "price_minor": 9900,
            "currency": "CNY",
            "enabled": True,
            "reason": "接入测试期渠道报价",
        },
    )
    assert offer.status_code == 201, offer.text
    assert offer.json()["currency"] == "CNY"

    published = await client.post(
        f"/api/v1/admin/catalog/versions/{version_id}/publish",
        headers=headers,
        json={"reason": "通过商品发布检查"},
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "active"

    catalog = await client.get("/api/v1/admin/catalog")
    assert catalog.status_code == 200, catalog.text
    assert catalog.headers["cache-control"] == "private, no-store, max-age=0"
    assert catalog.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
    assert catalog.json()["families"][0]["versions"][0]["offers"][0]["enabled"] is True

    async with database.sessions() as session:
        audits = list(
            await session.scalars(
                select(AdminAuditEvent).where(
                    AdminAuditEvent.action.like("catalog.%")
                )
            )
        )
    assert {audit.action for audit in audits} == {
        "catalog.family.created",
        "catalog.version.created",
        "catalog.offer.created",
        "catalog.version.published",
    }
    assert all(audit.event_metadata["reason"] for audit in audits)


async def test_admin_catalog_mutations_require_csrf_and_operator_role(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    await _admin_headers(client)
    missing_csrf = await client.post(
        "/api/v1/admin/catalog/families",
        json={
            "key": "missing-csrf",
            "label": "缺少 CSRF",
            "reason": "验证写入边界",
        },
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

    forbidden = await client.post(
        "/api/v1/admin/catalog/families",
        headers=headers,
        json={
            "key": f"support-{uuid4().hex[:8]}",
            "label": "客服不能创建",
            "reason": "验证角色边界",
        },
    )
    assert forbidden.status_code == 403

    read_forbidden = await client.get("/api/v1/admin/catalog")
    assert read_forbidden.status_code == 403
