from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PublicBaziCheckoutRequest(BaseModel):
    """The only client-selected value accepted by public checkout.

    The server resolves the enabled Bazi offer. A browser must not need to
    discover or guess an internal offer UUID.
    """

    model_config = ConfigDict(extra="forbid")

    reading_version_id: UUID


class PublicCheckoutOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: UUID
    reading_version_id: UUID | None = None
    product_id: Literal["bazi-deep"]
    product_version: str = Field(min_length=1)
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    status: str = Field(min_length=1)
    created_at: datetime
    paid_at: datetime | None = None


class PublicCheckoutAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: UUID
    channel: str = Field(min_length=1)
    status: str = Field(min_length=1)
    created_at: datetime


class PublicCheckoutResponse(BaseModel):
    """Minimal owner-scoped checkout projection.

    ``payment_id`` is omitted by the API until a local Payment row is
    confirmed.  A browser redirect or a provider query never creates it.
    """

    model_config = ConfigDict(extra="forbid")

    order: PublicCheckoutOrder
    attempt: PublicCheckoutAttempt
    gateway_status: Literal["unavailable", "pending", "succeeded", "failed"]
    redirect_url: str | None = None
    payment_id: UUID | None = None
    created: bool
