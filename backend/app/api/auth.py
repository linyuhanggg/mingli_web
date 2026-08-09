from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.otp import OtpDeliveryUnavailable
from app.api.dependencies import (
    database_session,
    require_device_csrf,
    require_guest_csrf,
)
from app.api.errors import ApiProblem
from app.config import Settings
from app.identity.cookies import clear_device_cookies, set_device_cookies
from app.identity.models import AuditEvent, DeviceSession, GuestSession
from app.identity.otp import InvalidDestination, InvalidOtp, OtpRateLimited
from app.identity.repository import IdentityRepository
from app.identity.schemas import (
    AuthSessionResponse,
    OtpChallengeResponse,
    OtpRequest,
    OtpVerifyRequest,
)
from app.identity.service import AuthService
from app.network import resolve_client_ip

router = APIRouter(prefix="/auth", tags=["Identity"])


def _auth_service(request: Request, session: AsyncSession) -> AuthService:
    settings: Settings = request.app.state.settings
    return AuthService(
        repository=IdentityRepository(session),
        challenge_store=request.app.state.otp_challenge_store,
        delivery=request.app.state.otp_delivery,
        identity_hash_key=settings.identity_hash_key.get_secret_value(),
        otp_code_factory=request.app.state.otp_code_factory,
        otp_cooldown_seconds=settings.otp_cooldown_seconds,
        device_session_days=settings.device_session_days,
    )


@router.post(
    "/otp/request",
    operation_id="requestOtp",
    response_model=OtpChallengeResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_otp(
    request: Request,
    payload: OtpRequest,
    session: AsyncSession = Depends(database_session),
    guest_session: GuestSession = Depends(require_guest_csrf),
) -> OtpChallengeResponse:
    settings: Settings = request.app.state.settings
    try:
        network_key = resolve_client_ip(
            request,
            trusted_proxy_networks=request.app.state.trusted_proxy_networks,
        )
        await request.app.state.otp_request_limiter.check(
            guest_key=str(guest_session.id),
            network_key=network_key,
        )
        requested = await _auth_service(request, session).request_otp(
            payload.channel, payload.destination
        )
    except InvalidDestination as error:
        raise ApiProblem(status=400, title="Invalid destination", detail=str(error)) from error
    except OtpRateLimited as error:
        raise ApiProblem(
            status=429,
            title="Please wait before requesting another code",
        ) from error
    except OtpDeliveryUnavailable as error:
        raise ApiProblem(status=503, title="OTP delivery unavailable") from error

    return OtpChallengeResponse(
        challenge_id=requested.challenge_id,
        expires_at=requested.expires_at,
        retry_after_seconds=requested.retry_after_seconds,
        development_code=(
            settings.fake_otp_code
            if settings.environment in {"local", "test"} and settings.otp_adapter == "fake"
            else None
        ),
    )


@router.post(
    "/otp/verify",
    operation_id="verifyOtp",
    response_model=AuthSessionResponse,
)
async def verify_otp(
    request: Request,
    response: Response,
    payload: OtpVerifyRequest,
    session: AsyncSession = Depends(database_session),
    guest_session: GuestSession = Depends(require_guest_csrf),
) -> AuthSessionResponse:
    try:
        created = await _auth_service(request, session).verify_otp(
            payload.challenge_id, payload.code
        )
    except InvalidOtp as error:
        raise ApiProblem(status=400, title="Invalid or expired code") from error
    except OtpRateLimited as error:
        raise ApiProblem(status=429, title="Too many verification attempts") from error

    from app.profiles.service import GuestAlreadyClaimedError, ProfileService

    try:
        await ProfileService(session, request.app.state.settings).claim_guest_ownership(
            guest_session,
            created.user.id,
        )
    except GuestAlreadyClaimedError as error:
        raise ApiProblem(
            status=409,
            title="Guest Session is already claimed",
        ) from error
    await session.commit()
    settings: Settings = request.app.state.settings
    set_device_cookies(
        response,
        settings=settings,
        session_token=created.token,
        csrf_token=created.csrf_token,
        expires_at=created.expires_at,
    )
    return AuthSessionResponse(
        user_id=created.user.id,
        session_id=created.session_id,
        expires_at=created.expires_at,
        csrf_token=created.csrf_token,
    )


@router.post("/logout", operation_id="logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_csrf),
) -> Response:
    now = datetime.now(UTC)
    device_session.revoked_at = now
    IdentityRepository(session).add_audit_event(
        AuditEvent(
            user_id=device_session.user_id,
            actor_session_id=device_session.id,
            action="device_session.revoked",
            event_metadata={"reason": "logout"},
        )
    )
    await session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_device_cookies(response, settings=request.app.state.settings)
    return response
