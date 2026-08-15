from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PaymentSnapshotStatus = Literal["pending", "succeeded", "failed", "refunded"]
RefundSnapshotStatus = Literal["pending", "succeeded", "failed"]


@dataclass(frozen=True, slots=True)
class ChannelPaymentSnapshot:
    """Normalized provider payment fact used by a reconciliation run."""

    transaction_id: str
    status: PaymentSnapshotStatus
    amount_minor: int
    currency: str


@dataclass(frozen=True, slots=True)
class ChannelRefundSnapshot:
    """Normalized provider refund fact used by a reconciliation run."""

    refund_id: str
    payment_transaction_id: str | None
    status: RefundSnapshotStatus
    amount_minor: int
    currency: str
