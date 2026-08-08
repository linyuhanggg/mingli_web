import importlib

from orchestrator_fakes import (
    FixedClock,
    MemoryRepository,
    ScriptedGuard,
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


async def test_prepared_is_persisted_before_the_model_and_copy_is_exact() -> None:
    orchestrator, contracts, narrative = modules()
    events: list[str] = []
    prepared = make_prepared(contracts)
    candidate = make_candidate(narrative)
    runtime = ScriptedRuntime(
        [
            prepared,
            lambda command: contracts.Accepted(
                command.state_token,
                command.public_copy,
            ),
        ],
        events,
    )
    model = ScriptedModel([candidate], events)
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job, events)

    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=model,
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    )

    prepared_outcome = await machine.run(job.id)
    assert prepared_outcome.status is orchestrator.ReadingStatus.PREPARED
    assert model.requests == []
    assert [command.kind for command in runtime.commands] == ["prepare"]

    completing_outcome = await machine.run(job.id)
    assert completing_outcome.status is orchestrator.ReadingStatus.COMPLETING
    assert [command.kind for command in runtime.commands] == ["prepare"]

    outcome = await machine.run(job.id)

    assert events.index("repo:prepared") < events.index("model:generate")
    request_payload = model.requests[0].to_dict()
    serialized = repr(request_payload).lower()
    assert "state_token" not in serialized
    assert "user_id" not in serialized
    assert "order" not in serialized
    assert "entitlement" not in serialized
    complete = runtime.commands[1]
    assert repository.checkpoint.completion_copy == complete.public_copy
    assert outcome.public_copy == complete.public_copy


async def test_guard_failure_retries_the_same_model_once_then_succeeds() -> None:
    orchestrator, contracts, narrative = modules()
    guard_module = importlib.import_module("app.readings.narrative_guard")
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
    model = ScriptedModel([candidate, candidate])
    guard = ScriptedGuard(
        [
            guard_module.GuardResult(False, ("scope_mismatch",)),
            guard_module.GuardResult(True, ()),
        ]
    )
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)

    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=model,
        guard=guard,
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.COMPLETING
    outcome = await machine.run(job.id)

    assert outcome.status is orchestrator.ReadingStatus.ACCEPTED
    assert len(model.requests) == 2
    assert guard.calls == 2
    assert [item[0] for item in repository.attempts] == [1, 2]


async def test_exhausted_guard_failures_never_call_complete() -> None:
    orchestrator, contracts, narrative = modules()
    guard_module = importlib.import_module("app.readings.narrative_guard")
    prepared = make_prepared(contracts)
    candidate = make_candidate(narrative)
    runtime = ScriptedRuntime([prepared])
    model = ScriptedModel([candidate, candidate])
    guard = ScriptedGuard(
        [
            guard_module.GuardResult(False, ("scope_mismatch",)),
            guard_module.GuardResult(False, ("scope_mismatch",)),
        ]
    )
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)

    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=model,
        guard=guard,
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    outcome = await machine.run(job.id)

    assert outcome.status is orchestrator.ReadingStatus.DELAYED
    assert [command.kind for command in runtime.commands] == ["prepare"]
    assert repository.checkpoint.completion_copy is None
