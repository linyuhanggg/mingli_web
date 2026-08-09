import asyncio
import smtplib
import ssl
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Literal, Protocol

from pydantic import SecretStr

OtpChannel = Literal["phone", "email"]
OtpSecurityMode = Literal["starttls", "ssl"]


class OtpDeliveryUnavailable(RuntimeError):
    pass


class OtpDeliveryAdapter(Protocol):
    async def deliver(self, *, channel: OtpChannel, destination: str, code: str) -> None: ...


@dataclass(frozen=True, slots=True)
class FakeOtpDelivery:
    channel: OtpChannel
    destination: str
    code: str


@dataclass(slots=True)
class FakeOtpDeliveryAdapter:
    """Records local deliveries without contacting a phone or email provider."""

    deliveries: list[FakeOtpDelivery] = field(default_factory=list)

    async def deliver(self, *, channel: OtpChannel, destination: str, code: str) -> None:
        self.deliveries.append(FakeOtpDelivery(channel=channel, destination=destination, code=code))


class DisabledOtpDeliveryAdapter:
    async def deliver(self, *, channel: OtpChannel, destination: str, code: str) -> None:
        del channel, destination, code
        raise OtpDeliveryUnavailable("OTP delivery adapter is not configured")


class ProductionFailClosedOtpDeliveryAdapter:
    """Refuses every delivery until a durable challenge store exists."""

    async def deliver(self, *, channel: OtpChannel, destination: str, code: str) -> None:
        del channel, destination, code
        raise OtpDeliveryUnavailable(
            "OTP delivery is disabled in production until a durable challenge store exists"
        )


class SmtpOtpDeliveryAdapter:
    """Staging-capable email delivery over stdlib smtplib, TLS only.

    The SMTP client comes from an injectable factory so tests never touch the
    network. ``security`` is ``starttls`` or ``ssl``; plaintext is never a mode,
    and a server that does not advertise STARTTLS is refused rather than
    downgraded. Credentials stay inside ``SecretStr`` and never appear in
    exception text or logs.
    """

    def __init__(
        self,
        *,
        sender: str,
        host: str,
        port: int,
        username: SecretStr,
        password: SecretStr,
        security: OtpSecurityMode = "starttls",
        timeout_seconds: float = 10.0,
        client_factory: Callable[[], smtplib.SMTP] | None = None,
    ) -> None:
        self.sender = sender
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.security = security
        self.timeout_seconds = timeout_seconds
        self._client_factory = client_factory or self._default_client_factory

    def _default_client_factory(self) -> smtplib.SMTP:
        if self.security == "ssl":
            return smtplib.SMTP_SSL(
                host=self.host,
                port=self.port,
                timeout=self.timeout_seconds,
                context=ssl.create_default_context(),
            )
        return smtplib.SMTP(host=self.host, port=self.port, timeout=self.timeout_seconds)

    async def deliver(self, *, channel: OtpChannel, destination: str, code: str) -> None:
        if channel != "email":
            raise OtpDeliveryUnavailable("Email OTP delivery is unavailable for this channel")
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = destination
        message["Subject"] = "明理验证码"
        message.set_content(f"你的明理验证码是 {code}，5 分钟内有效。如非本人操作，请忽略本邮件。")
        try:
            await asyncio.to_thread(self._send_via_smtp, message)
        except OtpDeliveryUnavailable:
            raise
        except Exception as error:
            raise OtpDeliveryUnavailable("Email OTP delivery failed") from error

    def _send_via_smtp(self, message: EmailMessage) -> None:
        client = self._client_factory()
        try:
            client.ehlo()
            if self.security == "starttls":
                if not client.has_extn("starttls"):
                    raise OtpDeliveryUnavailable(
                        "SMTP server does not advertise STARTTLS; refusing plaintext delivery"
                    )
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            client.login(self.username.get_secret_value(), self.password.get_secret_value())
            client.send_message(message)
        finally:
            with suppress(Exception):
                client.quit()
