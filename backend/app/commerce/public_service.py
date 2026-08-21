from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.payment import FakePaymentGateway, PaymentGateway
from app.commerce.models import (
    Order,
    Payment,
    PaymentAttempt,
    ProductFamily,
    ProductOffer,
    ProductVersion,
)
from app.commerce.service import CommerceService
from app.identity.policy import PURCHASE_CONSENT_CONTEXT, has_current_policy_keys
from app.identity.repository import IdentityRepository
from app.readings.models import ReadingJobRecord, ReadingRoot, ReadingVersion

BAZI_DEEP_PRODUCT_ID = "bazi-deep"
BAZI_DEEP_PRODUCT_FAMILY_KEY = "bazi-deep"

PublicGatewayStatus = Literal["unavailable", "pending", "succeeded", "failed"]


class PublicCheckoutError(RuntimeError):
    """Base class for failures safe to project at the public API boundary."""


class PublicCheckoutNotFound(PublicCheckoutError):
    """The requested owner-scoped reading or order does not exist."""


class PublicCheckoutConflict(PublicCheckoutError):
    """The requested reading, offer, or idempotency key cannot be used."""


class PublicCheckoutGatewayError(PublicCheckoutError):
    """The injected payment gateway could not create a checkout."""


class PublicCheckoutConsentRequired(PublicCheckoutError):
    """Owner is missing a current purchase ConsentRecord."""


@dataclass(frozen=True, slots=True)
class PublicCheckoutResult:
    order: Order
    attempt: PaymentAttempt
    product: ProductVersion
    payment: Payment | None
    reading_version_id: UUID | None
    gateway_status: PublicGatewayStatus
    redirect_url: str | None
    created: bool


def _key_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class PublicCheckoutService:
    """Owner-scoped seam between a Reading Version and a real payment adapter.

    This service deliberately stops at the adapter's checkout session.  The
    current adapter contract does not prove that a webhook or an active query
    is bound to this order, amount, currency, and target, so neither path is
    allowed to manufacture a confirmed Payment.
    """

    def __init__(self, session: AsyncSession, gateway: PaymentGateway) -> None:
        self.session = session
        self.gateway = gateway

    async def create_checkout(
        self,
        *,
        owner_user_id: UUID,
        reading_version_id: UUID,
        idempotency_key: str,
    ) -> PublicCheckoutResult:
        normalized_key = idempotency_key.strip()
        if not normalized_key:
            raise PublicCheckoutConflict("Idempotency-Key is required")

        version, root, _job = await self._owned_awaiting_bazi_version(
            owner_user_id=owner_user_id,
            reading_version_id=reading_version_id,
        )
        offer, product, _family = await self._enabled_bazi_offer()

        keys = await IdentityRepository(self.session).current_consent_keys(
            owner_user_id,
            contexts=frozenset({PURCHASE_CONSENT_CONTEXT}),
        )
        if not has_current_policy_keys(keys):
            raise PublicCheckoutConsentRequired("purchase consent is not current")

        key_hash = _key_hash(normalized_key)
        existing = await self.session.execute(
            select(PaymentAttempt, Order, ProductVersion)
            .join(Order, Order.id == PaymentAttempt.order_id)
            .join(ProductVersion, ProductVersion.id == Order.product_version_id)
            .where(
                Order.owner_user_id == owner_user_id,
                PaymentAttempt.idempotency_key_hash == key_hash,
            )
        )
        prior = existing.one_or_none()
        if prior is not None:
            attempt, order, prior_product = prior
            if (
                order.purchase_target_ref != str(root.id)
                or prior_product.id != product.id
                or order.amount_minor != offer.price_minor
                or order.currency != offer.currency
                or attempt.channel != offer.channel
            ):
                raise PublicCheckoutConflict(
                    "Idempotency-Key is already bound to another checkout"
                )
            payment = await self._confirmed_payment(attempt.id, order.id)
            return PublicCheckoutResult(
                order=order,
                attempt=attempt,
                product=prior_product,
                payment=payment,
                reading_version_id=version.id,
                gateway_status=self._local_gateway_status(attempt, payment),
                redirect_url=None,
                created=False,
            )

        commerce = CommerceService(self.session)
        order = await commerce.create_order(
            owner_user_id=owner_user_id,
            offer_id=offer.id,
            purchase_target_ref=str(root.id),
        )
        attempt, attempt_created = await commerce.create_payment_attempt(
            order_id=order.id,
            channel=offer.channel,
            idempotency_key=normalized_key,
        )
        if not attempt_created:
            payment = await self._confirmed_payment(attempt.id, order.id)
            return PublicCheckoutResult(
                order=order,
                attempt=attempt,
                product=product,
                payment=payment,
                reading_version_id=version.id,
                gateway_status=self._local_gateway_status(attempt, payment),
                redirect_url=None,
                created=False,
            )

        try:
            checkout = await self.gateway.create_checkout(
                order_id=order.id,
                amount_minor=order.amount_minor,
                currency=order.currency,
            )
        except Exception as error:
            raise PublicCheckoutGatewayError("payment gateway checkout failed") from error

        return PublicCheckoutResult(
            order=order,
            attempt=attempt,
            product=product,
            payment=None,
            reading_version_id=version.id,
            gateway_status=checkout.status,
            redirect_url=checkout.redirect_url,
            created=True,
        )

    async def get_checkout(
        self,
        *,
        owner_user_id: UUID,
        order_id: UUID,
    ) -> PublicCheckoutResult:
        row = await self.session.execute(
            select(Order, ProductVersion, ProductFamily)
            .join(ProductVersion, ProductVersion.id == Order.product_version_id)
            .join(ProductFamily, ProductFamily.id == ProductVersion.family_id)
            .where(
                Order.id == order_id,
                Order.owner_user_id == owner_user_id,
            )
        )
        result = row.one_or_none()
        if result is None:
            raise PublicCheckoutNotFound("checkout order not found")
        order, product, family = result
        if family.key != BAZI_DEEP_PRODUCT_FAMILY_KEY:
            raise PublicCheckoutNotFound("checkout order not found")

        root = await self.session.get(ReadingRoot, self._target_uuid(order))
        if (
            root is None
            or root.owner_user_id != owner_user_id
            or root.product_id != BAZI_DEEP_PRODUCT_ID
        ):
            raise PublicCheckoutNotFound("checkout order not found")

        attempt = await self.session.scalar(
            select(PaymentAttempt)
            .where(PaymentAttempt.order_id == order.id)
            .order_by(PaymentAttempt.created_at.desc(), PaymentAttempt.id.desc())
        )
        if attempt is None:
            raise PublicCheckoutNotFound("checkout attempt not found")
        payment = await self._confirmed_payment(attempt.id, order.id)
        reading_version_id = await self._reading_version_for_root(root.id)
        return PublicCheckoutResult(
            order=order,
            attempt=attempt,
            product=product,
            payment=payment,
            reading_version_id=reading_version_id,
            gateway_status=self._local_gateway_status(attempt, payment),
            redirect_url=None,
            created=False,
        )

    async def _owned_awaiting_bazi_version(
        self,
        *,
        owner_user_id: UUID,
        reading_version_id: UUID,
    ) -> tuple[ReadingVersion, ReadingRoot, ReadingJobRecord]:
        row = await self.session.execute(
            select(ReadingVersion, ReadingRoot)
            .join(ReadingRoot, ReadingRoot.id == ReadingVersion.reading_root_id)
            .where(
                ReadingVersion.id == reading_version_id,
                ReadingRoot.owner_user_id == owner_user_id,
            )
        )
        result = row.one_or_none()
        if result is None:
            raise PublicCheckoutNotFound("reading version not found")
        version, root = result
        if version.product_id != BAZI_DEEP_PRODUCT_ID:
            raise PublicCheckoutConflict("reading version is not a bazi deep read")

        job = await self.session.scalar(
            select(ReadingJobRecord)
            .where(ReadingJobRecord.reading_version_id == version.id)
            .order_by(ReadingJobRecord.created_at.desc(), ReadingJobRecord.id.desc())
        )
        if job is None or job.status != "awaiting_fulfillment":
            raise PublicCheckoutConflict("reading version is not awaiting fulfillment")
        return version, root, job

    async def _enabled_bazi_offer(
        self,
    ) -> tuple[ProductOffer, ProductVersion, ProductFamily]:
        row = await self.session.execute(
            select(ProductOffer, ProductVersion, ProductFamily)
            .join(ProductVersion, ProductVersion.id == ProductOffer.product_version_id)
            .join(ProductFamily, ProductFamily.id == ProductVersion.family_id)
            .where(
                ProductOffer.enabled.is_(True),
                ProductVersion.status == "active",
                ProductFamily.status == "active",
                ProductFamily.key == BAZI_DEEP_PRODUCT_FAMILY_KEY,
            )
        )
        results = row.all()
        if not results:
            raise PublicCheckoutConflict("no enabled bazi deep offer is available")
        if len(results) != 1:
            raise PublicCheckoutConflict(
                "multiple enabled bazi deep offers require a server channel policy"
            )
        selected = results[0]
        return selected[0], selected[1], selected[2]

    async def _confirmed_payment(
        self,
        attempt_id: UUID,
        order_id: UUID,
    ) -> Payment | None:
        payment = await self.session.scalar(
            select(Payment).where(
                Payment.attempt_id == attempt_id,
                Payment.order_id == order_id,
                Payment.status == "confirmed",
            )
        )
        return payment

    async def _reading_version_for_root(self, root_id: UUID) -> UUID | None:
        version = await self.session.scalar(
            select(ReadingVersion.id)
            .join(ReadingJobRecord, ReadingJobRecord.reading_version_id == ReadingVersion.id)
            .where(
                ReadingVersion.reading_root_id == root_id,
                ReadingVersion.product_id == BAZI_DEEP_PRODUCT_ID,
            )
            .order_by(ReadingVersion.created_at.desc(), ReadingVersion.id.desc())
        )
        return version

    @staticmethod
    def _target_uuid(order: Order) -> UUID:
        try:
            return UUID(order.purchase_target_ref)
        except (ValueError, AttributeError) as error:
            raise PublicCheckoutNotFound("checkout order not found") from error

    def _local_gateway_status(
        self,
        attempt: PaymentAttempt,
        payment: Payment | None,
    ) -> PublicGatewayStatus:
        if payment is not None:
            return "succeeded"
        if attempt.status == "failed":
            return "failed"
        if isinstance(self.gateway, FakePaymentGateway):
            return "unavailable"
        return "pending"
