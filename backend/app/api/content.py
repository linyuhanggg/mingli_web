from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import database_session
from app.api.errors import ApiProblem
from app.content.models import ContentRevisionRecord
from app.content.schemas import ContentPublicItem, ContentPublicResponse
from app.content.service import ContentService
from app.content.workflow import ContentError

router = APIRouter(prefix="/content", tags=["Content"])


def _response(record: ContentRevisionRecord) -> ContentPublicItem:
    return ContentPublicItem(
        content_key=record.content_key,
        locale=record.locale,
        revision=record.revision,
        title=record.title,
        summary=record.summary,
        topic=record.topic,
        source_title=record.source_title,
        source_url=record.source_url,
        body=record.body,
        created_at=record.created_at,
    )


def _not_found(error: ContentError) -> ApiProblem:
    return ApiProblem(status=404, title="Published content not found", detail=str(error))


@router.get(
    "",
    operation_id="listPublishedContent",
    response_model=ContentPublicResponse,
)
async def list_published_content(
    response: Response,
    prefix: str | None = Query(default=None, max_length=120),
    locale: str = Query(default="zh-CN", min_length=2, max_length=16),
    limit: int = Query(default=100, ge=1, le=200),
    q: str | None = Query(default=None, max_length=120),
    topic: str | None = Query(default=None, max_length=80),
    session: AsyncSession = Depends(database_session),
) -> ContentPublicResponse:
    records = await ContentService(session, editor_role="public").public_index(
        prefix=prefix,
        locale=locale,
        limit=limit,
        query=q,
        topic=topic,
    )
    response.headers["Cache-Control"] = "public, max-age=60"
    return ContentPublicResponse(items=[_response(record) for record in records])


@router.get(
    "/{content_key}",
    operation_id="getPublishedContent",
    response_model=ContentPublicItem,
)
async def get_published_content(
    response: Response,
    content_key: str = Path(min_length=1, max_length=160),
    locale: str = Query(default="zh-CN", min_length=2, max_length=16),
    session: AsyncSession = Depends(database_session),
) -> ContentPublicItem:
    try:
        record = await ContentService(session, editor_role="public").current(
            content_key=content_key,
            locale=locale,
        )
    except ContentError as error:
        raise _not_found(error) from error
    response.headers["Cache-Control"] = "public, max-age=60"
    return _response(record)
