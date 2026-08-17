from fastapi import APIRouter

from app.api.account import router as account_router
from app.api.account_commerce import router as account_commerce_router
from app.api.account_history import router as account_history_router
from app.api.admin import router as admin_router
from app.api.appeals_admin import router as appeals_admin_router
from app.api.audit_admin import router as audit_admin_router
from app.api.auth import router as auth_router
from app.api.capabilities_admin import router as capabilities_admin_router
from app.api.commerce_admin import router as commerce_admin_router
from app.api.commerce_public import router as commerce_public_router
from app.api.commerce_read_admin import router as commerce_read_admin_router
from app.api.content import router as content_router
from app.api.content_admin import router as content_admin_router
from app.api.guest_sessions import router as guest_sessions_router
from app.api.health import ReadinessProbe, build_health_router
from app.api.identity_admin import router as identity_admin_router
from app.api.model_profiles_admin import router as model_profiles_admin_router
from app.api.notifications_admin import router as notifications_admin_router
from app.api.physiognomy_media import router as physiognomy_media_router
from app.api.profiles import router as profiles_router
from app.api.readings import export_router, share_router
from app.api.readings import router as readings_router
from app.api.readings_admin import readings_router as readings_admin_readings_router
from app.api.readings_admin import router as readings_admin_router
from app.api.reconciliation_admin import router as reconciliation_admin_router
from app.api.referrals import router as referrals_router
from app.api.referrals_admin import router as referrals_admin_router
from app.api.referrals_public import router as referrals_public_router
from app.api.runtime_admin import router as runtime_admin_router
from app.api.sessions_admin import router as sessions_admin_router
from app.api.settings_admin import router as settings_admin_router
from app.api.staff_admin import router as staff_admin_router
from app.api.support_cases_admin import router as support_cases_admin_router
from app.api.verifications_admin import router as verifications_admin_router


def build_api_router(readiness_probe: ReadinessProbe) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(build_health_router(readiness_probe))
    router.include_router(content_router)
    router.include_router(guest_sessions_router)
    router.include_router(auth_router)
    router.include_router(account_router)
    router.include_router(account_commerce_router)
    router.include_router(account_history_router)
    router.include_router(profiles_router)
    router.include_router(physiognomy_media_router)
    router.include_router(readings_router)
    router.include_router(share_router)
    router.include_router(export_router)
    router.include_router(referrals_router)
    router.include_router(referrals_public_router)
    router.include_router(readings_admin_router)
    router.include_router(readings_admin_readings_router)
    router.include_router(admin_router)
    router.include_router(appeals_admin_router)
    router.include_router(audit_admin_router)
    router.include_router(capabilities_admin_router)
    router.include_router(content_admin_router)
    router.include_router(commerce_admin_router)
    router.include_router(commerce_public_router)
    router.include_router(commerce_read_admin_router)
    router.include_router(reconciliation_admin_router)
    router.include_router(runtime_admin_router)
    router.include_router(notifications_admin_router)
    router.include_router(model_profiles_admin_router)
    router.include_router(referrals_admin_router)
    router.include_router(sessions_admin_router)
    router.include_router(staff_admin_router)
    router.include_router(support_cases_admin_router)
    router.include_router(settings_admin_router)
    router.include_router(identity_admin_router)
    router.include_router(verifications_admin_router)
    return router
