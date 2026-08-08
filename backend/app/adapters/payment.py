from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CheckoutResult:
    channel: str
    status: Literal["unavailable", "pending"]
    redirect_url: str | None


@dataclass(frozen=True, slots=True)
class PaymentNotificationResult:
    verified: bool
    payment_succeeded: bool
    channel_transaction_id: str | None = None


class PaymentGateway(Protocol):
    async def create_checkout(
        self,
        *,
        order_id: UUID,
        amount_minor: int,
        currency: str,
    ) -> CheckoutResult: ...

    async def verify_notification(self, payload: bytes) -> PaymentNotificationResult: ...


class FakePaymentGateway:
    """Safe placeholder that can never turn untrusted input into a payment fact."""

    async def create_checkout(
        self,
        *,
        order_id: UUID,
        amount_minor: int,
        currency: str,
    ) -> CheckoutResult:
        del order_id, amount_minor, currency
        return CheckoutResult(channel="fake", status="unavailable", redirect_url=None)

    async def verify_notification(self, payload: bytes) -> PaymentNotificationResult:
        del payload
        return PaymentNotificationResult(verified=False, payment_succeeded=False)
