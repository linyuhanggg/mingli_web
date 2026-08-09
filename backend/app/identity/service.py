import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.adapters.otp import OtpChannel, OtpDeliveryAdapter
from app.identity.models import AuditEvent, DeviceSession, GuestSession, LoginIdentity, User
from app.identity.otp import (
    InMemoryOtpChallengeStore,
    hash_identity,
    normalize_destination,
)
from app.identity.repository import IdentityRepository
from app.identity.security import hash_token, new_opaque_token

GUEST_SESSION_LIFETIME = timedelta(hours=24)


def random_six_digit_otp_code() -> str:
    """Cryptographically random six-digit code for non-Fake OTP delivery."""
    return f"{secrets.randbelow(1_000_000):06d}"


@dataclass(frozen=True, slots=True)
class CreatedGuestSession:
    token: str
    csrf_token: str
    expires_at: datetime


class GuestSessionService:
    def __init__(self, repository: IdentityRepository) -> None:
        self.repository = repository

    async def create(self, existing_token: str | None = None) -> CreatedGuestSession:
        now = datetime.now(UTC)
        if existing_token:
            await self.repository.revoke_guest_session(hash_token(existing_token), now)

        token = new_opaque_token()
        csrf_token = new_opaque_token()
        expires_at = now + GUEST_SESSION_LIFETIME
        self.repository.add_guest_session(
            GuestSession(
                token_hash=hash_token(token),
                csrf_token_hash=hash_token(csrf_token),
                expires_at=expires_at,
            )
        )
        return CreatedGuestSession(
            token=token,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )


@dataclass(frozen=True, slots=True)
class RequestedOtp:
    challenge_id: UUID
    expires_at: datetime
    retry_after_seconds: int


@dataclass(frozen=True, slots=True)
class CreatedDeviceSession:
    user: User
    identity: LoginIdentity
    session_id: UUID
    token: str
    csrf_token: str
    expires_at: datetime


class AuthService:
    def __init__(
        self,
        *,
        repository: IdentityRepository,
        challenge_store: InMemoryOtpChallengeStore,
        delivery: OtpDeliveryAdapter,
        identity_hash_key: str,
        otp_code_factory: Callable[[], str],
        otp_cooldown_seconds: int,
        device_session_days: int,
    ) -> None:
        self.repository = repository
        self.challenge_store = challenge_store
        self.delivery = delivery
        self.identity_hash_key = identity_hash_key
        self.otp_code_factory = otp_code_factory
        self.otp_cooldown_seconds = otp_cooldown_seconds
        self.device_session_days = device_session_days

    async def request_otp(self, channel: OtpChannel, destination: str) -> RequestedOtp:
        address = normalize_destination(channel, destination)
        subject_hash = hash_identity(self.identity_hash_key, address)
        code = self.otp_code_factory()
        challenge = await self.challenge_store.issue(
            address=address,
            provider_subject_hash=subject_hash,
            code=code,
        )
        await self.delivery.deliver(
            channel=address.channel,
            destination=address.normalized,
            code=code,
        )
        return RequestedOtp(
            challenge_id=challenge.id,
            expires_at=challenge.expires_at,
            retry_after_seconds=self.otp_cooldown_seconds,
        )

    async def verify_otp(self, challenge_id: UUID, code: str) -> CreatedDeviceSession:
        challenge = await self.challenge_store.verify(challenge_id, code)
        now = datetime.now(UTC)
        user, identity = await self.repository.resolve_identity(
            provider=challenge.address.channel,
            provider_subject_hash=challenge.provider_subject_hash,
            masked_destination=challenge.address.masked,
            verified_at=now,
        )
        session_id = uuid4()
        token = new_opaque_token()
        csrf_token = new_opaque_token()
        expires_at = now + timedelta(days=self.device_session_days)
        self.repository.add_device_session(
            DeviceSession(
                id=session_id,
                user_id=user.id,
                token_hash=hash_token(token),
                csrf_token_hash=hash_token(csrf_token),
                expires_at=expires_at,
                last_seen_at=now,
            )
        )
        self.repository.add_audit_event(
            AuditEvent(
                user_id=user.id,
                actor_session_id=session_id,
                action="identity.otp_verified",
                event_metadata={"provider": challenge.address.channel},
            )
        )
        return CreatedDeviceSession(
            user=user,
            identity=identity,
            session_id=session_id,
            token=token,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )
