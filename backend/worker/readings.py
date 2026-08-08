from __future__ import annotations

import os
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from app.adapters.model import FakeModelGateway
from app.adapters.runtime import FakeMingliRuntimeAdapter
from app.config import Settings, get_settings
from app.database import Database
from app.readings.models import ReadingJobRecord
from app.readings.narrative_guard import NarrativeGuard
from app.readings.orchestrator import (
    NarrativeModelPort,
    ReadingOrchestrator,
    ReadingOutcome,
    RuntimePort,
)
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

    def __post_init__(self) -> None:
        if not self.worker_id.strip():
            raise ValueError("worker id must be non-empty")
        if self.lease_seconds < 1:
            raise ValueError("reading job lease must be positive")

    async def claim_one(self) -> WorkItem | None:
        now = self.clock.now()
        async with self.sessions() as session, session.begin():
            job = await session.scalar(reading_job_claim_statement(now))
            if job is None:
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
        async with self.sessions() as session, session.begin():
            job = await session.scalar(
                current_lease_statement(item, worker_id=self.worker_id, now=now)
            )
            if job is None:
                raise LeaseLostError("Reading Job lease is expired or owned by another Worker")
            outcome = await self.orchestrator_factory(session).run(item.id)
            status = self._job_status(outcome.status)
            available_at = self.clock.now() if status == "queued" else job.available_at
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

    def __call__(self, session: AsyncSession) -> ReadingOrchestrator:
        return ReadingOrchestrator(
            repository=SqlReadingRepository(session, self.cipher),
            runtime=self.runtime,
            model=self.model,
            guard=NarrativeGuard(),
            assembler=PublicCopyAssembler(),
            clock=self.clock,
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
    orchestrator_factory = SqlReadingOrchestratorFactory(
        cipher=EnvelopeCipher.from_settings(settings),
        runtime=resolved_runtime,
        model=resolved_model,
        clock=resolved_clock,
    )
    source = ReadingJobWorkSource(
        sessions=database.sessions,
        worker_id=worker_id,
        clock=resolved_clock,
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
    database = Database(settings.database_url)
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex}"
    try:
        yield build_reading_worker(
            settings=settings,
            database=database,
            worker_id=worker_id,
        )
    finally:
        await database.dispose()
