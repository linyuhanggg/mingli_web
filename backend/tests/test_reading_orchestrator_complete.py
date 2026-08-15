import asyncio
import hashlib
import importlib
from dataclasses import replace
from typing import Any
from uuid import uuid4

import pytest

# isort: split
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


def model_generation(candidate: object) -> tuple[object, object]:
    model = importlib.import_module("app.adapters.model")
    usage = model.ModelTokenUsage(input_tokens=3, output_tokens=7, total_tokens=10)
    price_digest = model.model_price_snapshot_digest(
        version="fixture-price-v1",
        currency="CNY",
        input_microunits_per_million_tokens=2_000_000,
        output_microunits_per_million_tokens=4_000_000,
    )
    audit = model.ModelCallReceipt(
        outcome="succeeded",
        error_code=None,
        model_profile_id="deepseek-v4-flash-p0-v1",
        model_profile_snapshot_digest="a" * 64,
        provider="deepseek",
        provider_model_version="deepseek-v4-flash",
        provider_request_fingerprint=hashlib.sha256(b"provider-request-fixture").hexdigest(),
        request_fingerprint="b" * 64,
        latency_ms=125,
        narrative_policy_version="policy-v1",
        output_contract_id="test-output-v1",
        price_snapshot=model.ModelPriceReceipt(
            version="fixture-price-v1",
            currency="CNY",
            snapshot_digest=price_digest,
            input_microunits_per_million_tokens=2_000_000,
            output_microunits_per_million_tokens=4_000_000,
        ),
        usage=usage,
        cost=model.ModelCost(
            currency="CNY",
            microunits=34,
            price_snapshot_version="fixture-price-v1",
            price_snapshot_digest=price_digest,
            input_microunits_per_million_tokens=2_000_000,
            output_microunits_per_million_tokens=4_000_000,
        ),
    )
    return model.ModelGenerationResult(candidate=candidate, receipt=audit), audit


async def test_model_receipt_is_persisted_with_the_successful_generation_attempt() -> None:
    orchestrator, contracts, narrative = modules()
    prepared = make_prepared(contracts)
    generation, audit = model_generation(make_candidate(narrative))
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)
    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=ScriptedRuntime([prepared]),
        model=ScriptedModel([generation]),
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.COMPLETING

    assert repository.model_receipts == [audit]


async def test_accepted_result_runs_the_reading_document_builder_before_returning() -> None:
    orchestrator, contracts, narrative = modules()
    prepared = make_prepared(contracts)
    candidate = make_candidate(narrative)
    job = replace(
        make_job(orchestrator, contracts, narrative),
        reading_version_id=uuid4(),
        product_id="bazi",
        runtime_release="runtime:test@v1",
    )
    repository = MemoryRepository(orchestrator, job)

    class RecordingDocumentBuilder:
        def __init__(self) -> None:
            self.context: Any | None = None

        def build(self, context: Any) -> object:
            self.context = context
            return {"document": "persisted"}

    builder = RecordingDocumentBuilder()
    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=ScriptedRuntime(
            [
                prepared,
                lambda command: contracts.Accepted(
                    command.state_token,
                    command.public_copy,
                ),
            ]
        ),
        model=ScriptedModel([candidate]),
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
        document_builder=builder,
        require_reading_document=True,
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.COMPLETING
    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.ACCEPTED

    assert builder.context is not None
    assert builder.context.accepted_copy_ref == "accepted-copy:test"
    assert repository.saved_document == {"document": "persisted"}


async def test_accepted_result_is_rejected_when_document_projection_is_unavailable() -> None:
    orchestrator, contracts, narrative = modules()
    prepared = make_prepared(contracts)
    candidate = make_candidate(narrative)
    job = replace(
        make_job(orchestrator, contracts, narrative),
        reading_version_id=uuid4(),
        product_id="bazi",
        runtime_release="runtime:test@v1",
    )
    repository = MemoryRepository(orchestrator, job)

    class MissingDocumentBuilder:
        def build(self, context: Any) -> None:
            del context
            return None

    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=ScriptedRuntime(
            [
                prepared,
                lambda command: contracts.Accepted(
                    command.state_token,
                    command.public_copy,
                ),
            ]
        ),
        model=ScriptedModel([candidate]),
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
        document_builder=MissingDocumentBuilder(),
        require_reading_document=True,
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.COMPLETING
    with pytest.raises(
        orchestrator.OrchestratorInvariantError,
        match="without ReadingDocument",
    ):
        await machine.run(job.id)


async def test_safe_failed_model_receipt_is_persisted_with_the_failed_attempt() -> None:
    orchestrator, contracts, narrative = modules()
    errors = importlib.import_module("app.readings.errors")
    _generation, successful_receipt = model_generation(make_candidate(narrative))
    failed_receipt = replace(
        successful_receipt,
        outcome="failed",
        error_code="model_invalid_response",
    )
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)
    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=ScriptedRuntime([make_prepared(contracts)]),
        model=ScriptedModel(
            [errors.NarrativeGenerationError("model_invalid_response", receipt=failed_receipt)]
        ),
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    assert repository.model_receipts == [failed_receipt]


async def test_cancelled_model_receipt_is_persisted_before_post_commit_signal() -> None:
    orchestrator, contracts, narrative = modules()
    errors = importlib.import_module("app.readings.errors")
    _generation, successful_receipt = model_generation(make_candidate(narrative))
    cancelled_receipt = replace(
        successful_receipt,
        outcome="failed",
        error_code="model_cancelled",
    )
    job = make_job(orchestrator, contracts, narrative)
    repository = MemoryRepository(orchestrator, job)
    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=ScriptedRuntime([make_prepared(contracts)]),
        model=ScriptedModel([errors.NarrativeGenerationCancelled(receipt=cancelled_receipt)]),
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    outcome = await machine.run(job.id)

    assert outcome.status is orchestrator.ReadingStatus.PREPARED
    assert outcome.cancel_after_commit is True
    assert repository.attempts == [(1, ("model_generation_cancelled",))]
    assert repository.model_receipts == [cancelled_receipt]


async def test_receipt_persistence_failure_never_advances_to_complete() -> None:
    orchestrator, contracts, narrative = modules()
    generation, _audit = model_generation(make_candidate(narrative))
    job = make_job(orchestrator, contracts, narrative)

    class RejectingRepository(MemoryRepository):
        async def record_successful_attempt(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            raise RuntimeError("model receipt persistence failed")

    repository = RejectingRepository(orchestrator, job)
    runtime = ScriptedRuntime([make_prepared(contracts)])
    machine = orchestrator.ReadingOrchestrator(
        repository=repository,
        runtime=runtime,
        model=ScriptedModel([generation]),
        guard=orchestrator.NarrativeGuard(),
        assembler=orchestrator.PublicCopyAssembler(),
        clock=FixedClock(),
    )

    assert (await machine.run(job.id)).status is orchestrator.ReadingStatus.PREPARED
    with pytest.raises(RuntimeError, match="receipt persistence"):
        await machine.run(job.id)

    assert [command.kind for command in runtime.commands] == ["prepare"]
    assert repository.checkpoint.completion_copy is None


async def test_two_concurrent_jobs_persist_their_own_receipts_without_cross_talk() -> None:
    orchestrator, contracts, narrative = modules()
    candidate = make_candidate(narrative)
    _base_generation, base_receipt = model_generation(candidate)

    class ConcurrentModel:
        async def generate(self, request: object) -> object:
            question = request.brief["question"]  # type: ignore[attr-defined,index]
            if question == "job-a-question":
                await asyncio.sleep(0.01)
                request_id = "provider-request-job-a"
            else:
                request_id = "provider-request-job-b"
            model_contracts = importlib.import_module("app.readings.model_contracts")
            return model_contracts.ModelGenerationResult(
                candidate=candidate,
                receipt=replace(
                    base_receipt,
                    provider_request_fingerprint=hashlib.sha256(request_id.encode()).hexdigest(),
                    request_fingerprint=hashlib.sha256(question.encode()).hexdigest(),
                ),
            )

    def prepared(question: str, token: str) -> object:
        payload = make_prepared(contracts).brief.to_dict()
        payload["question"] = question
        return contracts.Prepared(
            state_token=token,
            brief=contracts.ReadingBrief.from_dict(payload),
        )

    model = ConcurrentModel()
    machines: list[object] = []
    repositories: list[MemoryRepository] = []
    for suffix in ("a", "b"):
        job = replace(make_job(orchestrator, contracts, narrative), id=f"job:{suffix}")
        repository = MemoryRepository(orchestrator, job)
        repository.checkpoint = replace(
            repository.checkpoint,
            status=orchestrator.ReadingStatus.PREPARED,
            prepared=prepared(f"job-{suffix}-question", f"state-token-{suffix}"),
        )
        repositories.append(repository)
        machines.append(
            orchestrator.ReadingOrchestrator(
                repository=repository,
                runtime=ScriptedRuntime([]),
                model=model,
                guard=orchestrator.NarrativeGuard(),
                assembler=orchestrator.PublicCopyAssembler(),
                clock=FixedClock(),
            )
        )

    outcomes = await asyncio.gather(
        machines[0].run("job:a"),  # type: ignore[attr-defined]
        machines[1].run("job:b"),  # type: ignore[attr-defined]
    )

    assert [outcome.status for outcome in outcomes] == [
        orchestrator.ReadingStatus.COMPLETING,
        orchestrator.ReadingStatus.COMPLETING,
    ]
    assert (
        repositories[0].model_receipts[0].provider_request_fingerprint
        == hashlib.sha256(b"provider-request-job-a").hexdigest()
    )
    assert (
        repositories[1].model_receipts[0].provider_request_fingerprint
        == hashlib.sha256(b"provider-request-job-b").hexdigest()
    )
    assert (
        repositories[0].model_receipts[0].request_fingerprint
        != repositories[1].model_receipts[0].request_fingerprint
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
