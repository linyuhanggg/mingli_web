from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
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
    ProfileNotConfirmedError,
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
    except ProfileAuthorizationRequiredError as error:
        raise ApiProblem(status=400, title="Profile authorization is required") from error
    except ProfileAuthorizationPayloadError as error:
        raise ApiProblem(status=400, title="Profile authorization payload is invalid") from error
    except MinorGuardianConfirmationRequiredError as error:
        raise ApiProblem(status=400, title="Minor guardian confirmation is required") from error
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
