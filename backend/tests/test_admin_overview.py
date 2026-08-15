from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.commerce.models import (
    Order,
    Payment,
    PaymentAttempt,
    PaymentReconciliationRun,
    ProductFamily,
    ProductVersion,
    Refund,
)
from app.identity.models import GuestSession, User
from app.readings.models import ReadingJobRecord, ReadingRoot, ReadingVersion, RuntimeRelease
from httpx import AsyncClient


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_overview_aggregates_current_platform_facts(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC)
    yesterday = now - timedelta(days=1)
    user = User(id=uuid4())
    family = ProductFamily(
        id=uuid4(),
        key="overview-bazi",
        label="总览八字",
    )
    version = ProductVersion(
        id=uuid4(),
        family_id=family.id,
        version="v1",
        price_minor=9900,
        currency="CNY",
        contract_version="reading-document-v1",
        status="active",
    )
    order = Order(
        id=uuid4(),
        owner_user_id=user.id,
        product_version_id=version.id,
        purchase_target_ref="overview-target",
        amount_minor=9900,
        currency="CNY",
        status="paid",
        created_at=now,
        paid_at=now,
    )
    failed_today = PaymentAttempt(
        id=uuid4(),
        order_id=order.id,
        channel="closed",
        idempotency_key_hash="a" * 64,
        status="failed",
        created_at=now,
    )
    failed_yesterday = PaymentAttempt(
        id=uuid4(),
        order_id=order.id,
        channel="closed",
        idempotency_key_hash="b" * 64,
        status="failed",
        created_at=yesterday,
    )
    payment = Payment(
        id=uuid4(),
        order_id=order.id,
        attempt_id=failed_today.id,
        channel="closed",
        channel_transaction_id="overview-tx",
        amount_minor=9900,
        currency="CNY",
        status="confirmed",
        confirmed_at=now,
    )
    refund = Refund(
        id=uuid4(),
        payment_id=payment.id,
        channel="closed",
        channel_refund_id="overview-refund",
        amount_minor=9900,
        currency="CNY",
        reason="总览测试退款",
        status="pending",
        created_at=now,
    )
    guest = GuestSession(
        id=uuid4(),
        token_hash="g" * 64,
        csrf_token_hash="c" * 64,
        expires_at=now + timedelta(hours=2),
    )
    release = RuntimeRelease(
        id=uuid4(),
        name="overview-runtime",
        version="1.0",
        source_commit="overview-source",
        release_manifest_digest="overview-manifest",
        protocol_version="protocol-v1",
        describe_manifest_digest="overview-describe",
        production_ready=False,
    )
    root = ReadingRoot(
        id=uuid4(),
        owner_guest_session_id=guest.id,
        capability_id="bazi",
    )
    reading_version = ReadingVersion(
        id=uuid4(),
        reading_root_id=root.id,
        runtime_release_id=release.id,
        version=1,
        status="runtime_unknown",
        capability_id="bazi",
        object_id="natal",
        dimension_ids=["overview"],
        horizon={"kind_id": "natal", "start": None, "end": None},
        prepare_key_id="overview-key",
        prepare_nonce="overview-nonce",
        prepare_ciphertext="overview-ciphertext",
        prepare_digest="overview-digest",
        created_at=now,
    )
    reading_job = ReadingJobRecord(
        id=uuid4(),
        reading_version_id=reading_version.id,
        status="runtime_unknown",
        narrative_policy_version="narrative-v1",
        output_contract={"schema": "reading-document/v1"},
        language="zh-CN",
        max_output_chars=12000,
        max_attempts=3,
        available_at=now,
        created_at=now,
    )
    reconciliation = PaymentReconciliationRun(
        id=uuid4(),
        channel="closed",
        run_at=now,
        status="has_differences",
        item_count=3,
        matched_count=1,
        difference_count=2,
        created_at=now,
    )

    async with database.sessions() as session:
        session.add_all(
            [
                user,
                family,
                version,
                order,
                failed_today,
                failed_yesterday,
                payment,
                refund,
                guest,
                release,
                root,
                reading_version,
                reading_job,
                reconciliation,
            ]
        )
        await session.commit()

    await _admin_headers(client)
    response = await client.get("/api/v1/admin/overview")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["is_stub"] is False
    kpis = {item["id"]: item for item in body["kpis"]}
    queues = {item["id"]: item for item in body["queues"]}
    assert kpis["refunds_pending"] == {
        "id": "refunds_pending",
        "label": "待审退款",
        "value": 1,
        "is_stub": False,
    }
    assert kpis["readings_failed"]["value"] == 1
    assert kpis["payments_abnormal"]["value"] == 1
    assert kpis["reconcile_diff"]["value"] == 2
    assert queues["refund_queue"]["count"] == 1
    assert queues["reading_queue"]["count"] == 1
    assert all(not item["is_stub"] for item in body["kpis"])
    assert all(not item["is_stub"] for item in body["queues"])
