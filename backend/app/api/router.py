from fastapi import APIRouter

from app.api.account import router as account_router
from app.api.auth import router as auth_router
from app.api.guest_sessions import router as guest_sessions_router
from app.api.health import ReadinessProbe, build_health_router
from app.api.profiles import router as profiles_router
from app.api.readings import router as readings_router


def build_api_router(readiness_probe: ReadinessProbe) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(build_health_router(readiness_probe))
    router.include_router(guest_sessions_router)
    router.include_router(auth_router)
    router.include_router(account_router)
    router.include_router(profiles_router)
    router.include_router(readings_router)
    return router
