from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.commerce.models import (
    Order,
    PaymentAttempt,
    ProductFamily,
    ProductOffer,
    ProductVersion,
)
from app.commerce.public_service import PublicCheckoutService
from app.commerce.service import CommerceService
from app.identity.models import ConsentRecord, User
from app.identity.policy import CURRENT_POLICY_VERSION
from app.readings.models import (
    ReadingJobRecord,
    ReadingRoot,
    ReadingVersion,
    RuntimeRelease,
)
from httpx import AsyncClient
from sqlalchemy import func, select


async def _login(client: AsyncClient, destination: str) -> tuple[UUID, dict[str, str]]:
    guest = await client.post("/api/v1/guest-sessions")
    assert guest.status_code == 201, guest.text
    guest_headers = {"X-CSRF-Token": guest.json()["csrf_token"]}
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=guest_headers,
        json={"channel": "email", "destination": destination},
    )
    assert requested.status_code == 202, requested.text
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers=guest_headers,
        json={"challenge_id": requested.json()["challenge_id"], "code": "246810"},
    )
    assert verified.status_code == 200, verified.text
    return UUID(verified.json()["user_id"]), {
        "X-CSRF-Token": verified.json()["csrf_token"],
    }


async def _seed_target(
    database: Any,
    *,
    owner_user_id: UUID,
    product_id: str = "bazi-deep",
    family_key: str = "bazi-deep",
) -> SimpleNamespace:
    now = datetime.now(UTC)
    async with database.sessions() as session:
        family = ProductFamily(key=family_key, label="八字深读")
        session.add(family)
        await session.flush()
        product = ProductVersion(
            family_id=family.id,
            version="v1",
            price_minor=9900,
            currency="CNY",
            contract_version="reading-document-v1",
            status="active",
        )
        session.add(product)
        await session.flush()
        offer = ProductOffer(
            product_version_id=product.id,
            channel="fake",
            channel_sku=f"{family_key}-{uuid4().hex[:8]}",
            price_minor=9900,
            currency="CNY",
            enabled=True,
        )
        release = RuntimeRelease(
            name="checkout-test-runtime",
            version="v1",
            source_commit=uuid4().hex,
            release_manifest_digest=uuid4().hex,
            protocol_version="v1",
            describe_manifest_digest=uuid4().hex,
            production_ready=True,
        )
        session.add_all([offer, release])
        await session.flush()
        root = ReadingRoot(
            owner_user_id=owner_user_id,
            capability_id="bazi",
            product_id=product_id,
        )
        session.add(root)
        await session.flush()
        version = ReadingVersion(
            reading_root_id=root.id,
            runtime_release_id=release.id,
            version=1,
            status="input_ready",
            capability_id="bazi",
            product_id=product_id,
            object_id="natal",
            dimension_ids=["career"],
            horizon={"kind_id": "life"},
            prepare_key_id="checkout-test-key",
            prepare_nonce="checkout-test-nonce",
            prepare_ciphertext="checkout-test-ciphertext",
            prepare_digest="0" * 64,
        )
        session.add(version)
        await session.flush()
        job = ReadingJobRecord(
            reading_version_id=version.id,
            status="awaiting_fulfillment",
            narrative_policy_version="policy-v1",
            output_contract={"contract_id": "bazi-deep-output-v1"},
            language="zh-CN",
            max_output_chars=1000,
            max_attempts=1,
            available_at=now,
        )
        session.add(job)
        await session.commit()
        return SimpleNamespace(
            family=family,
            product=product,
            offer=offer,
            root=root,
            version=version,
            job=job,
        )



async def _record_purchase_consent(client: AsyncClient, headers: dict[str, str]) -> None:
    for policy_key in ("privacy", "terms"):
        response = await client.post(
            "/api/v1/auth/consents",
            headers=headers,
            json={
                "policy_key": policy_key,
                "policy_version": CURRENT_POLICY_VERSION,
                "context": "purchase",
            },
        )
        assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_checkout_requires_the_reading_owner_and_bazi_deep_product(
    client: AsyncClient,
    database: Any,
) -> None:
    owner_id, headers = await _login(client, "checkout-owner@example.com")
    other_id = uuid4()
    async with database.sessions() as session:
        session.add(User(id=other_id))
        await session.commit()
    foreign = await _seed_target(database, owner_user_id=other_id)
    response = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "foreign-target-1"},
        json={"reading_version_id": str(foreign.version.id)},
    )
    assert response.status_code == 404

    non_bazi = await _seed_target(
        database,
        owner_user_id=owner_id,
        product_id="qimen-deep",
        family_key="qimen-deep",
    )
    response = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "wrong-product-1"},
        json={"reading_version_id": str(non_bazi.version.id)},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_checkout_fails_closed_when_no_enabled_bazi_offer(
    client: AsyncClient,
    database: Any,
) -> None:
    owner_id, headers = await _login(client, "checkout-offer@example.com")
    target = await _seed_target(
        database,
        owner_user_id=owner_id,
        family_key="qimen-deep",
    )
    response = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "no-bazi-offer-1"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert response.status_code == 409


async def _add_enabled_offer(
    database: Any,
    *,
    product_version_id: UUID,
    channel: str,
) -> ProductOffer:
    async with database.sessions() as session:
        offer = ProductOffer(
            product_version_id=product_version_id,
            channel=channel,
            channel_sku=f"{channel}-{uuid4().hex[:8]}",
            price_minor=9900,
            currency="CNY",
            enabled=True,
        )
        session.add(offer)
        await session.commit()
        return offer


@pytest.mark.asyncio
async def test_checkout_fails_closed_when_multiple_bazi_offers_need_server_policy(
    client: AsyncClient,
    database: Any,
) -> None:
    owner_id, headers = await _login(client, "checkout-multiple-offers@example.com")
    target = await _seed_target(database, owner_user_id=owner_id)
    await _add_enabled_offer(
        database,
        product_version_id=target.product.id,
        channel="second-channel",
    )
    response = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "multiple-offers-1"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert response.status_code == 409
    async with database.sessions() as session:
        assert await session.scalar(select(func.count(Order.id))) == 0


@pytest.mark.asyncio
async def test_fake_gateway_is_unavailable_and_target_is_server_derived(
    client: AsyncClient,
    database: Any,
) -> None:
    owner_id, headers = await _login(client, "checkout-fake@example.com")
    target = await _seed_target(database, owner_user_id=owner_id)
    response = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "fake-gateway-1"},
        json={
            "reading_version_id": str(target.version.id),
            "offer_id": str(target.offer.id),
            "purchase_target_ref": "attacker-chosen-target",
        },
    )
    assert response.status_code == 400

    await _record_purchase_consent(client, headers)
    response = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "fake-gateway-2"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["gateway_status"] == "unavailable"
    assert "payment_id" not in body
    assert body["order"]["reading_version_id"] == str(target.version.id)

    async with database.sessions() as session:
        order = await session.get(Order, UUID(body["order"]["order_id"]))
        assert order is not None
        assert order.purchase_target_ref == str(target.root.id)
        assert order.purchase_target_ref != "attacker-chosen-target"


@pytest.mark.asyncio
async def test_checkout_idempotency_replays_one_order_and_attempt(
    client: AsyncClient,
    database: Any,
) -> None:
    owner_id, headers = await _login(client, "checkout-replay@example.com")
    target = await _seed_target(database, owner_user_id=owner_id)
    await _record_purchase_consent(client, headers)
    payload = {"reading_version_id": str(target.version.id)}
    request_headers = {**headers, "Idempotency-Key": "replay-checkout-1"}
    first = await client.post("/api/v1/commerce/checkout", headers=request_headers, json=payload)
    second = await client.post("/api/v1/commerce/checkout", headers=request_headers, json=payload)
    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["order"]["order_id"] == first.json()["order"]["order_id"]
    assert second.json()["attempt"]["attempt_id"] == first.json()["attempt"]["attempt_id"]
    async with database.sessions() as session:
        assert await session.scalar(select(func.count(Order.id))) == 1
        assert await session.scalar(select(func.count(PaymentAttempt.id))) == 1


@pytest.mark.asyncio
async def test_checkout_status_exposes_payment_id_only_after_local_confirmation(
    client: AsyncClient,
    database: Any,
) -> None:
    owner_id, headers = await _login(client, "checkout-status@example.com")
    target = await _seed_target(database, owner_user_id=owner_id)
    await _record_purchase_consent(client, headers)
    created = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "status-checkout-1"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert created.status_code == 201, created.text
    order_id = UUID(created.json()["order"]["order_id"])
    pending = await client.get(f"/api/v1/commerce/checkout/{order_id}")
    assert pending.status_code == 200, pending.text
    assert "payment_id" not in pending.json()

    async with database.sessions() as session:
        order = await session.get(Order, order_id)
        assert order is not None
        attempt = await session.scalar(
            select(PaymentAttempt).where(PaymentAttempt.order_id == order.id)
        )
        assert attempt is not None
        payment, _ = await CommerceService(session).confirm_payment(
            order_id=order.id,
            attempt_id=attempt.id,
            channel=attempt.channel,
            channel_transaction_id="checkout-confirmed-tx",
            verified=True,
        )
        await session.commit()

    confirmed = await client.get(f"/api/v1/commerce/checkout/{order_id}")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["payment_id"] == str(payment.id)
    assert confirmed.json()["gateway_status"] == "succeeded"
    assert str(owner_id) not in confirmed.text
    assert "purchase_target_ref" not in confirmed.text
    assert "idempotency_key_hash" not in confirmed.text


@pytest.mark.asyncio
async def test_status_does_not_turn_an_unbound_provider_query_into_payment(
    client: AsyncClient,
    database: Any,
) -> None:
    owner_id, headers = await _login(client, "checkout-query-boundary@example.com")
    target = await _seed_target(database, owner_user_id=owner_id)
    await _record_purchase_consent(client, headers)
    created = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "query-boundary-1"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert created.status_code == 201, created.text
    order_id = UUID(created.json()["order"]["order_id"])

    class QueryLyingGateway:
        query_calls = 0

        async def query_payment(self, *, attempt_id: UUID) -> Any:
            del attempt_id
            self.query_calls += 1
            return SimpleNamespace(
                status="succeeded",
                payment_succeeded=True,
                channel_transaction_id="unbound-provider-transaction",
            )

    gateway = QueryLyingGateway()
    async with database.sessions() as session:
        result = await PublicCheckoutService(session, gateway).get_checkout(
            owner_user_id=owner_id,
            order_id=order_id,
        )
    assert result.payment is None
    assert result.gateway_status == "pending"
    assert gateway.query_calls == 0


@pytest.mark.asyncio
async def test_checkout_rejects_without_purchase_consent(
    client: AsyncClient,
    database: Any,
) -> None:
    owner_id, headers = await _login(client, "checkout-no-consent@example.com")
    target = await _seed_target(database, owner_user_id=owner_id)
    response = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "no-purchase-consent-1"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert response.status_code == 400
    assert response.json()["title"] == "Policy version is not current"
    async with database.sessions() as session:
        assert await session.scalar(select(func.count(Order.id))) == 0


@pytest.mark.asyncio
async def test_checkout_accepts_after_record_consent(
    client: AsyncClient,
    database: Any,
) -> None:
    owner_id, headers = await _login(client, "checkout-with-consent@example.com")
    target = await _seed_target(database, owner_user_id=owner_id)
    await _record_purchase_consent(client, headers)
    response = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "with-purchase-consent-1"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert response.status_code in {200, 201}, response.text
    async with database.sessions() as session:
        consents = list(
            await session.scalars(
                select(ConsentRecord).where(
                    ConsentRecord.user_id == owner_id,
                    ConsentRecord.context == "purchase",
                    ConsentRecord.policy_version == CURRENT_POLICY_VERSION,
                )
            )
        )
        assert {record.policy_key for record in consents} == {"privacy", "terms"}
        assert await session.scalar(select(func.count(Order.id))) == 1


@pytest.mark.asyncio
async def test_checkout_rejects_stale_purchase_consent(
    client: AsyncClient,
    database: Any,
) -> None:
    owner_id, headers = await _login(client, "checkout-stale-consent@example.com")
    target = await _seed_target(database, owner_user_id=owner_id)
    await _record_purchase_consent(client, headers)
    async with database.sessions() as session:
        consents = list(
            await session.scalars(
                select(ConsentRecord).where(ConsentRecord.context == "purchase")
            )
        )
        for record in consents:
            record.policy_version = "old-policy-v0.0"
        await session.commit()
    response = await client.post(
        "/api/v1/commerce/checkout",
        headers={**headers, "Idempotency-Key": "stale-purchase-consent-1"},
        json={"reading_version_id": str(target.version.id)},
    )
    assert response.status_code == 400
    assert response.json()["title"] == "Policy version is not current"
    async with database.sessions() as session:
        assert await session.scalar(select(func.count(Order.id))) == 0
