"""Read-only Admin visibility for registered runtime releases."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import StaffSession, StaffUser
from app.admin.schemas import AdminRuntimeReleaseResponse, AdminRuntimeReleasesResponse
from app.api.admin import require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.readings.models import RuntimeRelease

router = APIRouter(prefix="/admin/runtime-releases", tags=["Admin Runtime"])


def _require_runtime_read(staff: StaffUser) -> None:
    if staff.role not in {"ops", "superadmin"}:
        raise ApiProblem(status=403, title="Runtime release read permission required")


@router.get(
    "",
    operation_id="listAdminRuntimeReleases",
    response_model=AdminRuntimeReleasesResponse,
)
async def list_admin_runtime_releases(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminRuntimeReleasesResponse:
    _require_runtime_read(principal[1])
    releases = list(
        await session.scalars(
            select(RuntimeRelease)
            .order_by(RuntimeRelease.created_at.desc(), RuntimeRelease.id.desc())
            .limit(limit)
        )
    )
    mark_private(response)
    return AdminRuntimeReleasesResponse(
        releases=[
            AdminRuntimeReleaseResponse(
                id=release.id,
                name=release.name,
                version=release.version,
                source_commit=release.source_commit,
                protocol_version=release.protocol_version,
                production_ready=release.production_ready,
                created_at=release.created_at,
            )
            for release in releases
        ]
    )
