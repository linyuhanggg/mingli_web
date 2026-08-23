from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.charts.projectors import project_runtime_view_model
from app.commerce.models import FulfillmentRecord, Order, Payment, ProductFamily, ProductVersion
from app.commerce.public_service import BAZI_DEEP_PRODUCT_FAMILY_KEY
from app.commerce.service import CommerceError, CommerceService
from app.config import Settings
from app.entitlements.service import EntitlementDeniedError, EntitlementService
from app.profiles.models import ProfileVersion
from app.profiles.service import OwnerProtocol, ProfileService, owner_ids
from app.readings.api_schemas import (
    AccountHistoryResponse,
    AccountHistoryRootResponse,
    AccountHistoryVersionSummary,
    CapabilityProjection,
    DeliveryState,
    Horizon,
    ReadingResultResponse,
    ReadingStartResponse,
    ReadingVerificationSummary,
    ReadingVersionSummary,
)
from app.readings.capability_policy import (
    project_capability,
    require_public_product_exposure,
    require_public_runtime_capabilities,
)
from app.readings.models import ReadingJobRecord, ReadingVersion
from app.readings.output_contracts import output_contract_for_product
from app.readings.relationship_deep_extract import (
    relationship_deep_http_follow_up,
    relationship_deep_http_result,
)
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
    compile_ziwei_prepare,
    compile_ziwei_year_prepare,
)
from app.readings.runtime_contracts import Prepare
from app.readings.status import ReadingStatus
from app.security.envelope import EnvelopeCipher

NARRATIVE_POLICY_VERSION = "policy-v1"
_PAID_PRODUCT_IDS = frozenset({"bazi-deep", "qimen-deep", "liuyao-deep"})
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


class InvalidReadingInputError(ReadingServiceError):
    """Supplied values do not satisfy the runtime input request."""


class ProfileVersionNotOwnedError(ReadingServiceError):
    """The requested Profile Version is missing or belongs to another owner."""


class IdempotencyConflictError(ReadingServiceError):
    """An Idempotency-Key was reused for a different action or payload."""


class PaidReadingNotGrantedError(ReadingServiceError):
    """Dogfood paid capability is closed for this owner."""

    def __init__(self, title: str, *, detail: str | None = None) -> None:
        super().__init__(title)
        self.title = title
        self.detail = detail


class ReadingFulfillmentUnavailableError(ReadingServiceError):
    """A verified payment cannot bind to the requested Reading Job."""


@dataclass(frozen=True, slots=True)
class IdempotencyContext:
    key_hash: str
    action: str
    request_fingerprint: str


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
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repository = SqlReadingRepository(
            session,
            EnvelopeCipher.from_settings(settings),
        )
        self.profiles = ProfileService(session, settings)
        self.entitlements = EntitlementService(session, settings)
        self._idempotency_secret = settings.identity_hash_key.get_secret_value().encode(
            "utf-8"
        )

    async def _require_paid_action(self, owner: OwnerProtocol, *, action: str) -> None:
        try:
            await self.entitlements.require_paid_action(owner, action=action)
        except EntitlementDeniedError as error:
            raise PaidReadingNotGrantedError(error.title, detail=error.detail) from error

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
            prepare = compile_bazi_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                dimension_ids=tuple(resolved_dimensions),
            )
        elif target_year is not None:
            prepare = compile_bazi_year_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                year=target_year,
                dimension_ids=tuple(resolved_dimensions),
            )
        elif target_month is not None:
            prepare = compile_bazi_month_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                month=target_month,
                dimension_ids=tuple(resolved_dimensions),
            )
        else:
            assert target_date is not None
            prepare = compile_bazi_day_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                target_date=target_date,
                dimension_ids=tuple(resolved_dimensions),
            )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="bazi",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
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
            "bazi-relationship-deep": ("bazi_relationship_preview", "bazi", "bazi"),
            "ziwei-relationship-deep": ("ziwei_relationship_preview", "ziwei", "ziwei"),
            "qizheng-relationship-deep": (
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
        if target_year is None and target_month is None:
            prepare = compile_ziwei_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                dimension_ids=tuple(resolved_dimensions),
            )
        elif target_year is not None:
            prepare = compile_ziwei_year_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                year=target_year,
                dimension_ids=tuple(resolved_dimensions),
            )
        else:
            assert target_month is not None
            prepare = compile_ziwei_month_prepare(
                action=action,
                query=resolved_query,
                profile=profile,
                month=target_month,
                dimension_ids=tuple(resolved_dimensions),
            )
        return await self._persist_start(
            owner,
            prepare,
            capability_id="ziwei",
            profile_version_id=profile_version_id,
            idempotency=idempotency,
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
        await self._require_paid_action(owner, action="liuyao_one_question")
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
            prepare = compile_bazi_prepare(
                action=action,
                query=resolved_query,
                profile=await self._owned_confirmed_profile(owner, profile_version_id),
                dimension_ids=tuple(resolved_dimensions),
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
        await self._require_paid_action(owner, action="liuyao_one_question")
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
        )

    async def supply_input(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        values: Mapping[str, Any],
    ) -> ReadingStartResponse:
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
            await self.repository.replace_prepare(version_id, new_prepare)
        except ReadingJobAlreadyQueuedError as error:
            raise ReadingAlreadyQueuedError("Reading is already queued") from error
        except ValueError as error:
            raise ReadingNotWaitingInputError(
                "Reading is not waiting for input"
            ) from error
        return await self.get_summary(owner, version_id)

    async def get_summary(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> ReadingStartResponse:
        root, version = await self._load_owned_version(
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
        return [await self._summary(root, version) for root, version in rows]

    async def list_account_history(self, user_id: UUID) -> AccountHistoryResponse:
        """Project owned Reading Roots with their public version summaries."""
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
        root, version = await self._load_owned_version(
            owner,
            version_id,
        )
        brief = await self.repository.load_fact_brief(version_id)
        product_id = version.product_id or root.product_id
        wired = await relationship_deep_http_result(
            repository=self.repository,
            reading_version_id=version_id,
            product_id=product_id,
        )
        if "relationship_deep_extract_not_applicable" in wired.errors:
            accepted_copy = await self.repository.load_accepted_copy(version_id)
            document = await self.repository.load_reading_document(version_id)
        elif wired.errors:
            raise ReadingNotAcceptedError("Accepted document is unavailable")
        else:
            accepted_copy = wired.accepted_copy
            document = wired.document
        verification = await self.repository.load_verification(version_id)
        waiting = await self.repository.load_waiting_input(version_id)
        capability_projection = project_capability(
            capability_id=version.capability_id,
            product_id=version.product_id or root.product_id,
            release_root=self.settings.runtime_release_root,
            release_profile=self.settings.runtime_release_profile,
        )
        return ReadingResultResponse(
            reading_version_id=version.id,
            status=ReadingStatus(version.status),
            accepted_copy=accepted_copy,
            fact_panel=project_public_fact_panel(brief),
            view_model=(
                None
                if brief is None
                else project_runtime_view_model(
                    brief.to_dict(),
                    product_id=version.product_id or root.product_id,
                    relationship_type=version.relationship_type,
                )
            ),
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
            document=document,
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
        product_id = version.product_id or root.product_id
        wired = await relationship_deep_http_follow_up(
            repository=self.repository,
            reading_version_id=version.id,
            product_id=product_id,
        )
        if "relationship_deep_extract_not_applicable" in wired.errors:
            accepted_copy = await self.repository.load_accepted_copy(version.id)
        elif wired.errors:
            raise ReadingNotAcceptedError("Accepted document is unavailable")
        else:
            accepted_copy = wired.accepted_copy
        if accepted_copy is None:
            raise ReadingNotAcceptedError("Accepted Copy is missing")
        await self._check_follow_up_contract(root, version)
        prepare = await self.repository.load_prepare(version.id)
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
    ) -> tuple[ReadingStartResponse, bool]:
        user_id, guest_id = owner_ids(owner)
        release = await self._runtime_release()
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
        version = await self.repository.create_version(
            reading_root_id=root.id,
            runtime_release_id=release.id,
            prepare_command=prepare,
            relationship_type=relationship_type,
        )
        await self.session.refresh(version)
        await self._create_job(version.id, status=initial_job_status)
        if idempotency is not None:
            replayed = await self._save_idempotency_or_replay(
                idempotency,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
                reading_version_id=version.id,
            )
            if replayed is not None:
                return replayed, False
        return await self._summary(root, version), True

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

    async def _create_job(self, version_id: UUID, *, status: str = "queued") -> None:
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
        await self.repository.create_job(
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
        try:
            root, version = await self.repository.load_owned_version(
                record.reading_version_id,
                owner_user_id=user_id,
                owner_guest_session_id=guest_id,
            )
        except LookupError as error:
            raise ReadingNotFoundError("Reading Version not found") from error
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

    async def _summary(
        self,
        root: Any,
        version: Any,
    ) -> ReadingStartResponse:
        waiting = await self.repository.load_waiting_input(version.id)
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
            status=ReadingStatus(version.status),
            object_id=version.object_id,
            dimension_ids=list(version.dimension_ids),
            horizon=Horizon.model_validate(version.horizon),
            prior_answer=await self._projected_prior_answer(version.id),
            input_request=(
                None if waiting is None else _public_json(waiting.input_request)
            ),
            created_at=version.created_at,
            delivery_state=await self._delivery_state(root, version),
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
