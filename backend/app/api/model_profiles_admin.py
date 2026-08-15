"""Read-only Admin visibility for persisted model and guard receipt metadata."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import StaffSession, StaffUser
from app.admin.schemas import AdminModelProfileResponse, AdminModelProfilesResponse
from app.api.admin import require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.readings.models import GenerationAttempt

router = APIRouter(prefix="/admin/model-profiles", tags=["Admin Model Profiles"])


def _require_model_profile_read(staff: StaffUser) -> None:
    if staff.role not in {"ops", "superadmin"}:
        raise ApiProblem(status=403, title="Model profile read permission required")


@router.get(
    "",
    operation_id="listAdminModelProfiles",
    response_model=AdminModelProfilesResponse,
)
async def list_admin_model_profiles(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminModelProfilesResponse:
    _require_model_profile_read(principal[1])
    attempts = list(
        await session.scalars(
            select(GenerationAttempt)
            .where(GenerationAttempt.model_receipt.is_not(None))
            .order_by(desc(GenerationAttempt.created_at), desc(GenerationAttempt.id))
            .limit(limit)
        )
    )
    profiles: list[AdminModelProfileResponse] = []
    for attempt in attempts:
        receipt = cast(dict[str, object], attempt.model_receipt)
        model_profile_id = receipt.get("model_profile_id")
        provider = receipt.get("provider")
        outcome = receipt.get("outcome")
        narrative_policy_version = receipt.get("narrative_policy_version")
        output_contract_id = receipt.get("output_contract_id")
        latency_ms = receipt.get("latency_ms")
        usage_known = receipt.get("usage_known")
        cost_known = receipt.get("cost_known")
        provider_model_version = receipt.get("provider_model_version")
        error_code = receipt.get("error_code")
        if not all(
            isinstance(value, str)
            for value in (
                model_profile_id,
                provider,
                outcome,
                narrative_policy_version,
                output_contract_id,
            )
        ):
            continue
        if not isinstance(latency_ms, int) or not isinstance(usage_known, bool):
            continue
        if not isinstance(cost_known, bool):
            continue
        if provider_model_version is not None and not isinstance(provider_model_version, str):
            continue
        if error_code is not None and not isinstance(error_code, str):
            continue
        profiles.append(
            AdminModelProfileResponse(
                generation_attempt_id=attempt.id,
                reading_version_id=attempt.reading_version_id,
                attempt_number=attempt.attempt_number,
                model_profile_id=model_profile_id,
                provider=provider,
                provider_model_version=provider_model_version,
                outcome=outcome,
                error_code=error_code,
                narrative_policy_version=narrative_policy_version,
                output_contract_id=output_contract_id,
                latency_ms=latency_ms,
                usage_known=usage_known,
                cost_known=cost_known,
                guard_error_count=len(attempt.guard_errors),
                created_at=attempt.created_at,
            )
        )
    mark_private(response)
    return AdminModelProfilesResponse(profiles=profiles)
