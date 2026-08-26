"""Read-only Admin visibility for the versioned product capability policy."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response

from app.admin.models import StaffSession, StaffUser
from app.admin.schemas import AdminCapabilitiesResponse, AdminCapabilityResponse
from app.api.admin import require_staff_session
from app.api.dependencies import mark_private
from app.api.errors import ApiProblem
from app.readings.capability_policy import (
    CAPABILITY_LABELS,
    P0_EXPOSED_CAPABILITY_IDS,
    V51_RELEASE_CAPABILITY_IDS,
    V53_TIME_CHECK_RELEASE_CAPABILITY_IDS,
    product_actions_for_capability,
)

router = APIRouter(prefix="/admin/capabilities", tags=["Admin Capabilities"])


def _require_capability_read(staff: StaffUser) -> None:
    if staff.role not in {"ops", "superadmin"}:
        raise ApiProblem(status=403, title="Capability policy read permission required")


@router.get(
    "",
    operation_id="listAdminCapabilities",
    response_model=AdminCapabilitiesResponse,
)
async def list_admin_capabilities(
    request: Request,
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminCapabilitiesResponse:
    _require_capability_read(principal[1])
    settings = request.app.state.settings
    capability_ids = (
        V53_TIME_CHECK_RELEASE_CAPABILITY_IDS
        if settings.runtime_release_profile == "v53-time-check"
        else V51_RELEASE_CAPABILITY_IDS
    )
    capabilities = []
    for capability_id in capability_ids[:limit]:
        public = capability_id in P0_EXPOSED_CAPABILITY_IDS
        capabilities.append(
            AdminCapabilityResponse(
                capability_id=capability_id,
                label=CAPABILITY_LABELS[capability_id],
                release_state="PUBLIC" if public else "INTERNAL_TEST",
                audience="P0 产品" if public else "内部 Provider",
                product_actions=list(product_actions_for_capability(capability_id)),
            )
        )
    mark_private(response)
    return AdminCapabilitiesResponse(
        environment=settings.environment,
        runtime_adapter=settings.runtime_adapter,
        runtime_release_profile=settings.runtime_release_profile,
        runtime_health="unverified",
        production_ready=False,
        capabilities=capabilities,
    )
