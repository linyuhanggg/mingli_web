import importlib

import pytest
from orchestrator_fakes import (
    FixedClock,
    MemoryRepository,
    ScriptedModel,
    ScriptedRuntime,
    make_candidate,
    make_job,
    make_prepare,
    make_prepared,
)


def modules() -> tuple[object, object, object]:
    return (
        importlib.import_module("app.readings.orchestrator"),
        importlib.import_module("app.readings.runtime_contracts"),
        importlib.import_module("app.readings.narrative_contracts"),
    )


async def test_new_prepare_sends_no_state_token_and_persists_need_input() -> None:
    orchestrator, contracts, narrative = modules()
    stopped = contracts.Stopped(
        reason="need_input",
        public_copy="还需要资料。",
        state_token="fake-opaque-state",
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
    )
    runtime = ScriptedRuntime([stopped])
    model = ScriptedModel([])
    job = make_job(
        orchestrator,
        contracts,
        narrative,
        prepare=make_prepare(contracts, facts=False),
    )
    repository = MemoryRepository(orchestrator, job)

    outcome = await orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=model,
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    ).run(job.id)

    assert runtime.commands[0].state_token is None
    assert outcome.status is orchestrator.ReadingStatus.WAITING_INPUT
    assert outcome.input_request == stopped.input_request
    assert repository.checkpoint.waiting_input.state_token == "fake-opaque-state"
    assert model.requests == []


async def test_resumed_prepare_reuses_the_persisted_token() -> None:
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
    resumed = make_prepare(
        contracts,
        state_token="fake-opaque-state",
        facts=True,
    )
    job = make_job(orchestrator, contracts, narrative, prepare=resumed)
    repository = MemoryRepository(orchestrator, job)

    await orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=model,
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    ).run(job.id)

    assert runtime.commands[0].state_token == "fake-opaque-state"


@pytest.mark.parametrize("reason", ["unsupported", "conflict", "error"])
async def test_terminal_stopped_does_not_switch_capability_or_retry(reason: str) -> None:
    orchestrator, contracts, narrative = modules()
    runtime = ScriptedRuntime(
        [
            contracts.Stopped(
                reason=reason,
                public_copy="核心终止了本轮。",
                state_token=None,
                input_request=None,
            )
        ]
    )
    model = ScriptedModel([])
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)

    outcome = await orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=model,
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    ).run(job.id)

    assert outcome.status is orchestrator.ReadingStatus.TERMINAL_STOPPED
    assert len(runtime.commands) == 1
    assert runtime.commands[0].intent["capability_id"] == "bazi"
    assert model.requests == []


async def test_unknown_no_token_prepare_is_not_retried() -> None:
    orchestrator, contracts, narrative = modules()
    errors = importlib.import_module("app.readings.errors")
    runtime = ScriptedRuntime([errors.RuntimeTransportError("lost result")])
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)

    outcome = await orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=ScriptedModel([]),
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    ).run(job.id)

    assert outcome.status is orchestrator.ReadingStatus.RUNTIME_UNKNOWN
    assert len(runtime.commands) == 1
    assert repository.events == ["repo:runtime_unknown"]
