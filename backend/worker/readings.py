from __future__ import annotations

import asyncio
import os
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from app.adapters.model import (
    DeepSeekStandaloneModelAdapter,
    FakeModelGateway,
    build_deepseek_model_adapter,
)
from app.adapters.runtime import FakeMingliRuntimeAdapter, build_runtime_startup_gate
from app.commerce.service import CommerceService
from app.config import Settings, get_settings
from app.database import Database
from app.observability import configure_logging
from app.readings.alerts import AlertSink, build_alert_sink
from app.readings.models import ReadingJobRecord, ReadingRoot, ReadingVersion
from app.readings.narrative_guard import NarrativeGuard
from app.readings.orchestrator import (
    NarrativeModelPort,
    ReadingOrchestrator,
    ReadingOutcome,
    RuntimePort,
)
from app.readings.presentation import ReadingDocumentBuilder
from app.readings.public_copy import PublicCopyAssembler
from app.readings.repository import SqlReadingRepository
from app.readings.status import ReadingStatus
from app.security.envelope import EnvelopeCipher
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql import Select

from worker.main import Worker, WorkItem, build_worker


class LeaseLostError(RuntimeError):
    """A stale Worker tried to process or finish a superseded claim."""


class Clock(Protocol):
    def now(self) -> datetime: ...


class OrchestratorRunner(Protocol):
    async def run(self, job_id: str) -> ReadingOutcome: ...


class OrchestratorFactory(Protocol):
    def __call__(self, session: AsyncSession) -> OrchestratorRunner: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def reading_job_claim_statement(now: datetime) -> Select[tuple[ReadingJobRecord]]:
    return (
        select(ReadingJobRecord)
        .where(
            or_(
                and_(
                    ReadingJobRecord.status == "queued",
                    ReadingJobRecord.available_at <= now,
                ),
                and_(
                    ReadingJobRecord.status == "claimed",
                    ReadingJobRecord.lease_expires_at.is_not(None),
                    ReadingJobRecord.lease_expires_at < now,
                ),
            )
        )
        .order_by(ReadingJobRecord.available_at, ReadingJobRecord.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )


def current_lease_statement(
    item: WorkItem,
    *,
    worker_id: str,
    now: datetime,
) -> Select[tuple[ReadingJobRecord]]:
    if item.claim_token is None or item.lease_generation is None:
        raise LeaseLostError("Reading Job work item has no fencing token")
    return (
        select(ReadingJobRecord)
        .where(
            ReadingJobRecord.id == UUID(item.id),
            ReadingJobRecord.status == "claimed",
            ReadingJobRecord.lease_owner == worker_id,
            ReadingJobRecord.lease_token == item.claim_token,
            ReadingJobRecord.lease_generation == item.lease_generation,
            ReadingJobRecord.lease_expires_at.is_not(None),
            ReadingJobRecord.lease_expires_at > now,
        )
        .with_for_update()
    )


@dataclass(slots=True)
class ReadingJobWorkSource:
    sessions: async_sessionmaker[AsyncSession]
    worker_id: str
    clock: Clock
    lease_seconds: int = 30
    cipher: EnvelopeCipher | None = None
    waiting_input_timeout: timedelta = timedelta(days=7)

    def __post_init__(self) -> None:
        if not self.worker_id.strip():
            raise ValueError("worker id must be non-empty")
        if self.lease_seconds < 1:
            raise ValueError("reading job lease must be positive")
        if self.waiting_input_timeout <= timedelta(0):
            raise ValueError("waiting input timeout must be positive")

    async def expire_stale_waiting_input(self, now: datetime) -> bool:
        if self.cipher is None:
            return False
        async with self.sessions() as session, session.begin():
            repository = SqlReadingRepository(session, self.cipher)
            job = await repository.expire_waiting_input(
                now=now,
                max_age=self.waiting_input_timeout,
            )
            if job is None:
                return False
            await CommerceService(session).release_fulfillment_for_job(
                reading_job_ref=str(job.id),
                reason="reading_waiting_input_timeout",
            )
            root = await session.scalar(
                select(ReadingRoot)
                .join(ReadingVersion, ReadingVersion.reading_root_id == ReadingRoot.id)
                .where(ReadingVersion.id == job.reading_version_id)
            )
            if root is not None and root.owner_user_id is not None:
                await CommerceService(session).enqueue_notification(
                    owner_user_id=root.owner_user_id,
                    kind="reading.failed",
                    dedupe_key=f"reading.failed:{job.id}:input-timeout",
                    payload={"reason": "input_timeout"},
                    channel="in_app",
                )
            return True

    async def claim_one(self) -> WorkItem | None:
        now = self.clock.now()
        await self.expire_stale_waiting_input(now)
        async with self.sessions() as session, session.begin():
            job = await session.scalar(reading_job_claim_statement(now))
            if job is None:
                return None
            expired_claim = job.status == "claimed"
            if expired_claim:
                version = await session.get(
                    ReadingVersion,
                    job.reading_version_id,
                    with_for_update=True,
                )
                if version is None:
                    raise RuntimeError("Reading Job points to a missing Reading Version")
                if (
                    version.status == ReadingStatus.INPUT_READY.value
                    and not version.prepare_has_state_token
                ):
                    # An expired no-token Prepare cannot distinguish a pre-call
                    # crash from a Runtime-side Root created before COMMIT.
                    # Tokened Prepare is replay-safe under the V5.1 protocol.
                    version.status = ReadingStatus.RUNTIME_UNKNOWN.value
                    job.status = "runtime_unknown"
                    job.lease_owner = None
                    job.lease_token = None
                    job.lease_expires_at = None
                    await session.flush()
                    return None
            claim_token = uuid4().hex
            job.status = "claimed"
            job.lease_generation += 1
            job.lease_owner = self.worker_id
            job.lease_token = claim_token
            job.lease_expires_at = now + timedelta(seconds=self.lease_seconds)
            await session.flush()
            return WorkItem(
                id=str(job.id),
                claim_token=claim_token,
                lease_generation=job.lease_generation,
            )


@dataclass(slots=True)
class ReadingJobProcessor:
    sessions: async_sessionmaker[AsyncSession]
    orchestrator_factory: OrchestratorFactory
    worker_id: str
    clock: Clock

    def __post_init__(self) -> None:
        if not self.worker_id.strip():
            raise ValueError("worker id must be non-empty")

    async def process(self, item: WorkItem) -> None:
        now = self.clock.now()
        cancel_after_commit = False
        async with self.sessions() as session, session.begin():
            job = await session.scalar(
                current_lease_statement(item, worker_id=self.worker_id, now=now)
            )
            if job is None:
                raise LeaseLostError("Reading Job lease is expired or owned by another Worker")
            outcome = await self.orchestrator_factory(session).run(item.id)
            commerce = CommerceService(session)
            if outcome.status is ReadingStatus.ACCEPTED:
                await commerce.deliver_fulfillment_for_job(
                    reading_job_ref=str(job.id),
                )
            elif outcome.status is ReadingStatus.TERMINAL_STOPPED:
                await commerce.release_fulfillment_for_job(
                    reading_job_ref=str(job.id),
                    reason="reading_terminal_stopped",
                )
            status = self._job_status(outcome.status)
            finished_at = self.clock.now()
            if outcome.retry_not_before is not None:
                if (
                    outcome.status not in {ReadingStatus.INPUT_READY, ReadingStatus.COMPLETING}
                    or status != "queued"
                    or outcome.retry_not_before <= finished_at
                ):
                    raise ValueError("retry_not_before must schedule a retryable Job in the future")
                available_at = outcome.retry_not_before
            else:
                available_at = finished_at if status == "queued" else job.available_at
            finished_id = await session.scalar(
                update(ReadingJobRecord)
                .where(
                    ReadingJobRecord.id == job.id,
                    ReadingJobRecord.lease_owner == self.worker_id,
                    ReadingJobRecord.lease_token == item.claim_token,
                    ReadingJobRecord.lease_generation == item.lease_generation,
                )
                .values(
                    status=status,
                    available_at=available_at,
                    lease_owner=None,
                    lease_token=None,
                    lease_expires_at=None,
                )
                .returning(ReadingJobRecord.id)
            )
            if finished_id is None:
                raise LeaseLostError("Reading Job fencing token changed before COMMIT")
            cancel_after_commit = outcome.cancel_after_commit
        if cancel_after_commit:
            raise asyncio.CancelledError from None

    @staticmethod
    def _job_status(status: ReadingStatus) -> str:
        return {
            ReadingStatus.INPUT_READY: "queued",
            ReadingStatus.WAITING_INPUT: "waiting_input",
            ReadingStatus.TERMINAL_STOPPED: "stopped",
            ReadingStatus.PREPARED: "queued",
            ReadingStatus.COMPLETING: "queued",
            ReadingStatus.ACCEPTED: "complete",
            ReadingStatus.DELAYED: "delayed",
            ReadingStatus.RUNTIME_UNKNOWN: "runtime_unknown",
        }[status]


@dataclass(slots=True)
class SqlReadingOrchestratorFactory:
    cipher: EnvelopeCipher
    runtime: RuntimePort
    model: NarrativeModelPort
    clock: Clock
    alert_sink: AlertSink
    require_reading_document: bool = False

    def __call__(self, session: AsyncSession) -> ReadingOrchestrator:
        return ReadingOrchestrator(
            repository=SqlReadingRepository(session, self.cipher),
            runtime=self.runtime,
            model=self.model,
            guard=NarrativeGuard(),
            assembler=PublicCopyAssembler(),
            document_builder=ReadingDocumentBuilder(),
            require_reading_document=self.require_reading_document,
            clock=self.clock,
            alert_sink=self.alert_sink,
        )


def build_reading_worker(
    *,
    settings: Settings,
    database: Database,
    worker_id: str,
    clock: Clock | None = None,
    runtime: RuntimePort | None = None,
    model: NarrativeModelPort | None = None,
) -> Worker:
    resolved_clock = clock or SystemClock()
    if settings.environment in {"staging", "production"} and (runtime is None or model is None):
        raise RuntimeError("staging and production require real Runtime and Model adapters")
    resolved_runtime = runtime or FakeMingliRuntimeAdapter()
    resolved_model = model or FakeModelGateway()
    resolved_cipher = EnvelopeCipher.from_settings(settings)
    orchestrator_factory = SqlReadingOrchestratorFactory(
        cipher=resolved_cipher,
        runtime=resolved_runtime,
        model=resolved_model,
        clock=resolved_clock,
        alert_sink=build_alert_sink(enabled=settings.alert_sink_enabled),
        require_reading_document=settings.runtime_adapter == "one-shot",
    )
    source = ReadingJobWorkSource(
        sessions=database.sessions,
        worker_id=worker_id,
        clock=resolved_clock,
        cipher=resolved_cipher,
    )
    processor = ReadingJobProcessor(
        sessions=database.sessions,
        orchestrator_factory=orchestrator_factory,
        worker_id=worker_id,
        clock=resolved_clock,
    )
    return build_worker(source=source, processor=processor)


@asynccontextmanager
async def configured_reading_worker() -> AsyncIterator[Worker]:
    settings = get_settings()
    configure_logging(settings.log_level)
    database = Database(settings.database_url)
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex}"
    model_adapter: DeepSeekStandaloneModelAdapter | None = None
    try:
        runtime: RuntimePort | None = None
        if settings.runtime_adapter == "one-shot":
            runtime_gate = build_runtime_startup_gate(settings)
            await runtime_gate.startup()
            runtime = runtime_gate.runtime
        model: NarrativeModelPort | None = None
        if settings.model_adapter == "deepseek":
            model_adapter = build_deepseek_model_adapter(settings)
            model = model_adapter
        yield build_reading_worker(
            settings=settings,
            database=database,
            worker_id=worker_id,
            runtime=runtime,
            model=model,
        )
    finally:
        try:
            if model_adapter is not None:
                await model_adapter.aclose()
        finally:
            await database.dispose()
