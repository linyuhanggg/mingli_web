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
from app.readings.api_schemas import (
    FollowUpRequest,
    FortuneStartRequest,
    LiuyaoStartRequest,
    PreviewStartRequest,
    ReadingResultResponse,
    ReadingStartResponse,
    ReadingVerificationSummary,
    SupplyInputRequest,
    VerificationRequest,
)
from app.readings.capability_policy import CapabilityNotExposedError
from app.readings.request_compiler import RequestCompilationError
from app.readings.service import (
    IdempotencyConflictError,
    InvalidReadingInputError,
    ProfileVersionNotOwnedError,
    ReadingAlreadyQueuedError,
    ReadingNotAcceptedError,
    ReadingNotFoundError,
    ReadingNotWaitingInputError,
    ReadingService,
    ReadingServiceError,
    RuntimeReleaseUnavailableError,
)

router = APIRouter(prefix="/readings", tags=["Readings"])


def _service(request: Request, session: AsyncSession) -> ReadingService:
    return ReadingService(session, request.app.state.settings)


def _check_rate(owner: Owner, request: Request) -> None:
    check_rate_limiter(
        limiter=request.app.state.reading_write_rate_limiter,
        key=f"{owner.kind}:{owner.id}",
        title="Too many reading requests",
    )


def _start_response(
    result: tuple[ReadingStartResponse, bool],
    response: Response,
) -> ReadingStartResponse:
    summary, created = result
    if not created:
        response.status_code = status.HTTP_200_OK
    return summary


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
    if isinstance(error, RuntimeReleaseUnavailableError):
        return ApiProblem(status=503, title="Runtime release unavailable")
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
    try:
        result = await _service(request, session).start_preview(
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
    await session.commit()
    mark_private(response)
    return summary


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
