from dataclasses import dataclass, field
from typing import Literal, Protocol

OtpChannel = Literal["phone", "email"]


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
