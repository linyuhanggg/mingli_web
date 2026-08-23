"""Deterministic relationship-deep draft: copy signal display_text only.

This is not a Worker and not a rewrite step. It fills 3–8 Candidate blocks
with the exact ``relationship_signals.display_text`` strings already published
on the brief. Wrapper fact ``display_text`` is never used.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast
from uuid import UUID

from app.persistence import ImmutableRecordError
from app.readings.narrative_contracts import (
    NarrativeCandidate,
    OutputContract,
    merge_claim_scopes,
)
from app.readings.output_contracts import (
    output_contract_for_product,
    resolve_output_contract,
)
from app.readings.presentation import (
    ReadingDocumentBuilder,
    ReadingDocumentContext,
    ReadingDocumentV1,
)
from app.readings.public_copy import PublicCopyAssembler, PublicCopyAssemblyError
from app.readings.runtime_contracts import (
    Accepted,
    Complete,
    ContractValidationError,
    Prepared,
    ReadingBrief,
)
from app.readings.status import ReadingStatus

RELATIONSHIP_DEEP_CONTRACT_IDS = frozenset(
    {
        "bazi-relationship-deep-output-v1",
        "ziwei-relationship-deep-output-v1",
        "qizheng-relationship-deep-output-v1",
    }
)
_SIGNALS_MISSING = "relationship_signals_missing"
_NOT_APPLICABLE = "relationship_deep_extract_not_applicable"
_INTENT_INVALID = "relationship_deep_complete_intent_invalid"
_ACCEPT_FAILED = "relationship_deep_fake_runtime_not_accepted"
_DOCUMENT_UNAVAILABLE = "relationship_deep_reading_document_unavailable"
_ACCEPTED_COPY_MISSING = "relationship_deep_accepted_copy_missing"
_DOCUMENT_IMMUTABLE = "relationship_deep_reading_document_immutable"
_CANDIDATE_MISSING = "relationship_deep_candidate_missing"
_PREPARED_BRIEF_MISSING = "relationship_deep_prepared_brief_missing"
_READING_VERSION_MISSING = "relationship_deep_reading_version_missing"
_OUTPUT_CONTRACT_MISSING = "relationship_deep_output_contract_missing"
_RELATIONSHIP_TYPE_MISSING = "relationship_deep_relationship_type_missing"
_RUNTIME_RELEASE_MISSING = "relationship_deep_runtime_release_missing"
_CONTRACT_PRODUCT_IDS = {
    "bazi-relationship-deep-output-v1": "bazi-relationship",
    "ziwei-relationship-deep-output-v1": "ziwei-relationship",
    "qizheng-relationship-deep-output-v1": "qizheng-relationship",
}


class _CompleteRuntime(Protocol):
    async def execute(self, command: Complete) -> object: ...


class _ReadingDocumentStore(Protocol):
    async def load_successful_candidate(self, job_id: str) -> NarrativeCandidate | None: ...

    async def load_prepared_brief(self, job_id: str) -> ReadingBrief | None: ...

    async def load_accepted(self, job_id: str) -> Accepted | None: ...

    async def load_reading_version_id(self, job_id: str) -> UUID | None: ...

    async def load_output_contract(self, job_id: str) -> OutputContract | None: ...

    async def load_relationship_type(self, job_id: str) -> str | None: ...

    async def load_runtime_release(self, job_id: str) -> str | None: ...

    async def load_accepted_copy_ref(self, job_id: str) -> str | None: ...

    async def save_reading_document_for_job(
        self,
        job_id: str,
        document: ReadingDocumentV1,
    ) -> None: ...

    async def load_reading_document_for_job(
        self, job_id: str
    ) -> ReadingDocumentV1 | None: ...


class _HttpResultStore(Protocol):
    async def load_accepted_copy(self, version_id: UUID) -> str | None: ...

    async def load_reading_document(
        self, version_id: UUID
    ) -> ReadingDocumentV1 | None: ...

    async def get_accepted_copy(self, version_id: UUID) -> Any: ...


@dataclass(frozen=True, slots=True)
class RelationshipDeepExtractResult:
    candidate: NarrativeCandidate | None
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RelationshipDeepCompleteIntentResult:
    command: Complete | None
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RelationshipDeepAcceptedResult:
    accepted: Accepted | None
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RelationshipDeepDocumentResult:
    document: ReadingDocumentV1 | None
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RelationshipDeepPersistResult:
    document: ReadingDocumentV1 | None
    created: bool
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RelationshipDeepPrepareResult:
    status: ReadingStatus | None
    public_copy: str | None
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RelationshipDeepHttpResult:
    accepted_copy: str | None
    document: ReadingDocumentV1 | None
    errors: tuple[str, ...]


def extract_relationship_deep_candidate(
    brief: ReadingBrief | Mapping[str, object],
    output_contract: str | OutputContract,
) -> RelationshipDeepExtractResult:
    contract = resolve_output_contract(output_contract)
    if contract.contract_id not in RELATIONSHIP_DEEP_CONTRACT_IDS:
        return RelationshipDeepExtractResult(candidate=None, errors=(_NOT_APPLICABLE,))

    reading_brief = brief if isinstance(brief, ReadingBrief) else ReadingBrief.from_dict(dict(brief))
    payload = reading_brief.to_dict()
    facts = {
        str(item["ref"]): item
        for item in payload.get("facts") or []
        if isinstance(item, Mapping) and isinstance(item.get("ref"), str)
    }
    sources = _signal_display_texts(facts)
    if len(sources) < contract.min_blocks:
        return RelationshipDeepExtractResult(candidate=None, errors=(_SIGNALS_MISSING,))

    scope = _relationship_scope(payload)
    if scope is None:
        return RelationshipDeepExtractResult(candidate=None, errors=(_SIGNALS_MISSING,))
    allowed_kinds = cast(tuple[str, ...], scope["allowed_kind_ids"])
    scope_fact_refs = frozenset(cast(tuple[str, ...], scope["fact_refs"]))
    claim_kind_id = allowed_kinds[0] if allowed_kinds else "kind.tendency"
    subject_ref = str(scope["subject_ref"])
    certainty_id = str(scope["certainty_ceiling_id"])

    selected = sources[: contract.max_blocks]
    assembler = PublicCopyAssembler()
    while selected:
        if any(fact_ref not in scope_fact_refs for fact_ref, _text in selected):
            return RelationshipDeepExtractResult(candidate=None, errors=(_SIGNALS_MISSING,))
        candidate = _candidate_from_selected(
            selected,
            subject_ref=subject_ref,
            claim_kind_id=claim_kind_id,
            certainty_id=certainty_id,
        )
        try:
            assembler.assemble(candidate, reading_brief, contract)
        except PublicCopyAssemblyError:
            if len(selected) <= contract.min_blocks:
                return RelationshipDeepExtractResult(candidate=None, errors=(_SIGNALS_MISSING,))
            selected = selected[:-1]
            continue
        return RelationshipDeepExtractResult(candidate=candidate, errors=())
    return RelationshipDeepExtractResult(candidate=None, errors=(_SIGNALS_MISSING,))


def relationship_deep_complete_intent(
    *,
    state_token: str,
    public_copy: str,
    output_contract: str | OutputContract,
) -> RelationshipDeepCompleteIntentResult:
    contract = resolve_output_contract(output_contract)
    if contract.contract_id not in RELATIONSHIP_DEEP_CONTRACT_IDS:
        return RelationshipDeepCompleteIntentResult(command=None, errors=(_NOT_APPLICABLE,))
    if not isinstance(public_copy, str) or not public_copy.strip():
        return RelationshipDeepCompleteIntentResult(command=None, errors=(_SIGNALS_MISSING,))
    if contract.disclosure_text not in public_copy.split("\n\n"):
        return RelationshipDeepCompleteIntentResult(command=None, errors=(_SIGNALS_MISSING,))
    if not isinstance(state_token, str) or not state_token.strip():
        return RelationshipDeepCompleteIntentResult(command=None, errors=(_INTENT_INVALID,))
    try:
        command = Complete(state_token=state_token, public_copy=public_copy)
    except ContractValidationError:
        return RelationshipDeepCompleteIntentResult(command=None, errors=(_INTENT_INVALID,))
    return RelationshipDeepCompleteIntentResult(command=command, errors=())


async def relationship_deep_fake_runtime_accept(
    intent: RelationshipDeepCompleteIntentResult,
    runtime: _CompleteRuntime,
) -> RelationshipDeepAcceptedResult:
    if intent.command is None:
        return RelationshipDeepAcceptedResult(
            accepted=None,
            errors=intent.errors or (_INTENT_INVALID,),
        )
    result = await runtime.execute(intent.command)
    if not isinstance(result, Accepted):
        return RelationshipDeepAcceptedResult(accepted=None, errors=(_ACCEPT_FAILED,))
    return RelationshipDeepAcceptedResult(accepted=result, errors=())


def relationship_deep_reading_document(
    accepted: RelationshipDeepAcceptedResult,
    *,
    brief: ReadingBrief | Mapping[str, object],
    candidate: NarrativeCandidate,
    output_contract: str | OutputContract,
    reading_version_id: UUID,
    relationship_type: str | None = None,
    runtime_release: str = "mingli-runtime-fake@local",
    accepted_copy_ref: str | None = None,
    builder: ReadingDocumentBuilder | None = None,
) -> RelationshipDeepDocumentResult:
    contract = resolve_output_contract(output_contract)
    if contract.contract_id not in RELATIONSHIP_DEEP_CONTRACT_IDS:
        return RelationshipDeepDocumentResult(document=None, errors=(_NOT_APPLICABLE,))
    if accepted.accepted is None:
        return RelationshipDeepDocumentResult(
            document=None,
            errors=accepted.errors or (_ACCEPT_FAILED,),
        )
    product_id = _CONTRACT_PRODUCT_IDS.get(contract.contract_id)
    if product_id is None:
        return RelationshipDeepDocumentResult(document=None, errors=(_NOT_APPLICABLE,))
    copy_blocks = accepted.accepted.public_copy.split("\n\n")
    if any(block.text not in copy_blocks for block in candidate.blocks):
        return RelationshipDeepDocumentResult(document=None, errors=(_SIGNALS_MISSING,))
    if contract.disclosure_text not in copy_blocks:
        return RelationshipDeepDocumentResult(document=None, errors=(_SIGNALS_MISSING,))
    reading_brief = brief if isinstance(brief, ReadingBrief) else ReadingBrief.from_dict(dict(brief))
    try:
        document = (builder or ReadingDocumentBuilder()).build(
            ReadingDocumentContext(
                reading_version_id=reading_version_id,
                accepted_copy_ref=accepted_copy_ref
                or f"accepted-copy:{accepted.accepted.state_token}",
                product_id=product_id,
                relationship_type=relationship_type,
                runtime_release=runtime_release,
                prepared=Prepared(
                    state_token=accepted.accepted.state_token,
                    brief=reading_brief,
                ),
                candidate=candidate,
                output_contract=contract,
            )
        )
    except (ValueError, ContractValidationError):
        return RelationshipDeepDocumentResult(document=None, errors=(_DOCUMENT_UNAVAILABLE,))
    if document is None:
        return RelationshipDeepDocumentResult(document=None, errors=(_DOCUMENT_UNAVAILABLE,))
    return RelationshipDeepDocumentResult(document=document, errors=())


async def relationship_deep_persist_reading_document(
    frozen: RelationshipDeepDocumentResult,
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
) -> RelationshipDeepPersistResult:
    if frozen.document is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=frozen.errors or (_DOCUMENT_UNAVAILABLE,),
        )
    try:
        accepted_copy_ref = await repository.load_accepted_copy_ref(job_id)
        existing = await repository.load_reading_document_for_job(job_id)
    except (LookupError, ValueError):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if accepted_copy_ref is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_ACCEPTED_COPY_MISSING,),
        )
    bound = frozen.document.model_copy(update={"accepted_copy_ref": accepted_copy_ref})
    try:
        await repository.save_reading_document_for_job(job_id, bound)
    except ImmutableRecordError:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_IMMUTABLE,),
        )
    except (LookupError, ValueError):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    stored = await repository.load_reading_document_for_job(job_id)
    if stored is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    return RelationshipDeepPersistResult(
        document=stored,
        created=existing is None,
        errors=(),
    )


async def relationship_deep_persist_job_candidate(
    accepted: RelationshipDeepAcceptedResult,
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
    brief: ReadingBrief | Mapping[str, object],
    output_contract: str | OutputContract,
    reading_version_id: UUID,
    relationship_type: str | None = None,
    runtime_release: str = "mingli-runtime-fake@local",
    builder: ReadingDocumentBuilder | None = None,
) -> RelationshipDeepPersistResult:
    contract = resolve_output_contract(output_contract)
    if contract.contract_id not in RELATIONSHIP_DEEP_CONTRACT_IDS:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_NOT_APPLICABLE,),
        )
    if accepted.accepted is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=accepted.errors or (_ACCEPT_FAILED,),
        )
    try:
        candidate = await repository.load_successful_candidate(job_id)
    except (LookupError, ValueError, ImmutableRecordError):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if candidate is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_CANDIDATE_MISSING,),
        )
    frozen = relationship_deep_reading_document(
        accepted,
        brief=brief,
        candidate=candidate,
        output_contract=contract,
        reading_version_id=reading_version_id,
        relationship_type=relationship_type,
        runtime_release=runtime_release,
        builder=builder,
    )
    return await relationship_deep_persist_reading_document(
        frozen,
        repository=repository,
        job_id=job_id,
    )


async def relationship_deep_persist_job_prepared(
    accepted: RelationshipDeepAcceptedResult,
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
    output_contract: str | OutputContract,
    reading_version_id: UUID,
    relationship_type: str | None = None,
    runtime_release: str = "mingli-runtime-fake@local",
    builder: ReadingDocumentBuilder | None = None,
) -> RelationshipDeepPersistResult:
    contract = resolve_output_contract(output_contract)
    if contract.contract_id not in RELATIONSHIP_DEEP_CONTRACT_IDS:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_NOT_APPLICABLE,),
        )
    if accepted.accepted is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=accepted.errors or (_ACCEPT_FAILED,),
        )
    try:
        brief = await repository.load_prepared_brief(job_id)
        candidate = await repository.load_successful_candidate(job_id)
    except (LookupError, ValueError, ImmutableRecordError):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if brief is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_PREPARED_BRIEF_MISSING,),
        )
    if candidate is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_CANDIDATE_MISSING,),
        )
    extracted = extract_relationship_deep_candidate(brief, contract)
    if extracted.candidate is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=extracted.errors or (_SIGNALS_MISSING,),
        )
    if tuple(block.text for block in extracted.candidate.blocks) != tuple(
        block.text for block in candidate.blocks
    ):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_SIGNALS_MISSING,),
        )
    frozen = relationship_deep_reading_document(
        accepted,
        brief=brief,
        candidate=candidate,
        output_contract=contract,
        reading_version_id=reading_version_id,
        relationship_type=relationship_type,
        runtime_release=runtime_release,
        builder=builder,
    )
    return await relationship_deep_persist_reading_document(
        frozen,
        repository=repository,
        job_id=job_id,
    )


async def relationship_deep_persist_job_accepted(
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
    output_contract: str | OutputContract,
    reading_version_id: UUID,
    relationship_type: str | None = None,
    runtime_release: str = "mingli-runtime-fake@local",
    builder: ReadingDocumentBuilder | None = None,
) -> RelationshipDeepPersistResult:
    contract = resolve_output_contract(output_contract)
    if contract.contract_id not in RELATIONSHIP_DEEP_CONTRACT_IDS:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_NOT_APPLICABLE,),
        )
    try:
        accepted = await repository.load_accepted(job_id)
        brief = await repository.load_prepared_brief(job_id)
        candidate = await repository.load_successful_candidate(job_id)
    except (LookupError, ValueError, ImmutableRecordError):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if accepted is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_ACCEPTED_COPY_MISSING,),
        )
    if brief is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_PREPARED_BRIEF_MISSING,),
        )
    if candidate is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_CANDIDATE_MISSING,),
        )
    extracted = extract_relationship_deep_candidate(brief, contract)
    if extracted.candidate is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=extracted.errors or (_SIGNALS_MISSING,),
        )
    if tuple(block.text for block in extracted.candidate.blocks) != tuple(
        block.text for block in candidate.blocks
    ):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_SIGNALS_MISSING,),
        )
    frozen = relationship_deep_reading_document(
        RelationshipDeepAcceptedResult(accepted=accepted, errors=()),
        brief=brief,
        candidate=candidate,
        output_contract=contract,
        reading_version_id=reading_version_id,
        relationship_type=relationship_type,
        runtime_release=runtime_release,
        builder=builder,
    )
    return await relationship_deep_persist_reading_document(
        frozen,
        repository=repository,
        job_id=job_id,
    )


async def relationship_deep_persist_job_version(
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
    output_contract: str | OutputContract,
    relationship_type: str | None = None,
    runtime_release: str = "mingli-runtime-fake@local",
    builder: ReadingDocumentBuilder | None = None,
) -> RelationshipDeepPersistResult:
    contract = resolve_output_contract(output_contract)
    if contract.contract_id not in RELATIONSHIP_DEEP_CONTRACT_IDS:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_NOT_APPLICABLE,),
        )
    try:
        reading_version_id = await repository.load_reading_version_id(job_id)
    except (LookupError, ValueError, ImmutableRecordError):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if reading_version_id is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_READING_VERSION_MISSING,),
        )
    return await relationship_deep_persist_job_accepted(
        repository=repository,
        job_id=job_id,
        output_contract=contract,
        reading_version_id=reading_version_id,
        relationship_type=relationship_type,
        runtime_release=runtime_release,
        builder=builder,
    )


async def relationship_deep_persist_job_output_contract(
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
    relationship_type: str | None = None,
    runtime_release: str = "mingli-runtime-fake@local",
    builder: ReadingDocumentBuilder | None = None,
) -> RelationshipDeepPersistResult:
    try:
        contract = await repository.load_output_contract(job_id)
    except (LookupError, ValueError, ImmutableRecordError):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if contract is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_OUTPUT_CONTRACT_MISSING,),
        )
    return await relationship_deep_persist_job_version(
        repository=repository,
        job_id=job_id,
        output_contract=contract,
        relationship_type=relationship_type,
        runtime_release=runtime_release,
        builder=builder,
    )


async def relationship_deep_persist_job_relationship_type(
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
    runtime_release: str = "mingli-runtime-fake@local",
    builder: ReadingDocumentBuilder | None = None,
) -> RelationshipDeepPersistResult:
    try:
        relationship_type = await repository.load_relationship_type(job_id)
    except (LookupError, ValueError, ImmutableRecordError):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if relationship_type is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_RELATIONSHIP_TYPE_MISSING,),
        )
    return await relationship_deep_persist_job_output_contract(
        repository=repository,
        job_id=job_id,
        relationship_type=relationship_type,
        runtime_release=runtime_release,
        builder=builder,
    )


async def relationship_deep_persist_job_runtime_release(
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
    builder: ReadingDocumentBuilder | None = None,
) -> RelationshipDeepPersistResult:
    try:
        runtime_release = await repository.load_runtime_release(job_id)
    except (LookupError, ValueError, ImmutableRecordError):
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if runtime_release is None:
        return RelationshipDeepPersistResult(
            document=None,
            created=False,
            errors=(_RUNTIME_RELEASE_MISSING,),
        )
    return await relationship_deep_persist_job_relationship_type(
        repository=repository,
        job_id=job_id,
        runtime_release=runtime_release,
        builder=builder,
    )


async def relationship_deep_persist_orchestrator(
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
    builder: ReadingDocumentBuilder | None = None,
) -> RelationshipDeepPersistResult:
    return await relationship_deep_persist_job_runtime_release(
        repository=repository,
        job_id=job_id,
        builder=builder,
    )


async def relationship_deep_generate_orchestrator(
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
) -> RelationshipDeepExtractResult:
    try:
        contract = await repository.load_output_contract(job_id)
        brief = await repository.load_prepared_brief(job_id)
    except (LookupError, ValueError, ImmutableRecordError):
        return RelationshipDeepExtractResult(
            candidate=None,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if contract is None:
        return RelationshipDeepExtractResult(
            candidate=None,
            errors=(_OUTPUT_CONTRACT_MISSING,),
        )
    if contract.contract_id not in RELATIONSHIP_DEEP_CONTRACT_IDS:
        return RelationshipDeepExtractResult(candidate=None, errors=(_NOT_APPLICABLE,))
    if brief is None:
        return RelationshipDeepExtractResult(
            candidate=None,
            errors=(_PREPARED_BRIEF_MISSING,),
        )
    extracted = extract_relationship_deep_candidate(brief, contract)
    if extracted.candidate is None:
        return RelationshipDeepExtractResult(
            candidate=None,
            errors=extracted.errors or (_SIGNALS_MISSING,),
        )
    return RelationshipDeepExtractResult(candidate=extracted.candidate, errors=())


class _RelationshipDeepPrepareClock:
    def now(self):
        from datetime import UTC, datetime

        return datetime.now(UTC)


class _RelationshipDeepRaisingModel:
    async def generate(self, request: object) -> object:
        del request
        raise AssertionError("model.generate must not run for relationship-deep")


async def relationship_deep_prepare_orchestrator(
    *,
    repository: _ReadingDocumentStore,
    job_id: str,
    runtime: object,
    model: object | None = None,
    clock: object | None = None,
) -> RelationshipDeepPrepareResult:
    try:
        contract = await repository.load_output_contract(job_id)
    except (LookupError, ValueError, ImmutableRecordError):
        return RelationshipDeepPrepareResult(
            status=None,
            public_copy=None,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if contract is None:
        return RelationshipDeepPrepareResult(
            status=None,
            public_copy=None,
            errors=(_OUTPUT_CONTRACT_MISSING,),
        )
    if contract.contract_id not in RELATIONSHIP_DEEP_CONTRACT_IDS:
        return RelationshipDeepPrepareResult(
            status=None,
            public_copy=None,
            errors=(_NOT_APPLICABLE,),
        )
    from app.readings.narrative_guard import NarrativeGuard
    from app.readings.orchestrator import ReadingOrchestrator

    outcome = await ReadingOrchestrator(
        repository=cast(Any, repository),
        runtime=cast(Any, runtime),
        model=cast(Any, model if model is not None else _RelationshipDeepRaisingModel()),
        guard=NarrativeGuard(),
        assembler=PublicCopyAssembler(),
        clock=cast(Any, clock if clock is not None else _RelationshipDeepPrepareClock()),
    ).run(job_id)
    return RelationshipDeepPrepareResult(
        status=outcome.status,
        public_copy=outcome.public_copy,
        errors=(),
    )


async def relationship_deep_http_result(
    *,
    repository: _HttpResultStore,
    reading_version_id: UUID,
    product_id: str | None,
) -> RelationshipDeepHttpResult:
    contract = output_contract_for_product(product_id, ())
    if contract.contract_id not in RELATIONSHIP_DEEP_CONTRACT_IDS:
        return RelationshipDeepHttpResult(
            accepted_copy=None,
            document=None,
            errors=(_NOT_APPLICABLE,),
        )
    try:
        accepted_copy = await repository.load_accepted_copy(reading_version_id)
        document = await repository.load_reading_document(reading_version_id)
        copy_row = await repository.get_accepted_copy(reading_version_id)
    except (LookupError, ValueError, ImmutableRecordError):
        return RelationshipDeepHttpResult(
            accepted_copy=None,
            document=None,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if accepted_copy is None and document is None:
        return RelationshipDeepHttpResult(
            accepted_copy=None,
            document=None,
            errors=(),
        )
    if accepted_copy is None:
        return RelationshipDeepHttpResult(
            accepted_copy=None,
            document=None,
            errors=(_ACCEPTED_COPY_MISSING,),
        )
    if document is None or copy_row is None:
        return RelationshipDeepHttpResult(
            accepted_copy=None,
            document=None,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    if document.accepted_copy_ref != f"accepted-copy:{copy_row.id}":
        return RelationshipDeepHttpResult(
            accepted_copy=None,
            document=None,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    copy_blocks = accepted_copy.split("\n\n")
    if any(claim.text not in copy_blocks for claim in document.claims):
        return RelationshipDeepHttpResult(
            accepted_copy=None,
            document=None,
            errors=(_SIGNALS_MISSING,),
        )
    return RelationshipDeepHttpResult(
        accepted_copy=accepted_copy,
        document=document,
        errors=(),
    )


async def relationship_deep_http_follow_up(
    *,
    repository: _HttpResultStore,
    reading_version_id: UUID,
    product_id: str | None,
) -> RelationshipDeepHttpResult:
    wired = await relationship_deep_http_result(
        repository=repository,
        reading_version_id=reading_version_id,
        product_id=product_id,
    )
    if _NOT_APPLICABLE in wired.errors or wired.errors:
        return wired
    if wired.accepted_copy is None or wired.document is None:
        return RelationshipDeepHttpResult(
            accepted_copy=None,
            document=None,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    return wired


async def relationship_deep_http_export(
    *,
    repository: _HttpResultStore,
    reading_version_id: UUID,
    product_id: str | None,
) -> RelationshipDeepHttpResult:
    wired = await relationship_deep_http_result(
        repository=repository,
        reading_version_id=reading_version_id,
        product_id=product_id,
    )
    if _NOT_APPLICABLE in wired.errors or wired.errors:
        return wired
    if wired.accepted_copy is None or wired.document is None:
        return RelationshipDeepHttpResult(
            accepted_copy=None,
            document=None,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    return wired


async def relationship_deep_http_share(
    *,
    repository: _HttpResultStore,
    reading_version_id: UUID,
    product_id: str | None,
) -> RelationshipDeepHttpResult:
    wired = await relationship_deep_http_result(
        repository=repository,
        reading_version_id=reading_version_id,
        product_id=product_id,
    )
    if _NOT_APPLICABLE in wired.errors or wired.errors:
        return wired
    if wired.accepted_copy is None or wired.document is None:
        return RelationshipDeepHttpResult(
            accepted_copy=None,
            document=None,
            errors=(_DOCUMENT_UNAVAILABLE,),
        )
    return wired


def _candidate_from_selected(
    selected: tuple[tuple[str, str], ...] | list[tuple[str, str]],
    *,
    subject_ref: str,
    claim_kind_id: str,
    certainty_id: str,
) -> NarrativeCandidate:
    blocks: list[dict[str, object]] = []
    for index, (fact_ref, text) in enumerate(selected, start=1):
        blocks.append(
            {
                "block_id": f"relationship-signal-{index}",
                "block_type": "claim",
                "text": text,
                "subject_ref": subject_ref,
                "dimension_id": "relationship",
                "claim_kind_id": claim_kind_id,
                "certainty_id": certainty_id,
                "fact_refs": [fact_ref],
                "finding_refs": [],
                "evidence_refs": [],
                "limit_kind_ids": [],
            }
        )
    return NarrativeCandidate.from_dict(
        {
            "schema_version": "mingli-narrative-candidate-v1",
            "blocks": blocks,
        }
    )


def _signal_display_texts(
    facts: Mapping[str, Mapping[str, object]],
) -> tuple[tuple[str, str], ...]:
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for fact in facts.values():
        ref = fact.get("ref")
        if (
            not isinstance(ref, str)
            or ref.rstrip("/").rsplit("/", 1)[-1] != "relationship_signals"
        ):
            continue
        raw_signals = fact.get("value")
        if not isinstance(raw_signals, (list, tuple)):
            continue
        for item in raw_signals:
            if not isinstance(item, Mapping):
                continue
            display_text = item.get("display_text")
            if not isinstance(display_text, str) or not display_text.strip():
                continue
            if display_text in seen:
                continue
            seen.add(display_text)
            ordered.append((ref, display_text))
    return tuple(ordered)


def _relationship_scope(payload: Mapping[str, object]) -> dict[str, object] | None:
    scopes = merge_claim_scopes(payload)
    for (_subject_ref, dimension_id), scope in scopes.items():
        if dimension_id == "relationship":
            return scope
    return None
