import asyncio
from collections.abc import AsyncIterator
from time import perf_counter
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    Owner,
    database_session,
    mark_private,
    require_device_csrf,
    require_owner,
    require_owner_csrf,
)
from app.api.errors import ApiProblem
from app.api.rate_guard import check_rate_limiter
from app.identity.models import DeviceSession
from app.privacy.service import DataRightsService
from app.profiles.schemas import (
    ConfirmProfileDraftAndStartPreviewRequest,
    ProfileConfirmRequest,
    ProfileDisplayNameUpdateRequest,
    ProfileDraftRequest,
    ProfileDraftResponse,
    ProfileListResponse,
    ProfileSummary,
    ProfileVersionListResponse,
    ProfileVersionRequest,
)
from app.profiles.service import (
    MinorGuardianConfirmationRequiredError,
    ProfileAlreadyConfirmedError,
    ProfileAuthorizationPayloadError,
    ProfileAuthorizationRequiredError,
    ProfileDifferenceNotAcknowledgedError,
    ProfileNameConflictError,
    ProfileNotConfirmedError,
    ProfileNotFoundError,
    ProfileService,
)
from app.readings.api_schemas import LatestProfileReadingResponse, ReadingStartResponse
from app.readings.capability_policy import CapabilityNotExposedError
from app.readings.request_compiler import RequestCompilationError
from app.readings.service import (
    ChartFastPathUnavailableError,
    IdempotencyConflictError,
    ProfileNotOwnedError,
    ProfileReadingUnavailableError,
    ProfileVersionNotOwnedError,
    ReadingService,
    ReadingServiceError,
    RuntimeReleaseUnavailableError,
)
from app.readings.status import ReadingStatus

router = APIRouter(prefix="/profiles", tags=["Profiles"])


class _DraftPreviewLock:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.users = 0


_draft_preview_locks: dict[tuple[str, UUID, UUID], _DraftPreviewLock] = {}


async def _serialize_draft_preview(
    draft_id: UUID,
    owner: Owner = Depends(require_owner_csrf),
) -> AsyncIterator[None]:
    key = (owner.kind, owner.id, draft_id)
    entry = _draft_preview_locks.setdefault(key, _DraftPreviewLock())
    entry.users += 1
    try:
        async with entry.lock:
            yield
    finally:
        entry.users -= 1
        if entry.users == 0 and _draft_preview_locks.get(key) is entry:
            del _draft_preview_locks[key]


def _service(request: Request, session: AsyncSession) -> ProfileService:
    return ProfileService(session, request.app.state.settings)


def _check_rate(owner: Owner, request: Request) -> None:
    check_rate_limiter(
        limiter=request.app.state.profile_write_rate_limiter,
        key=f"{owner.kind}:{owner.id}",
        title="Too many profile write requests",
    )


def _check_reading_rate(owner: Owner, request: Request) -> None:
    check_rate_limiter(
        limiter=request.app.state.reading_write_rate_limiter,
        key=f"{owner.kind}:{owner.id}",
        title="Too many reading requests",
    )
    settings = request.app.state.settings
    if not settings.dogfood_entitlement_gates_enabled:
        return
    check_rate_limiter(
        limiter=request.app.state.dogfood_daily_reading_limiter,
        key=f"{owner.kind}:{owner.id}",
        title="Daily reading limit reached",
        code=("guest_daily_reading_limit" if owner.kind == "guest" else "user_daily_reading_limit"),
        owner_kind=owner.kind,
        limit_scope="guest_session" if owner.kind == "guest" else "user_account",
    )


def _reading_problem(error: ReadingServiceError) -> ApiProblem:
    if isinstance(error, IdempotencyConflictError):
        return ApiProblem(status=409, title="Idempotency-Key conflict")
    if isinstance(error, (ProfileNotOwnedError, ProfileVersionNotOwnedError)):
        return ApiProblem(
            status=404,
            title="Subject Profile not found",
            problem_type="urn:mingli:problem:profile_not_found",
            code="profile_not_found",
        )
    if isinstance(error, ProfileReadingUnavailableError):
        return ApiProblem(
            status=409,
            title="Profile reading unavailable",
            problem_type=f"urn:mingli:problem:{error.code}",
            code=error.code,
        )
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
    return ApiProblem(status=400, title="Invalid request")


def _mark_reading_start(
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
    mark_private(response)
    return summary


@router.post(
    "/drafts",
    operation_id="createProfileDraft",
    response_model=ProfileDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile_draft(
    request: Request,
    response: Response,
    payload: ProfileDraftRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ProfileDraftResponse:
    _check_rate(owner, request)
    draft_id = await _service(request, session).create_draft(owner, label=payload.label)
    await session.commit()
    mark_private(response)
    return ProfileDraftResponse(draft_id=draft_id)


@router.delete(
    "/drafts/{draft_id}",
    operation_id="deleteProfileDraft",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_profile_draft(
    request: Request,
    response: Response,
    draft_id: UUID,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> None:
    _check_rate(owner, request)
    try:
        await _service(request, session).delete_draft(owner, draft_id)
    except ProfileNotFoundError as error:
        raise ApiProblem(status=404, title="Profile Draft not found") from error
    await session.commit()
    mark_private(response)


@router.post(
    "/drafts/{draft_id}/confirm",
    operation_id="confirmProfileDraft",
    response_model=ProfileSummary,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_profile_draft(
    request: Request,
    response: Response,
    draft_id: UUID,
    payload: ProfileConfirmRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ProfileSummary:
    _check_rate(owner, request)
    try:
        summary = await _service(request, session).confirm_draft(
            owner,
            draft_id,
            payload,
        )
    except ProfileNotFoundError as error:
        raise ApiProblem(status=404, title="Profile Draft not found") from error
    except ProfileAlreadyConfirmedError as error:
        raise ApiProblem(
            status=409,
            title="Profile Draft is already confirmed",
        ) from error
    except ProfileAuthorizationRequiredError as error:
        raise ApiProblem(status=400, title="Profile authorization is required") from error
    except ProfileAuthorizationPayloadError as error:
        raise ApiProblem(status=400, title="Profile authorization payload is invalid") from error
    except MinorGuardianConfirmationRequiredError as error:
        raise ApiProblem(status=400, title="Minor guardian confirmation is required") from error
    except ProfileNameConflictError as error:
        raise ApiProblem(
            status=409,
            title="Profile name already exists",
            problem_type="urn:mingli:problem:profile_name_conflict",
            detail="A confirmed profile already uses this name and birth date.",
            code="profile_name_conflict",
            extensions={
                "existing_profile_id": str(error.existing_profile_id),
                "existing_profile_version_id": str(error.existing_profile_version_id),
                "suggested_save_as_name": error.suggested_save_as_name,
                "options": ["overwrite", "save_as", "cancel"],
            },
        ) from error
    await session.commit()
    mark_private(response)
    return summary


@router.post(
    "/drafts/{draft_id}/readings/preview",
    operation_id="confirmProfileDraftAndStartPreviewReading",
    response_model=ReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_profile_draft_and_start_preview_reading(
    request: Request,
    response: Response,
    draft_id: UUID,
    payload: ConfirmProfileDraftAndStartPreviewRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    _draft_serialized: None = Depends(_serialize_draft_preview),
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> ReadingStartResponse:
    """Confirm one Draft and prepare its first chart in one transaction."""

    _check_rate(owner, request)
    _check_reading_rate(owner, request)
    reading_service = ReadingService(
        session,
        request.app.state.settings,
        request.app.state.chart_runtime,
    )
    reading = payload.reading
    try:
        replayed, idempotency = await reading_service.replay_confirm_profile_preview(
            owner,
            draft_id=draft_id,
            profile_payload=payload.profile.model_dump(mode="json"),
            query=reading.query,
            dimension_ids=reading.dimension_ids,
            target_year=reading.target_year,
            target_month=reading.target_month,
            target_date=reading.target_date,
            idempotency_key=idempotency_key,
        )
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    if replayed is not None:
        return _mark_reading_start((replayed, False), response)

    try:
        profile = await _service(request, session).confirm_draft(
            owner,
            draft_id,
            payload.profile,
        )
    except ProfileNotFoundError as error:
        await session.rollback()
        try:
            replayed, _ = await reading_service.replay_confirm_profile_preview(
                owner,
                draft_id=draft_id,
                profile_payload=payload.profile.model_dump(mode="json"),
                query=reading.query,
                dimension_ids=reading.dimension_ids,
                target_year=reading.target_year,
                target_month=reading.target_month,
                target_date=reading.target_date,
                idempotency_key=idempotency_key,
            )
        except ReadingServiceError as replay_error:
            raise _reading_problem(replay_error) from replay_error
        if replayed is not None:
            return _mark_reading_start((replayed, False), response)
        raise ApiProblem(
            status=404,
            title="Profile Draft not found",
            problem_type="urn:mingli:problem:profile_not_found",
            code="profile_not_found",
        ) from error
    except ProfileAlreadyConfirmedError as error:
        await session.rollback()
        discarded = await reading_service.discard_confirm_profile_preview_claim(
            idempotency
        )
        if not discarded:
            try:
                replayed, _ = await reading_service.replay_confirm_profile_preview(
                    owner,
                    draft_id=draft_id,
                    profile_payload=payload.profile.model_dump(mode="json"),
                    query=reading.query,
                    dimension_ids=reading.dimension_ids,
                    target_year=reading.target_year,
                    target_month=reading.target_month,
                    target_date=reading.target_date,
                    idempotency_key=idempotency_key,
                )
            except ReadingServiceError as replay_error:
                raise _reading_problem(replay_error) from replay_error
            if replayed is not None:
                return _mark_reading_start((replayed, False), response)
        raise ApiProblem(
            status=409,
            title="Profile Draft is already confirmed",
        ) from error
    except ProfileAuthorizationRequiredError as error:
        raise ApiProblem(status=400, title="Profile authorization is required") from error
    except ProfileAuthorizationPayloadError as error:
        raise ApiProblem(
            status=400,
            title="Profile authorization payload is invalid",
        ) from error
    except MinorGuardianConfirmationRequiredError as error:
        raise ApiProblem(
            status=400,
            title="Minor guardian confirmation is required",
        ) from error
    except ProfileNameConflictError as error:
        raise ApiProblem(
            status=409,
            title="Profile name already exists",
            problem_type="urn:mingli:problem:profile_name_conflict",
            detail="A confirmed profile already uses this name and birth date.",
            code="profile_name_conflict",
            extensions={
                "existing_profile_id": str(error.existing_profile_id),
                "existing_profile_version_id": str(error.existing_profile_version_id),
                "suggested_save_as_name": error.suggested_save_as_name,
                "options": ["overwrite", "save_as", "cancel"],
            },
        ) from error

    try:
        result = await reading_service.start_preview(
            owner,
            profile_version_id=profile.profile_version_id,
            query=reading.query,
            dimension_ids=reading.dimension_ids,
            idempotency_key=None,
            target_year=reading.target_year,
            target_month=reading.target_month,
            target_date=reading.target_date,
            idempotency_context=idempotency,
            rollback_on_failure=True,
        )
    except (RequestCompilationError, CapabilityNotExposedError) as error:
        raise ApiProblem(status=400, title="Invalid request") from error
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    if result[0].status is ReadingStatus.WAITING_INPUT:
        unavailable = ChartFastPathUnavailableError(
            "chart_runtime_need_input",
            code="chart_runtime_need_input",
        )
        raise _reading_problem(unavailable) from unavailable
    if not result[0].result_available:
        unavailable = ChartFastPathUnavailableError(
            "chart_view_model_projection_failed",
            code="chart_view_model_projection_failed",
        )
        raise _reading_problem(unavailable) from unavailable
    commit_started_at = perf_counter()
    await session.commit()
    commit_ms = (perf_counter() - commit_started_at) * 1000
    timing = result[0].fast_path_timing
    if timing is not None:
        timing.db_persistence_ms += commit_ms
        timing.total_ms += commit_ms
    return _mark_reading_start(result, response)


@router.post(
    "/{profile_id}/versions",
    operation_id="appendProfileVersion",
    response_model=ProfileSummary,
    status_code=status.HTTP_201_CREATED,
)
async def append_profile_version(
    profile_id: UUID,
    request: Request,
    response: Response,
    payload: ProfileVersionRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ProfileSummary:
    _check_rate(owner, request)
    try:
        summary = await _service(request, session).append_version(
            owner,
            profile_id,
            payload,
        )
    except ProfileNotFoundError as error:
        raise ApiProblem(status=404, title="Subject Profile not found") from error
    except ProfileNotConfirmedError as error:
        raise ApiProblem(status=409, title="Subject Profile has no confirmed version") from error
    except ProfileAuthorizationRequiredError as error:
        raise ApiProblem(status=400, title="Profile authorization is required") from error
    except ProfileAuthorizationPayloadError as error:
        raise ApiProblem(status=400, title="Profile authorization payload is invalid") from error
    except MinorGuardianConfirmationRequiredError as error:
        raise ApiProblem(status=400, title="Minor guardian confirmation is required") from error
    except ProfileDifferenceNotAcknowledgedError as error:
        raise ApiProblem(
            status=400,
            title="Profile version difference must be acknowledged",
        ) from error
    except ProfileNameConflictError as error:
        raise ApiProblem(
            status=409,
            title="Profile name already exists",
            problem_type="urn:mingli:problem:profile_name_conflict",
            detail="A confirmed profile already uses this name and birth date.",
            code="profile_name_conflict",
            extensions={
                "existing_profile_id": str(error.existing_profile_id),
                "existing_profile_version_id": str(error.existing_profile_version_id),
                "suggested_save_as_name": error.suggested_save_as_name,
                "options": ["overwrite", "save_as", "cancel"],
            },
        ) from error
    await session.commit()
    mark_private(response)
    return summary


@router.get(
    "",
    operation_id="listProfiles",
    response_model=ProfileListResponse,
)
async def list_profiles(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner),
) -> ProfileListResponse:
    summaries = await _service(request, session).list_profiles(owner)
    await session.commit()
    mark_private(response)
    return ProfileListResponse(profiles=summaries)


@router.get(
    "/{profile_id}/versions",
    operation_id="listProfileVersions",
    response_model=ProfileVersionListResponse,
)
async def list_profile_versions(
    profile_id: UUID,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner),
) -> ProfileVersionListResponse:
    try:
        versions = await _service(request, session).list_profile_versions(owner, profile_id)
    except ProfileNotFoundError as error:
        raise ApiProblem(status=404, title="Subject Profile not found") from error
    await session.commit()
    mark_private(response)
    return ProfileVersionListResponse(versions=versions)


@router.get(
    "/{profile_id}/readings/latest",
    operation_id="getLatestProfileReading",
    response_model=LatestProfileReadingResponse,
)
async def get_latest_profile_reading(
    profile_id: UUID,
    request: Request,
    response: Response,
    product_id: str = Query(min_length=1, max_length=80, pattern=r"^[a-z0-9-]+$"),
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner),
) -> LatestProfileReadingResponse:
    try:
        result = await ReadingService(
            session,
            request.app.state.settings,
            request.app.state.chart_runtime,
        ).get_latest_profile_reading(
            owner,
            profile_id=profile_id,
            product_id=product_id,
        )
    except ReadingServiceError as error:
        raise _reading_problem(error) from error
    mark_private(response)
    return result


@router.patch(
    "/{profile_id}",
    operation_id="updateProfileDisplayName",
    response_model=ProfileSummary,
)
async def update_profile_display_name(
    profile_id: UUID,
    request: Request,
    response: Response,
    payload: ProfileDisplayNameUpdateRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> ProfileSummary:
    _check_rate(owner, request)
    try:
        summary = await _service(request, session).update_display_name(
            owner,
            profile_id,
            payload.display_name,
        )
    except ProfileNotFoundError as error:
        raise ApiProblem(status=404, title="Subject Profile not found") from error
    except ProfileNotConfirmedError as error:
        raise ApiProblem(
            status=409,
            title="Subject Profile has no confirmed version",
        ) from error
    except ProfileNameConflictError as error:
        raise ApiProblem(
            status=409,
            title="Profile name already exists",
            problem_type="urn:mingli:problem:profile_name_conflict",
            detail="A confirmed profile already uses this name and birth date.",
            code="profile_name_conflict",
            extensions={
                "existing_profile_id": str(error.existing_profile_id),
                "existing_profile_version_id": str(error.existing_profile_version_id),
                "suggested_save_as_name": error.suggested_save_as_name,
                "options": ["overwrite", "save_as", "cancel"],
            },
        ) from error
    await session.commit()
    mark_private(response)
    return summary


@router.delete(
    "/{profile_id}",
    operation_id="deleteProfile",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_profile(
    request: Request,
    response: Response,
    profile_id: UUID,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_csrf),
) -> None:
    deleted = await DataRightsService(
        session, request.app.state.settings
    ).delete_profile(device_session.user_id, profile_id)
    if not deleted:
        raise ApiProblem(status=404, title="Profile not found")
    await session.commit()
    mark_private(response)
