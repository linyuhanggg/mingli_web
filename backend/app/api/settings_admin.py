"""Superadmin-only, non-secret runtime settings observability."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Request, Response

from app.admin.models import StaffSession, StaffUser
from app.admin.schemas import AdminSettingsResponse
from app.api.admin import require_staff_session
from app.api.dependencies import mark_private
from app.api.errors import ApiProblem
from app.config import Settings

router = APIRouter(prefix="/admin/settings", tags=["Admin Settings"])


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _require_settings_reader(staff: StaffUser) -> None:
    if staff.role != "superadmin":
        raise ApiProblem(status=403, title="Settings reader permission required")


@router.get(
    "",
    operation_id="getAdminSettings",
    response_model=AdminSettingsResponse,
)
async def get_admin_settings(
    request: Request,
    response: Response,
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminSettingsResponse:
    _require_settings_reader(principal[1])
    settings = _settings(request)
    mark_private(response)
    return AdminSettingsResponse(
        environment=settings.environment,
        cookie_secure=settings.cookie_secure,
        otp_adapter=settings.otp_adapter,
        runtime_adapter=settings.runtime_adapter,
        runtime_release_profile=settings.runtime_release_profile,
        admin_session_hours=settings.admin_session_hours,
        dogfood_entitlement_gates_enabled=settings.dogfood_entitlement_gates_enabled,
        real_traffic_enabled=settings.real_traffic_enabled,
        alert_sink_enabled=settings.alert_sink_enabled,
    )
