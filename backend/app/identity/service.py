import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.adapters.otp import OtpChannel, OtpDeliveryAdapter, OtpDeliveryUnavailable
from app.admin.passwords import hash_password, verify_password
from app.identity.models import (
    AuditEvent,
    ConsentRecord,
    DeviceSession,
    GuestSession,
    LoginIdentity,
    User,
)
from app.identity.otp import (
    InMemoryOtpChallengeStore,
    InMemoryOtpRequestLimiter,
    OtpRateLimited,
    OtpRequestReservation,
    hash_identity,
    normalize_destination,
)
from app.identity.policy import (
    LOGIN_CONSENT_CONTEXTS,
    InvalidPolicyVersion,
    has_current_policy_keys,
    require_current_policy_version,
)
from app.identity.repository import IdentityRepository
from app.identity.security import hash_token, new_opaque_token
from app.security.envelope import EnvelopeCipher

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
    is_new_user: bool = False


class InvalidPassword(RuntimeError):
    """The credentials do not identify an active password-enabled account."""


class IdentityAlreadyRegistered(RuntimeError):
    """The verified identity already has a password-enabled account."""


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
        request_limiter: InMemoryOtpRequestLimiter | None = None,
        destination_cipher: EnvelopeCipher | None = None,
    ) -> None:
        self.repository = repository
        self.challenge_store = challenge_store
        self.delivery = delivery
        self.identity_hash_key = identity_hash_key
        self.otp_code_factory = otp_code_factory
        self.otp_cooldown_seconds = otp_cooldown_seconds
        self.device_session_days = device_session_days
        self.request_limiter = request_limiter
        self.destination_cipher = destination_cipher

    async def request_otp(
        self,
        channel: OtpChannel,
        destination: str,
        *,
        guest_key: str | None = None,
        network_key: str | None = None,
    ) -> RequestedOtp:
        address = normalize_destination(channel, destination)
        subject_hash = hash_identity(self.identity_hash_key, address)
        code = self.otp_code_factory()
        challenge = await self.challenge_store.issue(
            address=address,
            provider_subject_hash=subject_hash,
            code=code,
        )
        reservation: OtpRequestReservation | None = None
        try:
            if (
                self.request_limiter is not None
                and guest_key is not None
                and network_key is not None
            ):
                reservation = await self.request_limiter.check(
                    guest_key=guest_key,
                    network_key=network_key,
                    destination_hash=subject_hash,
                )
        except OtpRateLimited:
            await self.challenge_store.release(challenge.id)
            raise
        try:
            await self.delivery.deliver(
                channel=address.channel,
                destination=address.normalized,
                code=code,
            )
        except OtpDeliveryUnavailable:
            # A provider outage must not consume guest or destination slots or
            # hold the destination cooldown hostage, so the retry succeeds
            # immediately once delivery recovers. The network window is
            # deliberately kept so an outage cannot be used to hammer retries
            # past the per-IP limit.
            if self.request_limiter is not None and reservation is not None:
                await self.request_limiter.rollback_delivery_failure(reservation)
            await self.challenge_store.release(challenge.id)
            raise
        return RequestedOtp(
            challenge_id=challenge.id,
            expires_at=challenge.expires_at,
            retry_after_seconds=self.otp_cooldown_seconds,
        )

    async def verify_otp(self, challenge_id: UUID, code: str) -> CreatedDeviceSession:
        peeked = await self.challenge_store.peek_active(challenge_id)
        if peeked is not None:
            found = await self.repository.find_identity(
                provider=peeked.address.channel,
                provider_subject_hash=peeked.provider_subject_hash,
            )
            if found is not None:
                keys = await self.repository.current_consent_keys(
                    found[0].id,
                    contexts=LOGIN_CONSENT_CONTEXTS,
                )
                if not has_current_policy_keys(keys):
                    raise InvalidPolicyVersion("policy version is not current")
        challenge = await self.challenge_store.verify(challenge_id, code)
        now = datetime.now(UTC)
        user, identity, is_new_user = await self.repository.resolve_identity(
            provider=challenge.address.channel,
            provider_subject_hash=challenge.provider_subject_hash,
            masked_destination=challenge.address.masked,
            verified_at=now,
        )
        await self._store_destination(identity, challenge.address.normalized)
        return await self._create_device_session(
            user=user,
            identity=identity,
            action="identity.otp_verified",
            is_new_user=is_new_user,
        )

    async def authenticate_password(
        self,
        channel: OtpChannel,
        destination: str,
        password: str,
    ) -> CreatedDeviceSession:
        address = normalize_destination(channel, destination)
        subject_hash = hash_identity(self.identity_hash_key, address)
        found = await self.repository.find_identity(
            provider=address.channel,
            provider_subject_hash=subject_hash,
        )
        if found is None:
            raise InvalidPassword("invalid credentials")
        user, identity = found
        credential = await self.repository.get_password_credential(user.id)
        if credential is None or not verify_password(password, credential.password_hash):
            raise InvalidPassword("invalid credentials")
        await self._store_destination(identity, address.normalized)
        keys = await self.repository.current_consent_keys(user.id, contexts=LOGIN_CONSENT_CONTEXTS)
        if not has_current_policy_keys(keys):
            raise InvalidPolicyVersion("policy version is not current")
        return await self._create_device_session(
            user=user,
            identity=identity,
            action="identity.password_verified",
        )

    async def recover_password(
        self,
        challenge_id: UUID,
        code: str,
        password: str,
    ) -> CreatedDeviceSession:
        challenge = await self.challenge_store.verify(challenge_id, code)
        found = await self.repository.find_identity(
            provider=challenge.address.channel,
            provider_subject_hash=challenge.provider_subject_hash,
        )
        if found is None:
            raise InvalidPassword("invalid recovery credentials")

        user, identity = found
        await self._store_destination(identity, challenge.address.normalized)
        await self.set_password(user.id, password)
        revoked_count = await self.repository.revoke_active_device_sessions(
            user.id,
            datetime.now(UTC),
        )
        self.repository.add_audit_event(
            AuditEvent(
                user_id=user.id,
                action="identity.password_recovery_sessions_revoked",
                event_metadata={"revoked_count": revoked_count},
            )
        )
        return await self._create_device_session(
            user=user,
            identity=identity,
            action="identity.password_recovered",
        )

    async def register_with_otp(
        self,
        challenge_id: UUID,
        code: str,
        password: str,
        policy_version: str,
    ) -> CreatedDeviceSession:
        normalized_policy_version = require_current_policy_version(policy_version)
        challenge = await self.challenge_store.verify(challenge_id, code)
        found = await self.repository.find_identity(
            provider=challenge.address.channel,
            provider_subject_hash=challenge.provider_subject_hash,
        )
        if found is None:
            now = datetime.now(UTC)
            user, identity, is_new_user = await self.repository.resolve_identity(
                provider=challenge.address.channel,
                provider_subject_hash=challenge.provider_subject_hash,
                masked_destination=challenge.address.masked,
                verified_at=now,
            )
        else:
            user, identity = found
            is_new_user = False
            if await self.repository.get_password_credential(user.id) is not None:
                raise IdentityAlreadyRegistered("identity already has a password")

        await self._store_destination(identity, challenge.address.normalized)
        await self.set_password(user.id, password)
        accepted_at = datetime.now(UTC)
        consent_records = [
            ConsentRecord(
                user_id=user.id,
                policy_key=policy_key,
                policy_version=normalized_policy_version,
                context="registration",
                accepted_at=accepted_at,
            )
            for policy_key in ("privacy", "terms")
        ]
        for record in consent_records:
            self.repository.add_consent_record(record)

        created = await self._create_device_session(
            user=user,
            identity=identity,
            action="identity.registered",
            is_new_user=is_new_user,
        )
        for record in consent_records:
            record.actor_session_id = created.session_id
        return created

    async def set_password(self, user_id: UUID, password: str) -> None:
        password_hash = hash_password(password)
        now = datetime.now(UTC)
        await self.repository.save_password_credential(
            user_id=user_id,
            password_hash=password_hash,
            updated_at=now,
        )
        self.repository.add_audit_event(
            AuditEvent(
                user_id=user_id,
                action="identity.password_set",
                event_metadata={},
            )
        )

    async def _store_destination(self, identity: LoginIdentity, destination: str) -> None:
        if self.destination_cipher is not None:
            await self.repository.store_destination(
                identity,
                destination,
                self.destination_cipher,
            )

    async def _create_device_session(
        self,
        *,
        user: User,
        identity: LoginIdentity,
        action: str,
        is_new_user: bool = False,
    ) -> CreatedDeviceSession:
        now = datetime.now(UTC)
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
                action=action,
                event_metadata={"provider": identity.provider},
            )
        )
        return CreatedDeviceSession(
            user=user,
            identity=identity,
            session_id=session_id,
            token=token,
            csrf_token=csrf_token,
            expires_at=expires_at,
            is_new_user=is_new_user,
        )
