from __future__ import annotations

import asyncio
import importlib
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from orchestrator_fakes import make_candidate
from sqlalchemy import event, func, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from test_narrative_guard import build_brief
from test_reading_repository import create_reading_graph


@pytest.fixture
async def worker_database() -> AsyncIterator[Any]:
    database_module = importlib.import_module("app.database")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
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
    def __init__(self, contracts: Any) -> None:
        self.contracts = contracts
        self.commands: list[Any] = []
        self.accepted_by_token: dict[str, str] = {}
        self.prepare_count = 0

    async def execute(self, command: Any) -> Any:
        self.commands.append(command)
        if isinstance(command, self.contracts.Prepare):
            self.prepare_count += 1
            return self.contracts.Prepared(
                state_token=f"postgres-state-token-{self.prepare_count}",
                brief=build_brief(),
            )
        if isinstance(command, self.contracts.Complete):
            accepted_copy = self.accepted_by_token.setdefault(
                command.state_token,
                command.public_copy,
            )
            return self.contracts.Accepted(
                state_token=command.state_token,
                public_copy=accepted_copy,
            )
        raise AssertionError(f"unexpected Runtime command: {command.kind}")


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


async def seed_job(database: Any) -> Any:
    async with database.sessions() as session, session.begin():
        _repository, _profile, _version, job, _contracts = await create_reading_graph(session)
        return job


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
    job = await seed_job(worker_database)
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
    await seed_job(worker_database)
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
