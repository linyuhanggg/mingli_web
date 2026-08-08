import importlib
from dataclasses import replace

from orchestrator_fakes import (
    FixedClock,
    MemoryRepository,
    ScriptedModel,
    ScriptedRuntime,
    make_candidate,
    make_job,
    make_prepared,
)


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

    outcome = await orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=ScriptedModel([candidate]),
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    ).run(job.id)

    first, replay = runtime.commands[1:]
    assert first.state_token == replay.state_token
    assert first.public_copy == replay.public_copy
    assert outcome.public_copy == first.public_copy


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
