from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import Owner, database_session, mark_private, require_owner_csrf
from app.api.errors import ApiProblem
from app.api.rate_guard import check_rate_limiter
from app.media.api_schemas import ObservationMode, PhysiognomyMediaResponse
from app.media.physiognomy import (
    MAX_MEDIA_BYTES,
    MediaNotFoundError,
    MediaQualityError,
    MediaValidationError,
    PhysiognomyMediaAsset,
    image_dimensions,
)
from app.media.service import PhysiognomyMediaService

router = APIRouter(prefix="/physiognomy", tags=["Physiognomy"])
PHOTO_CONSENT_POLICY_VERSION = "physiognomy-photo-v1"


def _service(request: Request, session: AsyncSession) -> PhysiognomyMediaService:
    return PhysiognomyMediaService(session, request.app.state.physiognomy_media_store)


def _check_rate(request: Request, owner: Owner) -> None:
    check_rate_limiter(
        limiter=request.app.state.reading_write_rate_limiter,
        key=f"{owner.kind}:{owner.id}",
        title="Too many physiognomy media requests",
    )


def _response(asset: PhysiognomyMediaAsset) -> PhysiognomyMediaResponse:
    return PhysiognomyMediaResponse(
        asset_id=UUID(asset.asset_id),
        content_type=asset.content_type,
        byte_size=asset.byte_size,
        width=asset.width,
        height=asset.height,
        mode=asset.mode,
        status=asset.status,
        created_at=asset.created_at.isoformat(),
        expires_at=asset.expires_at.isoformat(),
    )


@router.post(
    "/media",
    operation_id="uploadPhysiognomyMedia",
    response_model=PhysiognomyMediaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_physiognomy_media(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    mode: ObservationMode = Form("face"),
    consent: bool = Form(False),
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> PhysiognomyMediaResponse:
    _check_rate(request, owner)
    payload = await file.read(MAX_MEDIA_BYTES + 1)
    await file.close()
    content_type = file.content_type or ""
    try:
        width, height = image_dimensions(content_type, payload)
        asset = await _service(request, session).ingest(
            owner_kind=owner.kind,
            owner_id=owner.id,
            content_type=content_type,
            filename=file.filename or "upload",
            payload=payload,
            width=width,
            height=height,
            consent=consent,
            mode=mode,
            consent_policy_version=PHOTO_CONSENT_POLICY_VERSION,
            now=datetime.now(UTC),
        )
    except (MediaQualityError, MediaValidationError, ValueError) as error:
        raise ApiProblem(status=400, title="照片不符合当前采集条件") from error
    await session.commit()
    mark_private(response)
    return _response(asset)


@router.delete(
    "/media/{asset_id}",
    operation_id="deletePhysiognomyMedia",
    response_model=PhysiognomyMediaResponse,
)
async def delete_physiognomy_media(
    asset_id: UUID,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
) -> PhysiognomyMediaResponse:
    _check_rate(request, owner)
    try:
        asset = await _service(request, session).delete(
            owner_kind=owner.kind,
            owner_id=owner.id,
            asset_id=asset_id,
            now=datetime.now(UTC),
        )
    except MediaNotFoundError as error:
        raise ApiProblem(status=404, title="照片资产不存在") from error
    await session.commit()
    mark_private(response)
    return _response(asset)
