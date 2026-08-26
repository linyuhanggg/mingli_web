from datetime import timedelta
from time import perf_counter
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    Owner,
    database_session,
    mark_private,
    require_owner,
    require_owner_csrf,
)
from app.api.errors import ApiProblem
from app.api.rate_guard import check_rate_limiter
from app.media.api_schemas import PhysiognomyStartRequest
from app.media.physiognomy import (
    MediaNotFoundError,
    MediaNotReadyError,
    PhysiognomyMediaError,
)
from app.media.service import PhysiognomyMediaService
from app.readings.api_schemas import (
    BaziDeepStartRequest,
    CanwenStartRequest,
    ChartSimilarityStartRequest,
    ClaimVerificationRequest,
    ClaimVerificationSummary,
    CreateExportRequest,
    CreateShareRequest,
    DaliurenStartRequest,
    EventArtStartRequest,
    ExportResponse,
    FengshuiStartRequest,
    FiveElementsFactsStartRequest,
    FollowUpRequest,
    FortuneStartRequest,
    FulfillmentBindingRequest,
    FulfillmentBindingResponse,
    HecanStartRequest,
    LiuyaoDeepStartRequest,
    LiuyaoStartRequest,
    LumingNayinStartRequest,
    MeihuaStartRequest,
    PreviewStartRequest,
    QimenDeepStartRequest,
    ReadingListResponse,
    ReadingResultResponse,
    ReadingStartResponse,
    ReadingVerificationSummary,
    RecastLiuyaoRequest,
    RecastProfileRequest,
    RecastRequest,
    RelationshipStartRequest,
    ReportFeedbackRequest,
    ReportFeedbackSummary,
    RhythmStartRequest,
    SelectionStartRequest,
    SharedReadingResponse,
    ShareResponse,
    SupplyInputRequest,
    TaiyiStartRequest,
    TimeCheckStartRequest,
    VerificationRequest,
    WenshiStartRequest,
)
from app.readings.capability_policy import CapabilityNotExposedError
from app.readings.delivery import (
    ExportUnavailableError,
    ReadingDeliveryError,
    ReadingDeliveryService,
    ShareUnavailableError,
)
from app.readings.request_compiler import RequestCompilationError
from app.readings.service import (
    ChartFastPathUnavailableError,
    IdempotencyConflictError,
    InvalidReadingInputError,
    PaidReadingNotGrantedError,
    ProfileVersionNotOwnedError,
    ReadingAlreadyQueuedError,
    ReadingFollowUpUnavailableError,
    ReadingFulfillmentUnavailableError,
    ReadingNotAcceptedError,
    ReadingNotFoundError,
    ReadingNotWaitingInputError,
    ReadingService,
    ReadingServiceError,
    RuntimeReleaseUnavailableError,
)

router = APIRouter(prefix="/readings", tags=["Readings"])
share_router = APIRouter(prefix="/share", tags=["Readings"])
export_router = APIRouter(prefix="/exports", tags=["Readings"])


def _delivery_service(request: Request, session: AsyncSession) -> ReadingDeliveryService:
    from app.security.envelope import EnvelopeCipher

    return ReadingDeliveryService(
        session,
        EnvelopeCipher.from_settings(request.app.state.settings),
    )


def _service(request: Request, session: AsyncSession) -> ReadingService:
    return ReadingService(
        session,
        request.app.state.settings,
        request.app.state.chart_runtime,
    )


def _check_rate(owner: Owner, request: Request) -> None:
    check_rate_limiter(
        limiter=request.app.state.reading_write_rate_limiter,
        key=f"{owner.kind}:{owner.id}",
        title="Too many reading requests",
    )


def _check_dogfood_daily_limits(
    owner: Owner,
    request: Request,
    *,
    paid: bool,
) -> None:
    """Apply dogfood day ceilings only when entitlement gates are on."""
    settings = request.app.state.settings
    if not settings.dogfood_entitlement_gates_enabled:
        return
    owner_key = f"{owner.kind}:{owner.id}"
    limit_scope = "guest_session" if owner.kind == "guest" else "user_account"
    check_rate_limiter(
        limiter=request.app.state.dogfood_daily_reading_limiter,
        key=owner_key,
        title="Daily reading limit reached",
        code="guest_daily_reading_limit"
        if owner.kind == "guest"
        else "user_daily_reading_limit",
        owner_kind=owner.kind,
        limit_scope=limit_scope,
    )
    if paid:
        check_rate_limiter(
            limiter=request.app.state.dogfood_daily_paid_reading_limiter,
            key=owner_key,
            title="Daily paid reading limit reached",
            code="guest_daily_paid_reading_limit"
            if owner.kind == "guest"
            else "user_daily_paid_reading_limit",
            owner_kind=owner.kind,
            limit_scope=limit_scope,
        )


def _start_response(
    result: tuple[ReadingStartResponse, bool],
    response: Response,
) -> ReadingStartResponse:
    summary, created = result
    if not created:
        response.status_code = status.HTTP_200_OK
    timing = summary.fast_path_timing
    if timing is not None:
        response.headers["Server-Timing"] = ", ".join(
            (
                f"chart-runtime;dur={timing.runtime_one_shot_ms:.3f}",
                f"chart-db;dur={timing.db_persistence_ms:.3f}",
                f"chart-direct;dur={timing.total_ms:.3f}",
                "chart-queue;dur=0",
                "chart-worker;dur=0",
            )
        )
    return summary


async def _commit_chart_start_response(
    result: tuple[ReadingStartResponse, bool],
    response: Response,
    session: AsyncSession,
) -> ReadingStartResponse:
    commit_started_at = perf_counter()
    await session.commit()
    commit_ms = (perf_counter() - commit_started_at) * 1000
    timing = result[0].fast_path_timing
    if timing is not None:
        timing.db_persistence_ms += commit_ms
        timing.total_ms += commit_ms
    mark_private(response)
    return _start_response(result, response)


def _reading_problem(error: ReadingServiceError) -> ApiProblem:
    if isinstance(error, IdempotencyConflictError):
        return ApiProblem(status=409, title="Idempotency-Key conflict")
    if isinstance(error, ReadingNotFoundError):
        return ApiProblem(status=404, title="Reading not found")
    if isinstance(error, ProfileVersionNotOwnedError):
        return ApiProblem(status=404, title="Profile Version not found")
    if isinstance(error, InvalidReadingInputError):
        return ApiProblem(status=400, title="Invalid reading input")
    if isinstance(error, ReadingNotWaitingInputError):
        return ApiProblem(status=409, title="Reading is not waiting for input")
    if isinstance(error, ReadingAlreadyQueuedError):
        return ApiProblem(status=409, title="Reading is already queued")
    if isinstance(error, ReadingNotAcceptedError):
        return ApiProblem(status=409, title="Reading is not accepted")
    if isinstance(error, ReadingFollowUpUnavailableError):
        return ApiProblem(status=409, title="Follow-up unavailable", detail=str(error))
    if isinstance(error, ReadingFulfillmentUnavailableError):
        return ApiProblem(status=409, title="Fulfillment unavailable")
    if isinstance(error, RuntimeReleaseUnavailableError):
        return ApiProblem(status=503, title="Runtime release unavailable")
    if isinstance(error, ChartFastPathUnavailableError):
        return ApiProblem(
            status=400 if error.code == "chart_runtime_need_input" else 503,
            title="Chart generation unavailable",
            problem_type=f"urn:mingli:problem:{error.code}",
            detail=error.detail,
            code=error.code,
        )
    if isinstance(error, PaidReadingNotGrantedError):
        return ApiProblem(
            status=403,
            title=error.title,
            problem_type=f"urn:mingli:problem:{error.code}",
            detail=error.detail,
            code=error.code,
        )
    return ApiProblem(status=400, title="Invalid request")


def _delivery_problem(error: ReadingDeliveryError) -> ApiProblem:
    if isinstance(error, ShareUnavailableError):
        return ApiProblem(status=404, title="Share snapshot not found")
    if isinstance(error, ExportUnavailableError):
        return ApiProblem(status=404, title="Reading export not found")
    if "not accepted" in str(error).lower():
        return ApiProblem(status=409, title="Reading is not accepted")
    if "not found" in str(error).lower():
        return ApiProblem(status=404, title="Reading document not found")
    return ApiProblem(status=400, title="Invalid request")


@router.post(
    "/preview",
    operation_id="startPreviewReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_preview_reading(
    request: Request,
    response: Response,
    payload: PreviewStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_preview(
            owner,
            profile_version_id=payload.profile_version_id,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
            target_year=payload.target_year,
            target_month=payload.target_month,
            target_date=payload.target_date,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    return await _commit_chart_start_response(result, response, session)


@router.post(
    "/bazi-deep",
    operation_id="startBaziDeepReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_bazi_deep_reading(
    request: Request,
    response: Response,
    payload: BaziDeepStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=True)
    try:
        result = await _service(request, session).start_bazi_deep(
            owner,
            profile_version_id=payload.profile_version_id,
            query=payload.query,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/chart-similarity",
    operation_id="startChartSimilarityReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_chart_similarity_reading(
    request: Request,
    response: Response,
    payload: ChartSimilarityStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_chart_similarity(
            owner,
            profile_version_ids=payload.profile_version_ids,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/canwen",
    operation_id="startCanwenReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_canwen_reading(
    request: Request,
    response: Response,
    payload: CanwenStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_canwen(
            owner,
            profile_version_id=payload.profile_version_id,
            selected_art_ids=payload.selected_art_ids,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/hecan",
    operation_id="startHecanReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_hecan_reading(
    request: Request,
    response: Response,
    payload: HecanStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_hecan(
            owner,
            profile_version_id=payload.profile_version_id,
            selected_art_ids=payload.selected_art_ids,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


async def _start_relationship_reading(
    request: Request,
    response: Response,
    payload: RelationshipStartRequest,
    session: AsyncSession,
    owner: Owner,
    *,
    product_id: str,
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_relationship(
            owner,
            product_id=product_id,
            profile_version_ids=payload.profile_version_ids,
            relationship_type=payload.relationship_type,
            dimension_ids=payload.dimension_ids,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/bazi-relationship",
    operation_id="startBaziRelationshipReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_bazi_relationship_reading(
    request: Request,
    response: Response,
    payload: RelationshipStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ReadingStartResponse:
    return await _start_relationship_reading(
        request,
        response,
        payload,
        session,
        owner,
        product_id="bazi-relationship",
    )


@router.post(
    "/ziwei-relationship",
    operation_id="startZiweiRelationshipReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_ziwei_relationship_reading(
    request: Request,
    response: Response,
    payload: RelationshipStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ReadingStartResponse:
    return await _start_relationship_reading(
        request,
        response,
        payload,
        session,
        owner,
        product_id="ziwei-relationship",
    )


@router.post(
    "/qizheng-relationship",
    operation_id="startQizhengRelationshipReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_qizheng_relationship_reading(
    request: Request,
    response: Response,
    payload: RelationshipStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ReadingStartResponse:
    return await _start_relationship_reading(
        request,
        response,
        payload,
        session,
        owner,
        product_id="qizheng-relationship",
    )


@router.post(
    "/today",
    operation_id="startTodayReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_today_reading(
    request: Request,
    response: Response,
    payload: FortuneStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=True)
    try:
        result = await _service(request, session).start_fortune(
            owner,
            action="today",
            profile_version_id=payload.profile_version_id,
            query=payload.query,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/week",
    operation_id="startWeekReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_week_reading(
    request: Request,
    response: Response,
    payload: FortuneStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=True)
    try:
        result = await _service(request, session).start_fortune(
            owner,
            action="near_seven",
            profile_version_id=payload.profile_version_id,
            query=payload.query,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/liuyao",
    operation_id="startLiuyaoReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_liuyao_reading(
    request: Request,
    response: Response,
    payload: LiuyaoStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    cast_value = tuple(payload.cast) if isinstance(payload.cast, list) else payload.cast
    try:
        result = await _service(request, session).start_liuyao(
            owner,
            cast=cast_value,
            event_datetime=payload.event_datetime,
            timezone=payload.timezone,
            location=payload.location,
            subject_ref=payload.subject_ref,
            query=payload.query,
            question_class=payload.question_class,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    return await _commit_chart_start_response(result, response, session)


@router.post(
    "/liuyao-deep",
    operation_id="startLiuyaoDeepReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_liuyao_deep_reading(
    request: Request,
    response: Response,
    payload: LiuyaoDeepStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=True)
    cast_value = tuple(payload.cast) if isinstance(payload.cast, list) else payload.cast
    try:
        result = await _service(request, session).start_liuyao_deep(
            owner,
            cast=cast_value,
            event_datetime=payload.event_datetime,
            timezone=payload.timezone,
            location=payload.location,
            subject_ref=payload.subject_ref,
            query=payload.query,
            question_class=payload.question_class,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/wenshi",
    operation_id="startWenshiReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_wenshi_reading(
    request: Request,
    response: Response,
    payload: WenshiStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=True)
    cast_value = tuple(payload.cast) if isinstance(payload.cast, list) else payload.cast
    try:
        result = await _service(request, session).start_wenshi(
            owner,
            cast=cast_value,
            event_datetime=payload.event_datetime,
            timezone=payload.timezone,
            location=payload.location,
            subject_ref=payload.subject_ref,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            time_basis_policy=payload.time_basis_policy,
            zi_hour_policy=payload.zi_hour_policy,
            longitude=payload.longitude,
            latitude=payload.latitude,
            coordinate_source=payload.coordinate_source,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/ziwei",
    operation_id="startZiweiReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_ziwei_reading(
    request: Request,
    response: Response,
    payload: PreviewStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_ziwei(
            owner,
            profile_version_id=payload.profile_version_id,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
            target_year=payload.target_year,
            target_month=payload.target_month,
            target_date=payload.target_date,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    return await _commit_chart_start_response(result, response, session)


@router.post(
    "/qizheng",
    operation_id="startQizhengReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_qizheng_reading(
    request: Request,
    response: Response,
    payload: PreviewStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_qizheng(
            owner,
            profile_version_id=payload.profile_version_id,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
            target_year=payload.target_year,
            target_month=payload.target_month,
            target_date=payload.target_date,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/luming-nayin",
    operation_id="startLumingNayinReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_luming_nayin_reading(
    request: Request,
    response: Response,
    payload: LumingNayinStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_luming_nayin(
            owner,
            profile_version_id=payload.profile_version_id,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/five-elements-facts",
    operation_id="startFiveElementsFactsReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_five_elements_facts_reading(
    request: Request,
    response: Response,
    payload: FiveElementsFactsStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_five_elements_facts(
            owner,
            profile_version_id=payload.profile_version_id,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/time-check",
    operation_id="startTimeCheckReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_time_check_reading(
    request: Request,
    response: Response,
    payload: TimeCheckStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_time_check(
            owner,
            profile_version_id=payload.profile_version_id,
            time_range_start=payload.time_range_start,
            time_range_end=payload.time_range_end,
            known_events=payload.known_events,
            known_event_facts=[
                event.model_dump(mode="json") for event in payload.known_event_facts
            ],
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/rhythm",
    operation_id="startRhythmReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_rhythm_reading(
    request: Request,
    response: Response,
    payload: RhythmStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_rhythm(
            owner,
            profile_version_id=payload.profile_version_id,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/taiyi",
    operation_id="startTaiyiReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_taiyi_reading(
    request: Request,
    response: Response,
    payload: TaiyiStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_taiyi(
            owner,
            reference_datetime=payload.event_datetime,
            timezone=payload.timezone,
            location=payload.location,
            subject_ref=payload.subject_ref,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            time_basis_policy=payload.time_basis_policy,
            zi_hour_policy=payload.zi_hour_policy,
            longitude=payload.longitude,
            latitude=payload.latitude,
            coordinate_source=payload.coordinate_source,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/selection",
    operation_id="startSelectionReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_selection_reading(
    request: Request,
    response: Response,
    payload: SelectionStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_selection(
            owner,
            event_profile=payload.event_profile,
            requested_actions=tuple(payload.requested_actions),
            date_range_start=payload.date_range_start.isoformat(),
            date_range_end=payload.date_range_end.isoformat(),
            timezone=payload.timezone,
            location=payload.location,
            subject_ref=payload.subject_ref,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            requested_scopes=tuple(payload.requested_scopes),
            hard_constraints=payload.hard_constraints,
            participant_facts=tuple(payload.participant_facts),
            directional_context=payload.directional_context,
            include_folk_comparison=payload.include_folk_comparison,
            longitude=payload.longitude,
            latitude=payload.latitude,
            coordinate_source=payload.coordinate_source,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/fengshui",
    operation_id="startFengshuiReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_fengshui_reading(
    request: Request,
    response: Response,
    payload: FengshuiStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_fengshui(
            owner,
            subject_ref=payload.subject_ref,
            fengshui_spec=payload.fengshui_spec,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/qimen",
    operation_id="startQimenReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_qimen_reading(
    request: Request,
    response: Response,
    payload: EventArtStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_qimen(
            owner,
            event_datetime=payload.event_datetime,
            timezone=payload.timezone,
            location=payload.location,
            subject_ref=payload.subject_ref,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            time_basis_policy=payload.time_basis_policy,
            zi_hour_policy=payload.zi_hour_policy,
            longitude=payload.longitude,
            latitude=payload.latitude,
            coordinate_source=payload.coordinate_source,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/qimen-deep",
    operation_id="startQimenDeepReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_qimen_deep_reading(
    request: Request,
    response: Response,
    payload: QimenDeepStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    try:
        result = await _service(request, session).start_qimen_deep(
            owner,
            event_datetime=payload.event_datetime,
            timezone=payload.timezone,
            location=payload.location,
            subject_ref=payload.subject_ref,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            time_basis_policy=payload.time_basis_policy,
            zi_hour_policy=payload.zi_hour_policy,
            longitude=payload.longitude,
            latitude=payload.latitude,
            coordinate_source=payload.coordinate_source,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/daliuren",
    operation_id="startDaliurenReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_daliuren_reading(
    request: Request,
    response: Response,
    payload: DaliurenStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_liuren(
            owner,
            event_datetime=payload.event_datetime,
            timezone=payload.timezone,
            location=payload.location,
            subject_ref=payload.subject_ref,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            time_basis_policy=payload.time_basis_policy,
            zi_hour_policy=payload.zi_hour_policy,
            longitude=payload.longitude,
            latitude=payload.latitude,
            coordinate_source=payload.coordinate_source,
            timing_start=payload.timing_start,
            timing_end=payload.timing_end,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    return await _commit_chart_start_response(result, response, session)


@router.post(
    "/meihua",
    operation_id="startMeihuaReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_meihua_reading(
    request: Request,
    response: Response,
    payload: MeihuaStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    try:
        result = await _service(request, session).start_meihua(
            owner,
            casting_method=payload.casting_method,
            event_datetime=payload.event_datetime,
            timezone=payload.timezone,
            location=payload.location,
            subject_ref=payload.subject_ref,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            time_basis_policy=payload.time_basis_policy,
            zi_hour_policy=payload.zi_hour_policy,
            longitude=payload.longitude,
            latitude=payload.latitude,
            coordinate_source=payload.coordinate_source,
            number=payload.number,
            count=payload.count,
            upper_trigram=payload.upper_trigram,
            lower_trigram=payload.lower_trigram,
            moving_line=payload.moving_line,
            provenance=payload.provenance,
            observation_source=payload.observation_source,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    return await _commit_chart_start_response(result, response, session)


@router.post(
    "/physiognomy",
    operation_id="startPhysiognomyReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_physiognomy_reading(
    request: Request,
    response: Response,
    payload: PhysiognomyStartRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(owner, request, paid=False)
    resolved_query = payload.query or "请按已确认的可见观察展示相法结构。"
    observations = [item.model_dump() for item in payload.observations]
    runtime_subject_ref = f"sid-{payload.asset_id.hex}"
    try:
        runtime_input = await PhysiognomyMediaService(
            session,
            request.app.state.physiognomy_media_store,
        ).build_runtime_input(
            owner_kind=owner.kind,
            owner_id=owner.id,
            asset_id=payload.asset_id,
            subject_ref=runtime_subject_ref,
            observations=observations,
            dimension_ids=tuple(payload.dimension_ids),
        )
        prepare = runtime_input.to_prepare(
            query=resolved_query,
            action="physiognomy_preview",
        )
        result = await _service(request, session).start_physiognomy(
            owner,
            asset_id=payload.asset_id,
            subject_ref=runtime_subject_ref,
            query=payload.query,
            dimension_ids=payload.dimension_ids,
            observations=observations,
            prepare=prepare,
            idempotency_key=idempotency_key,
        )
    except (MediaNotFoundError, MediaNotReadyError) as error:
        raise ApiProblem(status=404, title="照片资产不存在或已失效") from error
    except PhysiognomyMediaError as error:
        raise ApiProblem(status=400, title="结构化观察不符合相法输入契约") from error
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.get(
    "",
    operation_id="listReadings",
    response_model=ReadingListResponse,
)
async def list_readings(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner),
) -> ReadingListResponse:
    summaries = await _service(request, session).list_summaries(owner)
    await session.commit()
    mark_private(response)
    return ReadingListResponse(readings=summaries)


@router.get(
    "/{reading_version_id}",
    operation_id="getReadingVersion",
    response_model=ReadingStartResponse,
)
async def get_reading_version(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner),
) -> ReadingStartResponse:
    try:
        summary = await _service(request, session).get_summary(
            owner,
            reading_version_id,
        )
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return summary


@router.post(
    "/{reading_version_id}/fulfillment",
    operation_id="bindReadingFulfillment",
    response_model=FulfillmentBindingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bind_reading_fulfillment(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    payload: FulfillmentBindingRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> FulfillmentBindingResponse:
    _check_rate(owner, request)
    try:
        result = await _service(request, session).bind_paid_fulfillment(
            owner,
            reading_version_id=reading_version_id,
            payment_id=payload.payment_id,
            idempotency_key=idempotency_key,
        )
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return FulfillmentBindingResponse(
        fulfillment_id=result.fulfillment_id,
        reading_version_id=result.reading_version_id,
        reading_job_id=result.reading_job_id,
        status=result.status,
        created=result.created,
    )


@router.post(
    "/{reading_version_id}/input",
    operation_id="supplyReadingInput",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def supply_reading_input(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    payload: SupplyInputRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    try:
        summary = await _service(request, session).supply_input(
            owner,
            version_id=reading_version_id,
            values=payload.values,
        )
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    return await _commit_chart_start_response((summary, True), response, session)


@router.get(
    "/{reading_version_id}/result",
    operation_id="getReadingResult",
    response_model=ReadingResultResponse,
)
async def get_reading_result(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner),
) -> ReadingResultResponse:
    try:
        result = await _service(request, session).get_result(
            owner,
            reading_version_id,
        )
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return result


@router.post(
    "/{reading_version_id}/verification",
    operation_id="submitReadingVerification",
    response_model=ReadingVerificationSummary,
    status_code=status.HTTP_201_CREATED,
)
async def submit_reading_verification(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    payload: VerificationRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ReadingVerificationSummary:
    _check_rate(owner, request)
    try:
        summary, created = await _service(request, session).submit_verification(
            owner,
            version_id=reading_version_id,
            outcome=payload.outcome,
            note=payload.note,
        )
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    if not created:
        response.status_code = status.HTTP_200_OK
    return summary


@router.post(
    "/{reading_version_id}/follow-up",
    operation_id="createReadingFollowUp",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reading_follow_up(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    payload: FollowUpRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    try:
        result = await _service(request, session).follow_up(
            owner,
            version_id=reading_version_id,
            query=payload.query,
            idempotency_key=idempotency_key,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    await session.commit()
    mark_private(response)
    return _start_response(result, response)


@router.post(
    "/{reading_version_id}/recast",
    operation_id="createReadingRecast",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reading_recast(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    payload: RecastRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    _check_rate(owner, request)
    _check_dogfood_daily_limits(
        owner,
        request,
        paid=(
            isinstance(payload, RecastProfileRequest)
            and payload.action in {"today", "week"}
        ),
    )
    try:
        service = _service(request, session)
        if isinstance(payload, RecastProfileRequest):
            result = await service.recast_profile(
                owner,
                source_version_id=reading_version_id,
                action=payload.action,
                profile_version_id=payload.profile_version_id,
                query=payload.query,
                dimension_ids=payload.dimension_ids,
                idempotency_key=idempotency_key,
            )
        elif isinstance(payload, RecastLiuyaoRequest):
            cast_value = tuple(payload.cast) if isinstance(payload.cast, list) else payload.cast
            result = await service.recast_liuyao(
                owner,
                source_version_id=reading_version_id,
                cast=cast_value,
                event_datetime=payload.event_datetime,
                timezone=payload.timezone,
                location=payload.location,
                subject_ref=payload.subject_ref,
                query=payload.query,
                question_class=payload.question_class,
                dimension_ids=payload.dimension_ids,
                idempotency_key=idempotency_key,
            )
        else:
            raise ApiProblem(status=400, title="Invalid Recast request")
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    return await _commit_chart_start_response(result, response, session)


@router.post(
    "/{reading_version_id}/claims/{claim_id}/verification",
    operation_id="submitClaimVerification",
    response_model=ClaimVerificationSummary,
    status_code=status.HTTP_201_CREATED,
)
async def submit_claim_verification(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    claim_id: str,
    payload: ClaimVerificationRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ClaimVerificationSummary:
    _check_rate(owner, request)
    try:
        result, created = await _delivery_service(request, session).submit_claim_verification(
            owner,
            version_id=reading_version_id,
            claim_id=claim_id,
            outcome=payload.outcome,
            note=payload.note,
        )
    except ReadingDeliveryError as error:
        raise _delivery_problem(error) from error
    await session.commit()
    mark_private(response)
    if not created:
        response.status_code = status.HTTP_200_OK
    return ClaimVerificationSummary(
        verification_id=result.id,
        reading_version_id=result.reading_version_id,
        claim_id=result.claim_id,
        outcome=result.outcome,
        note=result.note,
        created_at=result.created_at,
    )


@router.post(
    "/{reading_version_id}/feedback",
    operation_id="submitReportFeedback",
    response_model=ReportFeedbackSummary,
    status_code=status.HTTP_201_CREATED,
)
async def submit_report_feedback(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    payload: ReportFeedbackRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ReportFeedbackSummary:
    _check_rate(owner, request)
    try:
        result = await _delivery_service(request, session).submit_feedback(
            owner,
            version_id=reading_version_id,
            outcome=payload.outcome,
            note=payload.note,
        )
    except ReadingDeliveryError as error:
        raise _delivery_problem(error) from error
    await session.commit()
    mark_private(response)
    return ReportFeedbackSummary(
        feedback_id=result.id,
        reading_version_id=result.reading_version_id,
        outcome=result.outcome,
        note=result.note,
        created_at=result.created_at,
    )


@router.post(
    "/{reading_version_id}/export",
    operation_id="createReadingExport",
    response_model=ExportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reading_export(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    payload: CreateExportRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ExportResponse:
    _check_rate(owner, request)
    try:
        result = await _delivery_service(request, session).create_export(
            owner,
            version_id=reading_version_id,
            export_format=payload.format,
            ttl=timedelta(seconds=payload.ttl_seconds),
        )
    except ReadingDeliveryError as error:
        raise _delivery_problem(error) from error
    except ValueError as error:
        raise ApiProblem(status=400, title="Invalid export expiry") from error
    await session.commit()
    mark_private(response)
    return ExportResponse(
        export_id=result.export_id,
        token=result.token,
        format=result.format,
        content_type=result.content_type,
        file_name=result.file_name,
        expires_at=result.expires_at,
    )


@router.post(
    "/{reading_version_id}/share",
    operation_id="createReadingShare",
    response_model=ShareResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reading_share(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    payload: CreateShareRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ShareResponse:
    _check_rate(owner, request)
    try:
        result = await _delivery_service(request, session).create_share(
            owner,
            version_id=reading_version_id,
            ttl=timedelta(seconds=payload.ttl_seconds),
        )
    except ReadingDeliveryError as error:
        raise _delivery_problem(error) from error
    except ValueError as error:
        raise ApiProblem(status=400, title="Invalid share expiry") from error
    await session.commit()
    mark_private(response)
    return ShareResponse(
        snapshot_id=result.snapshot_id,
        token=result.token,
        expires_at=result.expires_at,
    )


@router.delete(
    "/{reading_version_id}/share/{snapshot_id}",
    operation_id="revokeReadingShare",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_reading_share(
    request: Request,
    response: Response,
    reading_version_id: UUID,
    snapshot_id: UUID,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> None:
    _check_rate(owner, request)
    try:
        await _delivery_service(request, session).revoke_share(
            owner,
            snapshot_id,
            reading_version_id,
        )
    except ReadingDeliveryError as error:
        raise _delivery_problem(error) from error
    await session.commit()
    mark_private(response)


@share_router.get(
    "/{token}",
    operation_id="getReadingShare",
    response_model=SharedReadingResponse,
)
async def get_reading_share(
    token: str,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
) -> SharedReadingResponse:
    try:
        document = await _delivery_service(request, session).load_share(token)
    except ReadingDeliveryError as error:
        raise _delivery_problem(error) from error
    await session.commit()
    mark_private(response)
    return SharedReadingResponse(document=document)


@export_router.get(
    "/{token}",
    operation_id="downloadReadingExport",
)
async def download_reading_export(
    token: str,
    request: Request,
    session: AsyncSession = Depends(database_session),
) -> Response:
    try:
        export = await _delivery_service(request, session).load_export(token)
    except ReadingDeliveryError as error:
        raise _delivery_problem(error) from error
    await session.commit()
    download = Response(
        content=export.payload,
        media_type=export.content_type,
        headers={
            "content-disposition": f'attachment; filename="{export.file_name}"',
        },
    )
    mark_private(download)
    return download
