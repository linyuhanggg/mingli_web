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


@dataclass(frozen=True, slots=True)
class PaymentQueryResult:
    status: Literal["unavailable", "pending", "succeeded", "failed"]
    payment_succeeded: bool
    channel_transaction_id: str | None = None


@dataclass(frozen=True, slots=True)
class RefundResult:
    status: Literal["unavailable", "pending", "succeeded", "failed"]
    refund_succeeded: bool
    channel_refund_id: str | None = None


class PaymentGateway(Protocol):
    async def create_checkout(
        self,
        *,
        order_id: UUID,
        amount_minor: int,
        currency: str,
    ) -> CheckoutResult: ...

    async def verify_notification(self, payload: bytes) -> PaymentNotificationResult: ...

    async def query_payment(self, *, attempt_id: UUID) -> PaymentQueryResult: ...

    async def request_refund(
        self,
        *,
        payment_id: UUID,
        amount_minor: int,
        reason: str,
    ) -> RefundResult: ...

    async def query_refund(self, *, refund_id: UUID) -> RefundResult: ...


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

    async def query_payment(self, *, attempt_id: UUID) -> PaymentQueryResult:
        del attempt_id
        return PaymentQueryResult(status="unavailable", payment_succeeded=False)

    async def request_refund(
        self,
        *,
        payment_id: UUID,
        amount_minor: int,
        reason: str,
    ) -> RefundResult:
        del payment_id, amount_minor, reason
        return RefundResult(status="unavailable", refund_succeeded=False)

    async def query_refund(self, *, refund_id: UUID) -> RefundResult:
        del refund_id
        return RefundResult(status="unavailable", refund_succeeded=False)
