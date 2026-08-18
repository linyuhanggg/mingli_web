from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.adapters.model import FakeModelGateway
from app.adapters.runtime import build_runtime_startup_gate
from app.commerce.catalog import CatalogService
from app.commerce.models import FulfillmentRecord, ProductOffer, ProductVersion
from app.commerce.service import CommerceService
from app.config import _RUNTIME_RELEASE_PROFILES, Settings
from app.readings.models import (
    GenerationAttempt,
    ReadingJobRecord,
    ReadingRoot,
    ReadingVersion,
)
from app.readings.repository import SqlReadingRepository
from app.security.envelope import EnvelopeCipher
from sqlalchemy import select
from worker.readings import ReadingJobWorkSource, SystemClock, build_reading_worker

# isort: split
from mingli_paths import MINGLI_RUNTIME_RELEASE_ROOT
from test_profiles_api import create_confirmed_profile, create_guest, login_current_guest
from test_readings_api import seed_runtime_release

RUNTIME_PYTHON = Path(
    os.environ.get(
        "MINGLI_RUNTIME_TEST_PYTHON",
        str(Path.home() / ".local/share/mingli-master/venv/bin/python"),
    )
)
RUNTIME_AVAILABLE = MINGLI_RUNTIME_RELEASE_ROOT.is_dir() and RUNTIME_PYTHON.is_file()


async def _catalog_product(
    session: Any,
    *,
    family_key: str,
    channel_sku: str,
) -> tuple[Any, ProductVersion, ProductOffer]:
    catalog = CatalogService(session)
    family = await catalog.create_family(key=family_key, label="八字深度解读")
    product = await catalog.create_version(
        family_id=family.id,
        version="v1",
        price_minor=9900,
        currency="CNY",
        contract_version="reading-document-v1",
        follow_up_count=2,
        follow_up_window_seconds=86_400,
    )
    offer = await catalog.create_offer(
        product_version_id=product.id,
        channel="closed",
        channel_sku=channel_sku,
        price_minor=9900,
        currency="CNY",
        enabled=True,
    )
    await catalog.publish_version(product.id)
    return family, product, offer


async def _payment_for_offer(
    session: Any,
    *,
    owner_id: UUID,
    offer_id: UUID,
    purchase_target_ref: str,
    suffix: str,
    succeeded: bool,
) -> tuple[Any, Any | None]:
    commerce = CommerceService(session)
    order = await commerce.create_order(
        owner_user_id=owner_id,
        offer_id=offer_id,
        purchase_target_ref=purchase_target_ref,
    )
    attempt, _ = await commerce.create_payment_attempt(
        order_id=order.id,
        channel="closed",
        idempotency_key=f"bazi-deep-attempt-{suffix}",
    )
    if succeeded:
        payment, _ = await commerce.confirm_payment(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            channel_transaction_id=f"bazi-deep-transaction-{suffix}",
            verified=True,
        )
        return order, payment

    payment, _ = await commerce.apply_payment_notification(
        order_id=order.id,
        attempt_id=attempt.id,
        channel="closed",
        external_event_id=f"bazi-deep-failed-event-{suffix}",
        channel_transaction_id=None,
        payment_succeeded=False,
        verified=True,
    )
    assert payment is None
    return order, None


async def _seed_v53_runtime_release(database: Any, settings: Settings) -> None:
    release_profile = _RUNTIME_RELEASE_PROFILES["v53-time-check"]
    async with database.sessions() as session:
        repository = SqlReadingRepository(
            session,
            EnvelopeCipher.from_settings(settings),
        )
        await repository.create_runtime_release(
            name=release_profile["release_name"],
            version="5.3",
            source_commit=release_profile["source_commit"],
            release_manifest_digest=release_profile["release_manifest_sha256"],
            protocol_version="mingli-portable-interface-v2",
            describe_manifest_digest=release_profile["manifest_digest"],
            image_digest=None,
            production_ready=True,
        )
        await session.commit()


class _ExtractiveModel:
    """A deterministic model port that only copies the Runtime's public facts."""

    async def generate(self, request: Any) -> Any:
        generated = await FakeModelGateway().generate(request)
        brief = request.brief.to_dict()
        facts = {
            str(item["ref"]): item
            for item in brief.get("facts", [])
            if isinstance(item, dict) and isinstance(item.get("ref"), str)
        }
        limits = {
            str(item["kind_id"]): item
            for item in brief.get("limits", [])
            if isinstance(item, dict) and isinstance(item.get("kind_id"), str)
        }
        blocks = []
        used_source_refs: set[str] = set()
        used_texts: set[str] = set()
        for block in generated.candidate.blocks:
            fact_source = next(
                (
                    (ref, str(facts[ref]["display_text"]))
                    for ref in block.fact_refs
                    if ref in facts
                    and ref not in used_source_refs
                    and isinstance(facts[ref].get("display_text"), str)
                    and str(facts[ref]["display_text"]) not in used_texts
                ),
                None,
            )
            limit_source = None
            if fact_source is None:
                limit_source = next(
                    (
                        (ref, str(limits[ref]["public_text"]))
                        for ref in block.limit_kind_ids
                        if ref in limits
                        and ref not in used_source_refs
                        and isinstance(limits[ref].get("public_text"), str)
                        and str(limits[ref]["public_text"]) not in used_texts
                    ),
                    None,
                )
            source = fact_source or limit_source
            if source is None:
                raise AssertionError("Runtime brief has fewer than three distinct public sources")
            source_ref, text = source
            used_source_refs.add(source_ref)
            used_texts.add(text)
            blocks.append(
                replace(
                    block,
                    text=text,
                    fact_refs=(source_ref,) if fact_source is not None else (),
                    finding_refs=(),
                    evidence_refs=(),
                    limit_kind_ids=(source_ref,) if limit_source is not None else (),
                )
            )
        return replace(
            generated,
            candidate=replace(generated.candidate, blocks=tuple(blocks)),
        )


async def test_bazi_deep_payment_fulfillment_vertical(
    client: Any,
    database: Any,
    test_settings: Any,
) -> None:
    guest_headers = await create_guest(client)
    profile = await create_confirmed_profile(client, guest_headers)
    await seed_runtime_release(database, test_settings)

    guest_start = await client.post(
        "/api/v1/readings/bazi-deep",
        headers=guest_headers,
        json={"profile_version_id": profile["profile_version_id"]},
    )
    assert guest_start.status_code == 403
    assert guest_start.json()["title"] == "Paid reading not granted"
    async with database.sessions() as session:
        assert not list(await session.scalars(select(ReadingJobRecord)))

    login = await login_current_guest(
        client,
        guest_headers,
        destination="13800138001",
    )
    user_headers = {"X-CSRF-Token": login["csrf_token"]}
    started = await client.post(
        "/api/v1/readings/bazi-deep",
        headers={**user_headers, "Idempotency-Key": "bazi-deep-start-1"},
        json={"profile_version_id": profile["profile_version_id"]},
    )
    assert started.status_code == 201, started.text
    started_body = started.json()
    assert started_body["product_id"] == "bazi-deep"
    assert started_body["status"] == "input_ready"
    assert started_body["delivery_state"] == "payment_required"
    version_id = UUID(started_body["reading_version_id"])

    async with database.sessions() as session:
        root = await session.get(ReadingRoot, UUID(started_body["reading_root_id"]))
        version = await session.get(ReadingVersion, version_id)
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version_id
            )
        )
        assert root is not None and version is not None and job is not None
        assert job.status == "awaiting_fulfillment"
        assert version.status == "input_ready"
        assert root.product_version_snapshot_id is None

        _family, product, offer = await _catalog_product(
            session,
            family_key="bazi-deep",
            channel_sku="bazi-deep-v1",
        )
        await session.commit()
        root_id = str(root.id)
        product_id = product.id
        offer_id = offer.id

        failed_order, failed_payment = await _payment_for_offer(
            session,
            owner_id=UUID(login["user_id"]),
            offer_id=offer_id,
            purchase_target_ref=root_id,
            suffix="failed",
            succeeded=False,
        )
        await session.commit()
        assert failed_payment is None
        assert failed_order.status == "payment_pending"

        _wrong_family, _wrong_product, wrong_offer = await _catalog_product(
            session,
            family_key="other-reading",
            channel_sku="other-reading-v1",
        )
        wrong_family_order, wrong_family_payment = await _payment_for_offer(
            session,
            owner_id=UUID(login["user_id"]),
            offer_id=wrong_offer.id,
            purchase_target_ref=root_id,
            suffix="wrong-family",
            succeeded=True,
        )
        wrong_target_order, wrong_target_payment = await _payment_for_offer(
            session,
            owner_id=UUID(login["user_id"]),
            offer_id=offer_id,
            purchase_target_ref=str(uuid4()),
            suffix="wrong-target",
            succeeded=True,
        )
        await session.commit()

    source = ReadingJobWorkSource(
        sessions=database.sessions,
        worker_id="bazi-deep-vertical-before-payment",
        clock=SystemClock(),
        cipher=EnvelopeCipher.from_settings(test_settings),
    )
    assert await source.claim_one() is None

    failed_bind = await client.post(
        f"/api/v1/readings/{version_id}/fulfillment",
        headers={**user_headers, "Idempotency-Key": "bazi-deep-failed-bind"},
        json={"payment_id": str(uuid4())},
    )
    assert failed_bind.status_code == 404
    assert failed_bind.json()["title"] == "Reading not found"

    wrong_family_bind = await client.post(
        f"/api/v1/readings/{version_id}/fulfillment",
        headers={**user_headers, "Idempotency-Key": "bazi-deep-wrong-family"},
        json={"payment_id": str(wrong_family_payment.id)},
    )
    assert wrong_family_bind.status_code == 409
    assert wrong_family_bind.json()["title"] == "Fulfillment unavailable"

    wrong_target_bind = await client.post(
        f"/api/v1/readings/{version_id}/fulfillment",
        headers={**user_headers, "Idempotency-Key": "bazi-deep-wrong-target"},
        json={"payment_id": str(wrong_target_payment.id)},
    )
    assert wrong_target_bind.status_code == 409
    assert wrong_target_bind.json()["title"] == "Fulfillment unavailable"

    async with database.sessions() as session:
        assert await session.scalar(
            select(FulfillmentRecord).where(
                FulfillmentRecord.order_id.in_(
                    [wrong_family_order.id, wrong_target_order.id]
                )
            )
        ) is None
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version_id
            )
        )
        root = await session.get(ReadingRoot, UUID(started_body["reading_root_id"]))
        assert job is not None and root is not None
        assert job.status == "awaiting_fulfillment"
        assert root.product_version_snapshot_id is None

    async with database.sessions() as session:
        right_order, right_payment = await _payment_for_offer(
            session,
            owner_id=UUID(login["user_id"]),
            offer_id=offer_id,
            purchase_target_ref=root_id,
            suffix="right",
            succeeded=True,
        )
        await session.commit()
    assert right_payment is not None

    bound = await client.post(
        f"/api/v1/readings/{version_id}/fulfillment",
        headers={**user_headers, "Idempotency-Key": "bazi-deep-right-bind"},
        json={"payment_id": str(right_payment.id)},
    )
    assert bound.status_code == 201, bound.text
    assert bound.json()["status"] == "running"
    assert bound.json()["created"] is True

    polled = await client.get(f"/api/v1/readings/{version_id}")
    assert polled.status_code == 200, polled.text
    assert polled.json()["status"] == "input_ready"
    assert polled.json()["delivery_state"] == "queued"

    async with database.sessions() as session:
        job = await session.scalar(
            select(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version_id
            )
        )
        root = await session.get(ReadingRoot, UUID(started_body["reading_root_id"]))
        fulfillment = await session.scalar(
            select(FulfillmentRecord).where(FulfillmentRecord.order_id == right_order.id)
        )
        assert job is not None and root is not None and fulfillment is not None
        assert job.status == "queued"
        assert fulfillment.status == "running"
        assert root.product_version_snapshot_id == product_id

    claimed = await ReadingJobWorkSource(
        sessions=database.sessions,
        worker_id="bazi-deep-vertical-after-payment",
        clock=SystemClock(),
        cipher=EnvelopeCipher.from_settings(test_settings),
    ).claim_one()
    assert claimed is not None
    assert claimed.id == str(job.id)


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real Runtime worker vertical is opt-in",
)
async def test_bazi_deep_real_runtime_worker_delivers_result(
    client: Any,
    database: Any,
    test_settings: Any,
    tmp_path: Path,
) -> None:
    """With the admitted one-shot Runtime, the same SQL Worker reaches delivery."""

    if not RUNTIME_AVAILABLE:
        pytest.skip("the admitted V53 Runtime or its pinned Python is not present")
    state_root = tmp_path / "runtime-state"
    state_root.mkdir(mode=0o700)
    state_root.chmod(0o700)
    release_profile = _RUNTIME_RELEASE_PROFILES["v53-time-check"]
    runtime_settings = test_settings.model_copy(
        update={
            "runtime_adapter": "one-shot",
            "runtime_release_profile": "v53-time-check",
            "runtime_launcher_path": (
                MINGLI_RUNTIME_RELEASE_ROOT
                / "scripts"
                / "run_reading_transaction.sh"
            ),
            "runtime_python_path": RUNTIME_PYTHON,
            "runtime_release_root": MINGLI_RUNTIME_RELEASE_ROOT,
            "runtime_state_root": state_root,
            "runtime_expected_manifest_digest": release_profile["manifest_digest"],
            "runtime_expected_capability_shape_sha256": release_profile[
                "capability_shape_sha256"
            ],
        }
    )

    guest_headers = await create_guest(client)
    confirmed_profile = await create_confirmed_profile(client, guest_headers)
    login = await login_current_guest(
        client,
        guest_headers,
        destination="13800138002",
    )
    user_headers = {"X-CSRF-Token": login["csrf_token"]}
    await _seed_v53_runtime_release(database, runtime_settings)
    started = await client.post(
        "/api/v1/readings/bazi-deep",
        headers={**user_headers, "Idempotency-Key": "bazi-deep-real-start"},
        json={"profile_version_id": confirmed_profile["profile_version_id"]},
    )
    assert started.status_code == 201, started.text
    version_id = UUID(started.json()["reading_version_id"])
    root_id = started.json()["reading_root_id"]

    async with database.sessions() as session:
        _family, _product, offer = await _catalog_product(
            session,
            family_key="bazi-deep",
            channel_sku="bazi-deep-v1",
        )
        _order, payment = await _payment_for_offer(
            session,
            owner_id=UUID(login["user_id"]),
            offer_id=offer.id,
            purchase_target_ref=root_id,
            suffix="real",
            succeeded=True,
        )
        await session.commit()

    bound = await client.post(
        f"/api/v1/readings/{version_id}/fulfillment",
        headers={**user_headers, "Idempotency-Key": "bazi-deep-real-bind"},
        json={"payment_id": str(payment.id)},
    )
    assert bound.status_code == 201, bound.text

    gate = build_runtime_startup_gate(runtime_settings)
    await gate.startup()
    worker = build_reading_worker(
        settings=runtime_settings,
        database=database,
        worker_id="bazi-deep-real-vertical",
        runtime=gate.runtime,
        model=_ExtractiveModel(),
    )
    for iteration in range(5):
        processed = await worker.run_once()
        async with database.sessions() as session:
            job = await session.scalar(
                select(ReadingJobRecord).where(
                    ReadingJobRecord.reading_version_id == version_id
                )
            )
            version = await session.get(ReadingVersion, version_id)
            attempts = list(
                await session.scalars(
                    select(GenerationAttempt)
                    .where(GenerationAttempt.reading_version_id == version_id)
                    .order_by(GenerationAttempt.attempt_number)
                )
            )
            assert processed is True, (
                f"real worker had no claim at iteration {iteration + 1}; "
                f"job_status={None if job is None else job.status!r}, "
                f"available_at={None if job is None else job.available_at!r}, "
                f"version_status={None if version is None else version.status!r}, "
                "guard_errors="
                f"{[tuple(attempt.guard_errors) for attempt in attempts]!r}"
            )
            if job is not None and job.status == "complete":
                break
    else:
        raise AssertionError("real worker did not complete bazi-deep within five claims")

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "accepted"
    assert result.json()["document"] is not None
    assert result.json()["document"]["versions"]["runtime_release"] == (
        f"{release_profile['release_name']}@5.3"
    )
    assert result.json()["view_model"]["schema_version"] == "bazi-chart/v1"
    summary = await client.get(f"/api/v1/readings/{version_id}")
    assert summary.status_code == 200
    assert summary.json()["delivery_state"] == "delivered"
