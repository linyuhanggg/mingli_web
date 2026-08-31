from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any, cast
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.adapters.runtime import (
    RUNTIME_TURN_AUDIT_NAME,
    WORKER_AUDIT_TIMEOUT_SECONDS,
    MingliRuntime,
    RuntimeTurnAudit,
    WorkerV2MingliRuntimeAdapter,
    append_runtime_turn_audit,
    failure_for_transport_fault,
    runtime_command_digest,
)
from app.charts.contracts import BaziChartV1, ZiweiChartV1
from app.charts.projectors import project_runtime_view_model
from app.commerce.models import FulfillmentRecord, Order, Payment, ProductFamily, ProductVersion
from app.commerce.public_service import BAZI_DEEP_PRODUCT_FAMILY_KEY
from app.commerce.service import CommerceError, CommerceService
from app.config import Settings
from app.entitlements.service import (
    EntitlementDeniedError,
    EntitlementService,
)
from app.profiles.models import ProfileVersion
from app.profiles.schemas import ProfileConfirmRequest
from app.profiles.service import OwnerProtocol, ProfileService, owner_ids
from app.readings.api_schemas import (
    AccountHistoryResponse,
    AccountHistoryRootResponse,
    AccountHistoryVersionSummary,
    CapabilityProjection,
    ChartFastPathTiming,
    DeliveryState,
    Horizon,
    LatestProfileReadingResponse,
    ReadingResultResponse,
    ReadingStartResponse,
    ReadingVerificationSummary,
    ReadingVersionSummary,
    TimeLayerEntitlementResponse,
)
from app.readings.capability_policy import (
    project_capability,
    require_public_product_exposure,
    require_public_runtime_capabilities,
)
from app.readings.errors import RuntimeTransportError
from app.readings.models import ReadingJobRecord, ReadingVersion
from app.readings.output_contracts import output_contract_for_product
from app.readings.presentation.access_policy import ACTIVE_CONTENT_ACCESS_POLICY
from app.readings.presentation.contracts import (
    ClaimCard,
    PresentationContract,
    PresentationSection,
    ReadingDocumentV1,
)
from app.readings.presentation.fact_panel import (
    project_presented_fact_panel,
    project_presented_view_model,
)
from app.readings.presentation.projector import build_reading_document
from app.readings.public_fact_panel import project_public_fact_panel
from app.readings.repository import (
    READING_HISTORY_LIMIT,
    ReadingJobAlreadyQueuedError,
    SqlReadingRepository,
)
from app.readings.request_compiler import (
    ConfirmedProfileVersion,
    RelationshipArt,
    RelationshipType,
    RequestCompilationError,
    compile_bazi_day_prepare,
    compile_bazi_month_prepare,
    compile_bazi_prepare,
    compile_bazi_year_prepare,
    compile_canwen_prepare,
    compile_chart_similarity_prepare,
    compile_fengshui_prepare,
    compile_five_elements_facts_prepare,
    compile_fortune_prepare,
    compile_hecan_prepare,
    compile_liuren_prepare,
    compile_liuyao_prepare,
    compile_luming_nayin_prepare,
    compile_meihua_prepare,
    compile_qimen_prepare,
    compile_qizheng_day_prepare,
    compile_qizheng_month_prepare,
    compile_qizheng_prepare,
    compile_qizheng_year_prepare,
    compile_relationship_prepare,
    compile_selection_prepare,
    compile_taiyi_prepare,
    compile_time_check_prepare,
    compile_wenshi_prepare,
    compile_ziwei_month_prepare,
    compile_ziwei_year_prepare,
)
from app.readings.runtime_contracts import (
    MingliResult,
    Prepare,
    Prepared,
    ReadingBrief,
    Stopped,
    TimeLayerEntitlementV1,
    project_time_layer_entitlement,
)
from app.readings.status import ReadingStatus
from app.security.envelope import EnvelopeCipher

NARRATIVE_POLICY_VERSION = "policy-v1"
_PAID_PRODUCT_IDS = frozenset({"bazi-deep", "qimen-deep", "liuyao-deep"})
_DIRECT_CHART_PRODUCT_IDS = frozenset(
    {"bazi", "ziwei", "liuyao", "meihua", "daliuren", "liuren"}
)
_PROFILE_PRODUCT_ALIASES = {
    "qizheng": "xingming",
    "daliuren": "liuren",
}
_POLL_STOP_STATUSES = frozenset(
    {
        ReadingStatus.ACCEPTED,
        ReadingStatus.TERMINAL_STOPPED,
        ReadingStatus.RUNTIME_UNKNOWN,
        ReadingStatus.WAITING_INPUT,
    }
)
_ATOMIC_PROFILE_PREVIEW_CLAIM_JOB_STATUS = "claim_pending"
_ATOMIC_PROFILE_PREVIEW_CLAIM_LEASE_SECONDS = 10.0
_ATOMIC_PROFILE_PREVIEW_CLAIM_UNEXPOSED_GENERATION = 1
_ATOMIC_PROFILE_PREVIEW_CLAIM_EXPOSED_GENERATION = 2
_ATOMIC_PROFILE_PREVIEW_REPLAY_LOCK_SALT = 0x21_5052_4556_4945
_POST_WRITE_RUNTIME_TRANSPORT_FAULTS = frozenset(
    {
        "invalid-result",
        "process-exited",
        "result-decode",
        "unbound-idle",
        "unbound-result",
    }
)
_logger = logging.getLogger("mingli.chart_fast_path")
DEFAULT_QUERIES = {
    "profile_preview": "请预览我的本命格局。",
    "bazi_deep": "请围绕事业主线生成八字结构化深读。",
    "qimen_deep": "请围绕这件事的行动、时机与局势生成奇门结构化深读。",
    "liuyao_deep": "请围绕这次六爻问题整理盘面、用神候选与旺衰证据。",
    "bazi_year_preview": "请展示我指定年份的八字流年事实。",
    "bazi_month_preview": "请展示我指定月份的八字流月事实。",
    "bazi_day_preview": "请展示我指定日期的八字流日事实。",
    "five_elements_facts_preview": "请展示我的五行事实与调候依据。",
    "chart_similarity_preview": "请比较两份已确认命盘的八字四柱事实。",
    "ziwei_preview": "请预览我的紫微命盘。",
    "ziwei_year_preview": "请展示我指定年份的紫微流年事实。",
    "ziwei_month_preview": "请展示我指定月份的紫微流月事实。",
    "qizheng_preview": "请预览我的七政四余星盘。",
    "qizheng_year_preview": "请展示我指定年份的七政四余时限事实。",
    "qizheng_month_preview": "请展示我指定月份的七政四余时限事实。",
    "qizheng_day_preview": "请展示我指定日期的七政四余时限事实。",
    "today": "请看看我今天的运势。",
    "near_seven": "请看看我这一周的运势。",
    "liuyao_one_question": "请为这个问题起一卦。",
    "wenshi_one_question": "请按同一问题、同一时空生成六爻、奇门与大六壬三术合参盘。",
    "canwen_preview": "请比较所选命盘在这个问题上的共同事实范围。",
    "hecan_preview": "请按所选命盘展示共同事实范围、分歧范围与缺失范围。",
    "bazi_relationship_preview": "请按双方已确认命盘生成八字跨盘结构事实。",
    "ziwei_relationship_preview": "请按双方已确认命盘生成紫微跨盘结构事实。",
    "qizheng_relationship_preview": "请按双方已确认星盘生成七政跨盘结构事实。",
    "qimen_one_question": "请排出这件事的奇门局。",
    "liuren_one_question": "请排出这件事的大六壬课盘。",
    "meihua_preview": "请按本次选择的起法为这个问题起一卦梅花易数。",
    "physiognomy_preview": "请按已确认的可见观察展示相法结构。",
    "luming_nayin_preview": "请展示禄命与纳音的基础结构事实。",
    "rhythm_preview": "请展示本命纳音音律的基础事实。",
    "time_check_preview": "请按已知时间范围枚举十二个时辰候选盘面事实。",
    "taiyi_preview": "请展示本次年度太乙年计盘结构。",
    "selection_preview": "请比较日期范围内的择日候选事实。",
    "fengshui_preview": "请展示已确认空间观察与风水结构事实。",
}


def _profile_default_preview_year(
    profile: ConfirmedProfileVersion,
    *,
    reference: datetime | None = None,
) -> int:
    """Select the default civil year in the confirmed Profile's timezone."""

    instant = reference or datetime.now(UTC)
    if instant.tzinfo is None:
        raise ValueError("preview reference datetime must be timezone-aware")
    return instant.astimezone(ZoneInfo(profile.timezone)).year


def _presented_public_facts(
    fact_panel: Mapping[str, object] | None,
) -> dict[str, str]:
    """Map final public fact refs to their presented display_text."""

    if fact_panel is None:
        return {}
    facts = fact_panel.get("facts")
    if not isinstance(facts, Sequence) or isinstance(facts, (str, bytes)):
        return {}
    public_facts: dict[str, str] = {}
    for item in facts:
        if not isinstance(item, Mapping):
            continue
        ref = item.get("ref")
        display_text = item.get("display_text")
        if isinstance(ref, str) and isinstance(display_text, str) and display_text:
            public_facts[ref] = display_text
    return public_facts


def _product_id_for_presented_document(document: ReadingDocumentV1) -> str:
    """Recover the product lane encoded in a stored document version string."""

    product_version = document.product_version.strip()
    prefix = product_version.split("/", 1)[0]
    if prefix.endswith("-reading"):
        return prefix[: -len("-reading")]
    return prefix


def _requires_extractive_claim_text(document: ReadingDocumentV1) -> bool:
    """bazi-deep NarrativeGuard requires claim text == referenced public source."""

    return _product_id_for_presented_document(document) == "bazi-deep"


def _project_presented_claim(
    claim: ClaimCard,
    *,
    public_facts: Mapping[str, str],
    retained_evidence_refs: frozenset[str],
    require_extractive_text: bool,
) -> ClaimCard | None:
    """Retain or rebuild a claim against the final public fact closure."""

    if not set(claim.fact_refs).issubset(public_facts):
        return None
    if not set(claim.evidence_refs).issubset(retained_evidence_refs):
        return None
    if not require_extractive_text or not claim.fact_refs:
        return claim
    if any(public_facts[ref] == claim.text for ref in claim.fact_refs):
        return claim
    # Fact-grounded bazi-deep blocks are extractive: rebuild from the single
    # referenced final display_text, or drop when the source is ambiguous.
    if len(claim.fact_refs) != 1:
        return None
    return claim.model_copy(update={"text": public_facts[claim.fact_refs[0]]})


def _presentation_contract_for_presented_document(
    document: ReadingDocumentV1,
    *,
    projected_claims: tuple[ClaimCard, ...] | None = None,
) -> PresentationContract:
    """Rebuild the PresentationContract Guard declared by this document."""

    output_contract = output_contract_for_product(
        _product_id_for_presented_document(document),
        tuple(
            dict.fromkeys(
                claim.dimension_id for claim in document.claims if claim.dimension_id
            )
        ),
    )
    source_claim_count = len(document.claims)
    # An accepted source document was valid under its Guard. Product policy still
    # supplies the floor when the source met it; otherwise keep the observed
    # accepted floor so projection cannot invent a stricter contract version.
    min_claims = (
        min(output_contract.min_blocks, source_claim_count)
        if source_claim_count > 0
        else output_contract.min_blocks
    )
    max_claims = max(
        output_contract.max_blocks,
        source_claim_count,
        min_claims,
    )
    allowed_kinds = tuple(
        dict.fromkeys(
            [
                *(claim.claim_kind_id for claim in document.claims),
                "kind.fact",
                "kind.tendency",
            ]
        )
    )
    claims_for_bounds = projected_claims if projected_claims is not None else document.claims
    max_chars = max(
        max((len(claim.text) for claim in document.claims), default=1),
        max((len(claim.text) for claim in claims_for_bounds), default=1),
        output_contract.max_output_chars,
    )
    return PresentationContract(
        contract_version=document.presentation_contract_version,
        product_version=document.product_version,
        renderer="reading-document/v1",
        sections=(
            PresentationSection(
                section_id="overview",
                title="判断",
                min_claims=min_claims,
                max_claims=max_claims,
                max_chars_per_claim=max_chars,
                allowed_claim_kind_ids=allowed_kinds,
            ),
        ),
        fixed_disclosures=tuple(boundary.text for boundary in document.boundaries),
    )


def _project_presented_document(
    document: ReadingDocumentV1,
    *,
    view_model: BaziChartV1 | ZiweiChartV1,
    public_facts: Mapping[str, str],
) -> ReadingDocumentV1 | None:
    """Keep public document dependencies inside the presented fact closure."""

    public_fact_refs = frozenset(public_facts)
    evidence = tuple(
        item
        for item in document.evidence
        if set(item.supports_fact_refs).issubset(public_fact_refs)
    )
    retained_evidence_refs = frozenset(item.evidence_ref for item in evidence)
    require_extractive_text = _requires_extractive_claim_text(document)
    retained_claims: list[ClaimCard] = []
    for claim in document.claims:
        projected_claim = _project_presented_claim(
            claim,
            public_facts=public_facts,
            retained_evidence_refs=retained_evidence_refs,
            require_extractive_text=require_extractive_text,
        )
        if projected_claim is not None:
            retained_claims.append(projected_claim)
    claims = tuple(retained_claims)
    answer_summary = (
        claims[0].text
        if claims
        else "当前没有可公开展示的结论。"
    )
    projected_document = document.model_copy(
        update={
            "view_model": view_model,
            "answer_summary": answer_summary,
            "claims": claims,
            "evidence": evidence,
        }
    )
    try:
        return build_reading_document(
            _presentation_contract_for_presented_document(
                document,
                projected_claims=claims,
            ),
            projected_document.model_dump(mode="json"),
        )
    except ValueError:
        # Filtering can drop a document below its declared PresentationContract
        # minima. Fail closed instead of shipping an illegal accepted document.
        return None


def _project_presented_accepted_copy(
    accepted_copy: str | None,
    *,
    source_document: ReadingDocumentV1 | None,
    presented_document: ReadingDocumentV1 | None,
) -> str | None:
    """Keep owner copy text inside the retained document claim closure."""

    if accepted_copy is None or source_document is None:
        return accepted_copy
    if presented_document is None:
        return None

    source_claim_ids = tuple(claim.claim_id for claim in source_document.claims)
    retained_claim_ids = tuple(claim.claim_id for claim in presented_document.claims)
    if source_document.claims == presented_document.claims:
        return accepted_copy
    if (
        len(set(source_claim_ids)) != len(source_claim_ids)
        or len(set(retained_claim_ids)) != len(retained_claim_ids)
    ):
        return None
    retained_claim_id_set = set(retained_claim_ids)
    if retained_claim_ids != tuple(
        claim_id
        for claim_id in source_claim_ids
        if claim_id in retained_claim_id_set
    ):
        return None
    if not presented_document.claims:
        return None

    separator = "\n\n"
    source_claim_prefix = separator.join(
        claim.text for claim in source_document.claims
    )
    if accepted_copy == source_claim_prefix:
        suffix = None
    elif accepted_copy.startswith(f"{source_claim_prefix}{separator}"):
        suffix = accepted_copy[len(source_claim_prefix) + len(separator) :]
    else:
        # The immutable copy and document are not mechanically aligned, so a
        # partial projection cannot prove which text belongs to a removed claim.
        return None

    parts = [claim.text for claim in presented_document.claims]
    if suffix:
        parts.append(suffix)
    return separator.join(parts)


def _project_active_time_layer_access(
    view_model: object,
) -> TimeLayerEntitlementV1 | None:
    return project_time_layer_entitlement(
        view_model,
        resolution=ACTIVE_CONTENT_ACCESS_POLICY.legacy_time_layer_resolution,
    )


@dataclass(frozen=True, slots=True)
class PresentedReadingProjection:
    fact_panel: dict[str, Any] | None
    view_model: object
    document: ReadingDocumentV1 | None
    time_layer_entitlement: TimeLayerEntitlementV1 | None


async def project_owned_reading_presentation(
    *,
    brief: ReadingBrief | Mapping[str, object] | None,
    view_model: object,
    document: ReadingDocumentV1 | None,
) -> PresentedReadingProjection:
    """Apply active content access and fact closure at an owned read boundary."""

    entitlement_view_model = (
        view_model
        if isinstance(view_model, (BaziChartV1, ZiweiChartV1))
        else document.view_model
        if document is not None
        and isinstance(document.view_model, (BaziChartV1, ZiweiChartV1))
        else None
    )
    time_layer_entitlement = _project_active_time_layer_access(
        entitlement_view_model
    )
    fact_panel = (
        project_presented_fact_panel(
            brief,
            view_model=view_model,
        )
        if isinstance(view_model, (BaziChartV1, ZiweiChartV1))
        else project_public_fact_panel(brief)
    )
    presented_view_model = (
        project_presented_view_model(
            view_model,
        )
        if isinstance(view_model, (BaziChartV1, ZiweiChartV1))
        else view_model
    )
    presented_document = document
    if document is not None and isinstance(
        document.view_model,
        (BaziChartV1, ZiweiChartV1),
    ):
        document_fact_panel = project_presented_fact_panel(
            brief,
            view_model=document.view_model,
        )
        presented_document = _project_presented_document(
            document,
            view_model=project_presented_view_model(
                document.view_model,
            ),
            public_facts=_presented_public_facts(document_fact_panel),
        )
    return PresentedReadingProjection(
        fact_panel=fact_panel,
        view_model=presented_view_model,
        document=presented_document,
        time_layer_entitlement=time_layer_entitlement,
    )


def _post_write_runtime_transport_fault(
    runtime: MingliRuntime | None,
    prepare: Prepare,
    result: Stopped,
) -> str | None:
    """Return the Worker audit fault only when a tokenless turn was written."""

    audit = _post_write_runtime_result_audit(runtime, prepare)
    if audit is None or audit.result_kind != result.kind:
        return None
    fault = audit.transport_fault
    if fault in _POST_WRITE_RUNTIME_TRANSPORT_FAULTS or (
        isinstance(fault, str) and fault.startswith("worker-isolate:")
    ):
        return fault
    return None


def _post_write_runtime_result_audit(
    runtime: MingliRuntime | None,
    prepare: Prepare,
) -> RuntimeTurnAudit | None:
    """Return only a fresh WorkerV2 result emitted after a tokenless write."""

    if (
        prepare.state_token is not None
        or getattr(runtime, "adapter_kind", None) != "runtime-worker-v2"
    ):
        return None
    audit = getattr(runtime, "last_turn", None)
    sequence = getattr(runtime, "_last_sequence", None)
    if (
        not isinstance(audit, RuntimeTurnAudit)
        or audit.command_digest != runtime_command_digest(prepare)
        or not isinstance(sequence, int)
        or audit.sequence != sequence
        or audit.result_kind not in {"prepared", "stopped"}
    ):
        return None
    return audit


class ReadingServiceError(RuntimeError):
    """Base class for explicit Phase 2 API service failures."""


class ReadingNotFoundError(ReadingServiceError):
    """A Reading Version is missing or belongs to another owner."""


class ReadingNotWaitingInputError(ReadingServiceError):
    """The Reading Version is not in the waiting_input state."""


class ReadingAlreadyQueuedError(ReadingServiceError):
    """A concurrent input submission already queued this Reading Version."""


class ReadingNotAcceptedError(ReadingServiceError):
    """The Reading Version has no Accepted Copy to follow up or verify."""


class ReadingFollowUpUnavailableError(ReadingServiceError):
    """A follow-up violates its frozen count, time, or linearity contract."""


class RuntimeReleaseUnavailableError(ReadingServiceError):
    """No Runtime Release is registered for a new Reading Version."""


class ChartFastPathUnavailableError(ReadingServiceError):
    """The deterministic chart Runtime did not finish within its short budget."""

    def __init__(
        self,
        detail: str,
        *,
        code: str | None = None,
        prepared_checkpoint: Prepared | None = None,
        waiting_input_checkpoint: Stopped | None = None,
        terminal_stopped_checkpoint: Stopped | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code or detail
        self.prepared_checkpoint = prepared_checkpoint
        self.waiting_input_checkpoint = waiting_input_checkpoint
        self.terminal_stopped_checkpoint = terminal_stopped_checkpoint


class InvalidReadingInputError(ReadingServiceError):
    """Supplied values do not satisfy the runtime input request."""


class ProfileVersionNotOwnedError(ReadingServiceError):
    """The requested Profile Version is missing or belongs to another owner."""


class ProfileNotOwnedError(ReadingServiceError):
    """The requested Profile is missing or belongs to another owner."""


class ProfileReadingUnavailableError(ReadingServiceError):
    """No successful renderable Reading satisfies the Profile lookup."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class IdempotencyConflictError(ReadingServiceError):
    """An Idempotency-Key was reused for a different action or payload."""


class PaidReadingNotGrantedError(ReadingServiceError):
    """Dogfood paid capability is closed for this owner."""

    def __init__(
        self,
        title: str,
        *,
        detail: str | None = None,
        code: str = "paid_reading_not_granted",
    ) -> None:
        super().__init__(title)
        self.title = title
        self.detail = detail
        self.code = code


class ReadingFulfillmentUnavailableError(ReadingServiceError):
    """A verified payment cannot bind to the requested Reading Job."""


@dataclass(frozen=True, slots=True)
class IdempotencyContext:
    key_hash: str
    action: str
    request_fingerprint: str


@dataclass(frozen=True, slots=True)
class AtomicProfilePreviewClaim:
    context: IdempotencyContext
    reading_version_id: UUID
    lease_token: str
    default_preview_year: int | None


@dataclass(frozen=True, slots=True)
class InputFieldPolicy:
    target: str
    type_ids: frozenset[str]
    minimum: int | float | None = None
    maximum: int | float | None = None


@dataclass(frozen=True, slots=True)
class FulfillmentBindingResult:
    fulfillment_id: UUID
    reading_version_id: UUID
    reading_job_id: UUID
    status: str
    created: bool


_INPUT_FIELD_POLICIES: dict[str, InputFieldPolicy] = {
    **{
        f"cast_{index}": InputFieldPolicy(
            target="cast",
            type_ids=frozenset({"integer"}),
            minimum=6,
            maximum=9,
        )
        for index in range(1, 7)
    },
    "zi_policy": InputFieldPolicy(
        target="zi_hour_policy",
        type_ids=frozenset({"choice"}),
    ),
    "fixture_input": InputFieldPolicy(
        target="fixture_input",
        type_ids=frozenset({"text", "textarea"}),
    ),
}


class ReadingService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        chart_runtime: MingliRuntime | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.repository = SqlReadingRepository(
            session,
            EnvelopeCipher.from_settings(settings),
        )
        self.profiles = ProfileService(session, settings)
        self.entitlements = EntitlementService(session, settings)
        self.chart_runtime = chart_runtime
        self._idempotency_secret = settings.identity_hash_key.get_secret_value().encode(
            "utf-8"
        )
        self._atomic_profile_preview_claim: AtomicProfilePreviewClaim | None = None

    async def _require_paid_action(self, owner: OwnerProtocol, *, action: str) -> None:
        try:
            await self.entitlements.require_paid_action(owner, action=action)
        except EntitlementDeniedError as error:
            raise PaidReadingNotGrantedError(
                error.title,
                detail=error.detail,
                code=error.code or "paid_reading_not_granted",
            ) from error

    async def replay_confirm_profile_preview(
        self,
        owner: OwnerProtocol,
        *,
        draft_id: UUID,
        profile_payload: Mapping[str, object],
        query: str | None,
        dimension_ids: Sequence[str] | None,
        target_year: int | None,
        target_month: str | None,
        target_date: date | None,
        idempotency_key: str,
    ) -> tuple[ReadingStartResponse | None, IdempotencyContext]:
        """Resolve the combined Profile+Reading idempotency key before writes."""

        action = (
            "bazi_year_preview"
            if target_year is not None
            else "bazi_month_preview"
            if target_month is not None
            else "bazi_day_preview"
            if target_date is not None
            else "profile_preview"
        )
        resolved_query = query or DEFAULT_QUERIES[action]
        resolved_dimensions = list(dimension_ids or ("career",))
        context = self._idempotency_context(
            idempotency_key,
            action="confirm_profile_preview",
            payload={
                "draft_id": str(draft_id),
                "profile": dict(profile_payload),
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "target_year": target_year,
                "target_month": target_month,
                "target_date": target_date.isoformat() if target_date else None,
            },
        )
        assert context is not None
        replayed = await self._replay_idempotency(owner, context)
        if replayed is not None:
            return replayed, context
        claimed = await self._claim_atomic_profile_preview(
            owner,
            draft_id=draft_id,
            profile_payload=profile_payload,
            query=resolved_query,
            dimension_ids=resolved_dimensions,
            target_year=target_year,
            target_month=target_month,
            target_date=target_date,
            idempotency=context,
        )
        return claimed, context

    async def _claim_atomic_profile_preview(
        self,
        owner: OwnerProtocol,
        *,
        draft_id: UUID,
        profile_payload: Mapping[str, object],
        query: str,
        dimension_ids: Sequence[str],
        target_year: int | None,
        target_month: str | None,
        target_date: date | None,
        idempotency: IdempotencyContext,
    ) -> ReadingStartResponse | None:
        """Commit the cross-process claim before Profile confirmation or Runtime I/O."""

        user_id, guest_id = owner_ids(owner)
        try:
            await self.profiles.repository.lock_profile_owner(
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
            )
        except LookupError:
            # Preserve the endpoint's existing Profile error mapping. No Runtime
            # can be reached because confirm_draft will fail on the same owner.
            return None

        # Reuse the authoritative Profile confirmation path as a validation and
        # compilation probe. Rolling back only this savepoint leaves the owner
        # lock in the outer transaction while discarding all Profile writes.
        savepoint = await self.session.begin_nested()
        try:
            profile_request = ProfileConfirmRequest.model_validate(profile_payload)
            profile = await self.profiles.confirm_draft(owner, draft_id, profile_request)
            confirmed = await self._owned_confirmed_profile(
                owner,
                profile.profile_version_id,
            )
            default_preview_year = (
                _profile_default_preview_year(confirmed)
                if target_year is None
                and target_month is None
                and target_date is None
                else None
            )
            prepare = self._compile_profile_preview_prepare(
                confirmed,
                query=query,
                dimension_ids=dimension_ids,
                target_year=target_year,
                target_month=target_month,
                target_date=target_date,
                default_preview_year=default_preview_year,
            )
        except (IntegrityError, LookupError, ValueError):
            await savepoint.rollback()
            # Let the endpoint's real confirmation attempt return its established
            # validation/conflict contract without leaving a provisional claim.
            return None
        except Exception:
            await savepoint.rollback()
            raise
        await savepoint.rollback()

        release = await self._runtime_release()
        require_public_runtime_capabilities(
            ("bazi",),
            environment=self.settings.environment,
            real_traffic_enabled=self.settings.real_traffic_enabled,
        )
        require_public_product_exposure(
            None,
            environment=self.settings.environment,
            real_traffic_enabled=self.settings.real_traffic_enabled,
        )
        root = await self.repository.create_root(
            capability_id="bazi",
            runtime_capability_ids=("bazi",),
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        version = await self.repository.create_version(
            reading_root_id=root.id,
            runtime_release_id=release.id,
            prepare_command=prepare,
        )
        await self.session.refresh(version)
        job = await self._create_job(
            version.id,
            status=_ATOMIC_PROFILE_PREVIEW_CLAIM_JOB_STATUS,
        )
        lease_token = uuid4().hex
        job.lease_generation = _ATOMIC_PROFILE_PREVIEW_CLAIM_UNEXPOSED_GENERATION
        job.lease_owner = "profile-preview-direct"
        job.lease_token = lease_token
        job.lease_expires_at = datetime.now(UTC) + timedelta(
            seconds=_ATOMIC_PROFILE_PREVIEW_CLAIM_LEASE_SECONDS
        )
        await self.session.flush()
        replayed = await self._save_idempotency_or_replay(
            idempotency,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
            reading_version_id=version.id,
        )
        if replayed is not None:
            return replayed
        # Keep the durable claim distinguishable from both executable work and
        # an actual Runtime failure. Same-key requests may replay this bounded
        # input_ready state while the winner confirms the Profile or calls
        # Runtime, but workers cannot claim the placeholder Job.
        await self.session.commit()
        self._atomic_profile_preview_claim = AtomicProfilePreviewClaim(
            context=idempotency,
            reading_version_id=version.id,
            lease_token=lease_token,
            default_preview_year=default_preview_year,
        )
        return None

    async def _recover_expired_atomic_profile_preview_claim(
        self,
        version_id: UUID,
    ) -> bool:
        """CAS one abandoned direct-start lease into a durable unknown result."""

        now = datetime.now(UTC)
        candidate = (
            await self.session.execute(
                select(
                    ReadingJobRecord.id,
                    ReadingJobRecord.status,
                    ReadingJobRecord.lease_token,
                    ReadingJobRecord.lease_expires_at,
                )
                .where(ReadingJobRecord.reading_version_id == version_id)
                .order_by(
                    ReadingJobRecord.created_at.desc(),
                    ReadingJobRecord.id.desc(),
                )
                .limit(1)
            )
        ).first()
        if (
            candidate is None
            or candidate.status != _ATOMIC_PROFILE_PREVIEW_CLAIM_JOB_STATUS
            or candidate.lease_token is None
            or candidate.lease_expires_at is None
            or not _datetime_lte(candidate.lease_expires_at, now)
        ):
            return False

        # Match load_start_claim(): lock the ReadingVersion before its Job so
        # expiry recovery cannot deadlock a late direct-start winner on
        # PostgreSQL. Re-check every CAS predicate after both locks are held.
        version = await self.session.scalar(
            select(ReadingVersion)
            .where(ReadingVersion.id == version_id)
            .with_for_update()
        )
        if (
            version is None
            or version.status != ReadingStatus.INPUT_READY.value
        ):
            await self.session.rollback()
            return False
        job = await self.session.scalar(
            select(ReadingJobRecord)
            .where(ReadingJobRecord.reading_version_id == version_id)
            .order_by(ReadingJobRecord.created_at.desc(), ReadingJobRecord.id.desc())
            .limit(1)
            .with_for_update()
        )
        if (
            job is None
            or job.status != _ATOMIC_PROFILE_PREVIEW_CLAIM_JOB_STATUS
            or job.id != candidate.id
            or job.lease_token != candidate.lease_token
            or job.lease_expires_at is None
            or not _datetime_lte(job.lease_expires_at, now)
        ):
            await self.session.rollback()
            return False
        version_result = await self.session.execute(
            update(ReadingVersion)
            .where(
                ReadingVersion.id == version_id,
                ReadingVersion.status == ReadingStatus.INPUT_READY.value,
            )
            .values(status=ReadingStatus.RUNTIME_UNKNOWN.value)
            .returning(ReadingVersion.id)
            .execution_options(synchronize_session=False)
        )
        if version_result.scalar_one_or_none() is None:
            await self.session.rollback()
            return False
        job_result = await self.session.execute(
            update(ReadingJobRecord)
            .where(
                ReadingJobRecord.id == job.id,
                ReadingJobRecord.status
                == _ATOMIC_PROFILE_PREVIEW_CLAIM_JOB_STATUS,
                ReadingJobRecord.lease_token == candidate.lease_token,
                ReadingJobRecord.lease_expires_at.is_not(None),
                ReadingJobRecord.lease_expires_at <= now,
            )
            .values(
                status="runtime_unknown",
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
            )
            .returning(ReadingJobRecord.id)
            .execution_options(synchronize_session=False)
        )
        if job_result.scalar_one_or_none() is None:
            await self.session.rollback()
            return False
        await self.session.commit()
        return True

    async def _mark_atomic_profile_preview_claim_exposed(
        self,
        version_id: UUID,
    ) -> bool:
        """Durably record that a provisional Reading was returned to a reader."""

        now = datetime.now(UTC)
        result = await self.session.execute(
            update(ReadingJobRecord)
            .where(
                ReadingJobRecord.reading_version_id == version_id,
                ReadingJobRecord.status
                == _ATOMIC_PROFILE_PREVIEW_CLAIM_JOB_STATUS,
                ReadingJobRecord.lease_generation
                < _ATOMIC_PROFILE_PREVIEW_CLAIM_EXPOSED_GENERATION,
                ReadingJobRecord.lease_expires_at.is_not(None),
                ReadingJobRecord.lease_expires_at > now,
            )
            .values(
                lease_generation=_ATOMIC_PROFILE_PREVIEW_CLAIM_EXPOSED_GENERATION
            )
            .returning(ReadingJobRecord.id)
            .execution_options(synchronize_session=False)
        )
        if result.scalar_one_or_none() is None:
            return False
        await self.session.commit()
        return True

    @staticmethod
    def _atomic_profile_preview_replay_lock_id(key_hash: str) -> int:
        """Map one idempotency digest into PostgreSQL's signed bigint keyspace."""

        digest_prefix = int(key_hash[:16], 16)
        return (digest_prefix ^ _ATOMIC_PROFILE_PREVIEW_REPLAY_LOCK_SALT) & (
            (1 << 63) - 1
        )

    @asynccontextmanager
    async def _hold_atomic_profile_preview_winner_fence(
        self,
        key_hash: str,
    ) -> AsyncIterator[None]:
        """Keep PostgreSQL replays behind one winner through rollback settlement."""

        if self.session.get_bind().dialect.name != "postgresql":
            yield
            return
        bind = self.session.bind
        if bind is None:
            raise RuntimeError("PostgreSQL Reading session is not bound")
        engine = bind if isinstance(bind, AsyncEngine) else bind.engine
        async with engine.connect() as connection, connection.begin():
            await connection.scalar(
                select(
                    func.pg_advisory_xact_lock(
                        self._atomic_profile_preview_replay_lock_id(key_hash)
                    )
                )
            )
            yield

    async def _hold_atomic_profile_preview_replay_intent(
        self,
        idempotency: IdempotencyContext,
    ) -> None:
        """Wait behind a PostgreSQL winner before reading its idempotency record."""

        if self.session.get_bind().dialect.name != "postgresql":
            return
        await self.session.scalar(
            select(
                func.pg_advisory_xact_lock(
                    self._atomic_profile_preview_replay_lock_id(idempotency.key_hash)
                )
            )
        )

    async def _stabilize_atomic_profile_preview_claim_for_read(
        self,
        version_id: UUID,
    ) -> None:
        if await self._recover_expired_atomic_profile_preview_claim(version_id):
            return
        if await self._mark_atomic_profile_preview_claim_exposed(version_id):
            return
        await self._recover_expired_atomic_profile_preview_claim(version_id)

    async def _stabilize_atomic_profile_preview_claims_for_list(
        self,
        version_ids: Sequence[UUID],
    ) -> bool:
        """Stabilize owned provisional rows before a list exposes their IDs."""

        if not version_ids:
            return False
        provisional_ids = tuple(
            await self.session.scalars(
                select(ReadingJobRecord.reading_version_id).where(
                    ReadingJobRecord.reading_version_id.in_(version_ids),
                    ReadingJobRecord.status
                    == _ATOMIC_PROFILE_PREVIEW_CLAIM_JOB_STATUS,
                )
            )
        )
        for version_id in dict.fromkeys(provisional_ids):
            await self._stabilize_atomic_profile_preview_claim_for_read(version_id)
        return bool(provisional_ids)

    async def _load_stabilized_owned_version_for_ids(
        self,
        version_id: UUID,
        *,
        user_id: UUID | None,
        guest_id: UUID | None,
    ) -> tuple[Any, Any]:
        """Verify ownership before any provisional-claim state transition."""

        try:
            await self.repository.load_owned_version(
                version_id,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
            )
        except LookupError as error:
            raise ReadingNotFoundError("Reading Version not found") from error
        await self._stabilize_atomic_profile_preview_claim_for_read(version_id)
        try:
            return await self.repository.load_owned_version(
                version_id,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
            )
        except LookupError as error:
            raise ReadingNotFoundError("Reading Version not found") from error

    async def _load_stabilized_owned_version(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> tuple[Any, Any]:
        user_id, guest_id = owner_ids(owner)
        return await self._load_stabilized_owned_version_for_ids(
            version_id,
            user_id=user_id,
            guest_id=guest_id,
        )

    async def _load_atomic_profile_preview_claim(
        self,
        version_id: UUID,
    ) -> tuple[Any, ReadingVersion, ReadingJobRecord]:
        root, version, job = await self.repository.load_start_claim(version_id)
        await self.session.refresh(version)
        await self.session.refresh(job)
        return root, version, job

    async def discard_confirm_profile_preview_claim(
        self,
        idempotency: IdempotencyContext,
    ) -> bool:
        """Delete this request's untouched claim after losing Profile confirmation."""

        claim = self._atomic_profile_preview_claim
        if claim is None or claim.context != idempotency:
            return False
        try:
            root, version, job = await self._load_atomic_profile_preview_claim(
                claim.reading_version_id
            )
        except LookupError:
            self._atomic_profile_preview_claim = None
            return False
        if (
            root.profile_version_id is not None
            or version.status != ReadingStatus.INPUT_READY.value
            or job.status != _ATOMIC_PROFILE_PREVIEW_CLAIM_JOB_STATUS
            or job.lease_token != claim.lease_token
        ):
            return False
        if (
            job.lease_generation
            >= _ATOMIC_PROFILE_PREVIEW_CLAIM_EXPOSED_GENERATION
        ):
            self._rearm_atomic_profile_preview_claim(
                version,
                job,
                initial_job_status="queued",
            )
            await self.repository.record_terminal_stopped(
                str(job.id),
                Stopped(
                    reason="error",
                    public_copy="档案确认未完成，本次排盘已终止。",
                ),
                datetime.now(UTC),
            )
            await self.session.commit()
            self._atomic_profile_preview_claim = None
            return False
        await self.repository.delete_start_claim(claim.reading_version_id)
        await self.session.commit()
        self._atomic_profile_preview_claim = None
        return True

    @staticmethod
    def _compile_profile_preview_prepare(
        profile: ConfirmedProfileVersion,
        *,
        query: str,
        dimension_ids: Sequence[str],
        target_year: int | None,
        target_month: str | None,
        target_date: date | None,
        default_preview_year: int | None = None,
    ) -> Prepare:
        resolved_dimensions = tuple(dimension_ids)
        if target_year is None and target_month is None and target_date is None:
            return compile_bazi_year_prepare(
                action="bazi_year_preview",
                query=query,
                profile=profile,
                year=(
                    default_preview_year
                    if default_preview_year is not None
                    else _profile_default_preview_year(profile)
                ),
                dimension_ids=resolved_dimensions,
            )
        if target_year is not None:
            return compile_bazi_year_prepare(
                action="bazi_year_preview",
                query=query,
                profile=profile,
                year=target_year,
                dimension_ids=resolved_dimensions,
            )
        if target_month is not None:
            return compile_bazi_month_prepare(
                action="bazi_month_preview",
                query=query,
                profile=profile,
                month=target_month,
                dimension_ids=resolved_dimensions,
            )
        assert target_date is not None
        return compile_bazi_day_prepare(
            action="bazi_day_preview",
            query=query,
            profile=profile,
            target_date=target_date,
            dimension_ids=resolved_dimensions,
        )

    async def start_preview(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
        target_year: int | None = None,
        target_month: str | None = None,
        target_date: date | None = None,
        idempotency_context: IdempotencyContext | None = None,
        rollback_on_failure: bool = False,
    ) -> tuple[ReadingStartResponse, bool]:
        target_count = sum(
            value is not None for value in (target_year, target_month, target_date)
        )
        if target_count > 1:
            raise RequestCompilationError("Bazi time targets are mutually exclusive")
        action = (
            "bazi_year_preview"
            if target_year is not None
            else "bazi_month_preview"
            if target_month is not None
            else "bazi_day_preview"
            if target_date is not None
            else "profile_preview"
        )
        resolved_query = query or DEFAULT_QUERIES[action]
        resolved_dimensions = list(dimension_ids or ("career",))
        idempotency = idempotency_context or self._idempotency_context(
            idempotency_key,
            action=action,
            payload={
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "target_year": target_year,
                "target_month": target_month,
                "target_date": target_date.isoformat() if target_date else None,
            },
        )
        claim = self._atomic_profile_preview_claim
        owns_claim = claim is not None and claim.context == idempotency
        if not owns_claim:
            replayed = await self._replay_idempotency(owner, idempotency)
            if replayed is not None:
                return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = self._compile_profile_preview_prepare(
            profile,
            query=resolved_query,
            dimension_ids=resolved_dimensions,
            target_year=target_year,
            target_month=target_month,
            target_date=target_date,
            default_preview_year=(
                claim.default_preview_year if owns_claim and claim is not None else None
            ),
        )
        if owns_claim and rollback_on_failure:
            assert claim is not None
            async with self._hold_atomic_profile_preview_winner_fence(
                claim.context.key_hash
            ):
                return await self._persist_start(
                    owner,
                    prepare,
                    capability_id="bazi",
                    profile_version_id=profile_version_id,
                    idempotency=idempotency,
                    direct_chart=True,
                    rollback_on_failure=rollback_on_failure,
                )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="bazi",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
            direct_chart=True,
            rollback_on_failure=rollback_on_failure,
        )

    async def start_bazi_deep(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        query: str | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        """Create a paid Bazi deep-read Job that waits for fulfillment binding."""

        if owner.kind != "user":
            raise PaidReadingNotGrantedError(
                "Paid reading not granted",
                detail="Paid deep reads cannot be created for a guest owner.",
                code="paid_reading_requires_account",
            )
        await self._require_paid_action(owner, action="bazi_deep")
        resolved_query = query or DEFAULT_QUERIES["bazi_deep"]
        idempotency = self._idempotency_context(
            idempotency_key,
            action="bazi_deep",
            payload={
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
                "dimension_ids": ["career"],
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = compile_bazi_prepare(
            action="bazi_deep",
            query=resolved_query,
            profile=profile,
            dimension_ids=("career",),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="bazi",
            product_id="bazi-deep",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
            initial_job_status="awaiting_fulfillment",
        )

    async def bind_paid_fulfillment(
        self,
        owner: OwnerProtocol,
        *,
        reading_version_id: UUID,
        payment_id: UUID,
        idempotency_key: str,
    ) -> FulfillmentBindingResult:
        """Reserve one verified payment and bind it to an owned Reading Job.

        The payment is checked against the authenticated User before the
        commerce transition so a caller cannot probe or reserve another
        owner's entitlement. Commerce remains the authority for ledger
        idempotency and ProductVersion snapshotting.
        """
        if owner.kind != "user":
            raise PaidReadingNotGrantedError(
                "Paid fulfillment requires a signed-in account",
                detail="Guest readings cannot bind a paid entitlement.",
            )
        if not idempotency_key.strip():
            raise InvalidReadingInputError("Fulfillment Idempotency-Key is required")

        try:
            root, version = await self.repository.load_owned_version(
                reading_version_id,
                owner_user_id=owner.id,
                owner_guest_session_id=None,
            )
        except LookupError as error:
            raise ReadingNotFoundError("Reading Version not found") from error

        job = await self.session.scalar(
            select(ReadingJobRecord)
            .where(ReadingJobRecord.reading_version_id == version.id)
            .order_by(ReadingJobRecord.created_at.desc(), ReadingJobRecord.id.desc())
        )
        if job is None:
            raise ReadingNotFoundError("Reading Job not found")

        payment = await self.session.scalar(
            select(Payment)
            .join(Order, Order.id == Payment.order_id)
            .where(Payment.id == payment_id, Order.owner_user_id == owner.id)
        )
        if payment is None:
            raise ReadingNotFoundError("Payment not found")

        order = await self.session.get(Order, payment.order_id)
        if order is None:
            raise ReadingFulfillmentUnavailableError(
                "Paid fulfillment cannot bind to this Reading Job"
            )
        await self._validate_paid_target(root, version, order)
        if job.status in {"failed", "canceled", "stopped", "runtime_unknown"}:
            already_bound = await self.session.scalar(
                select(FulfillmentRecord).where(
                    FulfillmentRecord.reading_job_ref == str(job.id)
                )
            )
            if already_bound is None or already_bound.payment_id != payment.id:
                raise ReadingFulfillmentUnavailableError(
                    "Paid fulfillment cannot bind to a terminal Reading Job"
                )
            return FulfillmentBindingResult(
                fulfillment_id=already_bound.id,
                reading_version_id=version.id,
                reading_job_id=job.id,
                status=already_bound.status,
                created=False,
            )

        commerce = CommerceService(self.session)
        try:
            fulfillment, reserved_created = await commerce.reserve_fulfillment(
                payment_id=payment.id,
                idempotency_key=idempotency_key,
            )
            fulfillment, bound_created = await commerce.bind_fulfillment_job(
                fulfillment_id=fulfillment.id,
                reading_version_ref=str(version.id),
                reading_job_ref=str(job.id),
            )
        except CommerceError as error:
            raise ReadingFulfillmentUnavailableError(
                "Paid fulfillment cannot bind to this Reading Job"
            ) from error

        # A paid deep-read is deliberately invisible to the Worker until the
        # ProductVersion snapshot is fixed by Commerce above.
        if job.status == "awaiting_fulfillment":
            job.status = "queued"
            job.available_at = datetime.now(UTC)
            await self.session.flush()

        return FulfillmentBindingResult(
            fulfillment_id=fulfillment.id,
            reading_version_id=version.id,
            reading_job_id=job.id,
            status=fulfillment.status,
            created=reserved_created or bound_created,
        )

    async def _validate_paid_target(
        self,
        root: Any,
        version: Any,
        order: Order,
    ) -> None:
        """Fail closed when a paid order is not for this deep-read root.

        The bazi-deep catalog family and the Reading Root are the two stable
        identities available to this binding API.  An arbitrary confirmed
        Payment must not unlock another product or another user's/root's
        reading merely because the owner id matches.
        """
        if version.product_id != "bazi-deep":
            return
        if root.product_id != "bazi-deep":
            raise ReadingFulfillmentUnavailableError(
                "Paid fulfillment target is not a Bazi deep read"
            )
        if order.purchase_target_ref != str(root.id):
            raise ReadingFulfillmentUnavailableError(
                "Paid order target does not match the Reading Root"
            )
        product = await self.session.get(ProductVersion, order.product_version_id)
        if product is None:
            raise ReadingFulfillmentUnavailableError(
                "Paid order product version is unavailable"
            )
        family = await self.session.get(ProductFamily, product.family_id)
        if family is None or family.key != BAZI_DEEP_PRODUCT_FAMILY_KEY:
            raise ReadingFulfillmentUnavailableError(
                "Paid order product is not the Bazi deep ProductFamily"
            )
        if root.product_version_snapshot_id not in {None, product.id}:
            raise ReadingFulfillmentUnavailableError(
                "Reading Root ProductVersion snapshot is immutable"
            )

    async def start_five_elements_facts(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["five_elements_facts_preview"]
        resolved_dimensions = list(dimension_ids or ("state",))
        idempotency = self._idempotency_context(
            idempotency_key,
            action="five_elements_facts_preview",
            payload={
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = compile_five_elements_facts_prepare(
            action="five_elements_facts_preview",
            query=resolved_query,
            profile=profile,
            dimension_ids=tuple(resolved_dimensions),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="bazi",
            product_id="five-elements-facts",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
        )

    async def start_time_check(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        time_range_start: str,
        time_range_end: str,
        known_events: Sequence[str],
        known_event_facts: Sequence[Mapping[str, Any]] = (),
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["time_check_preview"]
        resolved_dimensions = list(dimension_ids or ("time_options",))
        resolved_events = list(known_events)
        resolved_event_facts = [dict(event) for event in known_event_facts]
        idempotency = self._idempotency_context(
            idempotency_key,
            action="time_check_preview",
            payload={
                "profile_version_id": str(profile_version_id),
                "time_range_start": time_range_start,
                "time_range_end": time_range_end,
                "known_events": resolved_events,
                "known_event_facts": resolved_event_facts,
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = compile_time_check_prepare(
            action="time_check_preview",
            query=resolved_query,
            profile=profile,
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            known_events=tuple(resolved_events),
            known_event_facts=tuple(resolved_event_facts),
            dimension_ids=tuple(resolved_dimensions),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="time-check",
            product_id="time-check",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
        )

    async def start_hecan(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        selected_art_ids: Sequence[str],
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_dimensions = list(dimension_ids or ("career",))
        resolved_arts = list(selected_art_ids)
        idempotency = self._idempotency_context(
            idempotency_key,
            action="hecan_preview",
            payload={
                "profile_version_id": str(profile_version_id),
                "selected_art_ids": resolved_arts,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = compile_hecan_prepare(
            action="hecan_preview",
            query=DEFAULT_QUERIES["hecan_preview"],
            profile=profile,
            selected_art_ids=tuple(resolved_arts),
            dimension_ids=tuple(resolved_dimensions),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="bazi",
            product_id="hecan",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
        )

    async def start_canwen(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        selected_art_ids: Sequence[str],
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["canwen_preview"]
        resolved_dimensions = list(dimension_ids or ("career",))
        resolved_arts = list(selected_art_ids)
        idempotency = self._idempotency_context(
            idempotency_key,
            action="canwen_preview",
            payload={
                "profile_version_id": str(profile_version_id),
                "selected_art_ids": resolved_arts,
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = compile_canwen_prepare(
            action="canwen_preview",
            query=resolved_query,
            profile=profile,
            selected_art_ids=tuple(resolved_arts),
            dimension_ids=tuple(resolved_dimensions),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="bazi",
            product_id="canwen",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
        )

    async def start_chart_similarity(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_ids: Sequence[UUID],
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_ids = tuple(profile_version_ids)
        if len(resolved_ids) != 2 or len(set(resolved_ids)) != 2:
            raise InvalidReadingInputError(
                "chart similarity requires two distinct profiles"
            )
        resolved_query = query or DEFAULT_QUERIES["chart_similarity_preview"]
        resolved_dimensions = tuple(dimension_ids or ("state",))
        idempotency = self._idempotency_context(
            idempotency_key,
            action="chart_similarity_preview",
            payload={
                "profile_version_ids": [str(value) for value in resolved_ids],
                "query": resolved_query,
                "dimension_ids": list(resolved_dimensions),
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        try:
            owned_versions = (
                await self.profiles.get_owned_profile_version(owner, resolved_ids[0]),
                await self.profiles.get_owned_profile_version(owner, resolved_ids[1]),
            )
        except LookupError as error:
            raise ProfileVersionNotOwnedError("Profile Version not found") from error
        if owned_versions[0][0].id == owned_versions[1][0].id:
            raise InvalidReadingInputError(
                "chart similarity requires two distinct SubjectProfiles"
            )
        profiles = (
            await self._confirmed_profile_from_version(owned_versions[0][1]),
            await self._confirmed_profile_from_version(owned_versions[1][1]),
        )
        prepare = compile_chart_similarity_prepare(
            action="chart_similarity_preview",
            query=resolved_query,
            profiles=profiles,
            dimension_ids=resolved_dimensions,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="bazi",
            product_id="chart-similarity",
            profile_version_id=resolved_ids[0],
            profile_version_ids=resolved_ids,
            idempotency=idempotency,
        )

    async def start_relationship(
        self,
        owner: OwnerProtocol,
        *,
        product_id: str,
        profile_version_ids: Sequence[UUID],
        relationship_type: str,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        product_config: dict[str, tuple[str, str, str]] = {
            "bazi-relationship": ("bazi_relationship_preview", "bazi", "bazi"),
            "ziwei-relationship": ("ziwei_relationship_preview", "ziwei", "ziwei"),
            "qizheng-relationship": (
                "qizheng_relationship_preview",
                "qizheng",
                "xingming",
            ),
        }
        try:
            action, art_id, capability_id = product_config[product_id]
        except KeyError as error:
            raise ReadingServiceError(
                f"unsupported relationship product: {product_id!r}"
            ) from error
        resolved_ids = tuple(profile_version_ids)
        if len(resolved_ids) != 2 or len(set(resolved_ids)) != 2:
            raise InvalidReadingInputError("relationship requires two distinct profiles")
        resolved_dimensions = tuple(dimension_ids or ("relationship",))
        if relationship_type not in {
            "romantic",
            "married",
            "parent_child",
            "business",
            "work",
            "friend",
        }:
            raise InvalidReadingInputError("unsupported relationship type")
        idempotency = self._idempotency_context(
            idempotency_key,
            action=action,
            payload={
                "product_id": product_id,
                "profile_version_ids": [str(value) for value in resolved_ids],
                "relationship_type": relationship_type,
                "dimension_ids": list(resolved_dimensions),
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        try:
            owned_versions = (
                await self.profiles.get_owned_profile_version(owner, resolved_ids[0]),
                await self.profiles.get_owned_profile_version(owner, resolved_ids[1]),
            )
        except LookupError as error:
            raise ProfileVersionNotOwnedError("Profile Version not found") from error
        if owned_versions[0][0].id == owned_versions[1][0].id:
            raise InvalidReadingInputError(
                "relationship requires two distinct SubjectProfiles"
            )
        profiles = (
            await self._confirmed_profile_from_version(owned_versions[0][1]),
            await self._confirmed_profile_from_version(owned_versions[1][1]),
        )
        prepare = compile_relationship_prepare(
            action=action,
            query=DEFAULT_QUERIES[action],
            art_id=cast(RelationshipArt, art_id),
            relationship_type=cast(RelationshipType, relationship_type),
            profiles=profiles,
            dimension_ids=resolved_dimensions,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id=capability_id,
            product_id=product_id,
            profile_version_id=resolved_ids[0],
            profile_version_ids=resolved_ids,
            relationship_type=relationship_type,
            idempotency=idempotency,
        )

    async def start_fortune(
        self,
        owner: OwnerProtocol,
        *,
        action: str,
        profile_version_id: UUID,
        query: str | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        if action not in {"today", "near_seven"}:
            raise ReadingServiceError(f"unsupported fortune action: {action!r}")
        resolved_query = query or DEFAULT_QUERIES[action]
        idempotency = self._idempotency_context(
            idempotency_key,
            action=action,
            payload={
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        await self._require_paid_action(owner, action=action)
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = compile_fortune_prepare(
            action=action,
            query=resolved_query,
            profile=profile,
            server_reference_datetime=datetime.now(UTC),
            dimension_ids=("career",),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="fortune",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
        )

    async def start_ziwei(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
        target_year: int | None = None,
        target_month: str | None = None,
        target_date: date | None = None,
    ) -> tuple[ReadingStartResponse, bool]:
        target_count = sum(
            value is not None for value in (target_year, target_month, target_date)
        )
        if target_count > 1:
            raise RequestCompilationError("Ziwei time targets are mutually exclusive")
        if target_date is not None:
            raise RequestCompilationError(
                "Ziwei supports target_year or target_month, not target_date"
            )
        action = (
            "ziwei_year_preview"
            if target_year is not None
            else "ziwei_month_preview"
            if target_month is not None
            else "ziwei_preview"
        )
        resolved_query = query or DEFAULT_QUERIES[action]
        resolved_dimensions = list(dimension_ids or ("career",))
        idempotency = self._idempotency_context(
            idempotency_key,
            action=action,
            payload={
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "target_year": target_year,
                "target_month": target_month,
                "target_date": None,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = self._compile_ziwei_preview_prepare(
            profile,
            query=resolved_query,
            dimension_ids=resolved_dimensions,
            target_year=target_year,
            target_month=target_month,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="ziwei",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
            direct_chart=True,
        )

    @staticmethod
    def _compile_ziwei_preview_prepare(
        profile: ConfirmedProfileVersion,
        *,
        query: str,
        dimension_ids: Sequence[str],
        target_year: int | None,
        target_month: str | None,
        default_preview_year: int | None = None,
    ) -> Prepare:
        resolved_dimensions = tuple(dimension_ids)
        if target_year is None and target_month is None:
            return compile_ziwei_year_prepare(
                action="ziwei_year_preview",
                query=query,
                profile=profile,
                year=(
                    default_preview_year
                    if default_preview_year is not None
                    else _profile_default_preview_year(profile)
                ),
                dimension_ids=resolved_dimensions,
            )
        if target_year is not None:
            return compile_ziwei_year_prepare(
                action="ziwei_year_preview",
                query=query,
                profile=profile,
                year=target_year,
                dimension_ids=resolved_dimensions,
            )
        assert target_month is not None
        return compile_ziwei_month_prepare(
            action="ziwei_month_preview",
            query=query,
            profile=profile,
            month=target_month,
            dimension_ids=resolved_dimensions,
        )

    async def start_qizheng(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
        target_year: int | None = None,
        target_month: str | None = None,
        target_date: date | None = None,
    ) -> tuple[ReadingStartResponse, bool]:
        target_count = sum(
            value is not None for value in (target_year, target_month, target_date)
        )
        if target_count > 1:
            raise RequestCompilationError("Qizheng time targets are mutually exclusive")
        action = (
            "qizheng_year_preview"
            if target_year is not None
            else "qizheng_month_preview"
            if target_month is not None
            else "qizheng_day_preview"
            if target_date is not None
            else "qizheng_preview"
        )
        resolved_query = query or DEFAULT_QUERIES[action]
        resolved_dimensions = list(dimension_ids or ("career",))
        idempotency = self._idempotency_context(
            idempotency_key,
            action=action,
            payload={
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "target_year": target_year,
                "target_month": target_month,
                "target_date": target_date.isoformat() if target_date else None,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        if target_year is None and target_month is None and target_date is None:
            prepare = compile_qizheng_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                dimension_ids=tuple(resolved_dimensions),
            )
        elif target_year is not None:
            prepare = compile_qizheng_year_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                year=target_year,
                dimension_ids=tuple(resolved_dimensions),
            )
        elif target_month is not None:
            prepare = compile_qizheng_month_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                month=target_month,
                dimension_ids=tuple(resolved_dimensions),
            )
        else:
            assert target_date is not None
            prepare = compile_qizheng_day_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                target_date=target_date,
                dimension_ids=tuple(resolved_dimensions),
            )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="xingming",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
        )

    async def start_luming_nayin(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["luming_nayin_preview"]
        resolved_dimensions = list(dimension_ids or ("state", "career"))
        idempotency = self._idempotency_context(
            idempotency_key,
            action="luming_nayin_preview",
            payload={
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = compile_luming_nayin_prepare(
            action="luming_nayin_preview",
            query=resolved_query,
            profile=profile,
            dimension_ids=tuple(resolved_dimensions),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="luming-nayin",
            product_id="luming-nayin",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
        )

    async def start_rhythm(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        """Start the public rhythm tool as a bounded Nayin fact projection.

        The tool deliberately shares the installed Luming/Nayin Provider.  A
        separate product identity lets the result and audit trail say which
        tool was requested without inventing a second algorithm or allowing a
        browser-side sound interpretation.
        """

        resolved_query = query or DEFAULT_QUERIES["rhythm_preview"]
        resolved_dimensions = list(dimension_ids or ("state",))
        idempotency = self._idempotency_context(
            idempotency_key,
            action="rhythm_preview",
            payload={
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        prepare = compile_luming_nayin_prepare(
            action="rhythm_preview",
            query=resolved_query,
            profile=profile,
            dimension_ids=tuple(resolved_dimensions),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="luming-nayin",
            product_id="rhythm",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
        )

    async def start_taiyi(
        self,
        owner: OwnerProtocol,
        *,
        reference_datetime: datetime,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        time_basis_policy: str,
        zi_hour_policy: str,
        longitude: float | None,
        latitude: float | None,
        coordinate_source: str | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["taiyi_preview"]
        resolved_dimensions = list(dimension_ids or ("outcome", "timing"))
        resolved_subject_ref = subject_ref or f"taiyi:{uuid4().hex}"
        idempotency = self._idempotency_context(
            idempotency_key,
            action="taiyi_preview",
            payload={
                "reference_datetime": reference_datetime.isoformat(),
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "time_basis_policy": time_basis_policy,
                "zi_hour_policy": zi_hour_policy,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        prepare = compile_taiyi_prepare(
            action="taiyi_preview",
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            reference_datetime=reference_datetime,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=tuple(resolved_dimensions),
            time_basis_policy=time_basis_policy,
            zi_hour_policy=zi_hour_policy,
            longitude=longitude,
            latitude=latitude,
            coordinate_source=coordinate_source,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="taiyi",
            product_id="taiyi",
            profile_version_id=None,
            idempotency=idempotency,
        )

    async def start_selection(
        self,
        owner: OwnerProtocol,
        *,
        event_profile: str,
        requested_actions: Sequence[str],
        date_range_start: str,
        date_range_end: str,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        requested_scopes: Sequence[str],
        hard_constraints: Mapping[str, object],
        participant_facts: Sequence[Mapping[str, object]],
        directional_context: Mapping[str, str] | None,
        include_folk_comparison: bool,
        longitude: float | None,
        latitude: float | None,
        coordinate_source: str | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["selection_preview"]
        resolved_dimensions = list(dimension_ids or ("timing", "state"))
        resolved_subject_ref = subject_ref or f"selection:{uuid4().hex}"
        idempotency = self._idempotency_context(
            idempotency_key,
            action="selection_preview",
            payload={
                "event_profile": event_profile,
                "requested_actions": list(requested_actions),
                "date_range_start": date_range_start,
                "date_range_end": date_range_end,
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "requested_scopes": list(requested_scopes),
                "hard_constraints": dict(hard_constraints),
                "participant_facts": [dict(item) for item in participant_facts],
                "directional_context": (
                    dict(directional_context) if directional_context is not None else None
                ),
                "include_folk_comparison": include_folk_comparison,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        prepare = compile_selection_prepare(
            action="selection_preview",
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            event_profile=event_profile,
            requested_actions=tuple(requested_actions),
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=tuple(resolved_dimensions),
            requested_scopes=tuple(requested_scopes),
            hard_constraints=hard_constraints,
            participant_facts=tuple(participant_facts),
            directional_context=directional_context,
            include_folk_comparison=include_folk_comparison,
            longitude=longitude,
            latitude=latitude,
            coordinate_source=coordinate_source,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="selection",
            product_id="selection",
            profile_version_id=None,
            idempotency=idempotency,
        )

    async def start_fengshui(
        self,
        owner: OwnerProtocol,
        *,
        subject_ref: str | None,
        fengshui_spec: Mapping[str, object],
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["fengshui_preview"]
        resolved_dimensions = list(dimension_ids or ("current_state", "direction"))
        resolved_subject_ref = subject_ref or f"fengshui:{uuid4().hex}"
        idempotency = self._idempotency_context(
            idempotency_key,
            action="fengshui_preview",
            payload={
                "subject_ref": subject_ref,
                "fengshui_spec": dict(fengshui_spec),
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        prepare = compile_fengshui_prepare(
            action="fengshui_preview",
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            fengshui_spec=fengshui_spec,
            dimension_ids=tuple(resolved_dimensions),
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="fengshui",
            product_id="fengshui",
            profile_version_id=None,
            idempotency=idempotency,
        )

    async def start_liuyao(
        self,
        owner: OwnerProtocol,
        *,
        cast: tuple[int, ...] | str,
        event_datetime: datetime,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        question_class: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["liuyao_one_question"]
        resolved_dimensions = list(dimension_ids or ("career",))
        idempotency = self._idempotency_context(
            idempotency_key,
            action="liuyao_one_question",
            payload={
                "cast": list(cast) if isinstance(cast, tuple) else cast,
                "event_datetime": event_datetime.isoformat(),
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "question_class": question_class,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        resolved_subject_ref = subject_ref or f"liuyao:{uuid4().hex}"
        prepare = compile_liuyao_prepare(
            action="liuyao_one_question",
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            cast=cast,
            event_datetime=event_datetime,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=tuple(resolved_dimensions),
            question_class=question_class,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="liuyao",
            profile_version_id=None,
            idempotency=idempotency,
            direct_chart=True,
        )

    async def start_liuyao_deep(
        self,
        owner: OwnerProtocol,
        *,
        cast: tuple[int, ...] | str,
        event_datetime: datetime,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        question_class: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        """Create a paid Liuyao evidence-read Job awaiting fulfillment binding."""

        await self._require_paid_action(owner, action="liuyao_deep")
        resolved_query = query or DEFAULT_QUERIES["liuyao_deep"]
        resolved_dimensions = ("outcome", "timing", "state")
        requested_dimensions = tuple(
            dict.fromkeys(str(item) for item in (dimension_ids or ()))
        )
        if requested_dimensions and requested_dimensions != resolved_dimensions:
            raise InvalidReadingInputError(
                "Liuyao deep dimensions are fixed to outcome, timing, and state"
            )
        resolved_subject_ref = subject_ref or f"liuyao:{uuid4().hex}"
        idempotency = self._idempotency_context(
            idempotency_key,
            action="liuyao_deep",
            payload={
                "cast": list(cast) if isinstance(cast, tuple) else cast,
                "event_datetime": event_datetime.isoformat(),
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "question_class": question_class,
                "dimension_ids": list(resolved_dimensions),
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        prepare = compile_liuyao_prepare(
            action="liuyao_deep",
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            cast=cast,
            event_datetime=event_datetime,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=resolved_dimensions,
            question_class=question_class,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="liuyao",
            product_id="liuyao-deep",
            profile_version_id=None,
            idempotency=idempotency,
            initial_job_status="awaiting_fulfillment",
        )

    async def start_wenshi(
        self,
        owner: OwnerProtocol,
        *,
        cast: tuple[int, ...] | str,
        event_datetime: datetime,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        time_basis_policy: str,
        zi_hour_policy: str,
        longitude: float | None,
        latitude: float | None,
        coordinate_source: str | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["wenshi_one_question"]
        resolved_dimensions = list(dimension_ids or ("outcome", "timing"))
        resolved_subject_ref = subject_ref or f"wenshi:{uuid4().hex}"
        idempotency = self._idempotency_context(
            idempotency_key,
            action="wenshi_one_question",
            payload={
                "cast": list(cast) if isinstance(cast, tuple) else cast,
                "event_datetime": event_datetime.isoformat(),
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "time_basis_policy": time_basis_policy,
                "zi_hour_policy": zi_hour_policy,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        await self._require_paid_action(owner, action="wenshi_one_question")
        prepare = compile_wenshi_prepare(
            action="wenshi_one_question",
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            cast=cast,
            event_datetime=event_datetime,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=tuple(resolved_dimensions),
            time_basis_policy=time_basis_policy,
            zi_hour_policy=zi_hour_policy,
            longitude=longitude,
            latitude=latitude,
            coordinate_source=coordinate_source,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="liuyao",
            product_id="wenshi",
            runtime_capability_ids=("liuyao", "qimen", "liuren"),
            profile_version_id=None,
            idempotency=idempotency,
        )

    async def start_qimen(
        self,
        owner: OwnerProtocol,
        *,
        event_datetime: datetime,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        time_basis_policy: str,
        zi_hour_policy: str,
        longitude: float | None,
        latitude: float | None,
        coordinate_source: str | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["qimen_one_question"]
        resolved_dimensions = list(dimension_ids or ("outcome", "timing"))
        resolved_subject_ref = subject_ref or f"qimen:{uuid4().hex}"
        idempotency = self._idempotency_context(
            idempotency_key,
            action="qimen_one_question",
            payload={
                "event_datetime": event_datetime.isoformat(),
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "time_basis_policy": time_basis_policy,
                "zi_hour_policy": zi_hour_policy,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        prepare = compile_qimen_prepare(
            action="qimen_one_question",
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            event_datetime=event_datetime,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=tuple(resolved_dimensions),
            time_basis_policy=time_basis_policy,
            zi_hour_policy=zi_hour_policy,
            longitude=longitude,
            latitude=latitude,
            coordinate_source=coordinate_source,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="qimen",
            profile_version_id=None,
            idempotency=idempotency,
        )

    async def start_qimen_deep(
        self,
        owner: OwnerProtocol,
        *,
        event_datetime: datetime,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        time_basis_policy: str,
        zi_hour_policy: str,
        longitude: float | None,
        latitude: float | None,
        coordinate_source: str | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        """Create a paid Qimen deep-read Job after the board facts are frozen."""

        await self._require_paid_action(owner, action="qimen_deep")
        resolved_query = query or DEFAULT_QUERIES["qimen_deep"]
        resolved_dimensions = ("outcome", "timing", "state")
        requested_dimensions = tuple(
            dict.fromkeys(str(item) for item in (dimension_ids or ()))
        )
        if requested_dimensions and requested_dimensions != resolved_dimensions:
            raise InvalidReadingInputError(
                "qimen deep dimensions are fixed to outcome, timing, and state"
            )
        resolved_subject_ref = subject_ref or f"qimen:{uuid4().hex}"
        idempotency = self._idempotency_context(
            idempotency_key,
            action="qimen_deep",
            payload={
                "event_datetime": event_datetime.isoformat(),
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "dimension_ids": list(resolved_dimensions),
                "time_basis_policy": time_basis_policy,
                "zi_hour_policy": zi_hour_policy,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        prepare = compile_qimen_prepare(
            action="qimen_deep",
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            event_datetime=event_datetime,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=resolved_dimensions,
            time_basis_policy=time_basis_policy,
            zi_hour_policy=zi_hour_policy,
            longitude=longitude,
            latitude=latitude,
            coordinate_source=coordinate_source,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="qimen",
            product_id="qimen-deep",
            profile_version_id=None,
            idempotency=idempotency,
            initial_job_status="awaiting_fulfillment",
        )

    async def start_liuren(
        self,
        owner: OwnerProtocol,
        *,
        event_datetime: datetime,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        time_basis_policy: str,
        zi_hour_policy: str,
        longitude: float | None,
        latitude: float | None,
        coordinate_source: str | None,
        timing_start: date | None,
        timing_end: date | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["liuren_one_question"]
        resolved_dimensions = list(dimension_ids or ("outcome",))
        action = (
            "liuren_timing_question"
            if timing_start is not None and timing_end is not None
            else "liuren_one_question"
        )
        resolved_subject_ref = subject_ref or f"liuren:{uuid4().hex}"
        idempotency = self._idempotency_context(
            idempotency_key,
            action=action,
            payload={
                "event_datetime": event_datetime.isoformat(),
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "time_basis_policy": time_basis_policy,
                "zi_hour_policy": zi_hour_policy,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
                "timing_start": timing_start.isoformat() if timing_start else None,
                "timing_end": timing_end.isoformat() if timing_end else None,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        prepare = compile_liuren_prepare(
            action=action,
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            event_datetime=event_datetime,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=tuple(resolved_dimensions),
            time_basis_policy=time_basis_policy,
            zi_hour_policy=zi_hour_policy,
            longitude=longitude,
            latitude=latitude,
            coordinate_source=coordinate_source,
            timing_start=timing_start,
            timing_end=timing_end,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="liuren",
            profile_version_id=None,
            idempotency=idempotency,
            direct_chart=True,
        )

    async def start_meihua(
        self,
        owner: OwnerProtocol,
        *,
        casting_method: str,
        event_datetime: datetime,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        time_basis_policy: str,
        zi_hour_policy: str,
        longitude: float | None,
        latitude: float | None,
        coordinate_source: str | None,
        number: int | None,
        count: int | None,
        upper_trigram: str | None,
        lower_trigram: str | None,
        moving_line: int | None,
        provenance: Mapping[str, object] | None,
        observation_source: Mapping[str, object] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["meihua_preview"]
        resolved_dimensions = list(dimension_ids or ("outcome", "state"))
        resolved_subject_ref = subject_ref or f"meihua:{uuid4().hex}"
        idempotency = self._idempotency_context(
            idempotency_key,
            action="meihua_preview",
            payload={
                "casting_method": casting_method,
                "event_datetime": event_datetime.isoformat(),
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "time_basis_policy": time_basis_policy,
                "zi_hour_policy": zi_hour_policy,
                "longitude": longitude,
                "latitude": latitude,
                "coordinate_source": coordinate_source,
                "number": number,
                "count": count,
                "upper_trigram": upper_trigram,
                "lower_trigram": lower_trigram,
                "moving_line": moving_line,
                "provenance": dict(provenance) if provenance is not None else None,
                "observation_source": (
                    dict(observation_source) if observation_source is not None else None
                ),
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        prepare = compile_meihua_prepare(
            action="meihua_preview",
            query=resolved_query,
            subject_ref=resolved_subject_ref,
            casting_method=casting_method,
            event_datetime=event_datetime,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=tuple(resolved_dimensions),
            time_basis_policy=time_basis_policy,
            zi_hour_policy=zi_hour_policy,
            longitude=longitude,
            latitude=latitude,
            coordinate_source=coordinate_source,
            number=number,
            count=count,
            upper_trigram=upper_trigram,
            lower_trigram=lower_trigram,
            moving_line=moving_line,
            provenance=provenance,
            observation_source=observation_source,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="meihua",
            profile_version_id=None,
            idempotency=idempotency,
            direct_chart=True,
        )

    async def start_physiognomy(
        self,
        owner: OwnerProtocol,
        *,
        asset_id: UUID,
        subject_ref: str,
        query: str | None,
        dimension_ids: Sequence[str],
        observations: Sequence[Mapping[str, object]],
        prepare: Prepare,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["physiognomy_preview"]
        resolved_dimensions = list(dimension_ids)
        idempotency = self._idempotency_context(
            idempotency_key,
            action="physiognomy_preview",
            payload={
                "asset_id": str(asset_id),
                "subject_ref": subject_ref,
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
                "observations": [dict(item) for item in observations],
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        return await self._persist_start(
            owner,
            prepare,
            capability_id="physiognomy",
            product_id="jianxiang",
            profile_version_id=None,
            idempotency=idempotency,
        )

    async def recast_profile(
        self,
        owner: OwnerProtocol,
        *,
        source_version_id: UUID,
        action: str,
        profile_version_id: UUID,
        query: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        compiler_action = "near_seven" if action == "week" else action
        resolved_query = query or DEFAULT_QUERIES.get(compiler_action)
        if resolved_query is None:
            raise ReadingServiceError(f"unsupported recast action: {action!r}")
        resolved_dimensions = list(dimension_ids or ("career",))
        idempotency = self._idempotency_context(
            idempotency_key,
            action="recast",
            payload={
                "source_version_id": str(source_version_id),
                "action": action,
                "profile_version_id": str(profile_version_id),
                "query": resolved_query,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        await self._require_accepted_source(owner, source_version_id)
        if action == "profile_preview":
            profile = await self._owned_confirmed_profile(
                owner,
                profile_version_id,
            )
            prepare = self._compile_profile_preview_prepare(
                profile,
                query=resolved_query,
                dimension_ids=tuple(resolved_dimensions),
                target_year=None,
                target_month=None,
                target_date=None,
            )
            capability_id = "bazi"
        elif action in {"today", "week"}:
            await self._require_paid_action(owner, action=compiler_action)
            prepare = compile_fortune_prepare(
                action=compiler_action,
                query=resolved_query,
                profile=await self._owned_confirmed_profile(owner, profile_version_id),
                server_reference_datetime=datetime.now(UTC),
                dimension_ids=tuple(resolved_dimensions),
            )
            capability_id = "fortune"
        else:
            raise ReadingServiceError(f"unsupported recast action: {action!r}")
        return await self._persist_start(
            owner,
            prepare,
            capability_id=capability_id,
            profile_version_id=profile_version_id,
            idempotency=idempotency,
            direct_chart=capability_id == "bazi",
        )

    async def recast_liuyao(
        self,
        owner: OwnerProtocol,
        *,
        source_version_id: UUID,
        cast: tuple[int, ...] | str,
        event_datetime: datetime,
        timezone: str,
        location: str,
        subject_ref: str | None,
        query: str | None,
        question_class: str | None,
        dimension_ids: Sequence[str] | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        resolved_query = query or DEFAULT_QUERIES["liuyao_one_question"]
        resolved_dimensions = list(dimension_ids or ("career",))
        idempotency = self._idempotency_context(
            idempotency_key,
            action="recast",
            payload={
                "source_version_id": str(source_version_id),
                "action": "liuyao_one_question",
                "cast": list(cast) if isinstance(cast, tuple) else cast,
                "event_datetime": event_datetime.isoformat(),
                "timezone": timezone,
                "location": location,
                "subject_ref": subject_ref,
                "query": resolved_query,
                "question_class": question_class,
                "dimension_ids": resolved_dimensions,
            },
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        await self._require_accepted_source(owner, source_version_id)
        prepare = compile_liuyao_prepare(
            action="liuyao_one_question",
            query=resolved_query,
            subject_ref=subject_ref or f"recast:liuyao:{uuid4().hex}",
            cast=cast,
            event_datetime=event_datetime,
            confirmed_timezone=timezone,
            location=location,
            dimension_ids=tuple(resolved_dimensions),
            question_class=question_class,
        )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="liuyao",
            profile_version_id=None,
            idempotency=idempotency,
            direct_chart=True,
        )

    async def supply_input(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        values: Mapping[str, Any],
    ) -> ReadingStartResponse:
        started_at = perf_counter()
        root, version = await self._load_owned_version(
            owner,
            version_id,
        )
        if version.status != ReadingStatus.WAITING_INPUT.value:
            raise ReadingNotWaitingInputError("Reading is not waiting for input")
        stopped = await self.repository.load_waiting_input(version_id)
        if stopped is None or stopped.input_request is None:
            raise ReadingNotWaitingInputError("Reading is not waiting for input")
        mapped_values = self._validate_input_values(stopped.input_request, values)
        prepare = await self.repository.load_prepare(version_id)
        state_token = await self.repository.load_state_token(version_id)
        new_prepare = Prepare(
            query=prepare.query,
            intent=prepare.intent,
            facts=_apply_runtime_inputs(prepare.facts, mapped_values),
            state_token=state_token,
            transition="correct",
        )
        try:
            job = await self.repository.replace_prepare(version_id, new_prepare)
        except ReadingJobAlreadyQueuedError as error:
            raise ReadingAlreadyQueuedError("Reading is already queued") from error
        except ValueError as error:
            raise ReadingNotWaitingInputError(
                "Reading is not waiting for input"
            ) from error
        product_id = version.product_id or root.product_id or root.capability_id
        if product_id in _DIRECT_CHART_PRODUCT_IDS:
            runtime_ms, persistence_ms = await self._run_chart_fast_path(
                job,
                version,
                product_id=product_id,
            )
            summary = await self._summary(root, version)
            summary.fast_path_timing = ChartFastPathTiming(
                queue_wait_ms=0,
                worker_pickup_ms=0,
                runtime_one_shot_ms=runtime_ms,
                db_persistence_ms=persistence_ms,
                total_ms=(perf_counter() - started_at) * 1000,
            )
            return summary
        return await self._summary(root, version)

    async def get_summary(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> ReadingStartResponse:
        root, version = await self._load_stabilized_owned_version(
            owner,
            version_id,
        )
        return await self._summary(root, version)

    async def list_summaries(
        self,
        owner: OwnerProtocol,
    ) -> list[ReadingVersionSummary]:
        """List the newest owned Reading Versions, newest first (max 50)."""
        user_id, guest_id = owner_ids(owner)
        rows = await self.repository.list_owned_versions(
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
            limit=READING_HISTORY_LIMIT,
        )
        if await self._stabilize_atomic_profile_preview_claims_for_list(
            tuple(version.id for _root, version in rows)
        ):
            rows = await self.repository.list_owned_versions(
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
                limit=READING_HISTORY_LIMIT,
            )
        return [await self._summary(root, version) for root, version in rows]

    async def get_latest_profile_reading(
        self,
        owner: OwnerProtocol,
        *,
        profile_id: UUID,
        product_id: str,
    ) -> LatestProfileReadingResponse:
        """Return the newest successful renderable result for an owned Profile."""

        user_id, guest_id = owner_ids(owner)
        profile = await self.profiles.repository.get_owned_profile(
            profile_id,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        if profile is None:
            raise ProfileNotOwnedError("Profile not found")
        rows = await self.repository.list_owned_profile_versions(
            profile.id,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        renderable_seen = False
        for root, version, matched_profile_version_id in rows:
            try:
                reading_status = ReadingStatus(version.status)
            except ValueError:
                continue
            if reading_status not in {
                ReadingStatus.PREPARED,
                ReadingStatus.ACCEPTED,
            }:
                continue
            try:
                summary = await self._summary(root, version)
            except (KeyError, TypeError, ValueError):
                continue
            if not summary.result_available:
                continue
            renderable_seen = True
            effective_product_id = version.product_id or root.product_id or root.capability_id
            if not _profile_product_matches(product_id, effective_product_id):
                continue
            return LatestProfileReadingResponse(
                profile_id=profile.id,
                profile_version_id=matched_profile_version_id,
                reading_root_id=summary.reading_root_id,
                reading_version_id=summary.reading_version_id,
                capability_id=summary.capability_id,
                product_id=product_id,
                status=summary.status,
                result_available=True,
                created_at=summary.created_at,
            )
        code = "unavailable_or_incompatible" if renderable_seen else "never_succeeded"
        raise ProfileReadingUnavailableError(code)

    async def list_account_history(self, user_id: UUID) -> AccountHistoryResponse:
        """Project owned Reading Roots with their public version summaries."""
        rows = await self.repository.list_owned_versions(
            owner_user_id=user_id,
            owner_guest_session_id=None,
            limit=READING_HISTORY_LIMIT,
        )
        if await self._stabilize_atomic_profile_preview_claims_for_list(
            tuple(version.id for _root, version in rows)
        ):
            rows = await self.repository.list_owned_versions(
                owner_user_id=user_id,
                owner_guest_session_id=None,
                limit=READING_HISTORY_LIMIT,
            )
        grouped: dict[UUID, AccountHistoryRootResponse] = {}
        for root, version in rows:
            history_root = grouped.get(root.id)
            if history_root is None:
                history_root = AccountHistoryRootResponse(
                    reading_root_id=root.id,
                    profile_version_id=root.profile_version_id,
                    capability_id=root.capability_id,
                    product_id=root.product_id or root.capability_id,
                    runtime_capability_ids=(
                        list(root.runtime_capability_ids)
                        if root.runtime_capability_ids
                        else [root.capability_id]
                    ),
                    created_at=root.created_at,
                    versions=[],
                )
                grouped[root.id] = history_root
            history_root.versions.append(
                AccountHistoryVersionSummary(
                    reading_version_id=version.id,
                    reading_root_id=root.id,
                    capability_id=version.capability_id,
                    product_id=version.product_id or root.product_id or root.capability_id,
                    runtime_capability_ids=(
                        list(version.runtime_capability_ids)
                        if version.runtime_capability_ids
                        else [version.capability_id]
                    ),
                    version=version.version,
                    status=ReadingStatus(version.status),
                    object_id=version.object_id,
                    dimension_ids=list(version.dimension_ids),
                    horizon=Horizon.model_validate(version.horizon),
                    created_at=version.created_at,
                )
            )

        roots = list(grouped.values())
        roots.sort(key=lambda item: (item.created_at, str(item.reading_root_id)), reverse=True)
        for history_root in roots:
            history_root.versions.sort(
                key=lambda item: (item.version, str(item.reading_version_id)),
                reverse=True,
            )
        return AccountHistoryResponse(roots=roots)

    async def get_result(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> ReadingResultResponse:
        root, version = await self._load_stabilized_owned_version(
            owner,
            version_id,
        )
        brief = await self.repository.load_fact_brief(version_id)
        accepted_copy = await self.repository.load_accepted_copy(version_id)
        document = await self.repository.load_reading_document(version_id)
        verification = await self.repository.load_verification(version_id)
        waiting = await self.repository.load_waiting_input(version_id)
        capability_projection = project_capability(
            capability_id=version.capability_id,
            product_id=version.product_id or root.product_id,
            release_root=self.settings.runtime_release_root,
            release_profile=self.settings.runtime_release_profile,
        )
        view_model = (
            None
            if brief is None
            else project_runtime_view_model(
                brief.to_dict(),
                product_id=version.product_id or root.product_id,
                relationship_type=version.relationship_type,
            )
        )
        status = ReadingStatus(version.status)
        job_status = (
            await self._latest_job_status(version.id)
            if status is ReadingStatus.PREPARED
            else None
        )
        result_available, poll_required, poll_after_seconds = self._poll_fields(
            status,
            view_model,
            job_status=job_status,
        )
        presentation = await project_owned_reading_presentation(
            brief=brief,
            view_model=view_model,
            document=document,
        )
        return ReadingResultResponse(
            reading_version_id=version.id,
            status=status,
            accepted_copy=_project_presented_accepted_copy(
                accepted_copy,
                source_document=document,
                presented_document=presentation.document,
            ),
            fact_panel=presentation.fact_panel,
            view_model=presentation.view_model,
            capability=CapabilityProjection(
                capability_id=capability_projection.capability_id,
                label=capability_projection.label,
                tier=capability_projection.tier,
                source_system=capability_projection.source_system,
                runtime_active_rule_count=capability_projection.runtime_active_rule_count,
                judgment_rule_count=capability_projection.judgment_rule_count,
                source_status=capability_projection.source_status,
                user_decision_pending=capability_projection.user_decision_pending,
            ),
            verification=(
                None
                if verification is None
                else _verification_summary(verification)
            ),
            input_request=(
                None if waiting is None else _public_json(waiting.input_request)
            ),
            document=presentation.document,
            result_available=result_available,
            poll_required=poll_required,
            poll_after_seconds=poll_after_seconds,
            time_layer_entitlement=TimeLayerEntitlementResponse.from_contract(
                presentation.time_layer_entitlement
            ),
        )

    async def submit_verification(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        outcome: str,
        note: str | None,
    ) -> tuple[ReadingVerificationSummary, bool]:
        _root, version = await self._load_owned_version(
            owner,
            version_id,
        )
        if version.status != ReadingStatus.ACCEPTED.value:
            raise ReadingNotAcceptedError("Reading is not accepted")
        saved, created = await self.repository.save_verification(
            version_id=version_id,
            outcome=outcome,
            note=note,
        )
        return _verification_summary(saved), created

    async def follow_up(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        query: str | None,
        idempotency_key: str | None,
    ) -> tuple[ReadingStartResponse, bool]:
        user_id, guest_id = owner_ids(owner)
        idempotency = self._idempotency_context(
            idempotency_key,
            action="follow_up",
            payload={"reading_version_id": str(version_id), "query": query},
        )
        replayed = await self._replay_idempotency(owner, idempotency)
        if replayed is not None:
            return replayed, False
        root, version = await self._load_owned_version(
            owner,
            version_id,
        )
        if version.status != ReadingStatus.ACCEPTED.value:
            raise ReadingNotAcceptedError("Follow-up requires an Accepted Reading")
        stored_accepted_copy = await self.repository.load_accepted_copy(version.id)
        if stored_accepted_copy is None:
            raise ReadingNotAcceptedError("Accepted Copy is missing")
        await self._check_follow_up_contract(root, version)
        prepare = await self.repository.load_prepare(version.id)
        brief = await self.repository.load_fact_brief(version.id)
        document = await self.repository.load_reading_document(version.id)
        view_model = (
            None
            if brief is None
            else project_runtime_view_model(
                brief.to_dict(),
                product_id=version.product_id or root.product_id,
                relationship_type=version.relationship_type,
            )
        )
        presentation = await project_owned_reading_presentation(
            brief=brief,
            view_model=view_model,
            document=document,
        )
        accepted_copy = _project_presented_accepted_copy(
            stored_accepted_copy,
            source_document=document,
            presented_document=presentation.document,
        )
        if accepted_copy is None:
            raise ReadingNotAcceptedError("Accepted Copy is unavailable")
        facts: dict[str, object] = {}
        for subject_ref in cast(tuple[object, ...], prepare.intent["subject_refs"]):
            ref = str(subject_ref)
            subject_facts = dict(
                cast(Mapping[str, object], prepare.facts.get(ref, {}))
            )
            subject_facts["prior_answer"] = accepted_copy
            facts[ref] = subject_facts
        # Follow-up continues the same lineage with the latest Accepted token.
        # transition stays null; only explicit fact correction uses "correct".
        state_token = await self.repository.load_state_token(version.id)
        new_prepare = Prepare(
            query=query or prepare.query,
            intent=prepare.intent,
            facts=facts,
            state_token=state_token,
            transition=None,
        )
        new_version = await self._create_version_and_job(
            root,
            new_prepare,
        )
        if idempotency is not None:
            replayed = await self._save_idempotency_or_replay(
                idempotency,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
                reading_version_id=new_version.id,
            )
            if replayed is not None:
                return replayed, False
        summary = await self._summary(root, new_version)
        summary.prior_answer = accepted_copy
        return summary, True

    async def _check_follow_up_contract(self, root: Any, version: Any) -> None:
        """Enforce the frozen paid follow-up contract when one is present.

        Legacy/free preview roots have no ProductVersion snapshot and retain
        the existing local preview behavior until a paid fulfillment binds one.
        """
        if root.follow_up_count_snapshot is None:
            return
        count_limit = root.follow_up_count_snapshot
        window_seconds = root.follow_up_window_seconds_snapshot
        if count_limit < 0 or (window_seconds is not None and window_seconds < 0):
            raise ReadingFollowUpUnavailableError("Follow-up contract is invalid")

        versions = list(
            await self.session.scalars(
                select(ReadingVersion)
                .where(ReadingVersion.reading_root_id == root.id)
                .order_by(ReadingVersion.version.desc())
            )
        )
        latest = versions[0] if versions else None
        if latest is None or latest.id != version.id:
            raise ReadingFollowUpUnavailableError(
                "Reading Root already has a later follow-up; branching is not allowed"
            )

        accepted_follow_ups = sum(
            item.version > 1 and item.status == ReadingStatus.ACCEPTED.value
            for item in versions
        )
        if accepted_follow_ups >= count_limit:
            raise ReadingFollowUpUnavailableError("Follow-up count has been exhausted")

        if window_seconds is None:
            return
        started_at = root.follow_up_started_at
        if started_at is None:
            initial = next((item for item in versions if item.version == 1), None)
            if initial is None:
                raise ReadingFollowUpUnavailableError("Initial Reading Version is missing")
            initial_copy = await self.repository.get_accepted_copy(initial.id)
            if initial_copy is None:
                raise ReadingFollowUpUnavailableError("Initial Accepted Copy is missing")
            started_at = initial_copy.accepted_at
            root.follow_up_started_at = started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        if datetime.now(UTC) > started_at + timedelta(seconds=window_seconds):
            raise ReadingFollowUpUnavailableError("Follow-up window has expired")

    async def _save_idempotency_or_replay(
        self,
        idempotency: IdempotencyContext,
        *,
        owner_user_id: UUID | None,
        owner_guest_session_id: UUID | None,
        reading_version_id: UUID,
    ) -> ReadingStartResponse | None:
        try:
            await self.repository.save_idempotency(
                key_hash=idempotency.key_hash,
                action=idempotency.action,
                request_fingerprint=idempotency.request_fingerprint,
                owner_user_id=owner_user_id,
                owner_guest_session_id=owner_guest_session_id,
                reading_version_id=reading_version_id,
            )
        except IntegrityError:
            await self.session.rollback()
            return await self._replay_idempotency_for_ids(
                idempotency,
                user_id=owner_user_id,
                guest_id=owner_guest_session_id,
            )
        return None

    async def _persist_start(
        self,
        owner: OwnerProtocol,
        prepare: Prepare,
        *,
        capability_id: str,
        product_id: str | None = None,
        runtime_capability_ids: tuple[str, ...] | None = None,
        profile_version_id: UUID | None,
        profile_version_ids: tuple[UUID, ...] | None = None,
        relationship_type: str | None = None,
        idempotency: IdempotencyContext | None,
        initial_job_status: str = "queued",
        direct_chart: bool = False,
        rollback_on_failure: bool = False,
    ) -> tuple[ReadingStartResponse, bool]:
        if direct_chart and idempotency is None:
            raise InvalidReadingInputError(
                "Idempotency-Key is required for direct Runtime starts"
        )
        started_at = perf_counter()
        user_id, guest_id = owner_ids(owner)
        claim = self._atomic_profile_preview_claim
        owns_atomic_claim = (
            rollback_on_failure
            and direct_chart
            and idempotency is not None
            and claim is not None
            and claim.context == idempotency
        )
        release = None if owns_atomic_claim else await self._runtime_release()
        resolved_runtime_capability_ids = runtime_capability_ids
        if resolved_runtime_capability_ids is None:
            raw_comparisons = prepare.intent.get("comparisons", ())
            derived = [capability_id]
            if isinstance(raw_comparisons, (list, tuple)):
                for comparison in raw_comparisons:
                    if isinstance(comparison, Mapping):
                        comparison_capability_id = comparison.get("capability_id")
                        if isinstance(comparison_capability_id, str):
                            derived.append(comparison_capability_id)
            resolved_runtime_capability_ids = tuple(derived)
        require_public_runtime_capabilities(
            resolved_runtime_capability_ids,
            environment=self.settings.environment,
            real_traffic_enabled=self.settings.real_traffic_enabled,
        )
        require_public_product_exposure(
            product_id,
            environment=self.settings.environment,
            real_traffic_enabled=self.settings.real_traffic_enabled,
        )
        if owns_atomic_claim:
            assert claim is not None
            assert profile_version_id is not None
            _claim_root, claim_version, claim_job = (
                await self._load_atomic_profile_preview_claim(claim.reading_version_id)
            )
            if not self._atomic_profile_preview_claim_is_active(
                claim,
                claim_version,
                claim_job,
            ):
                await self.session.rollback()
                await self._recover_expired_atomic_profile_preview_claim(
                    claim.reading_version_id
                )
                raise ChartFastPathUnavailableError(
                    "chart_runtime_owner_lost",
                    code="chart_runtime_transport",
                )
            root, version, job = await self.repository.attach_start_claim_profile(
                claim.reading_version_id,
                profile_version_id,
            )
            self._rearm_atomic_profile_preview_claim(
                version,
                job,
                initial_job_status=initial_job_status,
            )
            version = await self.repository.replace_start_claim_prepare(
                version.id,
                prepare,
            )
        else:
            root = await self.repository.create_root(
                capability_id=capability_id,
                product_id=product_id,
                runtime_capability_ids=resolved_runtime_capability_ids,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
                profile_version_id=profile_version_id,
                profile_version_ids=profile_version_ids,
                relationship_type=relationship_type,
            )
            assert release is not None
            version = await self.repository.create_version(
                reading_root_id=root.id,
                runtime_release_id=release.id,
                prepare_command=prepare,
                relationship_type=relationship_type,
            )
            await self.session.refresh(version)
            job = await self._create_job(version.id, status=initial_job_status)
        if idempotency is not None and not owns_atomic_claim:
            replayed = await self._save_idempotency_or_replay(
                idempotency,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
                reading_version_id=version.id,
            )
            if replayed is not None:
                return replayed, False
        runtime_ms = 0.0
        persistence_ms = 0.0
        if direct_chart:
            try:
                runtime_ms, persistence_ms = await self._run_chart_fast_path(
                    job,
                    version,
                    product_id=version.product_id or root.product_id or root.capability_id,
                    commit_failures=not rollback_on_failure,
                )
            except ChartFastPathUnavailableError as error:
                if (
                    rollback_on_failure
                    and prepare.state_token is None
                    and error.code in {"chart_runtime_timeout", "chart_runtime_transport"}
                ):
                    await self.session.rollback()
                    await self._persist_runtime_unknown_quarantine(
                        owner,
                        prepare,
                        capability_id=capability_id,
                        product_id=product_id,
                        runtime_capability_ids=resolved_runtime_capability_ids,
                        relationship_type=relationship_type,
                        idempotency=idempotency,
                        initial_job_status=initial_job_status,
                    )
                elif (
                    rollback_on_failure
                    and prepare.state_token is None
                    and error.prepared_checkpoint is not None
                ):
                    await self.session.rollback()
                    await self._persist_prepared_checkpoint_quarantine(
                        owner,
                        prepare,
                        error.prepared_checkpoint,
                        capability_id=capability_id,
                        product_id=product_id,
                        runtime_capability_ids=resolved_runtime_capability_ids,
                        relationship_type=relationship_type,
                        idempotency=idempotency,
                        initial_job_status=initial_job_status,
                    )
                elif (
                    rollback_on_failure
                    and prepare.state_token is None
                    and error.waiting_input_checkpoint is not None
                ):
                    await self.session.rollback()
                    await self._persist_waiting_input_checkpoint_quarantine(
                        owner,
                        prepare,
                        error.waiting_input_checkpoint,
                        capability_id=capability_id,
                        product_id=product_id,
                        runtime_capability_ids=resolved_runtime_capability_ids,
                        relationship_type=relationship_type,
                        idempotency=idempotency,
                        initial_job_status=initial_job_status,
                    )
                elif owns_atomic_claim:
                    assert claim is not None
                    await self.session.rollback()
                    await self._settle_failed_atomic_profile_preview_claim(
                        claim,
                        prepare,
                        stopped=(
                            error.terminal_stopped_checkpoint
                            or Stopped(
                                reason="error",
                                public_copy="排盘未完成，本次结果已终止。",
                            )
                        ),
                    )
                raise
        summary = await self._summary(root, version)
        if direct_chart:
            summary.fast_path_timing = ChartFastPathTiming(
                queue_wait_ms=0,
                worker_pickup_ms=0,
                runtime_one_shot_ms=runtime_ms,
                db_persistence_ms=persistence_ms,
                total_ms=(perf_counter() - started_at) * 1000,
            )
            _logger.info(
                "chart_fast_path",
                extra={
                    "reading_version_id": str(version.id),
                    "capability_id": version.capability_id,
                    "product_id": version.product_id,
                    "runtime_one_shot_ms": round(runtime_ms, 3),
                    "db_persistence_ms": round(persistence_ms, 3),
                    "total_ms": round(summary.fast_path_timing.total_ms, 3),
                    "queue_wait_ms": 0,
                    "worker_pickup_ms": 0,
                },
            )
        return summary, True

    @staticmethod
    def _atomic_profile_preview_claim_is_active(
        claim: AtomicProfilePreviewClaim,
        version: ReadingVersion,
        job: ReadingJobRecord,
    ) -> bool:
        return (
            version.status == ReadingStatus.INPUT_READY.value
            and job.status == _ATOMIC_PROFILE_PREVIEW_CLAIM_JOB_STATUS
            and job.lease_token == claim.lease_token
            and job.lease_expires_at is not None
            and not _datetime_lte(job.lease_expires_at, datetime.now(UTC))
        )

    async def _settle_failed_atomic_profile_preview_claim(
        self,
        claim: AtomicProfilePreviewClaim,
        prepare: Prepare,
        *,
        stopped: Stopped,
    ) -> None:
        """Keep PostgreSQL failures replayable across the winner-fence handoff."""

        try:
            _root, version, job = await self._load_atomic_profile_preview_claim(
                claim.reading_version_id
            )
        except LookupError:
            return
        if (
            version.status != ReadingStatus.INPUT_READY.value
            or job.status != _ATOMIC_PROFILE_PREVIEW_CLAIM_JOB_STATUS
            or job.lease_token != claim.lease_token
        ):
            await self.session.rollback()
            return
        if job.lease_expires_at is None or _datetime_lte(
            job.lease_expires_at,
            datetime.now(UTC),
        ):
            await self.session.rollback()
            await self._recover_expired_atomic_profile_preview_claim(
                claim.reading_version_id
            )
            return
        if (
            job.lease_generation
            < _ATOMIC_PROFILE_PREVIEW_CLAIM_EXPOSED_GENERATION
            and self.session.get_bind().dialect.name != "postgresql"
        ):
            await self.repository.delete_start_claim(claim.reading_version_id)
            await self.session.commit()
            return
        # A pg_locks waiter check cannot close the gate: an identical replay can
        # join the advisory-lock queue after the check but before this transaction
        # commits. Retaining the terminal row is the durable handoff that prevents
        # that late replay (and later retries with the same key) from sending the
        # tokenless Prepare again. Other dialects remain process-serialized and
        # preserve the existing unexposed-failure cleanup above.
        self._rearm_atomic_profile_preview_claim(
            version,
            job,
            initial_job_status="queued",
        )
        await self.repository.replace_start_claim_prepare(
            claim.reading_version_id,
            prepare,
        )
        await self.repository.record_terminal_stopped(
            str(job.id),
            stopped,
            datetime.now(UTC),
        )
        await self.session.commit()

    async def _persist_runtime_unknown_quarantine(
        self,
        owner: OwnerProtocol,
        prepare: Prepare,
        *,
        capability_id: str,
        product_id: str | None,
        runtime_capability_ids: tuple[str, ...],
        relationship_type: str | None,
        idempotency: IdempotencyContext | None,
        initial_job_status: str,
    ) -> None:
        """Persist an uncertain tokenless call without confirming its Profile draft."""

        claim = self._atomic_profile_preview_claim
        if claim is not None and claim.context == idempotency:
            _root, version, job = await self._load_atomic_profile_preview_claim(
                claim.reading_version_id
            )
            if not self._atomic_profile_preview_claim_is_active(
                claim,
                version,
                job,
            ):
                await self.session.rollback()
                await self._recover_expired_atomic_profile_preview_claim(
                    claim.reading_version_id
                )
                return
            self._rearm_atomic_profile_preview_claim(
                version,
                job,
                initial_job_status=initial_job_status,
            )
            await self.repository.replace_start_claim_prepare(
                claim.reading_version_id,
                prepare,
            )
            await self.repository.mark_runtime_unknown(str(job.id), datetime.now(UTC))
            await self.session.commit()
            return

        user_id, guest_id = owner_ids(owner)
        release = await self._runtime_release()
        root = await self.repository.create_root(
            capability_id=capability_id,
            product_id=product_id,
            runtime_capability_ids=runtime_capability_ids,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
            relationship_type=relationship_type,
        )
        version = await self.repository.create_version(
            reading_root_id=root.id,
            runtime_release_id=release.id,
            prepare_command=prepare,
            relationship_type=relationship_type,
        )
        await self.session.refresh(version)
        job = await self._create_job(version.id, status=initial_job_status)
        if idempotency is not None:
            replayed = await self._save_idempotency_or_replay(
                idempotency,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
                reading_version_id=version.id,
            )
            if replayed is not None:
                return
        await self.repository.mark_runtime_unknown(str(job.id), datetime.now(UTC))
        await self.session.commit()

    async def _persist_prepared_checkpoint_quarantine(
        self,
        owner: OwnerProtocol,
        prepare: Prepare,
        prepared: Prepared,
        *,
        capability_id: str,
        product_id: str | None,
        runtime_capability_ids: tuple[str, ...],
        relationship_type: str | None,
        idempotency: IdempotencyContext | None,
        initial_job_status: str,
    ) -> None:
        """Persist a received Runtime checkpoint without confirming its Profile draft."""

        claim = self._atomic_profile_preview_claim
        if claim is not None and claim.context == idempotency:
            _root, version, job = await self._load_atomic_profile_preview_claim(
                claim.reading_version_id
            )
            if not self._atomic_profile_preview_claim_is_active(
                claim,
                version,
                job,
            ):
                await self.session.rollback()
                await self._recover_expired_atomic_profile_preview_claim(
                    claim.reading_version_id
                )
                return
            self._rearm_atomic_profile_preview_claim(
                version,
                job,
                initial_job_status=initial_job_status,
            )
            await self.repository.replace_start_claim_prepare(
                claim.reading_version_id,
                prepare,
            )
            await self.repository.record_prepared(
                str(job.id),
                prepared,
                datetime.now(UTC),
            )
            job.status = "complete"
            await self.session.flush()
            await self.session.commit()
            return

        user_id, guest_id = owner_ids(owner)
        release = await self._runtime_release()
        root = await self.repository.create_root(
            capability_id=capability_id,
            product_id=product_id,
            runtime_capability_ids=runtime_capability_ids,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
            relationship_type=relationship_type,
        )
        version = await self.repository.create_version(
            reading_root_id=root.id,
            runtime_release_id=release.id,
            prepare_command=prepare,
            relationship_type=relationship_type,
        )
        await self.session.refresh(version)
        job = await self._create_job(version.id, status=initial_job_status)
        if idempotency is not None:
            replayed = await self._save_idempotency_or_replay(
                idempotency,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
                reading_version_id=version.id,
            )
            if replayed is not None:
                return
        await self.repository.record_prepared(str(job.id), prepared, datetime.now(UTC))
        job.status = "complete"
        await self.session.flush()
        await self.session.commit()

    async def _persist_waiting_input_checkpoint_quarantine(
        self,
        owner: OwnerProtocol,
        prepare: Prepare,
        stopped: Stopped,
        *,
        capability_id: str,
        product_id: str | None,
        runtime_capability_ids: tuple[str, ...],
        relationship_type: str | None,
        idempotency: IdempotencyContext | None,
        initial_job_status: str,
    ) -> None:
        """Persist a correctable Runtime stop without confirming its Profile draft."""

        claim = self._atomic_profile_preview_claim
        if claim is not None and claim.context == idempotency:
            _root, version, job = await self._load_atomic_profile_preview_claim(
                claim.reading_version_id
            )
            if not self._atomic_profile_preview_claim_is_active(
                claim,
                version,
                job,
            ):
                await self.session.rollback()
                await self._recover_expired_atomic_profile_preview_claim(
                    claim.reading_version_id
                )
                return
            self._rearm_atomic_profile_preview_claim(
                version,
                job,
                initial_job_status=initial_job_status,
            )
            await self.repository.replace_start_claim_prepare(
                claim.reading_version_id,
                prepare,
            )
            await self.repository.record_waiting_input(
                str(job.id),
                stopped,
                datetime.now(UTC),
            )
            await self.session.commit()
            return

        user_id, guest_id = owner_ids(owner)
        release = await self._runtime_release()
        root = await self.repository.create_root(
            capability_id=capability_id,
            product_id=product_id,
            runtime_capability_ids=runtime_capability_ids,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
            relationship_type=relationship_type,
        )
        version = await self.repository.create_version(
            reading_root_id=root.id,
            runtime_release_id=release.id,
            prepare_command=prepare,
            relationship_type=relationship_type,
        )
        await self.session.refresh(version)
        job = await self._create_job(version.id, status=initial_job_status)
        if idempotency is not None:
            replayed = await self._save_idempotency_or_replay(
                idempotency,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
                reading_version_id=version.id,
            )
            if replayed is not None:
                return
        await self.repository.record_waiting_input(
            str(job.id),
            stopped,
            datetime.now(UTC),
        )
        await self.session.commit()

    @staticmethod
    def _rearm_atomic_profile_preview_claim(
        version: ReadingVersion,
        job: ReadingJobRecord,
        *,
        initial_job_status: str,
    ) -> None:
        """Make one durable quarantine executable inside the winner transaction."""

        version.status = ReadingStatus.INPUT_READY.value
        job.status = initial_job_status
        job.lease_owner = None
        job.lease_token = None
        job.lease_expires_at = None

    async def _run_chart_fast_path(
        self,
        job: ReadingJobRecord,
        version: ReadingVersion,
        *,
        product_id: str,
        commit_failures: bool = True,
    ) -> tuple[float, float]:
        """Prepare one deterministic base chart without exposing it to the Worker."""

        if self.chart_runtime is None:
            raise ChartFastPathUnavailableError(
                "chart_runtime_not_configured",
                code="chart_runtime_not_configured",
            )
        prepare = await self.repository.load_prepare(version.id)
        runtime_started_at = perf_counter()
        try:
            result = await self._execute_chart_runtime(prepare)
        except TimeoutError as error:
            await self._record_chart_runtime_timeout(
                job,
                prepare,
                commit_failure=commit_failures,
            )
            raise ChartFastPathUnavailableError(
                "chart_runtime_timeout",
                code="chart_runtime_timeout",
            ) from error
        except RuntimeTransportError as error:
            if str(error) == "runtime_timed_out":
                await self._record_chart_runtime_timeout(
                    job,
                    prepare,
                    commit_failure=commit_failures,
                )
                raise ChartFastPathUnavailableError(
                    "chart_runtime_timeout",
                    code="chart_runtime_timeout",
                ) from error
            await self._record_chart_runtime_fault(
                job,
                prepare,
                fault=f"transport:{type(error).__name__}",
                commit_failure=commit_failures,
            )
            raise ChartFastPathUnavailableError(
                f"chart_runtime_transport:{error}",
                code="chart_runtime_transport",
            ) from error
        except Exception as error:
            if isinstance(error, OSError) and (
                _post_write_runtime_result_audit(self.chart_runtime, prepare) is not None
            ):
                await self._record_chart_runtime_fault(
                    job,
                    prepare,
                    fault="audit-persistence",
                    commit_failure=commit_failures,
                )
                raise ChartFastPathUnavailableError(
                    "chart_runtime_transport",
                    code="chart_runtime_transport",
                ) from error
            await self._remember_chart_runtime_audit(
                prepare,
                None,
                fault=f"exception:{type(error).__name__}",
            )
            _logger.exception(
                "chart_runtime_error",
                extra={
                    "reading_version_id": str(version.id),
                    "capability_id": version.capability_id,
                    "error_type": type(error).__name__,
                },
            )
            raise ChartFastPathUnavailableError(
                "chart_runtime_error",
                code="chart_runtime_error",
            ) from error
        runtime_ms = (perf_counter() - runtime_started_at) * 1000

        persistence_started_at = perf_counter()
        now = datetime.now(UTC)
        if isinstance(result, Prepared):
            await self.repository.record_prepared(str(job.id), result, now)
            try:
                view_model = project_runtime_view_model(
                    cast(Any, result.brief).to_dict(),
                    product_id=product_id,
                    relationship_type=version.relationship_type,
                )
            except Exception as error:
                if commit_failures:
                    await self.session.commit()
                raise ChartFastPathUnavailableError(
                    "chart_view_model_projection_failed",
                    code="chart_view_model_projection_failed",
                    prepared_checkpoint=result,
                ) from error
            if view_model is None and getattr(self.chart_runtime, "adapter_kind", None) != "fake":
                if commit_failures:
                    await self.session.commit()
                raise ChartFastPathUnavailableError(
                    "chart_view_model_projection_failed",
                    code="chart_view_model_projection_failed",
                    prepared_checkpoint=result,
                )
            job.status = "complete"
            await self.session.flush()
        elif isinstance(result, Stopped) and (
            transport_fault := _post_write_runtime_transport_fault(
                self.chart_runtime,
                prepare,
                result,
            )
        ) is not None:
            await self._record_chart_runtime_fault(
                job,
                prepare,
                fault=transport_fault,
                commit_failure=commit_failures,
            )
            raise ChartFastPathUnavailableError(
                "chart_runtime_transport",
                code="chart_runtime_transport",
            )
        elif isinstance(result, Stopped) and result.reason == "need_input":
            await self.repository.record_waiting_input(str(job.id), result, now)
            if not commit_failures:
                raise ChartFastPathUnavailableError(
                    "chart_runtime_need_input",
                    code="chart_runtime_need_input",
                    waiting_input_checkpoint=result,
                )
        elif isinstance(result, Stopped):
            await self.repository.record_terminal_stopped(str(job.id), result, now)
            if commit_failures:
                await self.session.commit()
            await self._remember_chart_runtime_audit(prepare, result)
            code = f"chart_runtime_{result.reason}"
            raise ChartFastPathUnavailableError(
                result.public_copy or code,
                code=code,
                terminal_stopped_checkpoint=result,
            )
        else:
            await self._remember_chart_runtime_audit(
                prepare,
                result,
                fault="protocol-error",
            )
            raise ChartFastPathUnavailableError(
                "chart_runtime_protocol_error",
                code="chart_runtime_protocol_error",
            )
        return runtime_ms, (perf_counter() - persistence_started_at) * 1000

    async def _execute_chart_runtime(self, prepare: Prepare) -> MingliResult:
        """Run Worker v2 after its own admission lock starts the execution budget."""
        if self.chart_runtime is None:
            raise ChartFastPathUnavailableError(
                "chart_runtime_not_configured",
                code="chart_runtime_not_configured",
            )
        if isinstance(self.chart_runtime, WorkerV2MingliRuntimeAdapter):
            return await self.chart_runtime.execute(prepare)
        async with asyncio.timeout(self.settings.chart_fast_path_timeout_seconds):
            return await self.chart_runtime.execute(prepare)

    async def _record_chart_runtime_timeout(
        self,
        job: ReadingJobRecord,
        prepare: Prepare,
        *,
        commit_failure: bool = True,
    ) -> None:
        await self._record_chart_runtime_fault(
            job,
            prepare,
            fault="timeout",
            commit_failure=commit_failure,
        )

    async def _record_chart_runtime_fault(
        self,
        job: ReadingJobRecord,
        prepare: Prepare,
        *,
        fault: str,
        commit_failure: bool = True,
    ) -> None:
        if prepare.state_token is None:
            await self.repository.mark_runtime_unknown(str(job.id), datetime.now(UTC))
            # The API maps this outcome to a 503 and the request dependency rolls
            # back raised errors. Commit the non-replayable no-token claim first.
            if commit_failure:
                await self.session.commit()
        await self._remember_chart_runtime_audit(prepare, None, fault=fault)

    async def _remember_chart_runtime_audit(
        self,
        prepare: Prepare,
        result: Prepared | Stopped | object | None,
        *,
        fault: str | None = None,
    ) -> RuntimeTurnAudit:
        runtime = self.chart_runtime
        existing = getattr(runtime, "last_turn", None)
        if isinstance(existing, RuntimeTurnAudit) and (
            fault is None or existing.transport_fault is not None
        ):
            return existing
        failure = None
        result_kind = "error"
        if isinstance(result, Stopped):
            result_kind = result.kind
            if result.failure is not None:
                failure = result.failure.to_audit_dict()
        elif isinstance(result, Prepared):
            result_kind = result.kind
        if failure is None and fault is not None:
            failure = failure_for_transport_fault(fault).to_audit_dict()
        state = getattr(runtime, "_state_root", None)
        if isinstance(state, Path):
            store_root = str(state)
            audit_path: Path | None = state / RUNTIME_TURN_AUDIT_NAME
        elif self.settings.runtime_state_root is not None:
            store_root = str(self.settings.runtime_state_root)
            audit_path = self.settings.runtime_state_root / RUNTIME_TURN_AUDIT_NAME
        else:
            store_root = "unbound"
            audit_path = None
        pid = getattr(runtime, "_audit_pid", None)
        boot_nonce = getattr(runtime, "_audit_boot_nonce", None)
        sequence = getattr(runtime, "_last_sequence", None)
        transport_fault = fault or getattr(runtime, "_transport_fault", None)
        record = RuntimeTurnAudit(
            command_digest=runtime_command_digest(prepare),
            command_kind=prepare.kind,
            worker_pid=pid if isinstance(pid, int) else None,
            worker_boot_nonce=boot_nonce if isinstance(boot_nonce, str) else None,
            sequence=sequence if isinstance(sequence, int) else None,
            result_kind=result_kind,
            failure=failure,
            transport_fault=transport_fault if isinstance(transport_fault, str) else None,
            isolated=bool(getattr(runtime, "isolated", False)),
            store_root=store_root,
        )
        if runtime is not None:
            cast(Any, runtime).last_turn = record
        if audit_path is not None:
            raw_timeout = getattr(runtime, "_audit_timeout_seconds", None)
            audit_timeout = (
                float(raw_timeout)
                if isinstance(raw_timeout, (int, float)) and raw_timeout > 0
                else WORKER_AUDIT_TIMEOUT_SECONDS
            )
            try:
                async with asyncio.timeout(audit_timeout):
                    await asyncio.to_thread(
                        append_runtime_turn_audit,
                        audit_path,
                        record.to_dict(),
                    )
            except TimeoutError:
                _logger.warning(
                    "chart_runtime_audit_timeout",
                    extra={"command_kind": prepare.kind},
                )
            except Exception:
                _logger.exception(
                    "chart_runtime_audit_error",
                    extra={"command_kind": prepare.kind},
                )
        return record

    async def _create_version_and_job(
        self,
        root: Any,
        prepare: Prepare,
    ) -> Any:
        release = await self._runtime_release()
        version = await self.repository.create_version(
            reading_root_id=root.id,
            runtime_release_id=release.id,
            prepare_command=prepare,
        )
        await self.session.refresh(version)
        await self._create_job(version.id)
        return version

    async def _create_job(
        self,
        version_id: UUID,
        *,
        status: str = "queued",
    ) -> ReadingJobRecord:
        prepare = await self.repository.load_prepare(version_id)
        raw_dimensions = prepare.intent.get("dimension_ids")
        dimensions = (
            tuple(item for item in raw_dimensions if isinstance(item, str))
            if isinstance(raw_dimensions, tuple)
            else ()
        )
        version = await self.session.get(ReadingVersion, version_id)
        if version is None:
            raise ReadingNotFoundError("Reading Version not found")
        output_contract = output_contract_for_product(version.product_id, dimensions)
        return await self.repository.create_job(
            reading_version_id=version_id,
            narrative_policy_version=NARRATIVE_POLICY_VERSION,
            output_contract=output_contract,
            language="zh-CN",
            max_output_chars=output_contract.max_output_chars,
            max_attempts=2,
            status=status,
        )

    async def _runtime_release(self) -> Any:
        try:
            return await self.repository.resolve_runtime_release()
        except LookupError as error:
            raise RuntimeReleaseUnavailableError(
                "no Runtime Release is registered"
            ) from error

    async def _owned_confirmed_profile(
        self,
        owner: OwnerProtocol,
        profile_version_id: UUID,
    ) -> ConfirmedProfileVersion:
        try:
            _profile, version = await self.profiles.get_owned_profile_version(
                owner,
                profile_version_id,
            )
        except LookupError as error:
            raise ProfileVersionNotOwnedError(
                "Profile Version not found"
            ) from error
        return await self._confirmed_profile_from_version(version)

    async def _confirmed_profile_from_version(
        self,
        version: ProfileVersion,
    ) -> ConfirmedProfileVersion:
        payload = await self.profiles.repository.load_version_payload(version.id)
        return ConfirmedProfileVersion(
            subject_ref=f"profile-version:{version.id}",
            birth_datetime=str(payload["birth_datetime"]),
            birth_datetime_or_four_pillars=str(payload["birth_datetime"]),
            timezone=str(payload["timezone"]),
            location=str(payload["location"]),
            gender=str(payload["gender"]),
            time_basis_policy=str(payload["time_basis_policy"]),
            zi_hour_policy=str(payload["zi_hour_policy"]),
            longitude=cast(float | None, payload.get("longitude")),
            latitude=cast(float | None, payload.get("latitude")),
            coordinate_source=cast(str | None, payload.get("coordinate_source")),
        )

    async def _require_accepted_source(
        self,
        owner: OwnerProtocol,
        source_version_id: UUID,
    ) -> None:
        _root, version = await self._load_owned_version(owner, source_version_id)
        if (
            version.status != ReadingStatus.ACCEPTED.value
            or await self.repository.load_accepted_copy(version.id) is None
        ):
            raise ReadingNotAcceptedError("Recast requires an Accepted Reading")

    async def _replay_idempotency(
        self,
        owner: OwnerProtocol,
        idempotency: IdempotencyContext | None,
    ) -> ReadingStartResponse | None:
        if idempotency is None:
            return None
        user_id, guest_id = owner_ids(owner)
        return await self._replay_idempotency_for_ids(
            idempotency,
            user_id=user_id,
            guest_id=guest_id,
        )

    async def _replay_idempotency_for_ids(
        self,
        idempotency: IdempotencyContext,
        *,
        user_id: UUID | None,
        guest_id: UUID | None,
    ) -> ReadingStartResponse | None:
        if idempotency.action == "confirm_profile_preview":
            await self._hold_atomic_profile_preview_replay_intent(idempotency)
        record = await self.repository.find_idempotency(
            idempotency.key_hash,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        if record is None:
            return None
        if (
            record.action != idempotency.action
            or record.request_fingerprint != idempotency.request_fingerprint
        ):
            raise IdempotencyConflictError(
                "Idempotency-Key belongs to a different action or payload"
            )
        reading_version_id = record.reading_version_id
        root, version = await self._load_stabilized_owned_version_for_ids(
            reading_version_id,
            user_id=user_id,
            guest_id=guest_id,
        )
        return await self._summary(root, version)

    def _idempotency_context(
        self,
        idempotency_key: str | None,
        *,
        action: str,
        payload: Mapping[str, object],
    ) -> IdempotencyContext | None:
        if idempotency_key is None:
            return None
        if not idempotency_key.strip():
            raise ReadingServiceError("Idempotency-Key must be non-empty")
        return IdempotencyContext(
            key_hash=_hmac_digest(
                self._idempotency_secret,
                "reading-idempotency-key-v1",
                idempotency_key,
            ),
            action=action,
            request_fingerprint=_hmac_digest(
                self._idempotency_secret,
                "reading-idempotency-request-v1",
                _canonical_json(payload),
            ),
        )

    async def _load_owned_version(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> tuple[Any, Any]:
        user_id, guest_id = owner_ids(owner)
        try:
            return await self.repository.load_owned_version(
                version_id,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
            )
        except LookupError as error:
            raise ReadingNotFoundError("Reading Version not found") from error

    @staticmethod
    def project_time_layer_entitlement(
        view_model: object,
        owner: OwnerProtocol,
        *,
        request_failed: bool = False,
        paid_grant: bool | None = None,
    ) -> TimeLayerEntitlementV1 | None:
        """Project the dormant v1 shape through the active content policy.

        Owner, transport, and billing arguments remain accepted for internal
        compatibility, but do not gate supported development content.
        """

        _ = owner, request_failed, paid_grant
        return _project_active_time_layer_access(view_model)

    @staticmethod
    def _poll_fields(
        status: ReadingStatus,
        view_model: object,
        *,
        job_status: str | None = None,
    ) -> tuple[bool, bool, int | None]:
        result_available = view_model is not None and status in {
            ReadingStatus.PREPARED,
            ReadingStatus.ACCEPTED,
        }
        terminal_direct_prepared = (
            status is ReadingStatus.PREPARED and job_status == "complete"
        )
        poll_required = not (
            terminal_direct_prepared or status in _POLL_STOP_STATUSES
        )
        return result_available, poll_required, 4 if poll_required else None

    async def _latest_job_status(self, version_id: UUID) -> str | None:
        return cast(
            str | None,
            await self.session.scalar(
                select(ReadingJobRecord.status)
                .where(ReadingJobRecord.reading_version_id == version_id)
                .order_by(ReadingJobRecord.created_at.desc(), ReadingJobRecord.id.desc())
                .limit(1)
            ),
        )

    async def _summary(
        self,
        root: Any,
        version: Any,
    ) -> ReadingStartResponse:
        waiting = await self.repository.load_waiting_input(version.id)
        brief = await self.repository.load_fact_brief(version.id)
        view_model = (
            None
            if brief is None
            else project_runtime_view_model(
                brief.to_dict(),
                product_id=version.product_id or root.product_id,
                relationship_type=version.relationship_type,
            )
        )
        status = ReadingStatus(version.status)
        job_status = (
            await self._latest_job_status(version.id)
            if status is ReadingStatus.PREPARED
            else None
        )
        result_available, poll_required, poll_after_seconds = self._poll_fields(
            status,
            view_model,
            job_status=job_status,
        )
        return ReadingStartResponse(
            reading_version_id=version.id,
            reading_root_id=root.id,
            profile_version_id=root.profile_version_id,
            capability_id=version.capability_id,
            product_id=version.product_id or root.product_id or root.capability_id,
            runtime_capability_ids=(
                list(version.runtime_capability_ids)
                if version.runtime_capability_ids
                else [version.capability_id]
            ),
            version=version.version,
            status=status,
            object_id=version.object_id,
            dimension_ids=list(version.dimension_ids),
            horizon=Horizon.model_validate(version.horizon),
            prior_answer=await self._projected_prior_answer(version.id),
            input_request=(
                None if waiting is None else _public_json(waiting.input_request)
            ),
            view_model=view_model,
            created_at=version.created_at,
            delivery_state=await self._delivery_state(root, version),
            result_available=result_available,
            poll_required=poll_required,
            poll_after_seconds=poll_after_seconds,
        )

    async def _delivery_state(self, root: Any, version: Any) -> DeliveryState:
        """Project payment/fulfillment progress without exposing job internals."""
        product_id = version.product_id or root.product_id or root.capability_id
        if product_id not in _PAID_PRODUCT_IDS:
            return "not_required"
        job = await self.session.scalar(
            select(ReadingJobRecord)
            .where(ReadingJobRecord.reading_version_id == version.id)
            .order_by(ReadingJobRecord.created_at.desc(), ReadingJobRecord.id.desc())
        )
        if job is None or job.status == "awaiting_fulfillment":
            return "payment_required"
        fulfillment = await self.session.scalar(
            select(FulfillmentRecord).where(
                FulfillmentRecord.reading_job_ref == str(job.id)
            )
        )
        if fulfillment is None:
            return "payment_required"
        if fulfillment.status == "delivered":
            return "delivered"
        if fulfillment.status == "released":
            return "failed"
        if job.status == "queued":
            return "queued"
        if job.status in {"claimed", "running"}:
            return "processing"
        if job.status == "waiting_input":
            return "waiting_input"
        if job.status == "delayed":
            return "delayed"
        return "failed"

    async def _projected_prior_answer(self, version_id: UUID) -> str | None:
        brief = await self.repository.load_fact_brief(version_id)
        if brief is not None:
            prior = brief.get("prior_answer")
            if isinstance(prior, str) and prior:
                return prior
        prepare = await self.repository.load_prepare(version_id)
        for subject_ref in cast(tuple[object, ...], prepare.intent["subject_refs"]):
            subject_facts = cast(
                Mapping[str, object],
                prepare.facts.get(str(subject_ref), {}),
            )
            value = subject_facts.get("prior_answer")
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _validate_input_values(
        input_request: Mapping[str, Any],
        values: Mapping[str, Any],
    ) -> dict[str, object]:
        requirements = input_request.get("requirements")
        if not isinstance(requirements, (list, tuple)) or not requirements:
            raise InvalidReadingInputError("runtime input request is malformed")
        fields_by_id: dict[str, Mapping[str, object]] = {}
        selected_ids: list[str] = []
        for requirement in requirements:
            if not isinstance(requirement, Mapping):
                raise InvalidReadingInputError("runtime input request is malformed")
            any_of = requirement.get("any_of")
            if not isinstance(any_of, (list, tuple)) or not any_of:
                raise InvalidReadingInputError("runtime input request is malformed")
            fields = [field for field in any_of if isinstance(field, Mapping)]
            field_ids = {str(field.get("id")) for field in fields if field.get("id")}
            if len(field_ids) != len(fields):
                raise InvalidReadingInputError("runtime input request is malformed")
            for field in fields:
                fields_by_id[str(field["id"])] = cast(Mapping[str, object], field)
            selected = sorted(field_ids.intersection(values))
            if len(selected) != 1:
                raise InvalidReadingInputError(
                    "exactly one field from each input alternative is required"
                )
            selected_ids.extend(selected)

        unknown_keys = set(values) - set(fields_by_id)
        if unknown_keys:
            raise InvalidReadingInputError("unknown input fields are forbidden")

        mapped: dict[str, object] = {}
        cast_values: dict[int, int] = {}
        for field_id in selected_ids:
            policy = _INPUT_FIELD_POLICIES.get(field_id)
            if policy is None:
                raise InvalidReadingInputError("runtime input field is not product-approved")
            field = fields_by_id[field_id]
            type_id = field.get("type_id")
            if not isinstance(type_id, str) or type_id not in policy.type_ids:
                raise InvalidReadingInputError("runtime input field type is not approved")
            value = values[field_id]
            _validate_input_value(field, policy, value)
            if policy.target == "cast":
                cast_values[int(field_id.removeprefix("cast_"))] = cast(int, value)
            else:
                mapped[policy.target] = cast(object, value)

        if cast_values:
            if set(cast_values) != set(range(1, 7)):
                raise InvalidReadingInputError("all six cast values are required")
            mapped["cast"] = [cast_values[index] for index in range(1, 7)]
        return mapped


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _datetime_lte(value: datetime, other: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    if other.tzinfo is None:
        other = other.replace(tzinfo=UTC)
    return value <= other


def _profile_product_matches(requested: str, persisted: str) -> bool:
    if requested == persisted:
        return True
    return _PROFILE_PRODUCT_ALIASES.get(requested) == persisted


def _hmac_digest(secret: bytes, domain: str, value: str) -> str:
    return hmac.new(
        secret,
        f"{domain}\x00{value}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _validate_input_value(
    field: Mapping[str, object],
    policy: InputFieldPolicy,
    value: object,
) -> None:
    type_id = cast(str, field["type_id"])
    if type_id == "integer":
        if type(value) is not int:
            raise InvalidReadingInputError("integer input must be an integer")
    elif type_id in {"text", "textarea"}:
        if not isinstance(value, str) or not value.strip():
            raise InvalidReadingInputError("text input must be non-empty")
    elif type_id == "choice":
        if not isinstance(value, str):
            raise InvalidReadingInputError("choice input must be a string")
    else:
        raise InvalidReadingInputError("unsupported runtime input type")

    if isinstance(value, (int, float)) and type(value) is not bool:
        if policy.minimum is not None and value < policy.minimum:
            raise InvalidReadingInputError("numeric input is below the allowed range")
        if policy.maximum is not None and value > policy.maximum:
            raise InvalidReadingInputError("numeric input is above the allowed range")

    raw_choices = field.get("choices")
    if raw_choices:
        if not isinstance(raw_choices, (list, tuple)):
            raise InvalidReadingInputError("runtime input choices are malformed")
        choice_ids = {
            str(choice.get("id"))
            for choice in raw_choices
            if isinstance(choice, Mapping) and choice.get("id")
        }
        if value not in choice_ids:
            raise InvalidReadingInputError("input value is outside the allowed choices")


def _apply_runtime_inputs(
    facts: Mapping[str, object],
    values: Mapping[str, Any],
) -> dict[str, object]:
    merged: dict[str, object] = {}
    for ref, subject_facts in facts.items():
        if isinstance(subject_facts, Mapping):
            merged[str(ref)] = {**dict(subject_facts), **dict(values)}
        else:
            merged[str(ref)] = subject_facts
    return merged


def _verification_summary(record: Any) -> ReadingVerificationSummary:
    return ReadingVerificationSummary(
        verification_id=record.id,
        reading_version_id=record.reading_version_id,
        outcome=record.outcome,
        note=record.note,
        created_at=record.created_at,
    )


def _public_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _public_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_public_json(item) for item in value]
    if isinstance(value, list):
        return [_public_json(item) for item in value]
    return value
