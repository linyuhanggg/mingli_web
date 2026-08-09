from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, cast

from app.readings.errors import (
    NarrativeGenerationError,
    OrchestratorInvariantError,
    RuntimeTransportError,
)
from app.readings.model_contracts import ModelCallReceipt, ModelGenerationResult
from app.readings.narrative_contracts import (
    NarrativeCandidate,
    NarrativeRequest,
    OutputContract,
)
from app.readings.narrative_guard import GuardResult
from app.readings.narrative_guard import NarrativeGuard as NarrativeGuard
from app.readings.public_copy import (
    PublicCopyAssembler as PublicCopyAssembler,
)
from app.readings.public_copy import (
    PublicCopyAssemblyError,
)
from app.readings.runtime_contracts import (
    Accepted,
    Complete,
    MingliCommand,
    MingliResult,
    Prepare,
    Prepared,
    ReadingBrief,
    Stopped,
)
from app.readings.status import ReadingStatus


@dataclass(frozen=True, slots=True)
class ReadingJob:
    id: str
    prepare_command: Prepare
    narrative_policy_version: str
    output_contract: OutputContract
    language: str
    max_output_chars: int
    max_attempts: int = 2

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("reading job id must be non-empty")
        if not 1 <= self.max_attempts <= 2:
            raise ValueError("P0 model attempts must be between one and two")


@dataclass(frozen=True, slots=True)
class ReadingCheckpoint:
    status: ReadingStatus = ReadingStatus.INPUT_READY
    waiting_input: Stopped | None = None
    terminal_stopped: Stopped | None = None
    prepared: Prepared | None = None
    attempt_count: int = 0
    completion_copy: str | None = None
    accepted: Accepted | None = None


@dataclass(frozen=True, slots=True)
class ReadingOutcome:
    status: ReadingStatus
    public_copy: str | None = None
    input_request: Mapping[str, object] | None = None
    stopped_reason: str | None = None
    retry_not_before: datetime | None = None


class Clock(Protocol):
    def now(self) -> datetime: ...


class RuntimePort(Protocol):
    async def execute(self, command: MingliCommand) -> MingliResult: ...


class NarrativeModelPort(Protocol):
    async def generate(self, request: NarrativeRequest) -> ModelGenerationResult: ...


class NarrativeGuardPort(Protocol):
    def validate(
        self,
        candidate: NarrativeCandidate,
        brief: ReadingBrief,
        output_contract: OutputContract,
    ) -> GuardResult: ...


class PublicCopyAssemblerPort(Protocol):
    def assemble(
        self,
        candidate: NarrativeCandidate,
        brief: ReadingBrief,
        output_contract: OutputContract,
    ) -> str: ...


class ReadingRepository(Protocol):
    async def load_job(self, job_id: str) -> ReadingJob: ...

    async def load_checkpoint(self, job_id: str) -> ReadingCheckpoint: ...

    async def record_waiting_input(
        self,
        job_id: str,
        stopped: Stopped,
        at: datetime,
    ) -> None: ...

    async def record_terminal_stopped(
        self,
        job_id: str,
        stopped: Stopped,
        at: datetime,
    ) -> None: ...

    async def record_prepared(
        self,
        job_id: str,
        prepared: Prepared,
        at: datetime,
    ) -> None: ...

    async def record_generation_attempt(
        self,
        job_id: str,
        attempt_number: int,
        candidate: NarrativeCandidate | None,
        guard_errors: tuple[str, ...],
        at: datetime,
        *,
        model_receipt: ModelCallReceipt | None = None,
    ) -> None: ...

    async def record_completion_intent(
        self,
        job_id: str,
        public_copy: str,
        at: datetime,
    ) -> None: ...

    async def record_successful_attempt(
        self,
        job_id: str,
        attempt_number: int,
        candidate: NarrativeCandidate,
        public_copy: str,
        at: datetime,
        *,
        model_receipt: ModelCallReceipt | None = None,
    ) -> None: ...

    async def record_accepted(
        self,
        job_id: str,
        accepted: Accepted,
        at: datetime,
    ) -> Accepted: ...

    async def mark_delayed(self, job_id: str, at: datetime) -> None: ...

    async def mark_runtime_unknown(self, job_id: str, at: datetime) -> None: ...


@dataclass(slots=True)
class ReadingOrchestrator:
    repository: ReadingRepository
    runtime: RuntimePort
    model: NarrativeModelPort
    guard: NarrativeGuardPort
    assembler: PublicCopyAssemblerPort
    clock: Clock
    prepare_transport_backoff: timedelta = timedelta(seconds=5)
    complete_transport_backoff: timedelta = timedelta(seconds=5)

    def __post_init__(self) -> None:
        if self.prepare_transport_backoff <= timedelta(0):
            raise ValueError("Prepare transport backoff must be positive")
        if self.complete_transport_backoff <= timedelta(0):
            raise ValueError("Complete transport backoff must be positive")

    async def run(self, job_id: str) -> ReadingOutcome:
        job = await self.repository.load_job(job_id)
        checkpoint = await self.repository.load_checkpoint(job_id)
        if checkpoint.accepted is not None:
            return ReadingOutcome(
                status=ReadingStatus.ACCEPTED,
                public_copy=checkpoint.accepted.public_copy,
            )
        if checkpoint.terminal_stopped is not None:
            return self._stopped_outcome(checkpoint.terminal_stopped)
        if checkpoint.completion_copy is not None:
            if checkpoint.prepared is None:
                raise OrchestratorInvariantError(
                    "completion intent exists without a Prepared checkpoint"
                )
            return await self._complete(
                job.id,
                checkpoint.prepared,
                checkpoint.completion_copy,
            )
        if checkpoint.status is ReadingStatus.DELAYED:
            return ReadingOutcome(status=ReadingStatus.DELAYED)
        if checkpoint.status is ReadingStatus.RUNTIME_UNKNOWN:
            return ReadingOutcome(status=ReadingStatus.RUNTIME_UNKNOWN)
        if (
            checkpoint.status is ReadingStatus.WAITING_INPUT
            and job.prepare_command.state_token is None
            and checkpoint.waiting_input is not None
        ):
            return self._stopped_outcome(checkpoint.waiting_input)
        if checkpoint.prepared is not None:
            return await self._generate(
                job,
                checkpoint.prepared,
                checkpoint.attempt_count,
            )
        return await self._prepare(job)

    async def _prepare(
        self,
        job: ReadingJob,
    ) -> ReadingOutcome:
        # A successful no-token Prepare followed by host death before this
        # checkpoint commits can leave an orphan Runtime Root. It is not safe
        # to invent request idempotency or replay that unknown Prepare here.
        try:
            result = await self.runtime.execute(job.prepare_command)
        except RuntimeTransportError:
            if job.prepare_command.state_token is not None:
                return ReadingOutcome(
                    status=ReadingStatus.INPUT_READY,
                    retry_not_before=(self.clock.now() + self.prepare_transport_backoff),
                )
            await self.repository.mark_runtime_unknown(job.id, self.clock.now())
            return ReadingOutcome(status=ReadingStatus.RUNTIME_UNKNOWN)
        if isinstance(result, Prepared):
            await self.repository.record_prepared(job.id, result, self.clock.now())
            return ReadingOutcome(status=ReadingStatus.PREPARED)
        if isinstance(result, Stopped):
            if result.reason == "need_input":
                await self.repository.record_waiting_input(
                    job.id,
                    result,
                    self.clock.now(),
                )
            else:
                await self.repository.record_terminal_stopped(
                    job.id,
                    result,
                    self.clock.now(),
                )
            return self._stopped_outcome(result)
        raise OrchestratorInvariantError(f"prepare returned unexpected result: {result.kind}")

    async def _generate(
        self,
        job: ReadingJob,
        prepared: Prepared,
        completed_attempts: int,
    ) -> ReadingOutcome:
        brief = cast(ReadingBrief, prepared.brief)
        request = NarrativeRequest(
            brief=brief,
            narrative_policy_version=job.narrative_policy_version,
            output_contract=job.output_contract,
            language=job.language,
            max_output_chars=job.max_output_chars,
        )
        if completed_attempts >= job.max_attempts:
            await self.repository.mark_delayed(job.id, self.clock.now())
            return ReadingOutcome(status=ReadingStatus.DELAYED)

        attempt_number = completed_attempts + 1
        candidate: NarrativeCandidate | None = None
        model_receipt: ModelCallReceipt | None = None
        errors: tuple[str, ...]
        public_copy: str | None = None
        try:
            generation = await self.model.generate(request)
            candidate = generation.candidate
            model_receipt = generation.receipt
            guard_result = self.guard.validate(
                candidate,
                brief,
                job.output_contract,
            )
            errors = guard_result.errors
            if guard_result.passed:
                try:
                    public_copy = self.assembler.assemble(
                        candidate,
                        brief,
                        job.output_contract,
                    )
                except PublicCopyAssemblyError:
                    errors = ("public_copy_invalid",)
        except NarrativeGenerationError as error:
            if isinstance(error.receipt, ModelCallReceipt):
                model_receipt = error.receipt
            errors = ("model_generation_failed",)

        if public_copy is None:
            await self.repository.record_generation_attempt(
                job.id,
                attempt_number,
                candidate,
                errors,
                self.clock.now(),
                model_receipt=model_receipt,
            )
            if attempt_number >= job.max_attempts:
                await self.repository.mark_delayed(job.id, self.clock.now())
                return ReadingOutcome(status=ReadingStatus.DELAYED)
            return ReadingOutcome(status=ReadingStatus.PREPARED)
        if candidate is None:
            raise OrchestratorInvariantError("public copy exists without a Narrative Candidate")
        await self.repository.record_successful_attempt(
            job.id,
            attempt_number,
            candidate,
            public_copy,
            self.clock.now(),
            model_receipt=model_receipt,
        )
        return ReadingOutcome(status=ReadingStatus.COMPLETING)

    async def _complete(
        self,
        job_id: str,
        prepared: Prepared,
        public_copy: str,
    ) -> ReadingOutcome:
        command = Complete(
            state_token=prepared.state_token,
            public_copy=public_copy,
        )
        try:
            result = await self.runtime.execute(command)
        except RuntimeTransportError:
            # The completion intent is already durable. Requeue this stage so
            # the next transaction replays the exact token and copy once.
            return ReadingOutcome(
                status=ReadingStatus.COMPLETING,
                retry_not_before=(self.clock.now() + self.complete_transport_backoff),
            )

        if isinstance(result, Accepted):
            if result.state_token != prepared.state_token:
                raise OrchestratorInvariantError("Accepted token differs from the Prepared token")
            if result.public_copy != public_copy:
                raise OrchestratorInvariantError(
                    "Accepted bytes differ from the persisted completion intent"
                )
            await self.repository.record_accepted(job_id, result, self.clock.now())
            return ReadingOutcome(
                status=ReadingStatus.ACCEPTED,
                public_copy=result.public_copy,
            )
        if isinstance(result, Stopped):
            await self.repository.record_terminal_stopped(
                job_id,
                result,
                self.clock.now(),
            )
            return self._stopped_outcome(result)
        raise OrchestratorInvariantError(f"complete returned unexpected result: {result.kind}")

    @staticmethod
    def _stopped_outcome(stopped: Stopped) -> ReadingOutcome:
        status = (
            ReadingStatus.WAITING_INPUT
            if stopped.reason == "need_input"
            else ReadingStatus.TERMINAL_STOPPED
        )
        return ReadingOutcome(
            status=status,
            public_copy=stopped.public_copy,
            input_request=stopped.input_request,
            stopped_reason=stopped.reason,
        )
