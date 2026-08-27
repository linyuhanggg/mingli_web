from __future__ import annotations

import asyncio
import importlib
import os
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from app.readings.alerts import NoopAlertSink
from sqlalchemy import event, func, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# isort: split
from orchestrator_fakes import make_candidate, make_model_receipt
from test_narrative_guard import build_brief
from test_reading_repository import create_reading_graph

WORKER_TEST_NOW = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)


@pytest.fixture
async def worker_database() -> AsyncIterator[Any]:
    database_module = importlib.import_module("app.database")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
    # The SQL Worker reaches Commerce on the accepted path even when the
    # seeded job has no paid fulfillment. Register the same model set as the
    # API fixture so a real PostgreSQL vertical test cannot pass only because
    # its accepted-path tables happen to be absent.
    importlib.import_module("app.admin.models")
    importlib.import_module("app.support.models")
    importlib.import_module("app.entitlements.models")
    importlib.import_module("app.commerce.models")
    importlib.import_module("app.referrals.models")
    importlib.import_module("app.content.models")
    importlib.import_module("app.privacy.models")
    importlib.import_module("app.media.models")
    database = database_module.Database("sqlite+aiosqlite:///:memory:")
    async with database.engine.begin() as connection:
        await connection.run_sync(identity_models.Base.metadata.create_all)
    yield database
    await database.dispose()


class PostgresDatabaseHarness:
    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def dispose(self) -> None:
        await self.engine.dispose()


@pytest.fixture
async def postgres_worker_database() -> AsyncIterator[Any]:
    url = os.environ.get("MINGLI_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("MINGLI_TEST_POSTGRES_URL is required for PostgreSQL concurrency tests")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
    schema = f"mingli_worker_test_{uuid4().hex}"
    admin_engine = create_async_engine(url, pool_pre_ping=True)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        url,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": schema}},
    )
    database = PostgresDatabaseHarness(engine)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(identity_models.Base.metadata.create_all)
        yield database
    finally:
        await database.dispose()
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current


class InjectedCommitFailure(RuntimeError):
    pass


class FirstWriteRuntime:
    def __init__(self, contracts: Any, *, complete_transport_failures: int = 0) -> None:
        self.contracts = contracts
        self.commands: list[Any] = []
        self.accepted_by_token: dict[str, str] = {}
        self.prepare_count = 0
        self.complete_transport_failures = complete_transport_failures

    async def execute(self, command: Any) -> Any:
        self.commands.append(command)
        if isinstance(command, self.contracts.Prepare):
            self.prepare_count += 1
            return self.contracts.Prepared(
                state_token=f"postgres-state-token-{self.prepare_count}",
                brief=build_brief(),
            )
        if isinstance(command, self.contracts.Complete):
            if self.complete_transport_failures > 0:
                self.complete_transport_failures -= 1
                errors = importlib.import_module("app.readings.errors")
                raise errors.RuntimeTransportError("simulated Complete response loss")
            accepted_copy = self.accepted_by_token.setdefault(
                command.state_token,
                command.public_copy,
            )
            return self.contracts.Accepted(
                state_token=command.state_token,
                public_copy=accepted_copy,
            )
        raise AssertionError(f"unexpected Runtime command: {command.kind}")


class ReplaySafeTokenRuntime:
    def __init__(self, contracts: Any) -> None:
        self.contracts = contracts
        self.commands: list[Any] = []

    async def execute(self, command: Any) -> Any:
        self.commands.append(command)
        if not isinstance(command, self.contracts.Prepare):
            raise AssertionError(f"unexpected Runtime command: {command.kind}")
        return self.contracts.Prepared(
            state_token="stable-replayed-prepared-token",
            brief=build_brief(),
        )


class CountingModel:
    def __init__(self, script: list[object]) -> None:
        self.script = list(script)
        self.requests: list[Any] = []

    async def generate(self, request: Any) -> Any:
        self.requests.append(request)
        if not self.script:
            raise AssertionError("model script exhausted")
        result = self.script.pop(0)
        if isinstance(result, Exception):
            raise result
        narrative = importlib.import_module("app.readings.narrative_contracts")
        if isinstance(result, narrative.NarrativeCandidate):
            contracts = importlib.import_module("app.readings.model_contracts")
            return contracts.ModelGenerationResult(
                candidate=result,
                receipt=make_model_receipt(request),
            )
        return result


def make_test_cipher() -> Any:
    envelope = importlib.import_module("app.security.envelope")
    return envelope.EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1")


async def process_one_stage(
    database: Any,
    *,
    worker_id: str,
    clock: MutableClock,
    orchestrator_factory: Any,
    lease_seconds: int = 30,
) -> Any:
    readings = importlib.import_module("worker.readings")
    source = readings.ReadingJobWorkSource(
        sessions=database.sessions,
        worker_id=worker_id,
        clock=clock,
        lease_seconds=lease_seconds,
    )
    item = await source.claim_one()
    assert item is not None
    processor = readings.ReadingJobProcessor(
        sessions=database.sessions,
        orchestrator_factory=orchestrator_factory,
        worker_id=worker_id,
        clock=clock,
    )
    await processor.process(item)
    return item


async def seed_job(
    database: Any,
    *,
    prepare_state_token: str | None = None,
) -> Any:
    async with database.sessions() as session, session.begin():
        _repository, _profile, _version, job, _contracts = await create_reading_graph(
            session,
            prepare_state_token=prepare_state_token,
            available_at=WORKER_TEST_NOW,
        )
        return job


async def seed_prepared_job(database: Any) -> Any:
    async with database.sessions() as session, session.begin():
        repository, _profile, _version, job, contracts = await create_reading_graph(session)
        now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
        await repository.record_prepared(
            str(job.id),
            contracts.Prepared(
                state_token="safe-expired-lease-token",
                brief=build_brief(),
            ),
            now,
        )
        job.status = "queued"
        job.available_at = now
        return job


async def test_worker_does_not_claim_a_job_waiting_for_paid_fulfillment(
    worker_database: Any,
) -> None:
    job = await seed_job(worker_database)
    readings_worker = importlib.import_module("worker.readings")
    readings_models = importlib.import_module("app.readings.models")
    async with worker_database.sessions() as session, session.begin():
        persisted = await session.get(readings_models.ReadingJobRecord, job.id)
        assert persisted is not None
        persisted.status = "awaiting_fulfillment"

    source = readings_worker.ReadingJobWorkSource(
        sessions=worker_database.sessions,
        worker_id="worker-paid-boundary",
        clock=MutableClock(WORKER_TEST_NOW),
    )

    assert await source.claim_one() is None


async def bind_paid_fulfillment(
    session: Any,
    *,
    version: Any,
    job: Any,
    key_prefix: str,
) -> Any:
    readings = importlib.import_module("app.readings.models")
    commerce_models = importlib.import_module("app.commerce.models")
    commerce_service = importlib.import_module("app.commerce.service")
    identity_models = importlib.import_module("app.identity.models")

    root = await session.get(readings.ReadingRoot, version.reading_root_id)
    assert root is not None and root.owner_user_id is not None
    user = await session.get(identity_models.User, root.owner_user_id)
    assert user is not None
    family = commerce_models.ProductFamily(
        key=f"{key_prefix}-family",
        label="Worker 超时释放测试",
    )
    session.add(family)
    await session.flush()
    product = commerce_models.ProductVersion(
        family_id=family.id,
        version="v1",
        price_minor=9900,
        currency="CNY",
        follow_up_count=0,
        follow_up_window_seconds=0,
        contract_version="reading-document-v1",
        status="active",
    )
    session.add(product)
    await session.flush()
    offer = commerce_models.ProductOffer(
        product_version_id=product.id,
        channel="closed",
        channel_sku=f"{key_prefix}-offer",
        price_minor=9900,
        currency="CNY",
        enabled=True,
    )
    session.add(offer)
    await session.flush()
    service = commerce_service.CommerceService(session)
    order = await service.create_order(
        owner_user_id=user.id,
        offer_id=offer.id,
        purchase_target_ref=f"{key_prefix}-target",
    )
    attempt, _ = await service.create_payment_attempt(
        order_id=order.id,
        channel="closed",
        idempotency_key=f"{key_prefix}-attempt",
    )
    payment, _ = await service.confirm_payment(
        order_id=order.id,
        attempt_id=attempt.id,
        channel="closed",
        channel_transaction_id=f"{key_prefix}-transaction",
        verified=True,
    )
    fulfillment, _ = await service.reserve_fulfillment(
        payment_id=payment.id,
        idempotency_key=f"{key_prefix}-fulfillment",
    )
    await service.bind_fulfillment_job(
        fulfillment_id=fulfillment.id,
        reading_version_ref=str(version.id),
        reading_job_ref=str(job.id),
    )
    return fulfillment


async def test_worker_expires_stale_waiting_input_and_releases_fulfillment(
    database: Any,
) -> None:
    readings = importlib.import_module("app.readings.models")
    commerce_models = importlib.import_module("app.commerce.models")
    runtime_contracts = importlib.import_module("app.readings.runtime_contracts")
    waiting_at = WORKER_TEST_NOW - timedelta(days=7)
    async with database.sessions() as session, session.begin():
        repository, _profile, version, job, _contracts = await create_reading_graph(
            session,
            available_at=WORKER_TEST_NOW,
        )
        await repository.record_waiting_input(
            str(job.id),
            runtime_contracts.Stopped(
                reason="need_input",
                public_copy="还需要补充资料。",
                state_token="waiting-timeout-token",
                input_request={
                    "requirements": [
                        {
                            "any_of": [
                                {
                                    "id": "birth_datetime",
                                    "label": "出生时间",
                                    "type_id": "datetime",
                                    "description": None,
                                    "choices": [],
                                }
                            ]
                        }
                    ]
                },
            ),
            waiting_at,
        )
        fulfillment = await bind_paid_fulfillment(
            session,
            version=version,
            job=job,
            key_prefix="waiting-timeout",
        )

    readings_worker = importlib.import_module("worker.readings")
    clock = MutableClock(WORKER_TEST_NOW)
    source = readings_worker.ReadingJobWorkSource(
        sessions=database.sessions,
        worker_id="worker-waiting-timeout",
        clock=clock,
        cipher=make_test_cipher(),
    )
    assert await source.claim_one() is None
    assert await source.claim_one() is None

    async with database.sessions() as session:
        persisted_version = await session.get(readings.ReadingVersion, version.id)
        persisted_job = await session.get(readings.ReadingJobRecord, job.id)
        persisted_fulfillment = await session.get(
            commerce_models.FulfillmentRecord,
            fulfillment.id,
        )
        assert persisted_version is not None
        assert persisted_job is not None
        assert persisted_fulfillment is not None
        assert persisted_version.status == "terminal_stopped"
        assert persisted_job.status == "stopped"
        assert persisted_version.runtime_failure_schema_version is None
        assert persisted_version.runtime_failure_code is None
        assert persisted_version.runtime_failure_category is None
        assert persisted_version.runtime_failure_retryable is None
        assert persisted_fulfillment.status == "released"
        envelope = importlib.import_module("app.security.envelope")
        payload = make_test_cipher().decrypt_json(
            envelope.EncryptedPayload(
                key_id=persisted_version.last_result_key_id or "",
                nonce=persisted_version.last_result_nonce or "",
                ciphertext=persisted_version.last_result_ciphertext or "",
                fingerprint=persisted_version.last_result_digest or "",
            ),
            context=f"reading-version:{persisted_version.id}:last-result",
        )
        assert payload == {
            "kind": "host_lifecycle",
            "reason": "input_wait_expired",
            "public_copy": "补充资料超过 7 天，任务已取消。",
        }
        release_events = list(
            await session.scalars(
                select(commerce_models.EntitlementEventRecord).where(
                    commerce_models.EntitlementEventRecord.entitlement_id
                    == fulfillment.entitlement_id,
                    commerce_models.EntitlementEventRecord.kind == "RELEASE",
                )
            )
        )
        assert len(release_events) == 1
        root = await session.get(readings.ReadingRoot, persisted_version.reading_root_id)
        assert root is not None and root.owner_user_id is not None
        notifications = list(
            await session.scalars(
                select(commerce_models.NotificationOutbox).where(
                    commerce_models.NotificationOutbox.owner_user_id == root.owner_user_id,
                    commerce_models.NotificationOutbox.kind == "reading.failed",
                )
            )
        )
        assert len(notifications) == 1
        assert notifications[0].payload["reason"] == "input_timeout"


async def test_worker_keeps_recent_waiting_input_and_reserved_fulfillment(
    database: Any,
) -> None:
    readings = importlib.import_module("app.readings.models")
    runtime_contracts = importlib.import_module("app.readings.runtime_contracts")
    waiting_at = WORKER_TEST_NOW - timedelta(days=6, hours=23)
    async with database.sessions() as session, session.begin():
        repository, _profile, version, job, _contracts = await create_reading_graph(
            session,
            available_at=WORKER_TEST_NOW,
        )
        await repository.record_waiting_input(
            str(job.id),
            runtime_contracts.Stopped(
                reason="need_input",
                public_copy="还需要补充资料。",
                state_token="recent-waiting-token",
                input_request={
                    "requirements": [
                        {
                            "any_of": [
                                {
                                    "id": "birth_datetime",
                                    "label": "出生时间",
                                    "type_id": "datetime",
                                    "description": None,
                                    "choices": [],
                                }
                            ]
                        }
                    ]
                },
            ),
            waiting_at,
        )

    readings_worker = importlib.import_module("worker.readings")
    clock = MutableClock(WORKER_TEST_NOW)
    source = readings_worker.ReadingJobWorkSource(
        sessions=database.sessions,
        worker_id="worker-recent-waiting",
        clock=clock,
        cipher=make_test_cipher(),
    )
    assert await source.claim_one() is None

    async with database.sessions() as session:
        persisted_version = await session.get(readings.ReadingVersion, version.id)
        persisted_job = await session.get(readings.ReadingJobRecord, job.id)
        assert persisted_version is not None
        assert persisted_job is not None
        assert persisted_version.status == "waiting_input"
        assert persisted_job.status == "waiting_input"


async def test_worker_releases_bound_fulfillment_on_terminal_stop(
    database: Any,
) -> None:
    readings = importlib.import_module("app.readings.models")
    commerce_models = importlib.import_module("app.commerce.models")
    commerce_service = importlib.import_module("app.commerce.service")
    identity_models = importlib.import_module("app.identity.models")
    orchestrator = importlib.import_module("app.readings.orchestrator")

    async with database.sessions() as session, session.begin():
        repository, _profile_version, version, job, _contracts = await create_reading_graph(
            session,
            available_at=WORKER_TEST_NOW,
        )
        root = await session.get(readings.ReadingRoot, version.reading_root_id)
        assert root is not None and root.owner_user_id is not None
        user = await session.get(identity_models.User, root.owner_user_id)
        assert user is not None
        family = commerce_models.ProductFamily(
            key="worker-terminal-stop-family",
            label="Worker 终止释放测试",
        )
        session.add(family)
        await session.flush()
        product = commerce_models.ProductVersion(
            family_id=family.id,
            version="v1",
            price_minor=9900,
            currency="CNY",
            follow_up_count=0,
            follow_up_window_seconds=0,
            contract_version="reading-document-v1",
            status="active",
        )
        session.add(product)
        await session.flush()
        offer = commerce_models.ProductOffer(
            product_version_id=product.id,
            channel="closed",
            channel_sku="worker-terminal-stop-v1",
            price_minor=9900,
            currency="CNY",
            enabled=True,
        )
        session.add(offer)
        await session.flush()
        service = commerce_service.CommerceService(session)
        order = await service.create_order(
            owner_user_id=user.id,
            offer_id=offer.id,
            purchase_target_ref="worker-terminal-stop-target",
        )
        attempt, _ = await service.create_payment_attempt(
            order_id=order.id,
            channel="closed",
            idempotency_key="worker-terminal-stop-attempt",
        )
        payment, _ = await service.confirm_payment(
            order_id=order.id,
            attempt_id=attempt.id,
            channel="closed",
            channel_transaction_id="worker-terminal-stop-transaction",
            verified=True,
        )
        fulfillment, _ = await service.reserve_fulfillment(
            payment_id=payment.id,
            idempotency_key="worker-terminal-stop-fulfillment",
        )
        await service.bind_fulfillment_job(
            fulfillment_id=fulfillment.id,
            reading_version_ref=str(version.id),
            reading_job_ref=str(job.id),
        )

    class TerminalStopFactory:
        def __call__(self, _session: Any) -> TerminalStopFactory:
            return self

        async def run(self, _job_id: str) -> Any:
            return orchestrator.ReadingOutcome(
                status=orchestrator.ReadingStatus.TERMINAL_STOPPED,
                stopped_reason="terminal test stop",
            )

    clock = MutableClock(WORKER_TEST_NOW)
    await process_one_stage(
        database,
        worker_id="worker-terminal-stop",
        clock=clock,
        orchestrator_factory=TerminalStopFactory(),
    )

    async with database.sessions() as session:
        persisted = await session.get(commerce_models.FulfillmentRecord, fulfillment.id)
        assert persisted is not None
        assert persisted.status == "released"
        events = list(
            await session.scalars(
                select(commerce_models.EntitlementEventRecord).where(
                    commerce_models.EntitlementEventRecord.entitlement_id
                    == fulfillment.entitlement_id,
                    commerce_models.EntitlementEventRecord.kind == "RELEASE",
                )
            )
        )
        assert len(events) == 1
        persisted_job = await session.get(readings.ReadingJobRecord, job.id)
        assert persisted_job is not None
        assert persisted_job.status == "stopped"


async def test_worker_persists_runtime_failure_without_replaying_no_token_prepare(
    worker_database: Any,
) -> None:
    contracts = importlib.import_module("app.readings.runtime_contracts")
    models = importlib.import_module("app.readings.models")
    readings = importlib.import_module("worker.readings")
    job = await seed_job(worker_database)
    clock = MutableClock(WORKER_TEST_NOW)

    class RetryableFailureRuntime:
        def __init__(self) -> None:
            self.commands: list[Any] = []

        async def execute(self, command: Any) -> Any:
            self.commands.append(command)
            return contracts.Stopped(
                reason="error",
                public_copy="运行时暂时不可用。",
                failure=contracts.RuntimeFailure(
                    code="transient.resource_unavailable",
                    category="transient",
                    retryable=True,
                ),
            )

    runtime = RetryableFailureRuntime()
    factory = readings.SqlReadingOrchestratorFactory(
        cipher=make_test_cipher(),
        runtime=runtime,
        model=CountingModel([]),
        clock=clock,
        alert_sink=NoopAlertSink(),
    )

    await process_one_stage(
        worker_database,
        worker_id="worker-runtime-failure",
        clock=clock,
        orchestrator_factory=factory,
    )

    assert [command.kind for command in runtime.commands] == ["prepare"]
    async with worker_database.sessions() as session:
        version = await session.get(models.ReadingVersion, job.reading_version_id)
        persisted_job = await session.get(models.ReadingJobRecord, job.id)
        assert version is not None
        assert persisted_job is not None
        assert version.status == "terminal_stopped"
        assert persisted_job.status == "stopped"
        assert version.runtime_failure_schema_version == "mingli-runtime-failure/v1"
        assert version.runtime_failure_code == "transient.resource_unavailable"
        assert version.runtime_failure_category == "transient"
        assert version.runtime_failure_retryable is True

    assert await readings.ReadingJobWorkSource(
        sessions=worker_database.sessions,
        worker_id="worker-runtime-failure-retry",
        clock=clock,
    ).claim_one() is None
    assert [command.kind for command in runtime.commands] == ["prepare"]


def test_claim_query_is_fail_safe_for_postgresql_workers() -> None:
    readings = importlib.import_module("worker.readings")
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)

    compiled = str(
        readings.reading_job_claim_statement(now).compile(dialect=postgresql.dialect())
    ).upper()

    assert "FOR UPDATE SKIP LOCKED" in compiled


async def test_postgresql_workers_concurrently_claim_a_job_at_most_once(
    postgres_worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    job = await seed_job(postgres_worker_database)
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    first = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-1",
        clock=clock,
        lease_seconds=30,
    )
    second = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-2",
        clock=clock,
        lease_seconds=30,
    )
    release = asyncio.Event()

    async def claim_when_released(source: Any) -> Any:
        await release.wait()
        return await source.claim_one()

    first_task = asyncio.create_task(claim_when_released(first))
    second_task = asyncio.create_task(claim_when_released(second))
    release.set()
    claimed = await asyncio.gather(first_task, second_task)

    items = [item for item in claimed if item is not None]
    assert len(items) == 1
    assert items[0].id == str(job.id)
    assert items[0].claim_token
    assert items[0].lease_generation == 1


@pytest.mark.parametrize("owner_kind", ["user", "guest"])
async def test_postgresql_idempotency_key_insert_is_atomic_per_owner(
    postgres_worker_database: Any,
    owner_kind: str,
) -> None:
    identity_models = importlib.import_module("app.identity.models")
    reading_models = importlib.import_module("app.readings.models")

    async with postgres_worker_database.sessions() as session, session.begin():
        _repository, _profile_version, version, _job, _contracts = await create_reading_graph(
            session
        )
        root = await session.get(reading_models.ReadingRoot, version.reading_root_id)
        assert root is not None
        user_id = root.owner_user_id
        assert user_id is not None
        guest_id = None
        if owner_kind == "guest":
            guest = identity_models.GuestSession(
                token_hash=f"guest-token-{uuid4().hex}",
                csrf_token_hash=f"guest-csrf-{uuid4().hex}",
                expires_at=datetime(2099, 1, 1, tzinfo=UTC),
            )
            session.add(guest)
            await session.flush()
            guest_id = guest.id
        version_id = version.id

    async def insert_once() -> bool:
        async with postgres_worker_database.sessions() as session:
            session.add(
                reading_models.ReadingIdempotencyKey(
                    key_hash=f"{owner_kind}-same-key",
                    action="profile_preview",
                    request_fingerprint="f" * 64,
                    owner_user_id=user_id if owner_kind == "user" else None,
                    owner_guest_session_id=guest_id,
                    reading_version_id=version_id,
                )
            )
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return False
            return True

    outcomes = await asyncio.gather(insert_once(), insert_once())

    assert sorted(outcomes) == [False, True]
    async with postgres_worker_database.sessions() as session:
        records = list(await session.scalars(select(reading_models.ReadingIdempotencyKey)))
    assert len(records) == 1


async def test_postgresql_owner_lock_serializes_same_tuple_profile_confirms(
    postgres_worker_database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity_models = importlib.import_module("app.identity.models")
    profile_models = importlib.import_module("app.profiles.models")
    profile_schemas = importlib.import_module("app.profiles.schemas")
    profile_service = importlib.import_module("app.profiles.service")

    async with postgres_worker_database.sessions() as session, session.begin():
        user = identity_models.User()
        session.add(user)
        await session.flush()
        service = profile_service.ProfileService(session, test_settings)
        owner = type("Owner", (), {"kind": "user", "id": user.id})()
        first_draft_id = await service.create_draft(owner, label="本人")
        second_draft_id = await service.create_draft(owner, label="本人")
        user_id = user.id

    first_check_finished = asyncio.Event()
    second_check_finished = asyncio.Event()
    release_first = asyncio.Event()
    original_check = profile_service.ProfileService._name_birth_conflict
    check_count = 0

    async def delayed_conflict_check(self: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal check_count
        conflict = await original_check(self, *args, **kwargs)
        check_count += 1
        if check_count == 1:
            first_check_finished.set()
            await release_first.wait()
        else:
            second_check_finished.set()
        return conflict

    monkeypatch.setattr(
        profile_service.ProfileService,
        "_name_birth_conflict",
        delayed_conflict_check,
    )
    payload = profile_schemas.ProfileConfirmRequest(
        birth_datetime="1994-04-30T05:55:00+08:00",
        timezone="Asia/Shanghai",
        location="北京市朝阳区",
        gender="female",
        time_basis_policy="civil",
        zi_hour_policy="midnight",
    )

    async def confirm(draft_id: Any) -> str:
        async with postgres_worker_database.sessions() as session:
            service = profile_service.ProfileService(session, test_settings)
            owner = type("Owner", (), {"kind": "user", "id": user_id})()
            try:
                await service.confirm_draft(owner, draft_id, payload)
            except profile_service.ProfileNameConflictError:
                await session.rollback()
                return "conflict"
            await session.commit()
            return "confirmed"

    first = asyncio.create_task(confirm(first_draft_id))
    await asyncio.wait_for(first_check_finished.wait(), timeout=2)
    second = asyncio.create_task(confirm(second_draft_id))
    with suppress(TimeoutError):
        await asyncio.wait_for(second_check_finished.wait(), timeout=0.2)
    release_first.set()

    outcomes = await asyncio.wait_for(asyncio.gather(first, second), timeout=5)

    assert sorted(outcomes) == ["confirmed", "conflict"]
    async with postgres_worker_database.sessions() as session:
        versions = list(await session.scalars(select(profile_models.ProfileVersion)))
    assert len(versions) == 1


async def test_active_postgresql_processor_lock_fences_an_expired_reclaim(
    postgres_worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    orchestrator = importlib.import_module("app.readings.orchestrator")
    job = await seed_job(postgres_worker_database)
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    source_a = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-a",
        clock=clock,
        lease_seconds=1,
    )
    item_a = await source_a.claim_one()
    started = asyncio.Event()
    finish = asyncio.Event()

    class SlowRunner:
        async def run(self, job_id: str) -> Any:
            assert job_id == str(job.id)
            started.set()
            await finish.wait()
            return orchestrator.ReadingOutcome(status=orchestrator.ReadingStatus.ACCEPTED)

    processor_a = readings.ReadingJobProcessor(
        sessions=postgres_worker_database.sessions,
        orchestrator_factory=lambda _session: SlowRunner(),
        worker_id="worker-a",
        clock=clock,
    )
    processing = asyncio.create_task(processor_a.process(item_a))
    await asyncio.wait_for(started.wait(), timeout=2)
    clock.current += timedelta(seconds=2)
    source_b = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-b",
        clock=clock,
        lease_seconds=30,
    )

    assert await source_b.claim_one() is None

    finish.set()
    await asyncio.wait_for(processing, timeout=2)


async def test_expired_lease_recovery_rotates_the_fencing_token(
    worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    job = await seed_prepared_job(worker_database)
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    first = readings.ReadingJobWorkSource(
        sessions=worker_database.sessions,
        worker_id="worker-before-restart",
        clock=clock,
        lease_seconds=30,
    )
    first_item = await first.claim_one()

    clock.current += timedelta(seconds=31)
    restarted = readings.ReadingJobWorkSource(
        sessions=worker_database.sessions,
        worker_id="worker-after-restart",
        clock=clock,
        lease_seconds=30,
    )
    recovered = await restarted.claim_one()

    assert recovered.id == str(job.id)
    assert recovered.claim_token != first_item.claim_token
    assert recovered.lease_generation == first_item.lease_generation + 1


async def test_expired_worker_cannot_commit_after_another_worker_reclaims(
    worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    orchestrator = importlib.import_module("app.readings.orchestrator")
    await seed_prepared_job(worker_database)
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    source_a = readings.ReadingJobWorkSource(
        sessions=worker_database.sessions,
        worker_id="worker-a",
        clock=clock,
        lease_seconds=30,
    )
    item_a = await source_a.claim_one()
    clock.current += timedelta(seconds=31)
    source_b = readings.ReadingJobWorkSource(
        sessions=worker_database.sessions,
        worker_id="worker-b",
        clock=clock,
        lease_seconds=30,
    )
    item_b = await source_b.claim_one()
    calls: list[str] = []

    class Runner:
        async def run(self, job_id: str) -> Any:
            calls.append(job_id)
            return orchestrator.ReadingOutcome(status=orchestrator.ReadingStatus.ACCEPTED)

    processor_a = readings.ReadingJobProcessor(
        sessions=worker_database.sessions,
        orchestrator_factory=lambda _session: Runner(),
        worker_id="worker-a",
        clock=clock,
    )
    processor_b = readings.ReadingJobProcessor(
        sessions=worker_database.sessions,
        orchestrator_factory=lambda _session: Runner(),
        worker_id="worker-b",
        clock=clock,
    )

    with pytest.raises(readings.LeaseLostError):
        await processor_a.process(item_a)
    await processor_b.process(item_b)

    assert calls == [item_b.id]


async def test_processor_passes_only_job_id_and_records_outcome(
    worker_database: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    readings = importlib.import_module("worker.readings")
    orchestrator = importlib.import_module("app.readings.orchestrator")
    models = importlib.import_module("app.readings.models")
    job = await seed_job(worker_database)
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    source = readings.ReadingJobWorkSource(
        sessions=worker_database.sessions,
        worker_id="worker-1",
        clock=clock,
        lease_seconds=30,
    )
    item = await source.claim_one()
    calls: list[str] = []

    class RecordingOrchestrator:
        async def run(self, job_id: str) -> Any:
            calls.append(job_id)
            return orchestrator.ReadingOutcome(
                status=orchestrator.ReadingStatus.ACCEPTED,
                public_copy="sensitive accepted copy",
            )

    processor = readings.ReadingJobProcessor(
        sessions=worker_database.sessions,
        orchestrator_factory=lambda _session: RecordingOrchestrator(),
        worker_id="worker-1",
        clock=clock,
    )

    await processor.process(item)

    assert calls == [str(job.id)]
    async with worker_database.sessions() as session:
        persisted = await session.get(models.ReadingJobRecord, job.id)
        assert persisted.status == "complete"
        assert persisted.lease_owner is None
        assert persisted.lease_token is None
        assert persisted.lease_expires_at is None
    assert "sensitive accepted copy" not in caplog.text
    assert "runtime-secret-token" not in caplog.text
    assert item.claim_token not in caplog.text


async def test_model_cancellation_commits_attempt_before_worker_propagates(
    worker_database: Any,
) -> None:
    errors = importlib.import_module("app.readings.errors")
    models = importlib.import_module("app.readings.models")
    readings = importlib.import_module("worker.readings")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    clock = MutableClock(WORKER_TEST_NOW)
    job = await seed_prepared_job(worker_database)

    class CancellingModel:
        def __init__(self) -> None:
            self.calls = 0

        async def generate(self, request: Any) -> Any:
            self.calls += 1
            receipt = make_model_receipt(request)
            raise errors.NarrativeGenerationCancelled(
                receipt=replace(
                    receipt,
                    outcome="failed",
                    error_code="model_cancelled",
                )
            )

    model = CancellingModel()
    factory = readings.SqlReadingOrchestratorFactory(
        cipher=make_test_cipher(),
        runtime=FirstWriteRuntime(contracts),
        model=model,
        clock=clock,
            alert_sink=NoopAlertSink(),
    )
    source = readings.ReadingJobWorkSource(
        sessions=worker_database.sessions,
        worker_id="worker-cancelled-model",
        clock=clock,
        lease_seconds=30,
    )
    item = await source.claim_one()
    assert item is not None
    processor = readings.ReadingJobProcessor(
        sessions=worker_database.sessions,
        orchestrator_factory=factory,
        worker_id="worker-cancelled-model",
        clock=clock,
    )

    with pytest.raises(asyncio.CancelledError):
        await processor.process(item)

    async with worker_database.sessions() as session:
        persisted_job = await session.get(models.ReadingJobRecord, job.id)
        attempt = await session.scalar(
            select(models.GenerationAttempt).where(
                models.GenerationAttempt.reading_version_id == job.reading_version_id
            )
        )
    assert model.calls == 1
    assert attempt is not None
    assert attempt.attempt_number == 1
    assert attempt.model_receipt["outcome"] == "failed"
    assert attempt.model_receipt["error_code"] == "model_cancelled"
    assert persisted_job.status == "queued"
    assert persisted_job.lease_owner is None
    assert persisted_job.lease_token is None
    assert persisted_job.lease_expires_at is None

    reclaimed = await source.claim_one()
    assert reclaimed is not None
    assert reclaimed.lease_generation == item.lease_generation + 1


async def test_processor_schedules_tokened_prepare_transport_retry(
    worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    orchestrator = importlib.import_module("app.readings.orchestrator")
    models = importlib.import_module("app.readings.models")
    job = await seed_job(
        worker_database,
        prepare_state_token="accepted-parent-token",
    )
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    retry_at = clock.now() + timedelta(seconds=5)
    source = readings.ReadingJobWorkSource(
        sessions=worker_database.sessions,
        worker_id="worker-tokened-transport-unknown",
        clock=clock,
        lease_seconds=30,
    )
    item = await source.claim_one()
    assert item is not None

    class RetryRunner:
        async def run(self, job_id: str) -> Any:
            assert job_id == str(job.id)
            return orchestrator.ReadingOutcome(
                status=orchestrator.ReadingStatus.INPUT_READY,
                retry_not_before=retry_at,
            )

    processor = readings.ReadingJobProcessor(
        sessions=worker_database.sessions,
        orchestrator_factory=lambda _session: RetryRunner(),
        worker_id="worker-tokened-transport-unknown",
        clock=clock,
    )
    await processor.process(item)

    async with worker_database.sessions() as session:
        persisted = await session.get(models.ReadingJobRecord, job.id)
        assert persisted.status == "queued"
        assert persisted.available_at == retry_at.replace(tzinfo=None)
        assert persisted.lease_owner is None
        assert persisted.lease_token is None
        assert persisted.lease_expires_at is None
    assert await source.claim_one() is None

    clock.current = retry_at
    recovered = await source.claim_one()
    assert recovered is not None
    assert recovered.lease_generation == item.lease_generation + 1


async def test_postgresql_prepared_checkpoint_commits_before_model_restart(
    postgres_worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    repository_module = importlib.import_module("app.readings.repository")
    orchestrator = importlib.import_module("app.readings.orchestrator")
    narrative = importlib.import_module("app.readings.narrative_contracts")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    runtime = FirstWriteRuntime(contracts)
    model = CountingModel([make_candidate(narrative)])
    cipher = make_test_cipher()
    factory = readings.SqlReadingOrchestratorFactory(
        cipher=cipher,
        runtime=runtime,
        model=model,
        clock=MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC)),
            alert_sink=NoopAlertSink(),
    )
    clock = factory.clock
    job = await seed_job(postgres_worker_database)

    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-prepare",
        clock=clock,
        orchestrator_factory=factory,
    )

    assert runtime.prepare_count == 1
    assert model.requests == []
    assert [command.kind for command in runtime.commands] == ["prepare"]
    async with postgres_worker_database.sessions() as session:
        checkpoint = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
        assert checkpoint.status is orchestrator.ReadingStatus.PREPARED
        assert checkpoint.prepared is not None
        assert checkpoint.attempt_count == 0

    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-after-restart",
        clock=clock,
        orchestrator_factory=factory,
    )

    assert runtime.prepare_count == 1
    assert len(model.requests) == 1
    assert [command.kind for command in runtime.commands] == ["prepare"]
    async with postgres_worker_database.sessions() as session:
        checkpoint = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
        assert checkpoint.status is orchestrator.ReadingStatus.COMPLETING
        assert checkpoint.attempt_count == 1
        assert checkpoint.completion_copy is not None


async def test_expired_initial_prepare_claim_is_quarantined_without_runtime_replay(
    postgres_worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    models = importlib.import_module("app.readings.models")
    repository_module = importlib.import_module("app.readings.repository")
    orchestrator = importlib.import_module("app.readings.orchestrator")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    runtime = FirstWriteRuntime(contracts)
    model = CountingModel([])
    cipher = make_test_cipher()
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    base_factory = readings.SqlReadingOrchestratorFactory(
        cipher=cipher,
        runtime=runtime,
        model=model,
        clock=clock,
            alert_sink=NoopAlertSink(),
    )
    job = await seed_job(postgres_worker_database)

    def failing_commit_factory(session: Any) -> Any:
        def fail_before_commit(_session: Any) -> None:
            raise InjectedCommitFailure("Prepared checkpoint commit failed")

        event.listen(session.sync_session, "before_commit", fail_before_commit, once=True)
        return base_factory(session)

    source = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-prepare-crashed",
        clock=clock,
        lease_seconds=30,
    )
    crashed_item = await source.claim_one()
    assert crashed_item is not None
    processor = readings.ReadingJobProcessor(
        sessions=postgres_worker_database.sessions,
        orchestrator_factory=failing_commit_factory,
        worker_id="worker-prepare-crashed",
        clock=clock,
    )
    with pytest.raises(InjectedCommitFailure, match="Prepared checkpoint"):
        await processor.process(crashed_item)

    assert runtime.prepare_count == 1
    assert [command.kind for command in runtime.commands] == ["prepare"]
    async with postgres_worker_database.sessions() as session:
        before_recovery = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
        persisted_job = await session.get(models.ReadingJobRecord, job.id)
        assert before_recovery.status is orchestrator.ReadingStatus.INPUT_READY
        assert before_recovery.prepared is None
        assert persisted_job.status == "claimed"

    clock.current += timedelta(seconds=31)
    recovering_source = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-must-not-replay-prepare",
        clock=clock,
        lease_seconds=30,
    )
    assert await recovering_source.claim_one() is None

    assert runtime.prepare_count == 1
    assert [command.kind for command in runtime.commands] == ["prepare"]
    async with postgres_worker_database.sessions() as session:
        quarantined = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
        persisted_job = await session.get(models.ReadingJobRecord, job.id)
        assert quarantined.status is orchestrator.ReadingStatus.RUNTIME_UNKNOWN
        assert quarantined.prepared is None
        assert persisted_job.status == "runtime_unknown"
        assert persisted_job.lease_owner is None
        assert persisted_job.lease_token is None
        assert persisted_job.lease_expires_at is None


async def test_expired_tokened_prepare_rotates_fence_and_replays_original_token(
    postgres_worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    repository_module = importlib.import_module("app.readings.repository")
    orchestrator = importlib.import_module("app.readings.orchestrator")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    original_state_token = "accepted-parent-token"
    runtime = ReplaySafeTokenRuntime(contracts)
    model = CountingModel([])
    cipher = make_test_cipher()
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    base_factory = readings.SqlReadingOrchestratorFactory(
        cipher=cipher,
        runtime=runtime,
        model=model,
        clock=clock,
            alert_sink=NoopAlertSink(),
    )
    job = await seed_job(
        postgres_worker_database,
        prepare_state_token=original_state_token,
    )

    def failing_commit_factory(session: Any) -> Any:
        def fail_before_commit(_session: Any) -> None:
            raise InjectedCommitFailure("tokened Prepared checkpoint commit failed")

        event.listen(session.sync_session, "before_commit", fail_before_commit, once=True)
        return base_factory(session)

    first_source = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-tokened-prepare-crashed",
        clock=clock,
        lease_seconds=30,
    )
    first_item = await first_source.claim_one()
    assert first_item is not None
    first_processor = readings.ReadingJobProcessor(
        sessions=postgres_worker_database.sessions,
        orchestrator_factory=failing_commit_factory,
        worker_id="worker-tokened-prepare-crashed",
        clock=clock,
    )
    with pytest.raises(InjectedCommitFailure, match="tokened Prepared"):
        await first_processor.process(first_item)

    clock.current += timedelta(seconds=31)
    recovering_source = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-tokened-prepare-recovery",
        clock=clock,
        lease_seconds=30,
    )
    recovered_item = await recovering_source.claim_one()
    assert recovered_item is not None
    assert recovered_item.id == first_item.id
    assert recovered_item.claim_token != first_item.claim_token
    assert recovered_item.lease_generation == first_item.lease_generation + 1

    recovering_processor = readings.ReadingJobProcessor(
        sessions=postgres_worker_database.sessions,
        orchestrator_factory=base_factory,
        worker_id="worker-tokened-prepare-recovery",
        clock=clock,
    )
    await recovering_processor.process(recovered_item)

    prepare_commands = [
        command for command in runtime.commands if isinstance(command, contracts.Prepare)
    ]
    assert len(prepare_commands) == 2
    assert [command.state_token for command in prepare_commands] == [
        original_state_token,
        original_state_token,
    ]
    async with postgres_worker_database.sessions() as session:
        checkpoint = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
        assert checkpoint.status is orchestrator.ReadingStatus.PREPARED
        assert checkpoint.prepared is not None
        assert checkpoint.prepared.state_token == "stable-replayed-prepared-token"


async def test_postgresql_complete_commit_failure_replays_exact_intent(
    postgres_worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    models = importlib.import_module("app.readings.models")
    repository_module = importlib.import_module("app.readings.repository")
    orchestrator = importlib.import_module("app.readings.orchestrator")
    narrative = importlib.import_module("app.readings.narrative_contracts")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    runtime = FirstWriteRuntime(contracts)
    model = CountingModel([make_candidate(narrative)])
    cipher = make_test_cipher()
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    base_factory = readings.SqlReadingOrchestratorFactory(
        cipher=cipher,
        runtime=runtime,
        model=model,
        clock=clock,
            alert_sink=NoopAlertSink(),
    )
    job = await seed_job(postgres_worker_database)

    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-prepare",
        clock=clock,
        orchestrator_factory=base_factory,
    )
    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-model",
        clock=clock,
        orchestrator_factory=base_factory,
    )
    async with postgres_worker_database.sessions() as session:
        before_complete = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
    assert before_complete.prepared is not None
    assert before_complete.completion_copy is not None

    def failing_commit_factory(session: Any) -> Any:
        def fail_before_commit(_session: Any) -> None:
            raise InjectedCommitFailure("database commit failed after Runtime Accepted")

        event.listen(session.sync_session, "before_commit", fail_before_commit, once=True)
        return base_factory(session)

    source = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-before-crash",
        clock=clock,
        lease_seconds=30,
    )
    crashed_item = await source.claim_one()
    assert crashed_item is not None
    crashed_processor = readings.ReadingJobProcessor(
        sessions=postgres_worker_database.sessions,
        orchestrator_factory=failing_commit_factory,
        worker_id="worker-before-crash",
        clock=clock,
    )
    with pytest.raises(InjectedCommitFailure, match="commit failed"):
        await crashed_processor.process(crashed_item)

    complete_commands = [command for command in runtime.commands if command.kind == "complete"]
    assert len(complete_commands) == 1
    assert complete_commands[0].state_token == before_complete.prepared.state_token
    assert complete_commands[0].public_copy.encode() == before_complete.completion_copy.encode()
    async with postgres_worker_database.sessions() as session:
        rolled_back = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
        accepted_count = await session.scalar(select(func.count()).select_from(models.AcceptedCopy))
        persisted_job = await session.get(models.ReadingJobRecord, job.id)
        assert rolled_back.status is orchestrator.ReadingStatus.COMPLETING
        assert rolled_back.accepted is None
        assert rolled_back.completion_copy == before_complete.completion_copy
        assert accepted_count == 0
        assert persisted_job.lease_owner == "worker-before-crash"

    clock.current += timedelta(seconds=31)
    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-after-crash",
        clock=clock,
        orchestrator_factory=base_factory,
    )

    complete_commands = [command for command in runtime.commands if command.kind == "complete"]
    assert len(complete_commands) == 2
    assert complete_commands[1].state_token == complete_commands[0].state_token
    assert complete_commands[1].public_copy.encode() == complete_commands[0].public_copy.encode()
    assert len(runtime.accepted_by_token) == 1
    async with postgres_worker_database.sessions() as session:
        recovered = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
        accepted_count = await session.scalar(select(func.count()).select_from(models.AcceptedCopy))
        assert recovered.status is orchestrator.ReadingStatus.ACCEPTED
        assert recovered.accepted is not None
        assert recovered.accepted.state_token == before_complete.prepared.state_token
        assert recovered.accepted.public_copy == before_complete.completion_copy
        assert accepted_count == 1


async def test_postgresql_complete_transport_retry_is_delayed_and_exact(
    postgres_worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    models = importlib.import_module("app.readings.models")
    repository_module = importlib.import_module("app.readings.repository")
    orchestrator = importlib.import_module("app.readings.orchestrator")
    narrative = importlib.import_module("app.readings.narrative_contracts")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    runtime = FirstWriteRuntime(contracts, complete_transport_failures=1)
    model = CountingModel([make_candidate(narrative)])
    cipher = make_test_cipher()
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    factory = readings.SqlReadingOrchestratorFactory(
        cipher=cipher,
        runtime=runtime,
        model=model,
        clock=clock,
            alert_sink=NoopAlertSink(),
    )
    job = await seed_job(postgres_worker_database)

    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-prepare",
        clock=clock,
        orchestrator_factory=factory,
    )
    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-model",
        clock=clock,
        orchestrator_factory=factory,
    )

    async with postgres_worker_database.sessions() as session:
        generated_job = await session.get(models.ReadingJobRecord, job.id)
        assert generated_job.status == "queued"
        assert generated_job.available_at <= clock.now()

    immediate_source = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-first-complete",
        clock=clock,
        lease_seconds=30,
    )
    immediate_item = await immediate_source.claim_one()
    assert immediate_item is not None
    immediate_processor = readings.ReadingJobProcessor(
        sessions=postgres_worker_database.sessions,
        orchestrator_factory=factory,
        worker_id="worker-first-complete",
        clock=clock,
    )
    await immediate_processor.process(immediate_item)

    async with postgres_worker_database.sessions() as session:
        delayed_job = await session.get(models.ReadingJobRecord, job.id)
        assert delayed_job.status == "queued"
        assert delayed_job.lease_owner is None
        assert delayed_job.lease_token is None
        assert delayed_job.lease_expires_at is None
        assert delayed_job.available_at > clock.now()
        retry_not_before = delayed_job.available_at

    early_source = readings.ReadingJobWorkSource(
        sessions=postgres_worker_database.sessions,
        worker_id="worker-too-early",
        clock=clock,
        lease_seconds=30,
    )
    assert await early_source.claim_one() is None

    clock.current = retry_not_before
    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-replay-complete",
        clock=clock,
        orchestrator_factory=factory,
    )

    complete_commands = [command for command in runtime.commands if command.kind == "complete"]
    assert len(complete_commands) == 2
    assert complete_commands[1].state_token == complete_commands[0].state_token
    assert complete_commands[1].public_copy.encode() == complete_commands[0].public_copy.encode()
    async with postgres_worker_database.sessions() as session:
        checkpoint = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
        assert checkpoint.status is orchestrator.ReadingStatus.ACCEPTED


async def test_postgresql_failed_model_attempt_commits_before_restart(
    postgres_worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    errors = importlib.import_module("app.readings.errors")
    models = importlib.import_module("app.readings.models")
    repository_module = importlib.import_module("app.readings.repository")
    orchestrator = importlib.import_module("app.readings.orchestrator")
    narrative = importlib.import_module("app.readings.narrative_contracts")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    runtime = FirstWriteRuntime(contracts)
    model = CountingModel(
        [
            errors.NarrativeGenerationError("first model call failed"),
            make_candidate(narrative),
        ]
    )
    cipher = make_test_cipher()
    clock = MutableClock(datetime(2026, 8, 9, 12, 0, tzinfo=UTC))
    factory = readings.SqlReadingOrchestratorFactory(
        cipher=cipher,
        runtime=runtime,
        model=model,
        clock=clock,
            alert_sink=NoopAlertSink(),
    )
    job = await seed_job(postgres_worker_database)

    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-prepare",
        clock=clock,
        orchestrator_factory=factory,
    )
    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-first-model",
        clock=clock,
        orchestrator_factory=factory,
    )

    assert len(model.requests) == 1
    async with postgres_worker_database.sessions() as session:
        checkpoint = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
        attempt_numbers = list(
            await session.scalars(
                select(models.GenerationAttempt.attempt_number).order_by(
                    models.GenerationAttempt.attempt_number
                )
            )
        )
        assert checkpoint.status is orchestrator.ReadingStatus.PREPARED
        assert checkpoint.attempt_count == 1
        assert checkpoint.completion_copy is None
        assert attempt_numbers == [1]

    await process_one_stage(
        postgres_worker_database,
        worker_id="worker-second-model",
        clock=clock,
        orchestrator_factory=factory,
    )

    assert len(model.requests) == 2
    async with postgres_worker_database.sessions() as session:
        checkpoint = await repository_module.SqlReadingRepository(
            session,
            cipher,
        ).load_checkpoint(str(job.id))
        attempt_numbers = list(
            await session.scalars(
                select(models.GenerationAttempt.attempt_number).order_by(
                    models.GenerationAttempt.attempt_number
                )
            )
        )
        assert checkpoint.status is orchestrator.ReadingStatus.COMPLETING
        assert checkpoint.attempt_count == 2
        assert checkpoint.completion_copy is not None
        assert attempt_numbers == [1, 2]
    assert [command.kind for command in runtime.commands] == ["prepare"]


def test_reading_worker_builder_uses_database_queue_and_orchestrator_processor(
    worker_database: Any,
) -> None:
    readings = importlib.import_module("worker.readings")
    config = importlib.import_module("app.config")

    worker = readings.build_reading_worker(
        settings=config.Settings(environment="test"),
        database=worker_database,
        worker_id="worker-built-for-test",
    )

    assert isinstance(worker.source, readings.ReadingJobWorkSource)
    assert isinstance(worker.processor, readings.ReadingJobProcessor)
    assert worker.processor.worker_id == "worker-built-for-test"
