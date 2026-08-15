"""Admin support case applications and safe read surface."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.admin.schemas import (
    AdminSupportCaseCreateRequest,
    AdminSupportCaseResponse,
    AdminSupportCasesResponse,
)
from app.api.admin import require_staff_csrf, require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.identity.models import User
from app.support.models import SupportCase

router = APIRouter(prefix="/admin/support-cases", tags=["Admin Support Cases"])


def _require_reader(staff: StaffUser) -> None:
    if staff.role not in {"support", "finance", "ops", "superadmin"}:
        raise ApiProblem(status=403, title="Support case reader permission required")


def _require_submitter(staff: StaffUser) -> None:
    if staff.role not in {"support", "superadmin"}:
        raise ApiProblem(status=403, title="Support case submission permission required")


def _normalized(value: str, *, title: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ApiProblem(status=400, title=title)
    return normalized


def _response(case: SupportCase) -> AdminSupportCaseResponse:
    return AdminSupportCaseResponse(
        id=case.id,
        owner_user_id=case.owner_user_id,
        subject_ref=case.subject_ref,
        category=case.category,
        summary=case.summary,
        status=case.status,
        created_by_staff_user_id=case.created_by_staff_user_id,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get(
    "",
    operation_id="listAdminSupportCases",
    response_model=AdminSupportCasesResponse,
)
async def list_admin_support_cases(
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminSupportCasesResponse:
    _require_reader(principal[1])
    cases = list(
        await session.scalars(
            select(SupportCase)
            .order_by(desc(SupportCase.created_at), desc(SupportCase.id))
            .limit(100)
        )
    )
    mark_private(response)
    return AdminSupportCasesResponse(cases=[_response(case) for case in cases])


@router.post(
    "",
    operation_id="createAdminSupportCase",
    response_model=AdminSupportCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_support_case(
    payload: AdminSupportCaseCreateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminSupportCaseResponse:
    staff_session, staff = principal
    _require_submitter(staff)
    subject_ref = _normalized(payload.subject_ref, title="Support case subject is required")
    summary = _normalized(payload.summary, title="Support case summary is required")
    reason = _normalized(payload.reason, title="Support case operation reason is required")
    if payload.owner_user_id is not None:
        owner = await session.get(User, payload.owner_user_id)
        if owner is None:
            raise ApiProblem(status=404, title="Support case owner not found")

    case = SupportCase(
        owner_user_id=payload.owner_user_id,
        subject_ref=subject_ref,
        category=payload.category,
        summary=summary,
        created_by_staff_user_id=staff.id,
    )
    session.add(case)
    await session.flush()
    await session.refresh(case)
    event_metadata: dict[str, Any] = {
        "case_id": str(case.id),
        "category": case.category,
        "subject_ref": case.subject_ref,
        "reason": reason,
    }
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action="support_case.created",
            event_metadata=event_metadata,
        )
    )
    await session.commit()
    mark_private(response)
    return _response(case)
