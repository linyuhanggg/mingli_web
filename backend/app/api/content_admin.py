from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.api.admin import require_staff_csrf, require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.content.models import ContentRevisionRecord
from app.content.schemas import (
    ContentCreateRequest,
    ContentEditRequest,
    ContentHistoryResponse,
    ContentIndexItem,
    ContentIndexResponse,
    ContentReasonRequest,
    ContentRevisionResponse,
    ContentScheduleRequest,
    ContentWithdrawRequest,
)
from app.content.service import ContentService
from app.content.workflow import ContentError

router = APIRouter(prefix="/admin/cms", tags=["Admin CMS"])


def _editor(principal: tuple[StaffSession, StaffUser]) -> StaffUser:
    staff = principal[1]
    if staff.role not in {"ops", "superadmin"}:
        raise ApiProblem(status=403, title="CMS editor permission required")
    return staff


def _service(session: AsyncSession, staff: StaffUser) -> ContentService:
    return ContentService(session, editor_role=staff.role)


def _response(record: ContentRevisionRecord) -> ContentRevisionResponse:
    return ContentRevisionResponse(
        revision_id=record.id,
        content_key=record.content_key,
        locale=record.locale,
        revision=record.revision,
        state=record.state,
        title=record.title,
        summary=record.summary,
        topic=record.topic,
        source_title=record.source_title,
        source_url=record.source_url,
        body=record.body,
        author_ref=record.author_ref,
        publish_at=record.publish_at,
        withdrawn_reason=record.withdrawn_reason,
        created_at=record.created_at,
    )


def _index_response(record: ContentRevisionRecord) -> ContentIndexItem:
    return ContentIndexItem(
        revision_id=record.id,
        content_key=record.content_key,
        locale=record.locale,
        revision=record.revision,
        state=record.state,
        title=record.title,
        summary=record.summary,
        topic=record.topic,
        source_title=record.source_title,
        source_url=record.source_url,
        author_ref=record.author_ref,
        publish_at=record.publish_at,
        withdrawn_reason=record.withdrawn_reason,
        created_at=record.created_at,
    )


def _problem(error: ContentError) -> ApiProblem:
    return ApiProblem(
        status=404 if "not found" in str(error) else 409,
        title=(
            "Content revision not found"
            if "not found" in str(error)
            else "Invalid content transition"
        ),
        detail=str(error),
    )


def _audit(
    principal: tuple[StaffSession, StaffUser],
    *,
    action: str,
    record: ContentRevisionRecord,
    reason: str,
) -> AdminAuditEvent:
    staff_session, staff = principal
    return AdminAuditEvent(
        staff_user_id=staff.id,
        actor_session_id=staff_session.id,
        action=action,
        event_metadata={
            "content_key": record.content_key,
            "locale": record.locale,
            "reason": reason,
            "revision": record.revision,
            "state": str(record.state),
            "target_id": str(record.id),
        },
    )


@router.post(
    "",
    operation_id="createContentDraft",
    response_model=ContentRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_content_draft(
    payload: ContentCreateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> ContentRevisionResponse:
    staff = _editor(principal)
    try:
        record = await _service(session, staff).create(
            content_key=payload.content_key,
            locale=payload.locale,
            body=payload.body,
            author_ref=staff.email,
            author_staff_user_id=staff.id,
            title=payload.title,
            summary=payload.summary,
            topic=payload.topic,
            source_title=payload.source_title,
            source_url=payload.source_url,
        )
    except ContentError as error:
        raise _problem(error) from error
    session.add(
        _audit(
            principal,
            action="cms.draft.created",
            record=record,
            reason=payload.reason,
        )
    )
    await session.commit()
    mark_private(response)
    return _response(record)


@router.get(
    "",
    operation_id="listContentIndex",
    response_model=ContentIndexResponse,
)
async def list_content_index(
    response: Response,
    prefix: str | None = Query(default=None, max_length=120),
    locale: str = Query(default="zh-CN", min_length=2, max_length=16),
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> ContentIndexResponse:
    staff = _editor(principal)
    records = await _service(session, staff).index(
        prefix=prefix,
        locale=locale,
        limit=limit,
    )
    mark_private(response)
    return ContentIndexResponse(revisions=[_index_response(item) for item in records])


@router.patch(
    "/{revision_id}",
    operation_id="editContentDraft",
    response_model=ContentRevisionResponse,
)
async def edit_content_draft(
    revision_id: UUID,
    payload: ContentEditRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> ContentRevisionResponse:
    staff = _editor(principal)
    try:
        metadata = {
            field: getattr(payload, field)
            for field in ("title", "summary", "topic", "source_title", "source_url")
            if field in payload.model_fields_set
        }
        record = await _service(session, staff).edit(
            revision_id,
            body=payload.body,
            metadata=metadata,
        )
    except ContentError as error:
        raise _problem(error) from error
    session.add(
        _audit(
            principal,
            action="cms.draft.edited",
            record=record,
            reason=payload.reason,
        )
    )
    await session.commit()
    mark_private(response)
    return _response(record)


@router.get(
    "/{content_key}/history",
    operation_id="listContentHistory",
    response_model=ContentHistoryResponse,
)
async def list_content_history(
    content_key: str,
    response: Response,
    locale: str = "zh-CN",
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> ContentHistoryResponse:
    staff = _editor(principal)
    records = await _service(session, staff).history(content_key=content_key, locale=locale)
    await session.commit()
    mark_private(response)
    return ContentHistoryResponse(revisions=[_response(item) for item in records])


@router.post(
    "/{revision_id}/preview",
    operation_id="previewContentRevision",
    response_model=ContentRevisionResponse,
)
async def preview_content_revision(
    revision_id: UUID,
    payload: ContentReasonRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> ContentRevisionResponse:
    staff = _editor(principal)
    try:
        record = await _service(session, staff).preview(revision_id)
    except ContentError as error:
        raise _problem(error) from error
    session.add(
        _audit(
            principal,
            action="cms.revision.previewed",
            record=record,
            reason=payload.reason,
        )
    )
    await session.commit()
    mark_private(response)
    return _response(record)


@router.post(
    "/{revision_id}/schedule",
    operation_id="scheduleContentRevision",
    response_model=ContentRevisionResponse,
)
async def schedule_content_revision(
    revision_id: UUID,
    payload: ContentScheduleRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> ContentRevisionResponse:
    staff = _editor(principal)
    try:
        record = await _service(session, staff).schedule(
            revision_id,
            publish_at=payload.publish_at,
        )
    except ContentError as error:
        raise _problem(error) from error
    session.add(
        _audit(
            principal,
            action="cms.revision.scheduled",
            record=record,
            reason=payload.reason,
        )
    )
    await session.commit()
    mark_private(response)
    return _response(record)


@router.post(
    "/{revision_id}/publish",
    operation_id="publishContentRevision",
    response_model=ContentRevisionResponse,
)
async def publish_content_revision(
    revision_id: UUID,
    payload: ContentReasonRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> ContentRevisionResponse:
    staff = _editor(principal)
    try:
        record = await _service(session, staff).publish(revision_id)
    except ContentError as error:
        raise _problem(error) from error
    session.add(
        _audit(
            principal,
            action="cms.revision.published",
            record=record,
            reason=payload.reason,
        )
    )
    await session.commit()
    mark_private(response)
    return _response(record)


@router.post(
    "/{revision_id}/withdraw",
    operation_id="withdrawContentRevision",
    response_model=ContentRevisionResponse,
)
async def withdraw_content_revision(
    revision_id: UUID,
    payload: ContentWithdrawRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> ContentRevisionResponse:
    staff = _editor(principal)
    try:
        record = await _service(session, staff).withdraw(
            revision_id,
            reason=payload.reason,
        )
    except ContentError as error:
        raise _problem(error) from error
    session.add(
        _audit(
            principal,
            action="cms.revision.withdrawn",
            record=record,
            reason=payload.reason,
        )
    )
    await session.commit()
    mark_private(response)
    return _response(record)


@router.post(
    "/{revision_id}/archive",
    operation_id="archiveContentRevision",
    response_model=ContentRevisionResponse,
)
async def archive_content_revision(
    revision_id: UUID,
    payload: ContentReasonRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> ContentRevisionResponse:
    staff = _editor(principal)
    try:
        record = await _service(session, staff).archive(revision_id)
    except ContentError as error:
        raise _problem(error) from error
    session.add(
        _audit(
            principal,
            action="cms.revision.archived",
            record=record,
            reason=payload.reason,
        )
    )
    await session.commit()
    mark_private(response)
    return _response(record)


@router.post(
    "/{revision_id}/restore",
    operation_id="restoreContentRevision",
    response_model=ContentRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def restore_content_revision(
    revision_id: UUID,
    payload: ContentReasonRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> ContentRevisionResponse:
    staff = _editor(principal)
    try:
        record = await _service(session, staff).restore(
            revision_id,
            author_ref=staff.email,
            author_staff_user_id=staff.id,
        )
    except ContentError as error:
        raise _problem(error) from error
    session.add(
        _audit(
            principal,
            action="cms.revision.restored",
            record=record,
            reason=payload.reason,
        )
    )
    await session.commit()
    mark_private(response)
    return _response(record)
