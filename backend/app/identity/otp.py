import asyncio
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from email_validator import EmailNotValidError, validate_email

from app.adapters.otp import OtpChannel


class InvalidDestination(ValueError):
    pass


class OtpRateLimited(RuntimeError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("OTP request is rate limited")
        self.retry_after_seconds = retry_after_seconds


class InvalidOtp(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IdentityAddress:
    channel: OtpChannel
    normalized: str
    masked: str


@dataclass(slots=True)
class OtpChallenge:
    id: UUID
    address: IdentityAddress
    provider_subject_hash: str
    code_hash: str
    created_at: datetime
    expires_at: datetime
    attempts: int = 0
    consumed_at: datetime | None = None


@dataclass(slots=True)
class RateWindow:
    started_at: datetime
    count: int


@dataclass(frozen=True, slots=True)
class OtpRequestReservation:
    """Tracks which limiter windows one OTP request consumed, for rollback."""

    guest_key: str
    guest_started_at: datetime
    network_key: str
    network_started_at: datetime
    destination_hash: str
    destination_started_at: datetime


class InMemoryOtpRequestLimiter:
    """Layered local/test limiter; a real delivery adapter requires Redis."""

    def __init__(
        self,
        *,
        window_seconds: int,
        guest_limit: int,
        network_limit: int,
        destination_limit: int,
        max_keys: int = 20_000,
    ) -> None:
        self.window = timedelta(seconds=window_seconds)
        self.guest_limit = guest_limit
        self.network_limit = network_limit
        self.destination_limit = destination_limit
        self.max_keys = max_keys
        self._guest_windows: dict[str, RateWindow] = {}
        self._network_windows: dict[str, RateWindow] = {}
        self._destination_windows: dict[str, RateWindow] = {}
        self._lock = asyncio.Lock()

    async def check(
        self,
        *,
        guest_key: str,
        network_key: str,
        destination_hash: str,
    ) -> OtpRequestReservation:
        now = datetime.now(UTC)
        async with self._lock:
            guest_started = self._consume(self._guest_windows, guest_key, self.guest_limit, now)
            try:
                network_started = self._consume(
                    self._network_windows, network_key, self.network_limit, now
                )
            except OtpRateLimited:
                # A rejection at a later layer must not keep the counts this
                # call already consumed: release them atomically under the same
                # lock before propagating, so a denied request never burns
                # guest or network capacity.
                self._release(self._guest_windows, guest_key, guest_started)
                raise
            try:
                destination_started = self._consume(
                    self._destination_windows, destination_hash, self.destination_limit, now
                )
            except OtpRateLimited:
                self._release(self._guest_windows, guest_key, guest_started)
                self._release(self._network_windows, network_key, network_started)
                raise
        return OtpRequestReservation(
            guest_key=guest_key,
            guest_started_at=guest_started,
            network_key=network_key,
            network_started_at=network_started,
            destination_hash=destination_hash,
            destination_started_at=destination_started,
        )

    async def rollback_delivery_failure(self, reservation: OtpRequestReservation) -> None:
        """Undo a request whose delivery failed, keeping the network window.

        A provider outage must not consume guest or destination capacity or hold
        the destination cooldown hostage, so a retry succeeds immediately once
        delivery recovers. The network window is intentionally preserved: an
        attacker must not be able to bypass the per-IP limit by hammering
        retries for the whole duration of an outage.
        """
        async with self._lock:
            self._release(self._guest_windows, reservation.guest_key, reservation.guest_started_at)
            self._release(
                self._destination_windows,
                reservation.destination_hash,
                reservation.destination_started_at,
            )

    def _consume(
        self,
        windows: dict[str, RateWindow],
        key: str,
        limit: int,
        now: datetime,
    ) -> datetime:
        current = windows.get(key)
        if current is None or now - current.started_at >= self.window:
            if current is None and len(windows) >= self.max_keys:
                self._drop_expired(windows, now)
                if len(windows) >= self.max_keys:
                    raise OtpRateLimited(max(1, int(self.window.total_seconds())))
            windows[key] = RateWindow(started_at=now, count=1)
            return now

        if current.count >= limit:
            remaining = self.window - (now - current.started_at)
            raise OtpRateLimited(max(1, int(remaining.total_seconds()) + 1))
        current.count += 1
        return current.started_at

    def _release(
        self,
        windows: dict[str, RateWindow],
        key: str,
        started_at: datetime,
    ) -> None:
        """Drop one count only if the window this request touched is still live."""
        current = windows.get(key)
        if current is None or current.started_at != started_at:
            return
        current.count -= 1
        if current.count <= 0:
            windows.pop(key, None)

    def _drop_expired(self, windows: dict[str, RateWindow], now: datetime) -> None:
        expired = [key for key, value in windows.items() if now - value.started_at >= self.window]
        for key in expired:
            windows.pop(key, None)


def normalize_destination(channel: OtpChannel, destination: str) -> IdentityAddress:
    if channel == "phone":
        compact = "".join(character for character in destination if character.isdigit())
        if compact.startswith("86") and len(compact) == 13:
            compact = compact[2:]
        if len(compact) != 11 or compact[0] != "1" or compact[1] not in "3456789":
            raise InvalidDestination("Enter a valid mainland China mobile number")
        return IdentityAddress(
            channel="phone",
            normalized=f"+86{compact}",
            masked=f"+86 {compact[:3]}****{compact[-4:]}",
        )

    try:
        normalized = validate_email(
            destination.strip(), check_deliverability=False
        ).normalized.lower()
    except EmailNotValidError as error:
        raise InvalidDestination("Enter a valid email address") from error
    local, domain = normalized.rsplit("@", 1)
    masked_local = f"{local[0]}***" if local else "***"
    return IdentityAddress(
        channel="email",
        normalized=normalized,
        masked=f"{masked_local}@{domain}",
    )


def hash_identity(secret: str, address: IdentityAddress) -> str:
    message = f"{address.channel}\0{address.normalized}".encode()
    return hmac.new(secret.encode(), message, sha256).hexdigest()


def hash_otp(secret: str, challenge_id: UUID, code: str) -> str:
    message = f"{challenge_id}\0{code}".encode()
    return hmac.new(secret.encode(), message, sha256).hexdigest()


class InMemoryOtpChallengeStore:
    """Local/test OTP state; production must replace this with a Redis-backed port."""

    def __init__(
        self,
        *,
        secret: str,
        ttl_seconds: int,
        cooldown_seconds: int,
        max_attempts: int,
    ) -> None:
        self.secret = secret
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self.max_attempts = max_attempts
        self._challenges: dict[UUID, OtpChallenge] = {}
        self._last_issued_at: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def issue(
        self,
        *,
        address: IdentityAddress,
        provider_subject_hash: str,
        code: str,
    ) -> OtpChallenge:
        now = datetime.now(UTC)
        async with self._lock:
            previous = self._last_issued_at.get(provider_subject_hash)
            if previous is not None and now - previous < self.cooldown:
                remaining = self.cooldown - (now - previous)
                raise OtpRateLimited(max(1, int(remaining.total_seconds()) + 1))

            challenge_id = uuid4()
            challenge = OtpChallenge(
                id=challenge_id,
                address=address,
                provider_subject_hash=provider_subject_hash,
                code_hash=hash_otp(self.secret, challenge_id, code),
                created_at=now,
                expires_at=now + self.ttl,
            )
            self._challenges[challenge_id] = challenge
            self._last_issued_at[provider_subject_hash] = now
            return challenge

    async def release(self, challenge_id: UUID) -> None:
        """Drop an issued-but-undelivered challenge and its own cooldown claim.

        Delivery failures must not leave an orphaned challenge or hold the
        destination cooldown hostage. The cooldown entry is only cleared when it
        still belongs to this challenge (its issue timestamp), so releasing a
        stale challenge never removes a newer claim for the same destination.
        """
        async with self._lock:
            challenge = self._challenges.pop(challenge_id, None)
            if challenge is None:
                return
            issued_at = self._last_issued_at.get(challenge.provider_subject_hash)
            if issued_at == challenge.created_at:
                self._last_issued_at.pop(challenge.provider_subject_hash, None)

    async def verify(self, challenge_id: UUID, code: str) -> OtpChallenge:
        now = datetime.now(UTC)
        async with self._lock:
            challenge = self._challenges.get(challenge_id)
            if (
                challenge is None
                or challenge.consumed_at is not None
                or challenge.expires_at <= now
            ):
                raise InvalidOtp("OTP challenge is invalid or expired")
            if challenge.attempts >= self.max_attempts:
                raise OtpRateLimited(60)

            supplied_hash = hash_otp(self.secret, challenge_id, code)
            if not hmac.compare_digest(challenge.code_hash, supplied_hash):
                challenge.attempts += 1
                raise InvalidOtp("OTP challenge is invalid or expired")

            challenge.consumed_at = now
            self._last_issued_at.pop(challenge.provider_subject_hash, None)
            return challenge


    async def peek_active(self, challenge_id: UUID) -> OtpChallenge | None:
        now = datetime.now(UTC)
        async with self._lock:
            challenge = self._challenges.get(challenge_id)
            if (
                challenge is None
                or challenge.consumed_at is not None
                or challenge.expires_at <= now
            ):
                return None
            return challenge
