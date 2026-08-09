import re
import smtplib
from datetime import timedelta
from typing import Any

import pytest
from app.adapters.otp import (
    FakeOtpDeliveryAdapter,
    OtpDeliveryUnavailable,
    SmtpOtpDeliveryAdapter,
)
from app.identity.otp import (
    InMemoryOtpChallengeStore,
    InMemoryOtpRequestLimiter,
    OtpRateLimited,
    hash_identity,
    normalize_destination,
)
from app.identity.service import AuthService, random_six_digit_otp_code
from pydantic import SecretStr


class RecordingSmtpClient:
    """In-memory stand-in for smtplib that records every delivery detail."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self.starttls_calls = 0
        self.login_calls = 0
        self.login_user: str | None = None
        self.login_password: str | None = None
        self.starttls_advertised = True
        self.authentication_error = False

    def ehlo(self) -> None:
        return None

    def has_extn(self, name: str) -> bool:
        return self.starttls_advertised and name.lower() == "starttls"

    def starttls(self, context: object = None) -> None:
        del context
        if not self.starttls_advertised:
            raise smtplib.SMTPNotSupportedError("STARTTLS not advertised")
        self.starttls_calls += 1

    def login(self, user: str, password: str) -> None:
        if self.authentication_error:
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 username/password rejected")
        self.login_user = user
        self.login_password = password
        self.login_calls += 1

    def send_message(self, message: Any) -> None:
        self.sent.append((message["From"], message["To"], message.get_content()))

    def quit(self) -> None:
        return None


def _adapter(
    client: RecordingSmtpClient,
    *,
    security: str = "starttls",
    username: str = "smtp-user",
    password: str = "smtp-pass",
) -> SmtpOtpDeliveryAdapter:
    return SmtpOtpDeliveryAdapter(
        sender="no-reply@mingli.example",
        host="smtp.example.test",
        port=587,
        security=security,
        username=SecretStr(username),
        password=SecretStr(password),
        client_factory=lambda: client,
    )


async def test_smtp_delivery_uses_configured_sender_recipient_code_and_tls() -> None:
    client = RecordingSmtpClient()
    adapter = _adapter(client)

    await adapter.deliver(
        channel="email",
        destination="someone@example.com",
        code="583920",
    )

    assert client.starttls_calls == 1
    assert client.login_calls == 1
    assert client.login_user == "smtp-user"
    assert client.login_password == "smtp-pass"
    sender, recipient, body = client.sent[0]
    assert sender == "no-reply@mingli.example"
    assert recipient == "someone@example.com"
    assert "583920" in body


async def test_smtp_ssl_mode_connects_tls_first_without_starttls() -> None:
    client = RecordingSmtpClient()
    adapter = _adapter(client, security="ssl")

    await adapter.deliver(
        channel="email",
        destination="someone@example.com",
        code="583920",
    )

    assert client.starttls_calls == 0
    assert client.sent[0][1] == "someone@example.com"


async def test_smtp_never_downgrades_to_plaintext_when_starttls_is_missing() -> None:
    client = RecordingSmtpClient()
    client.starttls_advertised = False
    adapter = _adapter(client)

    with pytest.raises(OtpDeliveryUnavailable):
        await adapter.deliver(
            channel="email",
            destination="someone@example.com",
            code="583920",
        )

    assert client.sent == []
    assert client.starttls_calls == 0


async def test_smtp_rejects_phone_channel_without_exposing_destination_or_code() -> None:
    client = RecordingSmtpClient()
    adapter = _adapter(client)

    with pytest.raises(OtpDeliveryUnavailable) as excinfo:
        await adapter.deliver(
            channel="phone",
            destination="13800138000",
            code="583920",
        )

    message = str(excinfo.value)
    assert "13800138000" not in message
    assert "583920" not in message
    assert client.sent == []


async def test_smtp_phone_channel_never_opens_a_client() -> None:
    client = RecordingSmtpClient()
    calls: list[int] = []
    adapter = SmtpOtpDeliveryAdapter(
        sender="no-reply@mingli.example",
        host="smtp.example.test",
        port=587,
        username=SecretStr("smtp-user"),
        password=SecretStr("smtp-pass"),
        client_factory=lambda: calls.append(1) or client,
    )

    with pytest.raises(OtpDeliveryUnavailable):
        await adapter.deliver(
            channel="phone",
            destination="13800138000",
            code="583920",
        )

    assert calls == []


async def test_smtp_failure_becomes_generic_unavailable_without_leaking_credentials() -> None:
    client = RecordingSmtpClient()
    client.authentication_error = True
    adapter = _adapter(client, password="hunter2-secret")

    with pytest.raises(OtpDeliveryUnavailable) as excinfo:
        await adapter.deliver(
            channel="email",
            destination="someone@example.com",
            code="583920",
        )

    message = str(excinfo.value)
    assert message == "Email OTP delivery failed"
    assert "hunter2-secret" not in message
    assert "smtp-user" not in message
    assert client.sent == []


async def test_otp_service_generates_a_fresh_six_digit_code_per_challenge() -> None:
    store = InMemoryOtpChallengeStore(
        secret="test-secret",
        ttl_seconds=300,
        cooldown_seconds=1,
        max_attempts=5,
    )
    recorder = FakeOtpDeliveryAdapter()
    codes = iter(["000001", "999999"])
    service = AuthService(
        repository=None,  # request_otp never touches the repository
        challenge_store=store,
        delivery=recorder,
        identity_hash_key="test-hash-key",
        otp_code_factory=codes.__next__,
        otp_cooldown_seconds=1,
        device_session_days=30,
    )

    await service.request_otp("email", "first@example.com")
    await service.request_otp("email", "second@example.com")

    delivered_codes = [delivery.code for delivery in recorder.deliveries]
    assert delivered_codes == ["000001", "999999"]
    assert all(re.fullmatch(r"\d{6}", code) is not None for code in delivered_codes)


def test_random_otp_factory_zero_pads_the_secure_random_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter([0, 999_999])
    monkeypatch.setattr("app.identity.service.secrets.randbelow", lambda upper: next(values))

    assert random_six_digit_otp_code() == "000000"
    assert random_six_digit_otp_code() == "999999"


async def test_fake_otp_code_stays_fixed_at_the_configured_value() -> None:
    store = InMemoryOtpChallengeStore(
        secret="test-secret",
        ttl_seconds=300,
        cooldown_seconds=1,
        max_attempts=5,
    )
    recorder = FakeOtpDeliveryAdapter()
    service = AuthService(
        repository=None,
        challenge_store=store,
        delivery=recorder,
        identity_hash_key="test-hash-key",
        otp_code_factory=lambda: "246810",
        otp_cooldown_seconds=1,
        device_session_days=30,
    )

    await service.request_otp("email", "a@example.com")
    await service.request_otp("email", "b@example.com")

    assert [delivery.code for delivery in recorder.deliveries] == ["246810", "246810"]


class _FlakyDelivery:
    """Fails the first ``fail_times`` deliveries, then records later ones."""

    def __init__(self, *, fail_times: int = 1) -> None:
        self.fail_times = fail_times
        self.deliveries: list[tuple[str, str, str]] = []

    async def deliver(self, *, channel: str, destination: str, code: str) -> None:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise OtpDeliveryUnavailable("vendor unavailable")
        self.deliveries.append((channel, destination, code))


def _auth_service(
    *,
    store: InMemoryOtpChallengeStore,
    delivery: Any,
    limiter: InMemoryOtpRequestLimiter | None = None,
) -> AuthService:
    return AuthService(
        repository=None,
        challenge_store=store,
        delivery=delivery,
        identity_hash_key="test-hash-key",
        otp_code_factory=lambda: "246810",
        otp_cooldown_seconds=0,
        device_session_days=30,
        request_limiter=limiter,
    )


async def test_delivery_failure_releases_the_challenge_and_its_cooldown() -> None:
    store = InMemoryOtpChallengeStore(
        secret="test-secret",
        ttl_seconds=300,
        cooldown_seconds=60,
        max_attempts=5,
    )
    service = _auth_service(store=store, delivery=_FlakyDelivery(fail_times=1))

    with pytest.raises(OtpDeliveryUnavailable):
        await service.request_otp("email", "retry@example.com")

    # No orphaned challenge survives the failed delivery...
    assert store._challenges == {}
    # ...and the cooldown claim is released, so the retry succeeds immediately.
    requested = await service.request_otp("email", "retry@example.com")
    assert requested.expires_at is not None


async def test_release_only_clears_the_cooldown_owned_by_that_challenge() -> None:
    store = InMemoryOtpChallengeStore(
        secret="test-secret",
        ttl_seconds=300,
        cooldown_seconds=60,
        max_attempts=5,
    )
    service = _auth_service(store=store, delivery=FakeOtpDeliveryAdapter())
    await service.request_otp("email", "owner@example.com")
    challenge_id = next(iter(store._challenges))
    subject = hash_identity(
        "test-hash-key",
        normalize_destination("email", "owner@example.com"),
    )
    newer_claim = store._last_issued_at[subject] + timedelta(minutes=2)
    store._last_issued_at[subject] = newer_claim

    await store.release(challenge_id)

    # A newer cooldown claim for the same destination is not the released
    # challenge's own, so it must survive the release.
    assert store._last_issued_at[subject] == newer_claim
    assert challenge_id not in store._challenges


async def test_limiter_destination_full_rejection_does_not_grow_guest_or_network() -> None:
    limiter = InMemoryOtpRequestLimiter(
        window_seconds=600,
        guest_limit=10,
        network_limit=10,
        destination_limit=1,
    )
    subject = hash_identity("test-hash-key", normalize_destination("email", "hot@example.com"))
    await limiter.check(
        guest_key="guest-1",
        network_key="203.0.113.1",
        destination_hash=subject,
    )

    with pytest.raises(OtpRateLimited):
        await limiter.check(
            guest_key="guest-2",
            network_key="203.0.113.2",
            destination_hash=subject,
        )

    # The rejected request's guest and network windows were rolled back inside
    # the same lock, so neither key may keep a count...
    assert "guest-2" not in limiter._guest_windows
    assert "203.0.113.2" not in limiter._network_windows
    # ...while the accepted request's windows stay untouched.
    assert limiter._guest_windows["guest-1"].count == 1
    assert limiter._network_windows["203.0.113.1"].count == 1
    assert limiter._destination_windows[subject].count == 1

    # Capacity was not burned: the same guest/network pair can still request a
    # different destination.
    await limiter.check(
        guest_key="guest-2",
        network_key="203.0.113.2",
        destination_hash=hash_identity(
            "test-hash-key", normalize_destination("email", "cold@example.com")
        ),
    )


async def test_limiter_network_full_rejection_does_not_grow_guest() -> None:
    limiter = InMemoryOtpRequestLimiter(
        window_seconds=600,
        guest_limit=10,
        network_limit=1,
        destination_limit=10,
    )
    subject = hash_identity("test-hash-key", normalize_destination("email", "net@example.com"))
    await limiter.check(
        guest_key="guest-1",
        network_key="203.0.113.9",
        destination_hash=subject,
    )

    with pytest.raises(OtpRateLimited):
        await limiter.check(
            guest_key="guest-2",
            network_key="203.0.113.9",
            destination_hash=hash_identity(
                "test-hash-key", normalize_destination("email", "other@example.com")
            ),
        )

    # guest-2 was consumed then rolled back; the destination was never touched.
    assert "guest-2" not in limiter._guest_windows
    assert limiter._network_windows["203.0.113.9"].count == 1
    assert set(limiter._destination_windows) == {subject}
    # The rejected guest can still request from a different IP.
    await limiter.check(
        guest_key="guest-2",
        network_key="203.0.113.10",
        destination_hash=hash_identity(
            "test-hash-key", normalize_destination("email", "other@example.com")
        ),
    )


async def test_limiter_guest_full_rejection_consumes_nothing() -> None:
    limiter = InMemoryOtpRequestLimiter(
        window_seconds=600,
        guest_limit=1,
        network_limit=10,
        destination_limit=10,
    )
    subject = hash_identity("test-hash-key", normalize_destination("email", "guest@example.com"))
    await limiter.check(
        guest_key="guest-1",
        network_key="203.0.113.5",
        destination_hash=subject,
    )

    with pytest.raises(OtpRateLimited):
        await limiter.check(
            guest_key="guest-1",
            network_key="203.0.113.6",
            destination_hash=hash_identity(
                "test-hash-key", normalize_destination("email", "fresh@example.com")
            ),
        )

    # A rejection at the first layer must not consume network or destination.
    assert limiter._guest_windows["guest-1"].count == 1
    assert "203.0.113.6" not in limiter._network_windows
    assert len(limiter._destination_windows) == 1


async def test_delivery_failure_rolls_back_guest_and_destination_but_keeps_network() -> None:
    store = InMemoryOtpChallengeStore(
        secret="test-secret",
        ttl_seconds=300,
        cooldown_seconds=0,
        max_attempts=5,
    )
    limiter = InMemoryOtpRequestLimiter(
        window_seconds=600,
        guest_limit=10,
        network_limit=2,
        destination_limit=10,
    )
    service = _auth_service(
        store=store,
        delivery=_FlakyDelivery(fail_times=1),
        limiter=limiter,
    )

    with pytest.raises(OtpDeliveryUnavailable):
        await service.request_otp(
            "email",
            "slot@example.com",
            guest_key="guest-1",
            network_key="203.0.113.9",
        )

    # Guest and destination windows are rolled back and the orphaned challenge
    # is gone, so the same guest/destination can retry immediately...
    assert limiter._guest_windows == {}
    assert limiter._destination_windows == {}
    assert store._challenges == {}
    # ...but the network window keeps its count as provider-outage protection.
    assert limiter._network_windows["203.0.113.9"].count == 1

    await service.request_otp(
        "email",
        "slot@example.com",
        guest_key="guest-1",
        network_key="203.0.113.9",
    )
    assert limiter._network_windows["203.0.113.9"].count == 2

    with pytest.raises(OtpRateLimited):
        await service.request_otp(
            "email",
            "slot@example.com",
            guest_key="guest-1",
            network_key="203.0.113.9",
        )


async def test_request_limiter_destination_window_is_cross_guest() -> None:
    store = InMemoryOtpChallengeStore(
        secret="test-secret",
        ttl_seconds=300,
        cooldown_seconds=0,
        max_attempts=5,
    )
    limiter = InMemoryOtpRequestLimiter(
        window_seconds=600,
        guest_limit=10,
        network_limit=10,
        destination_limit=2,
    )
    service = _auth_service(
        store=store,
        delivery=FakeOtpDeliveryAdapter(),
        limiter=limiter,
    )

    await service.request_otp("email", "cross@example.com", guest_key="g1", network_key="n1")
    await service.request_otp("email", "cross@example.com", guest_key="g2", network_key="n1")
    with pytest.raises(OtpRateLimited):
        await service.request_otp("email", "cross@example.com", guest_key="g3", network_key="n1")
