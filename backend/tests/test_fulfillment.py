from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module
from typing import Any
from uuid import uuid4

import pytest
from app.api.dependencies import Owner
from app.commerce.models import (
    EntitlementEventRecord,
    ProductFamily,
    ProductOffer,
    ProductVersion,
)
from app.commerce.service import CommerceError, CommerceService
from app.identity.models import User
from app.readings.service import (
    PaidReadingNotGrantedError,
    ReadingFulfillmentUnavailableError,
    ReadingNotFoundError,
    ReadingService,
)
from sqlalchemy import select


async def _paid_order(
    session: Any,
    *,
    suffix: str = "1",
    owner: User | None = None,
) -> tuple[Any, Any, Any]:
    user = owner or User()
    family = ProductFamily(key=f"bazi-{suffix}", label="八字深读")
    session.add(family)
    if owner is None:
        session.add(user)
    await session.flush()
    product = ProductVersion(
        family_id=family.id,
        version="v1",
        price_minor=9900,
        currency="CNY",
        follow_up_count=2,
        follow_up_window_seconds=86_400,
        contract_version="reading-document-v1",
        status="active",
    )
    session.add(product)
    await session.flush()
    offer = ProductOffer(
        product_version_id=product.id,
        channel="closed",
        channel_sku=f"bazi-v1-{suffix}",
        price_minor=9900,
        currency="CNY",
        enabled=True,
    )
    session.add(offer)
    await session.flush()
    service = CommerceService(session)
    order = await service.create_order(
        owner_user_id=user.id,
        offer_id=offer.id,
        purchase_target_ref="reading-target-1",
    )
    attempt, _ = await service.create_payment_attempt(
        order_id=order.id,
        channel="closed",
            idempotency_key=f"attempt-fulfillment-{suffix}",
    )
    payment, _ = await service.confirm_payment(
        order_id=order.id,
        attempt_id=attempt.id,
        channel="closed",
        channel_transaction_id=f"tx-fulfillment-{suffix}",
        verified=True,
    )
    return service, user, payment


async def _reading_job_for_user(session: Any, user: User) -> tuple[Any, Any]:
    profiles = import_module("app.profiles.repository")
    repository_module = import_module("app.readings.repository")
    runtime_contracts = import_module("app.readings.runtime_contracts")
    narrative = import_module("app.readings.narrative_contracts")
    envelope = import_module("app.security.envelope")

    cipher = envelope.EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1")
    profile_repository = profiles.ProfileRepository(session, cipher)
    profile = await profile_repository.create_profile(owner_user_id=user.id)
    profile_version = await profile_repository.create_version(
        profile_id=profile.id,
        payload={"birth_datetime": "1994-04-30T05:55:00+08:00"},
    )
    repository = repository_module.SqlReadingRepository(session, cipher)
    release = await repository.create_runtime_release(
        name="test-runtime-binding",
        version="5.1",
        source_commit="test-commit-binding",
        release_manifest_digest="a" * 64,
        protocol_version="test-protocol",
        describe_manifest_digest="b" * 64,
        image_digest=None,
        production_ready=False,
    )
    root = await repository.create_root(
        owner_user_id=user.id,
        profile_version_id=profile_version.id,
        capability_id="bazi",
    )
    prepare = runtime_contracts.Prepare(
        query="事业上最该先抓住哪条主线？",
        intent={
            "subject_refs": [f"profile-version:{profile_version.id}"],
            "object_id": "natal",
            "dimension_ids": ["career"],
            "horizon": {"kind_id": "life", "start": None, "end": None},
            "capability_id": "bazi",
            "comparisons": [],
        },
        facts={
            f"profile-version:{profile_version.id}": {
                "birth_datetime_or_four_pillars": "1994-04-30T05:55:00+08:00",
            }
        },
    )
    version = await repository.create_version(
        reading_root_id=root.id,
        runtime_release_id=release.id,
        prepare_command=prepare,
    )
    job = await repository.create_job(
        reading_version_id=version.id,
        narrative_policy_version="policy-v1",
        output_contract=narrative.OutputContract(
            contract_id="test-contract-binding",
            language="zh-CN",
            min_blocks=1,
            max_blocks=1,
            max_output_chars=200,
            required_dimension_ids=("career",),
            required_limit_kind_ids=("limit:traditional",),
            disclosure_text="仅供传统文化参考。",
        ),
        language="zh-CN",
        max_output_chars=200,
        max_attempts=1,
    )
    return version, job


@pytest.mark.asyncio
async def test_fulfillment_reserves_paid_entitlement_once(database: Any) -> None:
    async with database.sessions() as session:
        service, _user, payment = await _paid_order(session)

        first, created = await service.reserve_fulfillment(
            payment_id=payment.id,
            idempotency_key="fulfillment-1",
        )
        replay, replayed = await service.reserve_fulfillment(
            payment_id=payment.id,
            idempotency_key="fulfillment-1",
        )

        assert created is True
        assert replayed is False
        assert replay.id == first.id
        assert first.status == "reserved"
        projection = await service.ledger.project(
            entitlement_id=f"order:{payment.order_id}",
            owner_user_id=_user.id,
        )
        assert projection.reserved == 1
        assert projection.available == 0


@pytest.mark.asyncio
async def test_fulfillment_idempotency_key_is_scoped_to_order(database: Any) -> None:
    async with database.sessions() as session:
        first_service, _first_user, first_payment = await _paid_order(session, suffix="1")
        second_service, _second_user, second_payment = await _paid_order(session, suffix="2")

        first, first_created = await first_service.reserve_fulfillment(
            payment_id=first_payment.id,
            idempotency_key="same-key-on-independent-orders",
        )
        second, second_created = await second_service.reserve_fulfillment(
            payment_id=second_payment.id,
            idempotency_key="same-key-on-independent-orders",
        )

        assert first_created is True
        assert second_created is True
        assert first.id != second.id


@pytest.mark.asyncio
async def test_fulfillment_requires_verified_payment(database: Any) -> None:
    async with database.sessions() as session:
        service, user, payment = await _paid_order(session)
        payment.status = "pending"
        await session.flush()

        with pytest.raises(CommerceError, match="confirmed payment"):
            await service.reserve_fulfillment(
                payment_id=payment.id,
                idempotency_key="fulfillment-unpaid",
            )

        projection = await service.ledger.project(
            entitlement_id=f"order:{payment.order_id}",
            owner_user_id=user.id,
        )
        assert projection.reserved == 0


@pytest.mark.asyncio
async def test_reading_service_binds_paid_fulfillment_once(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        commerce, user, payment = await _paid_order(session, suffix="service-binding")
        version, job = await _reading_job_for_user(session, user)
        reading_service = ReadingService(session, test_settings)
        owner = Owner(kind="user", id=user.id, csrf_token_hash="")

        first = await reading_service.bind_paid_fulfillment(
            owner,
            reading_version_id=version.id,
            payment_id=payment.id,
            idempotency_key="service-binding-1",
        )
        replay = await reading_service.bind_paid_fulfillment(
            owner,
            reading_version_id=version.id,
            payment_id=payment.id,
            idempotency_key="service-binding-1",
        )

        assert first.created is True
        assert replay.created is False
        assert first.fulfillment_id == replay.fulfillment_id
        assert first.reading_job_id == job.id
        assert first.status == replay.status == "running"
        projection = await commerce.ledger.project(
            entitlement_id=f"order:{payment.order_id}",
            owner_user_id=user.id,
        )
        assert projection.reserved == 1


@pytest.mark.asyncio
async def test_reading_service_rejects_wrong_owner_and_guest_fulfillment(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        commerce, user, payment = await _paid_order(session, suffix="owner-binding")
        version, _job = await _reading_job_for_user(session, user)
        reading_service = ReadingService(session, test_settings)

        other_service, other_user, other_payment = await _paid_order(
            session,
            suffix="owner-binding-other",
        )
        with pytest.raises(ReadingNotFoundError, match="Payment"):
            await reading_service.bind_paid_fulfillment(
                Owner(kind="user", id=user.id, csrf_token_hash=""),
                reading_version_id=version.id,
                payment_id=other_payment.id,
                idempotency_key="wrong-owner-binding",
            )
        with pytest.raises(PaidReadingNotGrantedError, match="signed-in"):
            await reading_service.bind_paid_fulfillment(
                Owner(kind="guest", id=uuid4(), csrf_token_hash=""),
                reading_version_id=version.id,
                payment_id=payment.id,
                idempotency_key="guest-binding",
            )

        first_projection = await commerce.ledger.project(
            entitlement_id=f"order:{payment.order_id}",
            owner_user_id=user.id,
        )
        second_projection = await other_service.ledger.project(
            entitlement_id=f"order:{other_payment.order_id}",
            owner_user_id=other_user.id,
        )
        assert first_projection.reserved == 0
        assert second_projection.reserved == 0


@pytest.mark.asyncio
async def test_reading_service_rejects_terminal_job_before_reserving(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        commerce, user, payment = await _paid_order(session, suffix="terminal-binding")
        version, job = await _reading_job_for_user(session, user)
        job.status = "stopped"
        await session.flush()

        with pytest.raises(ReadingFulfillmentUnavailableError, match="terminal"):
            await ReadingService(session, test_settings).bind_paid_fulfillment(
                Owner(kind="user", id=user.id, csrf_token_hash=""),
                reading_version_id=version.id,
                payment_id=payment.id,
                idempotency_key="terminal-binding-1",
            )

        projection = await commerce.ledger.project(
            entitlement_id=f"order:{payment.order_id}",
            owner_user_id=user.id,
        )
        assert projection.reserved == 0


@pytest.mark.asyncio
async def test_fulfillment_consumes_only_after_real_accepted_document(database: Any) -> None:
    readings = import_module("app.readings.models")
    profiles = import_module("app.profiles.repository")
    repository_module = import_module("app.readings.repository")
    runtime_contracts = import_module("app.readings.runtime_contracts")
    narrative = import_module("app.readings.narrative_contracts")
    envelope = import_module("app.security.envelope")

    async with database.sessions() as session:
        service, user, payment = await _paid_order(session)
        fulfillment, _ = await service.reserve_fulfillment(
            payment_id=payment.id,
            idempotency_key="fulfillment-accepted",
        )

        cipher = envelope.EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1")
        profile_repository = profiles.ProfileRepository(session, cipher)
        profile = await profile_repository.create_profile(owner_user_id=user.id)
        profile_version = await profile_repository.create_version(
            profile_id=profile.id,
            payload={"birth_datetime": "1994-04-30T05:55:00+08:00"},
        )
        repository = repository_module.SqlReadingRepository(session, cipher)
        release = await repository.create_runtime_release(
            name="test-runtime",
            version="5.1",
            source_commit="test-commit",
            release_manifest_digest="a" * 64,
            protocol_version="test-protocol",
            describe_manifest_digest="b" * 64,
            image_digest=None,
            production_ready=False,
        )
        root = await repository.create_root(
            owner_user_id=user.id,
            profile_version_id=profile_version.id,
            capability_id="bazi",
        )
        prepare = runtime_contracts.Prepare(
            query="事业上最该先抓住哪条主线？",
            intent={
                "subject_refs": [f"profile-version:{profile_version.id}"],
                "object_id": "natal",
                "dimension_ids": ["career"],
                "horizon": {"kind_id": "life", "start": None, "end": None},
                "capability_id": "bazi",
                "comparisons": [],
            },
            facts={
                f"profile-version:{profile_version.id}": {
                    "birth_datetime_or_four_pillars": "1994-04-30T05:55:00+08:00",
                }
            },
        )
        version = await repository.create_version(
            reading_root_id=root.id,
            runtime_release_id=release.id,
            prepare_command=prepare,
        )
        job = await repository.create_job(
            reading_version_id=version.id,
            narrative_policy_version="policy-v1",
            output_contract=narrative.OutputContract(
                contract_id="test-contract",
                language="zh-CN",
                min_blocks=1,
                max_blocks=1,
                max_output_chars=200,
                required_dimension_ids=("career",),
                required_limit_kind_ids=("limit:traditional",),
                disclosure_text="仅供传统文化参考。",
            ),
            language="zh-CN",
            max_output_chars=200,
            max_attempts=1,
        )
        bound, bound_created = await service.bind_fulfillment_job(
            fulfillment_id=fulfillment.id,
            reading_version_ref=str(version.id),
            reading_job_ref=str(job.id),
        )
        rebound, rebound_created = await service.bind_fulfillment_job(
            fulfillment_id=fulfillment.id,
            reading_version_ref=str(version.id),
            reading_job_ref=str(job.id),
        )
        assert bound_created is True
        assert rebound_created is False
        assert bound.id == rebound.id == fulfillment.id
        assert bound.status == "running"
        second_service, _same_user, second_payment = await _paid_order(
            session,
            suffix="2",
            owner=user,
        )
        second_fulfillment, _ = await second_service.reserve_fulfillment(
            payment_id=second_payment.id,
            idempotency_key="fulfillment-accepted-second",
        )
        with pytest.raises(CommerceError, match="already bound"):
            await second_service.bind_fulfillment_job(
                fulfillment_id=second_fulfillment.id,
                reading_version_ref=str(version.id),
                reading_job_ref=str(job.id),
            )
        second_root = await repository.create_root(
            owner_user_id=user.id,
            profile_version_id=profile_version.id,
            capability_id="bazi",
        )
        second_version = await repository.create_version(
            reading_root_id=second_root.id,
            runtime_release_id=release.id,
            prepare_command=prepare,
        )
        second_job = await repository.create_job(
            reading_version_id=second_version.id,
            narrative_policy_version="policy-v1",
            output_contract=narrative.OutputContract(
                contract_id="test-contract-release",
                language="zh-CN",
                min_blocks=1,
                max_blocks=1,
                max_output_chars=200,
                required_dimension_ids=("career",),
                required_limit_kind_ids=("limit:traditional",),
                disclosure_text="仅供传统文化参考。",
            ),
            language="zh-CN",
            max_output_chars=200,
            max_attempts=1,
        )
        await second_service.bind_fulfillment_job(
            fulfillment_id=second_fulfillment.id,
            reading_version_ref=str(second_version.id),
            reading_job_ref=str(second_job.id),
        )
        released, release_created = await second_service.release_fulfillment_for_job(
            reading_job_ref=str(second_job.id),
            reason="terminal stopped",
        )
        assert released is not None
        assert release_created is True
        assert released.status == "released"
        root_model = import_module("app.readings.models").ReadingRoot
        root = await session.get(root_model, version.reading_root_id)
        assert root is not None
        assert root.product_version_snapshot_id is not None
        assert root.follow_up_count_snapshot == 2
        assert root.follow_up_window_seconds_snapshot == 86_400
        await repository.record_completion_intent(
            str(job.id),
            "交付正文",
            datetime.now(UTC),
        )
        await repository.record_accepted(
            str(job.id),
            runtime_contracts.Accepted(
                state_token="accepted-token",
                public_copy="交付正文",
            ),
            datetime.now(UTC),
        )
        accepted_copy = await repository.get_accepted_copy(version.id)
        assert accepted_copy is not None
        document = readings.ReadingDocumentRecord(
            id=uuid4(),
            reading_version_id=version.id,
            accepted_copy_id=accepted_copy.id,
            schema_version="reading-document/v1",
            payload_key_id="test-key",
            payload_nonce="test-nonce",
            payload_ciphertext="test-payload",
            payload_digest="test-digest",
        )
        session.add(document)
        await session.flush()

        with pytest.raises(CommerceError, match="Accepted Copy"):
            await service.mark_fulfillment_delivered(
                fulfillment_id=fulfillment.id,
                reading_version_ref=str(version.id),
                reading_job_ref=str(job.id),
                accepted_copy_ref=str(uuid4()),
                reading_document_ref=str(document.id),
            )
        projection = await service.ledger.project(
            entitlement_id=f"order:{payment.order_id}",
            owner_user_id=user.id,
        )
        assert projection.consumed == 0
        assert projection.reserved == 1

        delivered, created = await service.deliver_fulfillment_for_job(
            reading_job_ref=str(job.id),
        )
        replay, replayed = await service.deliver_fulfillment_for_job(
            reading_job_ref=str(job.id),
        )

        assert created is True
        assert replayed is False
        assert delivered.id == replay.id == fulfillment.id
        assert delivered.status == "delivered"
        projection = await service.ledger.project(
            entitlement_id=f"order:{payment.order_id}",
            owner_user_id=user.id,
        )
        assert projection.consumed == 1
        assert projection.reserved == 0
        events = await session.scalars(
            select(EntitlementEventRecord).where(
                EntitlementEventRecord.entitlement_id == f"order:{payment.order_id}",
                EntitlementEventRecord.kind == "CONSUME",
            )
        )
        assert len(list(events)) == 1


@pytest.mark.asyncio
async def test_failed_fulfillment_releases_reserved_unit_once(database: Any) -> None:
    async with database.sessions() as session:
        service, user, payment = await _paid_order(session)
        fulfillment, _ = await service.reserve_fulfillment(
            payment_id=payment.id,
            idempotency_key="fulfillment-release",
        )

        first, created = await service.release_fulfillment(
            fulfillment_id=fulfillment.id,
            reason="Runtime 失败",
        )
        replay, replayed = await service.release_fulfillment(
            fulfillment_id=fulfillment.id,
            reason="重复处理不应改写原因",
        )

        assert created is True
        assert replayed is False
        assert first.id == replay.id
        assert first.status == "released"
        assert first.failure_reason == "Runtime 失败"
        projection = await service.ledger.project(
            entitlement_id=f"order:{payment.order_id}",
            owner_user_id=user.id,
        )
        assert projection.reserved == 0
        assert projection.released == 1
