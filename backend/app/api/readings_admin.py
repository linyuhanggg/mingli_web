"""Read-only Admin metadata for persisted reading jobs."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import StaffSession, StaffUser
from app.admin.schemas import (
    AdminReadingDetailResponse,
    AdminReadingJobResponse,
    AdminReadingJobsResponse,
    AdminReadingResponse,
    AdminReadingsResponse,
)
from app.api.admin import require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.readings.models import (
    ClaimVerificationEvent,
    ReadingDocumentRecord,
    ReadingJobRecord,
    ReadingVerification,
    ReadingVersion,
    ReportFeedback,
)

router = APIRouter(prefix="/admin/reading-jobs", tags=["Admin Readings"])
readings_router = APIRouter(prefix="/admin/readings", tags=["Admin Readings"])


def _require_read_access(staff: StaffUser) -> None:
    if staff.role not in {"support", "ops", "superadmin"}:
        raise ApiProblem(status=403, title="Reading job read permission required")


@router.get(
    "",
    operation_id="listAdminReadingJobs",
    response_model=AdminReadingJobsResponse,
)
async def list_admin_reading_jobs(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminReadingJobsResponse:
    _require_read_access(principal[1])
    rows = list(
        (
            await session.execute(
                select(ReadingJobRecord, ReadingVersion)
                .join(
                    ReadingVersion,
                    ReadingVersion.id == ReadingJobRecord.reading_version_id,
                )
                .order_by(ReadingJobRecord.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
    mark_private(response)
    return AdminReadingJobsResponse(
        jobs=[
            AdminReadingJobResponse(
                id=job.id,
                reading_version_id=job.reading_version_id,
                reading_root_id=version.reading_root_id,
                reading_version=version.version,
                capability_id=version.capability_id,
                reading_status=version.status,
                job_status=job.status,
                language=job.language,
                narrative_policy_version=job.narrative_policy_version,
                max_attempts=job.max_attempts,
                available_at=job.available_at,
                lease_generation=job.lease_generation,
                created_at=job.created_at,
            )
            for job, version in rows
        ]
    )


@readings_router.get(
    "",
    operation_id="listAdminReadings",
    response_model=AdminReadingsResponse,
)
async def list_admin_readings(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminReadingsResponse:
    _require_read_access(principal[1])
    records = list(
        await session.scalars(
            select(ReadingVersion)
            .order_by(ReadingVersion.created_at.desc())
            .limit(limit)
        )
    )
    mark_private(response)
    return AdminReadingsResponse(
        readings=[
            AdminReadingResponse(
                reading_version_id=item.id,
                reading_root_id=item.reading_root_id,
                capability_id=item.capability_id,
                version=item.version,
                status=item.status,
                dimension_count=len(item.dimension_ids),
                created_at=item.created_at,
            )
            for item in records
        ]
    )


@readings_router.get(
    "/{reading_version_id}",
    operation_id="getAdminReading",
    response_model=AdminReadingDetailResponse,
)
async def get_admin_reading(
    reading_version_id: UUID,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminReadingDetailResponse:
    _require_read_access(principal[1])
    reading = await session.get(ReadingVersion, reading_version_id)
    if reading is None:
        raise ApiProblem(status=404, title="Reading version not found")
    job_count = await session.scalar(
        select(func.count(ReadingJobRecord.id)).where(
            ReadingJobRecord.reading_version_id == reading.id
        )
    )
    reading_verification_count = await session.scalar(
        select(func.count(ReadingVerification.id)).where(
            ReadingVerification.reading_version_id == reading.id
        )
    )
    claim_verification_count = await session.scalar(
        select(func.count(ClaimVerificationEvent.id)).where(
            ClaimVerificationEvent.reading_version_id == reading.id
        )
    )
    feedback_count = await session.scalar(
        select(func.count(ReportFeedback.id)).where(
            ReportFeedback.reading_version_id == reading.id
        )
    )
    document_count = await session.scalar(
        select(func.count(ReadingDocumentRecord.id)).where(
            ReadingDocumentRecord.reading_version_id == reading.id
        )
    )
    mark_private(response)
    return AdminReadingDetailResponse(
        reading_version_id=reading.id,
        reading_root_id=reading.reading_root_id,
        capability_id=reading.capability_id,
        version=reading.version,
        status=reading.status,
        dimension_count=len(reading.dimension_ids),
        job_count=int(job_count or 0),
        verification_event_count=int(
            (reading_verification_count or 0)
            + (claim_verification_count or 0)
            + (feedback_count or 0)
        ),
        document_available=bool(document_count),
        created_at=reading.created_at,
    )
