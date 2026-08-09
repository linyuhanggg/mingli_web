import importlib
from dataclasses import replace

import pytest

# isort: split
from orchestrator_fakes import (
    FixedClock,
    MemoryRepository,
    ScriptedModel,
    ScriptedRuntime,
    make_candidate,
    make_job,
    make_prepared,
)


class InjectedCrash(RuntimeError):
    pass


class CrashAfterAtomicSuccessRepository(MemoryRepository):
    crashed = False

    async def record_successful_attempt(
        self,
        job_id: str,
        attempt_number: int,
        candidate: object,
        public_copy: str,
        at: object,
        *,
        model_receipt: object | None = None,
    ) -> None:
        await super().record_successful_attempt(
            job_id,
            attempt_number,
            candidate,
            public_copy,
            at,
            model_receipt=model_receipt,
        )
        if not self.crashed:
            self.crashed = True
            raise InjectedCrash("process died after the atomic repository commit")


def modules() -> tuple[object, object, object]:
    return (
        importlib.import_module("app.readings.orchestrator"),
        importlib.import_module("app.readings.runtime_contracts"),
        importlib.import_module("app.readings.narrative_contracts"),
    )


async def test_complete_transport_unknown_replays_identical_token_and_copy() -> None:
    orchestrator, contracts, narrative = modules()
    errors = importlib.import_module("app.readings.errors")
    prepared = make_prepared(contracts)
    candidate = make_candidate(narrative)
    runtime = ScriptedRuntime(
        [
            prepared,
            errors.RuntimeTransportError("response lost"),
            lambda command: contracts.Accepted(
                command.state_token,
                command.public_copy,
            ),
        ]
    )
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)

    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=ScriptedModel([candidate]),
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.COMPLETING
    retry_outcome = await machine.run(job.id)
    assert retry_outcome.status is orchestrator.ReadingStatus.COMPLETING
    assert retry_outcome.retry_not_before > FixedClock().now()
    assert [command.kind for command in runtime.commands] == ["prepare", "complete"]

    outcome = await machine.run(job.id)

    first, replay = runtime.commands[1:]
    assert first.state_token == replay.state_token
    assert first.public_copy == replay.public_copy
    assert outcome.public_copy == first.public_copy


async def test_successful_attempt_and_completion_intent_survive_one_atomic_crash() -> None:
    orchestrator, contracts, narrative = modules()
    prepared = make_prepared(contracts)
    candidate = make_candidate(narrative)
    runtime = ScriptedRuntime(
        [
            prepared,
            lambda command: contracts.Accepted(
                command.state_token,
                command.public_copy,
            ),
        ]
    )
    model = ScriptedModel([candidate])
    job = make_job(orchestrator, contracts, narrative)
    repository = CrashAfterAtomicSuccessRepository(orchestrator, job)
    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=model,
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    with pytest.raises(InjectedCrash):
        await machine.run(job.id)

    assert repository.checkpoint.attempt_count == 1
    assert repository.checkpoint.completion_copy is not None
    outcome = await machine.run(job.id)
    assert outcome.status is orchestrator.ReadingStatus.ACCEPTED
    assert len(model.requests) == 1
    assert [command.kind for command in runtime.commands] == ["prepare", "complete"]


async def test_accepted_token_must_equal_the_prepared_token() -> None:
    orchestrator, contracts, narrative = modules()
    errors = importlib.import_module("app.readings.errors")
    prepared = make_prepared(contracts)
    runtime = ScriptedRuntime(
        [
            prepared,
            lambda command: contracts.Accepted(
                "different-runtime-token",
                command.public_copy,
            ),
        ]
    )
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)

    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=ScriptedModel([make_candidate(narrative)]),
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.COMPLETING
    with pytest.raises(errors.OrchestratorInvariantError, match="token"):
        await machine.run(job.id)


async def test_persisted_completion_intent_recovers_without_regeneration() -> None:
    orchestrator, contracts, narrative = modules()
    prepared = make_prepared(contracts)
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)
    repository.checkpoint = replace(
        repository.checkpoint,
        status=orchestrator.ReadingStatus.RUNTIME_UNKNOWN,
        prepared=prepared,
        completion_copy="已经持久化的 exact copy",
    )
    runtime = ScriptedRuntime([contracts.Accepted(prepared.state_token, "已经持久化的 exact copy")])
    model = ScriptedModel([])

    outcome = await orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=model,
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    ).run(job.id)

    assert outcome.status is orchestrator.ReadingStatus.ACCEPTED
    assert outcome.public_copy == "已经持久化的 exact copy"
    assert model.requests == []
    assert [command.kind for command in runtime.commands] == ["complete"]


async def test_already_accepted_checkpoint_returns_without_any_external_call() -> None:
    orchestrator, contracts, narrative = modules()
    prepared = make_prepared(contracts)
    accepted = contracts.Accepted(prepared.state_token, "第一次 Accepted")
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)
    repository.checkpoint = replace(
        repository.checkpoint,
        status=orchestrator.ReadingStatus.ACCEPTED,
        prepared=prepared,
        completion_copy=accepted.public_copy,
        accepted=accepted,
    )
    runtime = ScriptedRuntime([])
    model = ScriptedModel([])

    outcome = await orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=model,
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    ).run(job.id)

    assert outcome.public_copy == "第一次 Accepted"
    assert runtime.commands == []
    assert model.requests == []
