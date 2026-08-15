from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from httpx import AsyncClient


async def _create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def _login(client: AsyncClient, guest_headers: dict[str, str]) -> None:
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=guest_headers,
        json={"channel": "email", "destination": "commerce@example.com"},
    )
    assert requested.status_code == 202, requested.text
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers=guest_headers,
        json={"challenge_id": requested.json()["challenge_id"], "code": "246810"},
    )
    assert verified.status_code == 200, verified.text


async def test_account_commerce_reads_are_owner_scoped_and_project_the_ledger(
    client: AsyncClient,
    database: Any,
) -> None:
    guest_headers = await _create_guest(client)
    await _login(client, guest_headers)
    account = await client.get("/api/v1/account")
    assert account.status_code == 200, account.text
    owner_id = UUID(account.json()["user_id"])

    from app.commerce.models import (
        EntitlementEventRecord,
        Order,
        ProductFamily,
        ProductVersion,
    )
    from app.identity.models import User

    now = datetime(2026, 8, 14, 5, 0, tzinfo=UTC)
    async with database.sessions() as session:
        other_user = User()
        family = ProductFamily(key="account-commerce", label="八字深读")
        session.add_all([other_user, family])
        await session.flush()
        version = ProductVersion(
            family_id=family.id,
            version="v1",
            price_minor=9900,
            currency="CNY",
            contract_version="reading-document-v1",
            status="active",
        )
        session.add(version)
        await session.flush()
        owner_order = Order(
            owner_user_id=owner_id,
            product_version_id=version.id,
            purchase_target_ref="owner-target",
            amount_minor=9900,
            currency="CNY",
            status="paid",
            created_at=now,
            paid_at=now + timedelta(minutes=1),
        )
        other_order = Order(
            owner_user_id=other_user.id,
            product_version_id=version.id,
            purchase_target_ref="other-target",
            amount_minor=9900,
            currency="CNY",
            status="paid",
            created_at=now,
            paid_at=now + timedelta(minutes=1),
        )
        session.add_all([owner_order, other_order])
        await session.flush()
        session.add_all(
            [
                EntitlementEventRecord(
                    entitlement_id=f"order:{owner_order.id}",
                    owner_user_id=owner_id,
                    kind="GRANT",
                    quantity=1,
                    source_type="order",
                    source_ref=f"{owner_order.id}:grant",
                    created_at=now,
                ),
                EntitlementEventRecord(
                    entitlement_id=f"order:{owner_order.id}",
                    owner_user_id=owner_id,
                    kind="RESERVE",
                    quantity=1,
                    source_type="order",
                    source_ref=f"{owner_order.id}:reserve",
                    created_at=now + timedelta(minutes=1),
                ),
                EntitlementEventRecord(
                    entitlement_id=f"order:{owner_order.id}",
                    owner_user_id=owner_id,
                    kind="CONSUME",
                    quantity=1,
                    source_type="order",
                    source_ref=f"{owner_order.id}:consume",
                    created_at=now + timedelta(minutes=2),
                ),
                EntitlementEventRecord(
                    entitlement_id=f"order:{other_order.id}",
                    owner_user_id=other_user.id,
                    kind="GRANT",
                    quantity=9,
                    source_type="other-order",
                    source_ref=f"{other_order.id}:grant",
                    created_at=now,
                ),
            ]
        )
        await session.commit()

    orders = await client.get("/api/v1/account/orders")
    assert orders.status_code == 200, orders.text
    assert orders.headers["cache-control"] == "private, no-store, max-age=0"
    order_body = orders.json()
    assert len(order_body["orders"]) == 1
    assert order_body["orders"][0]["product_label"] == "八字深读"
    assert order_body["orders"][0]["amount_minor"] == 9900
    assert order_body["orders"][0]["status"] == "paid"
    assert str(other_order.id) not in orders.text
    assert str(owner_id) not in orders.text

    entitlements = await client.get("/api/v1/account/entitlements")
    assert entitlements.status_code == 200, entitlements.text
    entitlement_body = entitlements.json()
    assert len(entitlement_body["entitlements"]) == 1
    projection = entitlement_body["entitlements"][0]
    assert projection["available"] == 0
    assert projection["granted"] == 1
    assert projection["consumed"] == 1
    assert [event["kind"] for event in projection["events"]] == [
        "GRANT",
        "RESERVE",
        "CONSUME",
    ]
    assert "source_ref" not in entitlements.text
    assert str(other_order.id) not in entitlements.text
    assert str(owner_id) not in entitlements.text


async def test_account_commerce_requires_a_verified_device(client: AsyncClient) -> None:
    for path in ("/api/v1/account/orders", "/api/v1/account/entitlements"):
        response = await client.get(path)
        assert response.status_code == 401
