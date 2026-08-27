from __future__ import annotations

import importlib
from collections.abc import AsyncIterator, Mapping
from typing import Any, Literal
from uuid import UUID

import pytest
from app.charts.projectors import project_runtime_view_model
from app.readings.alerts import NoopAlertSink
from app.readings.errors import OrchestratorInvariantError
from app.readings.narrative_contracts import OutputContract
from app.readings.presentation import ReadingDocumentBuilder, build_reading_document
from sqlalchemy import select

# isort: split
from orchestrator_fakes import make_candidate, make_output_contract, make_prepared
from test_reading_delivery import _document_payload, _presentation_contract
from test_reading_repository import create_reading_graph
from test_reading_worker import (
    WORKER_TEST_NOW,
    CountingModel,
    FirstWriteRuntime,
    MutableClock,
    bind_paid_fulfillment,
    make_test_cipher,
    process_one_stage,
)

GateKind = Literal["candidate", "accepted-copy-ref", "typed-view-model", "reading-document"]


@pytest.fixture
async def worker_database() -> AsyncIterator[Any]:
    database_module = importlib.import_module("app.database")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
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


def _document_flag(worker_database: Any, adapter: str) -> bool:
    readings = importlib.import_module("worker.readings")
    config = importlib.import_module("app.config")
    worker = readings.build_reading_worker(
        settings=config.Settings(environment="test", runtime_adapter=adapter),
        database=worker_database,
        worker_id=f"document-flag-{adapter}",
    )
    return worker.processor.orchestrator_factory.require_reading_document


def test_reading_worker_builder_requires_document_for_one_shot_and_worker_v2(
    worker_database: Any,
) -> None:
    assert _document_flag(worker_database, "fake") is False
    assert _document_flag(worker_database, "one-shot") is True
    assert _document_flag(worker_database, "worker-v2") is True


class DropDocumentInputsRepository:
    def __init__(
        self,
        inner: Any,
        *,
        drop_candidate: bool = False,
        drop_copy_ref: bool = False,
    ) -> None:
        self._inner = inner
        self._drop_candidate = drop_candidate
        self._drop_copy_ref = drop_copy_ref

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    async def load_successful_candidate(self, job_id: str) -> Any | None:
        if self._drop_candidate:
            return None
        return await self._inner.load_successful_candidate(job_id)

    async def load_accepted_copy_ref(self, job_id: str) -> str | None:
        if self._drop_copy_ref:
            return None
        return await self._inner.load_accepted_copy_ref(job_id)


class FixtureReadingDocumentBuilder:
    def build(self, context: Any) -> Any:
        payload = _document_payload(
            str(context.reading_version_id),
            context.accepted_copy_ref,
        )
        versions = dict(payload["versions"])  # type: ignore[arg-type]
        versions["runtime_release"] = context.runtime_release
        payload["versions"] = versions
        return build_reading_document(_presentation_contract(), payload)


class MissingReadingDocumentBuilder:
    def build(self, context: Any) -> None:
        del context
        return None


class MissingTypedViewModelBuilder:
    def build(self, context: Any) -> None:
        brief = context.prepared.brief
        payload: Mapping[str, object] = (
            brief.to_dict() if hasattr(brief, "to_dict") else dict(brief)
        )
        view_model = project_runtime_view_model(
            payload,
            product_id=context.product_id,
            relationship_type=context.relationship_type,
        )
        assert view_model is None
        return None


class WorkerV2DocumentFactory:
    def __init__(
        self,
        *,
        runtime: Any,
        model: Any,
        clock: MutableClock,
        require_reading_document: bool,
        document_builder: Any,
        drop_candidate: bool = False,
        drop_copy_ref: bool = False,
    ) -> None:
        self.runtime = runtime
        self.model = model
        self.clock = clock
        self.require_reading_document = require_reading_document
        self.document_builder = document_builder
        self.drop_candidate = drop_candidate
        self.drop_copy_ref = drop_copy_ref
        self.cipher = make_test_cipher()

    def __call__(self, session: Any) -> Any:
        orchestrator = importlib.import_module("app.readings.orchestrator")
        repository_module = importlib.import_module("app.readings.repository")
        repository: Any = repository_module.SqlReadingRepository(session, self.cipher)
        if self.drop_candidate or self.drop_copy_ref:
            repository = DropDocumentInputsRepository(
                repository,
                drop_candidate=self.drop_candidate,
                drop_copy_ref=self.drop_copy_ref,
            )
        return orchestrator.ReadingOrchestrator(
            repository=repository,
            runtime=self.runtime,
            model=self.model,
            guard=orchestrator.NarrativeGuard(),
            assembler=orchestrator.PublicCopyAssembler(),
            clock=self.clock,
            alert_sink=NoopAlertSink(),
            document_builder=self.document_builder,
            require_reading_document=self.require_reading_document,
        )


def _factory_for_gate(
    worker_database: Any,
    *,
    gate: GateKind | None,
    runtime: Any,
    model: Any,
    clock: MutableClock,
) -> WorkerV2DocumentFactory:
    require_document = _document_flag(worker_database, "worker-v2")
    document_builder: Any = FixtureReadingDocumentBuilder()
    drop_candidate = gate == "candidate"
    drop_copy_ref = gate == "accepted-copy-ref"
    if gate == "typed-view-model":
        document_builder = MissingTypedViewModelBuilder()
    elif gate == "reading-document":
        document_builder = MissingReadingDocumentBuilder()
    return WorkerV2DocumentFactory(
        runtime=runtime,
        model=model,
        clock=clock,
        require_reading_document=require_document,
        document_builder=document_builder,
        drop_candidate=drop_candidate,
        drop_copy_ref=drop_copy_ref,
    )


async def _seed_paid_job(database: Any, *, key_prefix: str) -> tuple[Any, Any, Any]:
    async with database.sessions() as session, session.begin():
        _repository, _profile, version, job, _contracts = await create_reading_graph(
            session,
            available_at=WORKER_TEST_NOW,
        )
        fulfillment = await bind_paid_fulfillment(
            session,
            version=version,
            job=job,
            key_prefix=key_prefix,
        )
        return version, job, fulfillment


async def _drive_to_completing(
    database: Any,
    *,
    factory: WorkerV2DocumentFactory,
    worker_prefix: str,
) -> None:
    await process_one_stage(
        database,
        worker_id=f"{worker_prefix}-prepare",
        clock=factory.clock,
        orchestrator_factory=factory,
    )
    await process_one_stage(
        database,
        worker_id=f"{worker_prefix}-generate",
        clock=factory.clock,
        orchestrator_factory=factory,
    )


async def _assert_not_accepted(
    database: Any,
    *,
    version_id: UUID,
    job_id: UUID,
    fulfillment_id: UUID | None,
) -> None:
    models = importlib.import_module("app.readings.models")
    commerce_models = importlib.import_module("app.commerce.models")
    async with database.sessions() as session:
        version = await session.get(models.ReadingVersion, version_id)
        job = await session.get(models.ReadingJobRecord, job_id)
        accepted = await session.scalar(
            select(models.AcceptedCopy).where(
                models.AcceptedCopy.reading_version_id == version_id
            )
        )
        document = await session.scalar(
            select(models.ReadingDocumentRecord).where(
                models.ReadingDocumentRecord.reading_version_id == version_id
            )
        )
        assert version is not None
        assert job is not None
        assert version.status == "completing"
        assert job.status != "complete"
        assert accepted is None
        assert document is None
        if fulfillment_id is not None:
            fulfillment = await session.get(commerce_models.FulfillmentRecord, fulfillment_id)
            assert fulfillment is not None
            assert fulfillment.status != "delivered"


async def _assert_accepted_with_document(
    database: Any,
    *,
    version_id: UUID,
    job_id: UUID,
    fulfillment_id: UUID | None,
) -> None:
    models = importlib.import_module("app.readings.models")
    commerce_models = importlib.import_module("app.commerce.models")
    async with database.sessions() as session:
        version = await session.get(models.ReadingVersion, version_id)
        job = await session.get(models.ReadingJobRecord, job_id)
        accepted = await session.scalar(
            select(models.AcceptedCopy).where(
                models.AcceptedCopy.reading_version_id == version_id
            )
        )
        document = await session.scalar(
            select(models.ReadingDocumentRecord).where(
                models.ReadingDocumentRecord.reading_version_id == version_id
            )
        )
        assert version is not None
        assert job is not None
        assert version.status == "accepted"
        assert job.status == "complete"
        assert accepted is not None
        assert document is not None
        assert document.accepted_copy_id == accepted.id
        if fulfillment_id is not None:
            fulfillment = await session.get(commerce_models.FulfillmentRecord, fulfillment_id)
            assert fulfillment is not None
            assert fulfillment.status == "delivered"


async def _create_follow_up_job(
    database: Any,
    *,
    parent_version: Any,
    parent_job: Any,
) -> tuple[Any, Any]:
    runtime_contracts = importlib.import_module("app.readings.runtime_contracts")
    repository_module = importlib.import_module("app.readings.repository")
    async with database.sessions() as session, session.begin():
        repository = repository_module.SqlReadingRepository(session, make_test_cipher())
        prepare = await repository.load_prepare(parent_version.id)
        accepted_copy = await repository.load_accepted_copy(parent_version.id)
        state_token = await repository.load_state_token(parent_version.id)
        assert accepted_copy is not None
        facts: dict[str, object] = {}
        for subject_ref in prepare.intent["subject_refs"]:
            ref = str(subject_ref)
            subject_facts = dict(prepare.facts.get(ref, {}))
            subject_facts["prior_answer"] = accepted_copy
            facts[ref] = subject_facts
        follow_up = runtime_contracts.Prepare(
            query=prepare.query,
            intent=prepare.intent,
            facts=facts,
            state_token=state_token,
            transition=None,
        )
        version = await repository.create_version(
            reading_root_id=parent_version.reading_root_id,
            runtime_release_id=parent_version.runtime_release_id,
            prepare_command=follow_up,
        )
        job = await repository.create_job(
            reading_version_id=version.id,
            narrative_policy_version=parent_job.narrative_policy_version,
            output_contract=OutputContract.from_dict(parent_job.output_contract),
            language=parent_job.language,
            max_output_chars=parent_job.max_output_chars,
            max_attempts=parent_job.max_attempts,
            available_at=WORKER_TEST_NOW,
        )
        return version, job


def test_real_builder_returns_none_without_typed_view_model() -> None:
    narrative = importlib.import_module("app.readings.narrative_contracts")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    context = importlib.import_module("app.readings.presentation").ReadingDocumentContext(
        reading_version_id=UUID("33333333-3333-4333-8333-333333333333"),
        accepted_copy_ref="accepted-copy:fixture",
        product_id="bazi",
        relationship_type=None,
        runtime_release="runtime:test@v1",
        prepared=make_prepared(contracts),
        candidate=make_candidate(narrative),
        output_contract=make_output_contract(narrative),
    )
    assert ReadingDocumentBuilder().build(context) is None


@pytest.mark.parametrize(
    "gate",
    ("candidate", "accepted-copy-ref", "typed-view-model", "reading-document"),
)
async def test_worker_v2_paid_deep_read_rolls_back_when_document_chain_is_incomplete(
    worker_database: Any,
    gate: GateKind,
) -> None:
    narrative = importlib.import_module("app.readings.narrative_contracts")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    version, job, fulfillment = await _seed_paid_job(
        worker_database,
        key_prefix=f"paid-{gate}",
    )
    clock = MutableClock(WORKER_TEST_NOW)
    factory = _factory_for_gate(
        worker_database,
        gate=gate,
        runtime=FirstWriteRuntime(contracts),
        model=CountingModel([make_candidate(narrative)]),
        clock=clock,
    )
    await _drive_to_completing(
        worker_database,
        factory=factory,
        worker_prefix=f"paid-{gate}",
    )
    with pytest.raises(OrchestratorInvariantError, match="ReadingDocument"):
        await process_one_stage(
            worker_database,
            worker_id=f"paid-{gate}-complete",
            clock=clock,
            orchestrator_factory=factory,
        )
    await _assert_not_accepted(
        worker_database,
        version_id=version.id,
        job_id=job.id,
        fulfillment_id=fulfillment.id,
    )


async def test_worker_v2_paid_deep_read_commits_accepted_document_chain(
    worker_database: Any,
) -> None:
    narrative = importlib.import_module("app.readings.narrative_contracts")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    version, job, fulfillment = await _seed_paid_job(
        worker_database,
        key_prefix="paid-complete",
    )
    clock = MutableClock(WORKER_TEST_NOW)
    factory = _factory_for_gate(
        worker_database,
        gate=None,
        runtime=FirstWriteRuntime(contracts),
        model=CountingModel([make_candidate(narrative)]),
        clock=clock,
    )
    await _drive_to_completing(
        worker_database,
        factory=factory,
        worker_prefix="paid-complete",
    )
    await process_one_stage(
        worker_database,
        worker_id="paid-complete-accept",
        clock=clock,
        orchestrator_factory=factory,
    )
    await _assert_accepted_with_document(
        worker_database,
        version_id=version.id,
        job_id=job.id,
        fulfillment_id=fulfillment.id,
    )


@pytest.mark.parametrize(
    "gate",
    ("candidate", "accepted-copy-ref", "typed-view-model", "reading-document"),
)
async def test_worker_v2_follow_up_rolls_back_when_document_chain_is_incomplete(
    worker_database: Any,
    gate: GateKind,
) -> None:
    narrative = importlib.import_module("app.readings.narrative_contracts")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    parent_version, parent_job, fulfillment = await _seed_paid_job(
        worker_database,
        key_prefix=f"follow-parent-{gate}",
    )
    clock = MutableClock(WORKER_TEST_NOW)
    parent_factory = _factory_for_gate(
        worker_database,
        gate=None,
        runtime=FirstWriteRuntime(contracts),
        model=CountingModel([make_candidate(narrative), make_candidate(narrative)]),
        clock=clock,
    )
    await _drive_to_completing(
        worker_database,
        factory=parent_factory,
        worker_prefix=f"follow-parent-{gate}",
    )
    await process_one_stage(
        worker_database,
        worker_id=f"follow-parent-{gate}-accept",
        clock=clock,
        orchestrator_factory=parent_factory,
    )
    await _assert_accepted_with_document(
        worker_database,
        version_id=parent_version.id,
        job_id=parent_job.id,
        fulfillment_id=fulfillment.id,
    )

    follow_version, follow_job = await _create_follow_up_job(
        worker_database,
        parent_version=parent_version,
        parent_job=parent_job,
    )
    follow_factory = _factory_for_gate(
        worker_database,
        gate=gate,
        runtime=FirstWriteRuntime(contracts),
        model=CountingModel([make_candidate(narrative)]),
        clock=clock,
    )
    await _drive_to_completing(
        worker_database,
        factory=follow_factory,
        worker_prefix=f"follow-{gate}",
    )
    with pytest.raises(OrchestratorInvariantError, match="ReadingDocument"):
        await process_one_stage(
            worker_database,
            worker_id=f"follow-{gate}-complete",
            clock=clock,
            orchestrator_factory=follow_factory,
        )
    await _assert_not_accepted(
        worker_database,
        version_id=follow_version.id,
        job_id=follow_job.id,
        fulfillment_id=None,
    )


async def test_worker_v2_follow_up_commits_accepted_document_chain(
    worker_database: Any,
) -> None:
    narrative = importlib.import_module("app.readings.narrative_contracts")
    contracts = importlib.import_module("app.readings.runtime_contracts")
    parent_version, parent_job, fulfillment = await _seed_paid_job(
        worker_database,
        key_prefix="follow-parent-complete",
    )
    clock = MutableClock(WORKER_TEST_NOW)
    parent_factory = _factory_for_gate(
        worker_database,
        gate=None,
        runtime=FirstWriteRuntime(contracts),
        model=CountingModel([make_candidate(narrative), make_candidate(narrative)]),
        clock=clock,
    )
    await _drive_to_completing(
        worker_database,
        factory=parent_factory,
        worker_prefix="follow-parent-complete",
    )
    await process_one_stage(
        worker_database,
        worker_id="follow-parent-complete-accept",
        clock=clock,
        orchestrator_factory=parent_factory,
    )
    follow_version, follow_job = await _create_follow_up_job(
        worker_database,
        parent_version=parent_version,
        parent_job=parent_job,
    )
    follow_factory = _factory_for_gate(
        worker_database,
        gate=None,
        runtime=FirstWriteRuntime(contracts),
        model=CountingModel([make_candidate(narrative)]),
        clock=clock,
    )
    await _drive_to_completing(
        worker_database,
        factory=follow_factory,
        worker_prefix="follow-complete",
    )
    await process_one_stage(
        worker_database,
        worker_id="follow-complete-accept",
        clock=clock,
        orchestrator_factory=follow_factory,
    )
    await _assert_accepted_with_document(
        worker_database,
        version_id=follow_version.id,
        job_id=follow_job.id,
        fulfillment_id=None,
    )
    await _assert_accepted_with_document(
        worker_database,
        version_id=parent_version.id,
        job_id=parent_job.id,
        fulfillment_id=fulfillment.id,
    )
