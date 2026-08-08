from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.problems import problem_response

ReadinessProbe = Callable[[], Awaitable[None]]


def build_health_router(readiness_probe: ReadinessProbe) -> APIRouter:
    router = APIRouter(prefix="/health", tags=["Health"])

    @router.get("/live", operation_id="getLiveness")
    async def liveness() -> dict[str, str]:
        return {"status": "ok", "service": "api"}

    @router.get(
        "/ready",
        operation_id="getReadiness",
        response_model=None,
        responses={503: {"description": "Required dependency is unavailable"}},
    )
    async def readiness(request: Request) -> JSONResponse:
        try:
            await readiness_probe()
        except Exception:
            return problem_response(
                request,
                status=503,
                title="Service unavailable",
                problem_type="urn:fateradar:problem:dependency-unavailable",
            )
        return JSONResponse({"status": "ok", "service": "database"})

    return router
