"""Public read-only projection of the admitted Runtime capability tiers."""

from fastapi import APIRouter, Request, Response

from app.readings.api_schemas import CapabilityProjection, CapabilityProjectionResponse
from app.readings.capability_policy import project_capabilities

router = APIRouter(prefix="/capabilities", tags=["Capabilities"])


@router.get(
    "",
    operation_id="listCapabilityProjection",
    response_model=CapabilityProjectionResponse,
)
async def list_capability_projection(
    request: Request,
    response: Response,
) -> CapabilityProjectionResponse:
    settings = request.app.state.settings
    projections = project_capabilities(
        release_root=settings.runtime_release_root,
        release_profile=settings.runtime_release_profile,
    )
    source_status = (
        "available"
        if projections and projections[0].source_status == "available"
        else "unavailable"
    )
    response.headers["Cache-Control"] = "public, max-age=60"
    return CapabilityProjectionResponse(
        runtime_release_profile=settings.runtime_release_profile,
        source_status=source_status,
        capabilities=[
            CapabilityProjection(
                capability_id=item.capability_id,
                label=item.label,
                tier=item.tier,
                source_system=item.source_system,
                runtime_active_rule_count=item.runtime_active_rule_count,
                judgment_rule_count=item.judgment_rule_count,
                source_status=item.source_status,
                user_decision_pending=item.user_decision_pending,
            )
            for item in projections
        ],
    )
