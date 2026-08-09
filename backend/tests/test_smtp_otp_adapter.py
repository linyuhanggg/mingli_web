import re
import smtplib
from typing import Any

import pytest
from app.adapters.otp import (
    FakeOtpDeliveryAdapter,
    OtpDeliveryUnavailable,
    SmtpOtpDeliveryAdapter,
)
from app.identity.otp import InMemoryOtpChallengeStore
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
