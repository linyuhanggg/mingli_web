from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
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
from app.profiles.schemas import (
    ProfileConfirmRequest,
    ProfileDraftRequest,
    ProfileDraftResponse,
    ProfileListResponse,
    ProfileSummary,
)
from app.profiles.service import (
    ProfileAlreadyConfirmedError,
    ProfileNotFoundError,
    ProfileService,
)

router = APIRouter(prefix="/profiles", tags=["Profiles"])


def _service(request: Request, session: AsyncSession) -> ProfileService:
    return ProfileService(session, request.app.state.settings)


def _check_rate(owner: Owner, request: Request) -> None:
    check_rate_limiter(
        limiter=request.app.state.profile_write_rate_limiter,
        key=f"{owner.kind}:{owner.id}",
        title="Too many profile write requests",
    )


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
    await session.commit()
    mark_private(response)
    return summary


@router.post(
    "/{profile_id}/versions",
    operation_id="appendProfileVersion",
    response_model=ProfileSummary,
    status_code=status.HTTP_201_CREATED,
)
async def append_profile_version(
    request: Request,
    response: Response,
    profile_id: UUID,
    payload: ProfileConfirmRequest,
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
