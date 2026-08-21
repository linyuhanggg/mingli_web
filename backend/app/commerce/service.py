from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent
from app.commerce.ledger import EntitlementProjection, LedgerEventKind
from app.commerce.models import (
    EntitlementEventRecord,
    FulfillmentRecord,
    NotificationOutbox,
    NotificationPreference,
    Order,
    Payment,
    PaymentAttempt,
    PaymentNotificationReceipt,
    PaymentReconciliationItem,
    PaymentReconciliationRun,
    ProductOffer,
    ProductVersion,
    Refund,
)
from app.commerce.notifications import is_in_app_notification
from app.commerce.reconciliation import ChannelPaymentSnapshot, ChannelRefundSnapshot
from app.commerce.repository import CommerceRepository
from app.identity.models import User


class CommerceError(ValueError):
    """The local commerce state cannot accept the requested transition."""


PaymentStatus = Literal["pending", "succeeded", "failed"]
NotificationChannel = Literal["in_app", "email", "sms"]
SnapshotT = TypeVar("SnapshotT")


def _key_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class CommerceService:
    """Local order, payment-fact, ledger, and notification orchestration.

    A payment channel remains closed until an external adapter verifies a
    provider callback. ``confirm_payment`` therefore requires an explicit
    ``verified=True`` assertion from that adapter and never calls a provider.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ledger = CommerceRepository(session)

    async def create_order(
        self,
        *,
        owner_user_id: UUID,
        offer_id: UUID,
        purchase_target_ref: str,
    ) -> Order:
        offer, product = (
            await self.session.execute(
                select(ProductOffer, ProductVersion)
                .join(ProductVersion, ProductVersion.id == ProductOffer.product_version_id)
                .where(
                    ProductOffer.id == offer_id,
                    ProductOffer.enabled.is_(True),
                    ProductVersion.status == "active",
                )
            )
        ).one_or_none() or (None, None)
        if offer is None or product is None:
            raise CommerceError("product offer is not available")
        if not purchase_target_ref.strip():
            raise CommerceError("purchase target is required")
        order = Order(
            owner_user_id=owner_user_id,
            product_version_id=product.id,
            purchase_target_ref=purchase_target_ref,
            amount_minor=offer.price_minor,
            currency=offer.currency,
            status="created",
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def create_payment_attempt(
        self,
        *,
        order_id: UUID,
        channel: str,
        idempotency_key: str,
        referral_attribution_id: UUID | None = None,
        now: datetime | None = None,
    ) -> tuple[PaymentAttempt, bool]:
        if not channel.strip() or not idempotency_key.strip():
            raise CommerceError("payment channel and idempotency key are required")
        order = await self.session.get(Order, order_id)
        if order is None or order.status not in {"created", "payment_pending"}:
            raise CommerceError("order is not payable")
        key_hash = _key_hash(idempotency_key)
        existing = await self.session.scalar(
            select(PaymentAttempt).where(
                PaymentAttempt.order_id == order_id,
                PaymentAttempt.idempotency_key_hash == key_hash,
            )
        )
        if existing is not None:
            if referral_attribution_id is not None:
                from app.referrals.service import ReferralService

                await ReferralService(self.session).reserve_reward_for_payment(
                    attribution_id=referral_attribution_id,
                    payment_attempt_id=existing.id,
                    now=now,
                )
            return existing, False
        attempt = PaymentAttempt(
            order_id=order_id,
            channel=channel,
            idempotency_key_hash=key_hash,
            status="pending",
        )
        order.status = "payment_pending"
        self.session.add(attempt)
        await self.session.flush()
        if referral_attribution_id is not None:
            from app.referrals.service import ReferralService

            await ReferralService(self.session).reserve_reward_for_payment(
                attribution_id=referral_attribution_id,
                payment_attempt_id=attempt.id,
                now=now,
            )
        return attempt, True

    async def confirm_payment(
        self,
        *,
        order_id: UUID,
        attempt_id: UUID,
        channel: str,
        channel_transaction_id: str,
        verified: bool,
        now: datetime | None = None,
    ) -> tuple[Payment, bool]:
        if not verified:
            raise CommerceError("payment channel verification is required")
        if not channel_transaction_id.strip():
            raise CommerceError("channel transaction id is required")
        order = await self.session.get(Order, order_id)
        attempt = await self.session.get(PaymentAttempt, attempt_id)
        if order is None or attempt is None or attempt.order_id != order_id:
            raise CommerceError("payment attempt does not belong to order")
        if attempt.channel != channel:
            raise CommerceError("payment channel does not match attempt")
        prior_payment = await self.session.scalar(
            select(Payment).where(Payment.attempt_id == attempt.id)
        )
        if prior_payment is not None:
            if prior_payment.channel_transaction_id != channel_transaction_id:
                raise CommerceError("payment attempt is already confirmed")
            await self._commit_referral_reward_for_payment(
                payment_attempt_id=attempt.id,
                confirmed_at=prior_payment.confirmed_at,
            )
            return prior_payment, False
        if attempt.status != "pending":
            raise CommerceError("payment attempt is already confirmed")
        existing = await self.session.scalar(
            select(Payment).where(
                Payment.channel == channel,
                Payment.channel_transaction_id == channel_transaction_id,
            )
        )
        if existing is not None:
            if existing.order_id != order_id:
                raise CommerceError("channel transaction is already bound to another order")
            return existing, False
        if order.status == "paid":
            raise CommerceError("order is already paid")
        if order.status == "refunded":
            raise CommerceError("order has already been refunded")
        confirmed_at = now or datetime.now(UTC)
        payment = Payment(
            order_id=order.id,
            attempt_id=attempt.id,
            channel=channel,
            channel_transaction_id=channel_transaction_id,
            amount_minor=order.amount_minor,
            currency=order.currency,
            status="confirmed",
            confirmed_at=confirmed_at,
        )
        self.session.add(payment)
        await self.session.flush()
        attempt.status = "succeeded"
        order.status = "paid"
        order.paid_at = payment.confirmed_at
        await self.ledger.append_entitlement_event(
            entitlement_id=f"order:{order.id}",
            owner_user_id=order.owner_user_id,
            kind="GRANT",
            quantity=1,
            source_type="payment",
            source_ref=str(payment.id),
            target_ref=order.purchase_target_ref,
        )
        await self._commit_referral_reward_for_payment(
            payment_attempt_id=attempt.id,
            confirmed_at=payment.confirmed_at,
        )
        await self.session.flush()
        return payment, True

    async def _commit_referral_reward_for_payment(
        self,
        *,
        payment_attempt_id: UUID,
        confirmed_at: datetime | None,
    ) -> None:
        """Commit one pending referral reservation in the payment transaction."""
        from app.referrals.models import ReferralRewardReservation
        from app.referrals.service import ReferralService

        reservation = await self.session.scalar(
            select(ReferralRewardReservation).where(
                ReferralRewardReservation.payment_attempt_id == payment_attempt_id,
            )
        )
        if reservation is None or reservation.status != "reserved":
            return
        await ReferralService(self.session).commit_reward(
            reservation.id,
            now=confirmed_at or datetime.now(UTC),
        )

    async def _reverse_referral_reward_for_refund(
        self,
        *,
        payment_attempt_id: UUID,
        refund_id: UUID,
    ) -> None:
        from app.referrals.service import ReferralService

        await ReferralService(self.session).reverse_reward_for_refund(
            payment_attempt_id=payment_attempt_id,
            refund_id=refund_id,
        )

    async def _release_referral_reward_for_payment(
        self,
        *,
        payment_attempt_id: UUID,
    ) -> None:
        from app.referrals.service import ReferralService

        await ReferralService(self.session).release_reward_for_payment(
            payment_attempt_id=payment_attempt_id,
        )

    async def _require_referral_refund_confirmation(
        self,
        *,
        payment: Payment,
        order: Order,
        confirmation_id: UUID | None,
    ) -> None:
        from app.referrals.models import (
            ReferralRefundConfirmation,
            ReferralRewardReservation,
        )

        reservation = await self.session.scalar(
            select(ReferralRewardReservation).where(
                ReferralRewardReservation.payment_attempt_id == payment.attempt_id,
            )
        )
        if reservation is None or reservation.status == "released":
            return
        if reservation.status not in {"committed", "expired", "reversed"}:
            raise CommerceError("referral reward is not refundable")
        if confirmation_id is None:
            raise CommerceError("referral refund confirmation is required")
        confirmation = await self.session.get(
            ReferralRefundConfirmation,
            confirmation_id,
        )
        if (
            confirmation is None
            or confirmation.payment_id != payment.id
            or confirmation.order_id != order.id
            or confirmation.user_id != order.owner_user_id
            or confirmation.reservation_id != reservation.id
            or confirmation.campaign_version_id != reservation.campaign_version_id
            or confirmation.product_version_id != order.product_version_id
        ):
            raise CommerceError("referral refund confirmation does not match payment")

    async def apply_payment_notification(
        self,
        *,
        order_id: UUID,
        attempt_id: UUID,
        channel: str,
        external_event_id: str,
        channel_transaction_id: str | None,
        payment_succeeded: bool,
        verified: bool,
        now: datetime | None = None,
    ) -> tuple[Payment | None, bool]:
        """Apply one verified provider event without replaying the ledger grant."""
        if not verified:
            raise CommerceError("payment notification verification is required")
        normalized_channel = channel.strip()
        normalized_event_id = external_event_id.strip()
        normalized_transaction_id = (channel_transaction_id or "").strip() or None
        if not normalized_channel or not normalized_event_id:
            raise CommerceError("notification channel and event id are required")
        if payment_succeeded and normalized_transaction_id is None:
            raise CommerceError("successful payment notification needs a transaction id")
        processed_at = now or datetime.now(UTC)

        provider_status = "succeeded" if payment_succeeded else "pending"
        receipt = await self.session.scalar(
            select(PaymentNotificationReceipt).where(
                PaymentNotificationReceipt.channel == normalized_channel,
                PaymentNotificationReceipt.external_event_id == normalized_event_id,
            )
        )
        if receipt is not None:
            if (
                receipt.channel_transaction_id != normalized_transaction_id
                or receipt.provider_status != provider_status
            ):
                raise CommerceError("notification event is bound to a different payment")
        else:
            receipt = PaymentNotificationReceipt(
                channel=normalized_channel,
                external_event_id=normalized_event_id,
                channel_transaction_id=normalized_transaction_id,
                provider_status=provider_status,
                processing_status="received",
            )
            self.session.add(receipt)
            await self.session.flush()

        if not payment_succeeded:
            await self._release_referral_reward_for_payment(
                payment_attempt_id=attempt_id,
            )
            receipt.processing_status = "ignored"
            receipt.processed_at = processed_at
            await self.session.flush()
            return None, False

        payment, created = await self.confirm_payment(
            order_id=order_id,
            attempt_id=attempt_id,
            channel=normalized_channel,
            channel_transaction_id=normalized_transaction_id or "",
            verified=True,
            now=processed_at,
        )
        receipt.payment_id = payment.id
        receipt.processing_status = "processed"
        receipt.processed_at = processed_at
        await self.session.flush()
        return payment, created

    async def reserve_fulfillment(
        self,
        *,
        payment_id: UUID,
        idempotency_key: str,
    ) -> tuple[FulfillmentRecord, bool]:
        """Reserve one paid order for delivery, exactly once."""
        normalized_key = idempotency_key.strip()
        if not normalized_key:
            raise CommerceError("fulfillment idempotency key is required")
        payment = await self.session.get(Payment, payment_id)
        if payment is None or payment.status != "confirmed":
            raise CommerceError("confirmed payment is required")
        order = await self.session.get(Order, payment.order_id)
        if order is None or order.status != "paid":
            raise CommerceError("paid order is required")
        entitlement_id = f"order:{order.id}"
        key_hash = _key_hash(normalized_key)

        by_key = await self.session.scalar(
            select(FulfillmentRecord).where(
                FulfillmentRecord.order_id == order.id,
                FulfillmentRecord.idempotency_key_hash == key_hash,
            )
        )
        if by_key is not None:
            if by_key.payment_id != payment.id:
                raise CommerceError("fulfillment idempotency key is bound to another order")
            return by_key, False

        existing = await self.session.scalar(
            select(FulfillmentRecord).where(FulfillmentRecord.order_id == order.id)
        )
        if existing is not None:
            if existing.payment_id != payment.id:
                raise CommerceError("order fulfillment is bound to another payment")
            return existing, False

        projection = await self.ledger.project(
            entitlement_id=entitlement_id,
            owner_user_id=order.owner_user_id,
        )
        if projection.available < 1:
            raise CommerceError("paid entitlement is not available for fulfillment")

        fulfillment = FulfillmentRecord(
            id=uuid4(),
            owner_user_id=order.owner_user_id,
            order_id=order.id,
            payment_id=payment.id,
            entitlement_id=entitlement_id,
            purchase_target_ref=order.purchase_target_ref,
            idempotency_key_hash=key_hash,
            status="reserved",
        )
        self.session.add(fulfillment)
        await self.session.flush()
        await self.ledger.append_entitlement_event(
            entitlement_id=entitlement_id,
            owner_user_id=order.owner_user_id,
            kind="RESERVE",
            quantity=1,
            source_type="fulfillment",
            source_ref=f"{fulfillment.id}:reserve",
            target_ref=order.purchase_target_ref,
        )
        await self.session.flush()
        return fulfillment, True

    async def bind_fulfillment_job(
        self,
        *,
        fulfillment_id: UUID,
        reading_version_ref: str,
        reading_job_ref: str,
    ) -> tuple[FulfillmentRecord, bool]:
        """Bind a persisted Reading Job to a reserved paid target."""
        normalized_job_ref = reading_job_ref.strip()
        if not normalized_job_ref:
            raise CommerceError("Reading Job ref is required")
        fulfillment = await self._fulfillment(fulfillment_id)
        version, job = await self._reading_job(
            reading_version_ref=reading_version_ref,
            reading_job_ref=normalized_job_ref,
            owner_user_id=fulfillment.owner_user_id,
        )
        from app.readings.models import AcceptedCopy, ReadingRoot, ReadingVersion

        if fulfillment.status == "delivered":
            if (
                fulfillment.reading_version_ref == reading_version_ref
                and fulfillment.reading_job_ref == normalized_job_ref
            ):
                return fulfillment, False
            raise CommerceError("delivered fulfillment is immutable")
        if fulfillment.status == "released":
            raise CommerceError("released fulfillment cannot bind a job")
        if (
            fulfillment.reading_version_ref == reading_version_ref
            and fulfillment.reading_job_ref == normalized_job_ref
        ):
            return fulfillment, False
        if job.status in {"failed", "canceled", "stopped", "runtime_unknown"}:
            raise CommerceError("terminal Reading Job cannot be fulfilled")
        if fulfillment.reading_version_ref is not None:
            if (
                fulfillment.reading_version_ref != reading_version_ref
                or fulfillment.reading_job_ref != normalized_job_ref
            ):
                raise CommerceError("fulfillment is already bound to another Reading Job")
            return fulfillment, False

        already_bound = await self.session.scalar(
            select(FulfillmentRecord)
            .where(
                FulfillmentRecord.reading_job_ref == normalized_job_ref,
                FulfillmentRecord.id != fulfillment.id,
            )
            .with_for_update()
        )
        if already_bound is not None:
            raise CommerceError("Reading Job is already bound to another fulfillment")

        order = await self.session.get(Order, fulfillment.order_id)
        product = None if order is None else await self.session.get(
            ProductVersion,
            order.product_version_id,
        )
        root = await self.session.get(ReadingRoot, version.reading_root_id)
        if order is None or product is None or root is None:
            raise CommerceError("fulfillment product or Reading Root is missing")
        if product.follow_up_count < 0 or product.follow_up_window_seconds < 0:
            raise CommerceError("ProductVersion follow-up contract is invalid")
        snapshot = (
            product.id,
            product.follow_up_count,
            product.follow_up_window_seconds,
        )
        current_snapshot = (
            root.product_version_snapshot_id,
            root.follow_up_count_snapshot,
            root.follow_up_window_seconds_snapshot,
        )
        if root.product_version_snapshot_id is None:
            root.product_version_snapshot_id = snapshot[0]
            root.follow_up_count_snapshot = snapshot[1]
            root.follow_up_window_seconds_snapshot = snapshot[2]
            initial = await self.session.scalar(
                select(ReadingVersion).where(
                    ReadingVersion.reading_root_id == root.id,
                    ReadingVersion.version == 1,
                )
            )
            initial_copy = None if initial is None else await self.session.scalar(
                select(AcceptedCopy).where(AcceptedCopy.reading_version_id == initial.id)
            )
            if initial_copy is not None:
                root.follow_up_started_at = initial_copy.accepted_at
        elif current_snapshot != snapshot:
            raise CommerceError("Reading Root ProductVersion snapshot is immutable")
        fulfillment.reading_version_ref = reading_version_ref
        fulfillment.reading_job_ref = normalized_job_ref
        fulfillment.status = "running"
        fulfillment.updated_at = datetime.now(UTC)
        await self.session.flush()
        return fulfillment, True

    async def deliver_fulfillment_for_job(
        self,
        *,
        reading_job_ref: str,
    ) -> tuple[FulfillmentRecord, bool] | None:
        """Consume the one fulfillment bound to a completed Reading Job."""
        normalized_job_ref = reading_job_ref.strip()
        if not normalized_job_ref:
            raise CommerceError("Reading Job ref is required")
        from app.readings.models import AcceptedCopy, ReadingDocumentRecord, ReadingJobRecord

        try:
            job_id = UUID(normalized_job_ref)
        except ValueError as error:
            raise CommerceError("Reading Job ref must be a UUID") from error
        job = await self.session.get(ReadingJobRecord, job_id)
        if job is None:
            raise CommerceError("Reading Job not found")
        fulfillment = await self.session.scalar(
            select(FulfillmentRecord)
            .where(FulfillmentRecord.reading_job_ref == normalized_job_ref)
            .with_for_update()
        )
        if fulfillment is None:
            return None
        accepted_copy = await self.session.scalar(
            select(AcceptedCopy).where(
                AcceptedCopy.reading_version_id == job.reading_version_id
            )
        )
        document = await self.session.scalar(
            select(ReadingDocumentRecord).where(
                ReadingDocumentRecord.reading_version_id == job.reading_version_id
            )
        )
        if accepted_copy is None or document is None:
            raise CommerceError("Accepted Copy and ReadingDocument are required for delivery")
        return await self.mark_fulfillment_delivered(
            fulfillment_id=fulfillment.id,
            reading_version_ref=str(job.reading_version_id),
            reading_job_ref=normalized_job_ref,
            accepted_copy_ref=str(accepted_copy.id),
            reading_document_ref=str(document.id),
        )

    async def release_fulfillment_for_job(
        self,
        *,
        reading_job_ref: str,
        reason: str,
    ) -> tuple[FulfillmentRecord, bool] | None:
        """Release the one fulfillment bound to a terminal Reading Job."""
        normalized_job_ref = reading_job_ref.strip()
        if not normalized_job_ref:
            raise CommerceError("Reading Job ref is required")
        fulfillment = await self.session.scalar(
            select(FulfillmentRecord)
            .where(FulfillmentRecord.reading_job_ref == normalized_job_ref)
            .with_for_update()
        )
        if fulfillment is None:
            return None
        return await self.release_fulfillment(
            fulfillment_id=fulfillment.id,
            reason=reason,
        )

    async def mark_fulfillment_delivered(
        self,
        *,
        fulfillment_id: UUID,
        reading_version_ref: str,
        reading_job_ref: str,
        accepted_copy_ref: str,
        reading_document_ref: str,
    ) -> tuple[FulfillmentRecord, bool]:
        """Consume the reserved unit only after Accepted and its document exist."""
        fulfillment = await self._fulfillment(fulfillment_id)
        refs = (
            reading_version_ref.strip(),
            reading_job_ref.strip(),
            accepted_copy_ref.strip(),
            reading_document_ref.strip(),
        )
        if not all(refs):
            raise CommerceError("Reading Job, Accepted Copy and document refs are required")
        version, _job = await self._reading_job(
            reading_version_ref=refs[0],
            reading_job_ref=refs[1],
            owner_user_id=fulfillment.owner_user_id,
        )
        from app.readings.models import AcceptedCopy, ReadingDocumentRecord

        try:
            accepted_copy_id = UUID(refs[2])
            document_id = UUID(refs[3])
        except ValueError as error:
            raise CommerceError("Accepted Copy and document refs must be UUIDs") from error
        accepted_copy = await self.session.get(AcceptedCopy, accepted_copy_id)
        document = await self.session.get(ReadingDocumentRecord, document_id)
        if accepted_copy is None or accepted_copy.reading_version_id != version.id:
            raise CommerceError("Accepted Copy is not bound to the Reading Version")
        if (
            document is None
            or document.reading_version_id != version.id
            or document.accepted_copy_id != accepted_copy.id
        ):
            raise CommerceError("ReadingDocument is not bound to the Accepted Copy")
        if version.status != "accepted":
            raise CommerceError("Reading Version is not accepted")

        if fulfillment.status == "delivered":
            if (
                fulfillment.reading_version_ref,
                fulfillment.reading_job_ref,
                fulfillment.accepted_copy_ref,
                fulfillment.reading_document_ref,
            ) == refs:
                return fulfillment, False
            raise CommerceError("delivered fulfillment is immutable")
        if fulfillment.status == "released":
            raise CommerceError("released fulfillment cannot be delivered")
        if fulfillment.reading_version_ref is None or fulfillment.reading_job_ref is None:
            raise CommerceError("Reading Job must be bound before delivery")
        if fulfillment.reading_version_ref is not None and (
            fulfillment.reading_version_ref != refs[0]
            or fulfillment.reading_job_ref != refs[1]
        ):
            raise CommerceError("fulfillment is already bound to another Reading Job")

        consume_ref = f"{fulfillment.id}:consume"
        existing_consume = await self.ledger.find_events_by_source(
            source_type="fulfillment",
            source_ref=consume_ref,
        )
        if existing_consume:
            if len(existing_consume) != 1 or existing_consume[0].kind != "CONSUME":
                raise CommerceError("fulfillment consume event is inconsistent")
        else:
            await self.ledger.append_entitlement_event(
                entitlement_id=fulfillment.entitlement_id,
                owner_user_id=fulfillment.owner_user_id,
                kind="CONSUME",
                quantity=1,
                source_type="fulfillment",
                source_ref=consume_ref,
                target_ref=refs[0],
            )
        fulfillment.reading_version_ref = refs[0]
        fulfillment.reading_job_ref = refs[1]
        fulfillment.accepted_copy_ref = refs[2]
        fulfillment.reading_document_ref = refs[3]
        fulfillment.status = "delivered"
        fulfillment.delivered_at = datetime.now(UTC)
        fulfillment.updated_at = fulfillment.delivered_at
        await self.session.flush()
        return fulfillment, True

    async def release_fulfillment(
        self,
        *,
        fulfillment_id: UUID,
        reason: str,
    ) -> tuple[FulfillmentRecord, bool]:
        """Release a reserved unit after a terminal delivery failure."""
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise CommerceError("fulfillment release reason is required")
        fulfillment = await self._fulfillment(fulfillment_id)
        if fulfillment.status == "released":
            return fulfillment, False
        if fulfillment.status == "delivered":
            raise CommerceError("delivered fulfillment cannot be released")
        release_ref = f"{fulfillment.id}:release"
        existing_release = await self.ledger.find_events_by_source(
            source_type="fulfillment",
            source_ref=release_ref,
        )
        if not existing_release:
            await self.ledger.append_entitlement_event(
                entitlement_id=fulfillment.entitlement_id,
                owner_user_id=fulfillment.owner_user_id,
                kind="RELEASE",
                quantity=1,
                source_type="fulfillment",
                source_ref=release_ref,
                target_ref=normalized_reason,
            )
        fulfillment.status = "released"
        fulfillment.failure_reason = normalized_reason
        fulfillment.released_at = datetime.now(UTC)
        fulfillment.updated_at = fulfillment.released_at
        await self.session.flush()
        return fulfillment, True

    async def _fulfillment(self, fulfillment_id: UUID) -> FulfillmentRecord:
        fulfillment = await self.session.get(FulfillmentRecord, fulfillment_id)
        if fulfillment is None:
            raise CommerceError("fulfillment not found")
        return fulfillment

    async def _reading_job(
        self,
        *,
        reading_version_ref: str,
        reading_job_ref: str,
        owner_user_id: UUID,
    ) -> tuple[Any, Any]:
        from app.readings.models import ReadingJobRecord, ReadingRoot, ReadingVersion

        try:
            version_id = UUID(reading_version_ref.strip())
            job_id = UUID(reading_job_ref.strip())
        except ValueError as error:
            raise CommerceError("Reading Version and Job refs must be UUIDs") from error
        version = await self.session.get(ReadingVersion, version_id)
        job = await self.session.get(ReadingJobRecord, job_id)
        if version is None or job is None or job.reading_version_id != version.id:
            raise CommerceError("Reading Job is not bound to the Reading Version")
        root = await self.session.get(ReadingRoot, version.reading_root_id)
        if root is None or root.owner_user_id != owner_user_id:
            raise CommerceError("Reading Version is not owned by the paid user")
        return version, job

    async def reconcile_channel(
        self,
        *,
        channel: str,
        payments: Sequence[ChannelPaymentSnapshot],
        refunds: Sequence[ChannelRefundSnapshot],
        run_at: datetime | None = None,
    ) -> tuple[PaymentReconciliationRun, list[PaymentReconciliationItem]]:
        """Persist a comparison between local facts and a normalized provider snapshot."""
        normalized_channel = channel.strip()
        if not normalized_channel:
            raise CommerceError("reconciliation channel is required")
        provider_payments = self._index_snapshot(
            payments,
            reference_name="transaction_id",
            label="payment",
        )
        provider_refunds = self._index_snapshot(
            refunds,
            reference_name="refund_id",
            label="refund",
        )
        local_payments = list(
            await self.session.scalars(
                select(Payment).where(Payment.channel == normalized_channel)
            )
        )
        local_refunds = list(
            await self.session.scalars(
                select(Refund).where(Refund.channel == normalized_channel)
            )
        )
        local_payments_by_ref = {
            payment.channel_transaction_id: payment for payment in local_payments
        }
        local_payments_by_id = {payment.id: payment for payment in local_payments}
        local_refunds_by_ref = {
            refund.channel_refund_id or f"local:{refund.id}": refund
            for refund in local_refunds
        }
        local_refund_totals_by_payment_id: dict[UUID, int] = {}
        for local_refund_row in local_refunds:
            local_refund_totals_by_payment_id[local_refund_row.payment_id] = (
                local_refund_totals_by_payment_id.get(local_refund_row.payment_id, 0)
                + local_refund_row.amount_minor
            )
        provider_refund_totals_by_payment_ref: dict[str, int] = {}
        for provider_refund_row in provider_refunds.values():
            if provider_refund_row.payment_transaction_id:
                provider_refund_totals_by_payment_ref[
                    provider_refund_row.payment_transaction_id
                ] = (
                    provider_refund_totals_by_payment_ref.get(
                        provider_refund_row.payment_transaction_id, 0
                    )
                    + provider_refund_row.amount_minor
                )
        reconciliation_run = PaymentReconciliationRun(
            channel=normalized_channel,
            run_at=run_at or datetime.now(UTC),
        )
        self.session.add(reconciliation_run)
        await self.session.flush()

        items: list[PaymentReconciliationItem] = []
        for reference in sorted(set(local_payments_by_ref) | set(provider_payments)):
            local_payment = local_payments_by_ref.get(reference)
            provider_payment = provider_payments.get(reference)
            discrepancy = self._payment_discrepancy(local_payment, provider_payment)
            items.append(
                PaymentReconciliationItem(
                    run_id=reconciliation_run.id,
                    kind="payment",
                    reference=reference,
                    payment_id=local_payment.id if local_payment is not None else None,
                    local_status=local_payment.status if local_payment is not None else None,
                    provider_status=(
                        provider_payment.status if provider_payment is not None else None
                    ),
                    local_amount_minor=(
                        local_payment.amount_minor if local_payment is not None else None
                    ),
                    provider_amount_minor=(
                        provider_payment.amount_minor if provider_payment is not None else None
                    ),
                    local_currency=(
                        local_payment.currency if local_payment is not None else None
                    ),
                    provider_currency=(
                        provider_payment.currency if provider_payment is not None else None
                    ),
                    discrepancy=discrepancy,
                )
            )

        for reference in sorted(set(local_refunds_by_ref) | set(provider_refunds)):
            local_refund = local_refunds_by_ref.get(reference)
            provider_refund = provider_refunds.get(reference)
            discrepancy = self._refund_discrepancy(
                local=local_refund,
                provider=provider_refund,
                local_payments_by_id=local_payments_by_id,
                local_payments_by_ref=local_payments_by_ref,
                local_refund_totals_by_payment_id=local_refund_totals_by_payment_id,
                provider_refund_totals_by_payment_ref=provider_refund_totals_by_payment_ref,
            )
            local_payment = (
                local_payments_by_id.get(local_refund.payment_id)
                if local_refund is not None
                else None
            )
            if local_payment is None and provider_refund is not None:
                local_payment = local_payments_by_ref.get(
                    provider_refund.payment_transaction_id or ""
                )
            items.append(
                PaymentReconciliationItem(
                    run_id=reconciliation_run.id,
                    kind="refund",
                    reference=reference,
                    payment_id=local_payment.id if local_payment is not None else None,
                    refund_id=local_refund.id if local_refund is not None else None,
                    local_status=local_refund.status if local_refund is not None else None,
                    provider_status=(
                        provider_refund.status if provider_refund is not None else None
                    ),
                    local_amount_minor=(
                        local_refund.amount_minor if local_refund is not None else None
                    ),
                    provider_amount_minor=(
                        provider_refund.amount_minor if provider_refund is not None else None
                    ),
                    local_currency=(
                        local_refund.currency if local_refund is not None else None
                    ),
                    provider_currency=(
                        provider_refund.currency if provider_refund is not None else None
                    ),
                    discrepancy=discrepancy,
                )
            )

        matched_count = sum(item.discrepancy == "matched" for item in items)
        reconciliation_run.item_count = len(items)
        reconciliation_run.matched_count = matched_count
        reconciliation_run.difference_count = len(items) - matched_count
        reconciliation_run.status = (
            "matched" if reconciliation_run.difference_count == 0 else "has_differences"
        )
        self.session.add_all(items)
        await self.session.flush()
        return reconciliation_run, items

    @staticmethod
    def _index_snapshot(
        snapshots: Sequence[SnapshotT],
        *,
        reference_name: str,
        label: str,
    ) -> dict[str, SnapshotT]:
        indexed: dict[str, SnapshotT] = {}
        for snapshot in snapshots:
            reference = str(getattr(snapshot, reference_name, "")).strip()
            if not reference:
                raise CommerceError(f"{label} reference is required")
            amount_minor = getattr(snapshot, "amount_minor", None)
            currency = str(getattr(snapshot, "currency", "")).strip().upper()
            if not isinstance(amount_minor, int) or amount_minor < 0:
                raise CommerceError(f"{label} amount is invalid")
            if len(currency) != 3:
                raise CommerceError(f"{label} currency is invalid")
            if reference in indexed:
                raise CommerceError(f"duplicate {label} reference in provider snapshot")
            indexed[reference] = snapshot
        return indexed

    @staticmethod
    def _payment_discrepancy(
        local: Payment | None,
        provider: ChannelPaymentSnapshot | None,
    ) -> str:
        if local is None:
            return "provider_only"
        if provider is None:
            return "local_only"
        if local.currency.upper() != provider.currency.strip().upper():
            return "currency_mismatch"
        if local.amount_minor != provider.amount_minor:
            return "amount_mismatch"
        provider_status = provider.status
        if local.status == "confirmed" and provider_status == "succeeded":
            return "matched"
        if local.status == "refunded" and provider_status in {"succeeded", "refunded"}:
            return "matched"
        return "status_mismatch"

    @staticmethod
    def _refund_discrepancy(
        *,
        local: Refund | None,
        provider: ChannelRefundSnapshot | None,
        local_payments_by_id: dict[UUID, Payment],
        local_payments_by_ref: dict[str, Payment],
        local_refund_totals_by_payment_id: dict[UUID, int],
        provider_refund_totals_by_payment_ref: dict[str, int],
    ) -> str:
        provider_payment_ref = (
            provider.payment_transaction_id if provider is not None else None
        )
        provider_payment = (
            local_payments_by_ref.get(provider_payment_ref)
            if provider_payment_ref
            else None
        )
        if provider is not None and provider_payment_ref and provider_payment is None:
            return "refund_without_payment"
        if local is None:
            if (
                provider_payment is not None
                and provider_payment_ref is not None
                and provider_refund_totals_by_payment_ref[provider_payment_ref]
                > provider_payment.amount_minor
            ):
                return "refund_amount_exceeds_payment"
            return "provider_only"
        local_payment = local_payments_by_id.get(local.payment_id)
        if local_payment is None:
            return "refund_without_payment"
        if provider is None:
            if (
                local_refund_totals_by_payment_id.get(local.payment_id, 0)
                > local_payment.amount_minor
            ):
                return "refund_amount_exceeds_payment"
            return "local_only"
        if provider_payment_ref and provider_payment_ref != local_payment.channel_transaction_id:
            return "refund_without_payment"
        provider_total = (
            provider_refund_totals_by_payment_ref.get(
                provider_payment_ref, provider.amount_minor
            )
            if provider_payment_ref
            else provider.amount_minor
        )
        local_total = local_refund_totals_by_payment_id.get(
            local.payment_id, local.amount_minor
        )
        if max(local_total, provider_total) > local_payment.amount_minor:
            return "refund_amount_exceeds_payment"
        if local.currency.upper() != provider.currency.strip().upper():
            return "currency_mismatch"
        if local.amount_minor != provider.amount_minor:
            return "amount_mismatch"
        if local.status == "confirmed" and provider.status == "succeeded":
            return "matched"
        if local.status == "pending" and provider.status == "pending":
            return "matched"
        return "refund_status_mismatch"

    async def refund_payment(
        self,
        *,
        payment_id: UUID,
        channel: str,
        channel_refund_id: str,
        reason: str,
        verified: bool,
        referral_refund_confirmation_id: UUID | None = None,
    ) -> tuple[Refund, bool]:
        if not verified:
            raise CommerceError("refund channel verification is required")
        if not channel.strip() or not channel_refund_id.strip() or not reason.strip():
            raise CommerceError("refund channel, reference and reason are required")
        existing = await self.session.scalar(
            select(Refund).where(
                Refund.channel == channel,
                Refund.channel_refund_id == channel_refund_id,
            )
        )
        if existing is not None:
            if existing.payment_id != payment_id:
                raise CommerceError("refund reference is bound to another payment")
            return existing, False
        payment = await self.session.get(Payment, payment_id)
        if payment is None or payment.status != "confirmed":
            raise CommerceError("payment is not refundable")
        if payment.channel != channel:
            raise CommerceError("refund channel does not match payment")
        order = await self.session.get(Order, payment.order_id)
        if order is None:
            raise CommerceError("order is missing")
        await self._require_referral_refund_confirmation(
            payment=payment,
            order=order,
            confirmation_id=referral_refund_confirmation_id,
        )
        refund = Refund(
            payment_id=payment.id,
            channel=channel,
            channel_refund_id=channel_refund_id,
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            reason=reason,
            status="confirmed",
            confirmed_at=datetime.now(UTC),
        )
        self.session.add(refund)
        await self.session.flush()
        payment.status = "refunded"
        if order is not None:
            order.status = "refunded"
        projection = await self.ledger.project(
            entitlement_id=f"order:{payment.order_id}",
            owner_user_id=order.owner_user_id,
        )
        kind: LedgerEventKind
        if projection.consumed > projection.reversed:
            kind = "REVERSE"
        elif projection.available > 0:
            kind = "EXPIRE"
        elif projection.reserved > 0:
            kind = "RELEASE"
        else:
            raise CommerceError("entitlement has no refundable unit")
        await self.ledger.append_entitlement_event(
            entitlement_id=f"order:{order.id}",
            owner_user_id=order.owner_user_id,
            kind=kind,
            quantity=1,
            source_type="refund",
            source_ref=str(refund.id),
            target_ref=str(payment.id),
        )
        await self._reverse_referral_reward_for_refund(
            payment_attempt_id=payment.attempt_id,
            refund_id=refund.id,
        )
        await self.session.flush()
        return refund, True

    async def append_entitlement_event(
        self,
        *,
        owner_user_id: UUID,
        entitlement_id: str,
        kind: LedgerEventKind,
        quantity: int,
        source_type: str,
        source_ref: str,
        target_ref: str | None = None,
    ) -> EntitlementProjection:
        await self.ledger.append_entitlement_event(
            entitlement_id=entitlement_id,
            owner_user_id=owner_user_id,
            kind=kind,
            quantity=quantity,
            source_type=source_type,
            source_ref=source_ref,
            target_ref=target_ref,
        )
        return await self.ledger.project(
            entitlement_id=entitlement_id,
            owner_user_id=owner_user_id,
        )

    async def adjust_entitlement_as_staff(
        self,
        *,
        owner_user_id: UUID,
        entitlement_id: str,
        action: Literal["grant", "compensate", "revoke"],
        quantity: int,
        reason: str,
        source_ref: str,
        target_ref: str | None,
        actor_staff_user_id: UUID,
        actor_session_id: UUID,
    ) -> tuple[EntitlementEventRecord, bool]:
        """Append one operator adjustment and its immutable audit fact.

        Grant and compensation use separate entitlement ids supplied by the
        operator. Revoke derives the only valid closing event from the current
        ledger projection: reserved units are released, available units expire,
        and already-consumed units are reversed.
        """
        if quantity < 1:
            raise CommerceError("entitlement quantity must be positive")
        normalized_entitlement_id = entitlement_id.strip()
        normalized_source_ref = source_ref.strip()
        normalized_reason = reason.strip()
        normalized_target_ref = (target_ref or "").strip() or None
        if not normalized_entitlement_id:
            raise CommerceError("entitlement id is required")
        if not normalized_source_ref:
            raise CommerceError("source reference is required")
        if not normalized_reason:
            raise CommerceError("adjustment reason is required")
        if await self.session.get(User, owner_user_id) is None:
            raise CommerceError("owner user not found")

        if action == "grant":
            source_type = "admin_grant"
            kind: LedgerEventKind = "GRANT"
        elif action == "compensate":
            source_type = "admin_compensation"
            kind = "GRANT"
        elif action == "revoke":
            source_type = "admin_revoke"
            kind = "EXPIRE"  # resolved from the projection below
        else:
            raise CommerceError("unsupported entitlement adjustment")

        existing = await self.ledger.find_events_by_source(
            source_type=source_type,
            source_ref=normalized_source_ref,
        )
        if existing:
            if len(existing) != 1:
                raise CommerceError("source reference has multiple entitlement events")
            replayed = existing[0]
            if (
                replayed.owner_user_id != owner_user_id
                or replayed.entitlement_id != normalized_entitlement_id
                or replayed.quantity != quantity
                or replayed.target_ref != normalized_target_ref
            ):
                raise CommerceError("source reference is bound to a different event")
            return replayed, False

        if action == "revoke":
            projection = await self.ledger.project(
                entitlement_id=normalized_entitlement_id,
                owner_user_id=owner_user_id,
            )
            reversible = projection.consumed - projection.reversed
            if projection.granted == 0:
                raise CommerceError("entitlement has not been granted")
            if projection.reserved >= quantity:
                kind = "RELEASE"
            elif projection.available >= quantity:
                kind = "EXPIRE"
            elif reversible >= quantity:
                kind = "REVERSE"
            else:
                raise CommerceError("revoke quantity exceeds the current entitlement state")

        try:
            record = await self.ledger.append_entitlement_event(
                entitlement_id=normalized_entitlement_id,
                owner_user_id=owner_user_id,
                kind=kind,
                quantity=quantity,
                source_type=source_type,
                source_ref=normalized_source_ref,
                target_ref=normalized_target_ref,
            )
        except ValueError as error:
            raise CommerceError(str(error)) from error

        self.session.add(
            AdminAuditEvent(
                staff_user_id=actor_staff_user_id,
                actor_session_id=actor_session_id,
                action="entitlement.adjusted",
                event_metadata={
                    "action": action,
                    "owner_user_id": str(owner_user_id),
                    "entitlement_id": normalized_entitlement_id,
                    "kind": kind,
                    "quantity": quantity,
                    "reason": normalized_reason,
                    "source_type": source_type,
                    "source_ref": normalized_source_ref,
                    "target_ref": normalized_target_ref,
                    "event_id": str(record.id),
                },
            )
        )
        await self.session.flush()
        return record, True

    async def enqueue_notification(
        self,
        *,
        owner_user_id: UUID,
        kind: str,
        dedupe_key: str,
        payload: dict[str, object],
        channel: NotificationChannel = "in_app",
        available_at: datetime | None = None,
    ) -> tuple[NotificationOutbox | None, bool]:
        if channel not in {"in_app", "email", "sms"}:
            raise CommerceError("unsupported notification channel")
        preferences = await self.get_notification_preferences(owner_user_id)
        if not getattr(preferences, f"{channel}_enabled"):
            return None, False
        existing = await self.session.scalar(
            select(NotificationOutbox).where(NotificationOutbox.dedupe_key == dedupe_key)
        )
        if existing is not None:
            return existing, False
        item = NotificationOutbox(
            owner_user_id=owner_user_id,
            kind=kind,
            dedupe_key=dedupe_key,
            payload={**payload, "channel": channel},
            available_at=available_at or datetime.now(UTC),
        )
        self.session.add(item)
        await self.session.flush()
        return item, True

    async def get_notification_preferences(self, user_id: UUID) -> NotificationPreference:
        preference = await self.session.scalar(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        if preference is None:
            preference = NotificationPreference(user_id=user_id)
            self.session.add(preference)
            await self.session.flush()
        return preference

    async def list_account_notifications(
        self,
        user_id: UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> tuple[list[NotificationOutbox], int]:
        if limit < 1:
            raise CommerceError("notification list limit must be positive")
        rows = list(
            await self.session.scalars(
                select(NotificationOutbox)
                .where(
                    NotificationOutbox.owner_user_id == user_id,
                    NotificationOutbox.deleted_at.is_(None),
                )
                .order_by(desc(NotificationOutbox.available_at), desc(NotificationOutbox.id))
            )
        )
        in_app = [item for item in rows if is_in_app_notification(item)]
        unread_count = sum(item.read_at is None for item in in_app)
        if unread_only:
            in_app = [item for item in in_app if item.read_at is None]
        return in_app[:limit], unread_count

    async def mark_account_notification_read(
        self,
        user_id: UUID,
        notification_id: UUID,
        *,
        now: datetime | None = None,
    ) -> NotificationOutbox:
        item = await self._account_notification(user_id, notification_id)
        if item.read_at is None:
            item.read_at = now or datetime.now(UTC)
            await self.session.flush()
        return item

    async def mark_all_account_notifications_read(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
    ) -> int:
        current = now or datetime.now(UTC)
        rows = list(
            await self.session.scalars(
                select(NotificationOutbox).where(
                    NotificationOutbox.owner_user_id == user_id,
                    NotificationOutbox.deleted_at.is_(None),
                    NotificationOutbox.read_at.is_(None),
                )
            )
        )
        for item in rows:
            if is_in_app_notification(item):
                item.read_at = current
        await self.session.flush()
        return 0

    async def delete_account_notification(
        self,
        user_id: UUID,
        notification_id: UUID,
        *,
        now: datetime | None = None,
    ) -> None:
        item = await self._account_notification(user_id, notification_id)
        item.deleted_at = now or datetime.now(UTC)
        await self.session.flush()

    async def _account_notification(
        self,
        user_id: UUID,
        notification_id: UUID,
    ) -> NotificationOutbox:
        item = await self.session.scalar(
            select(NotificationOutbox).where(
                NotificationOutbox.id == notification_id,
                NotificationOutbox.owner_user_id == user_id,
                NotificationOutbox.deleted_at.is_(None),
            )
        )
        if item is None or not is_in_app_notification(item):
            raise CommerceError("notification not found")
        return item

    async def update_notification_preferences(
        self,
        user_id: UUID,
        *,
        in_app_enabled: bool,
        email_enabled: bool,
        sms_enabled: bool,
    ) -> NotificationPreference:
        preference = await self.get_notification_preferences(user_id)
        preference.in_app_enabled = in_app_enabled
        preference.email_enabled = email_enabled
        preference.sms_enabled = sms_enabled
        preference.updated_at = datetime.now(UTC)
        await self.session.flush()
        return preference

    async def claim_notifications(
        self,
        *,
        limit: int = 50,
        now: datetime | None = None,
        lease_seconds: int = 300,
    ) -> list[NotificationOutbox]:
        if limit < 1:
            raise CommerceError("notification limit must be positive")
        if lease_seconds < 1:
            raise CommerceError("notification lease must be positive")
        current = now or datetime.now(UTC)
        rows = list(
            await self.session.scalars(
                select(NotificationOutbox)
                .where(
                    or_(
                        and_(
                            NotificationOutbox.status == "pending",
                            NotificationOutbox.available_at <= current,
                        ),
                        and_(
                            NotificationOutbox.status == "processing",
                            or_(
                                NotificationOutbox.processing_until.is_(None),
                                NotificationOutbox.processing_until <= current,
                            ),
                        ),
                    )
                )
                .order_by(NotificationOutbox.available_at, NotificationOutbox.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        for item in rows:
            item.status = "processing"
            item.attempt_count += 1
            item.processing_until = current + timedelta(seconds=lease_seconds)
            item.processing_token = uuid4().hex
        await self.session.flush()
        return rows

    async def mark_notification_sent(
        self,
        notification_id: UUID,
        *,
        now: datetime | None = None,
        claim_token: str | None = None,
    ) -> None:
        item = await self.session.get(NotificationOutbox, notification_id)
        if item is None or item.status != "processing":
            raise CommerceError("notification is not processing")
        if claim_token is not None and item.processing_token != claim_token:
            raise CommerceError("notification claim token is stale")
        item.status = "sent"
        item.sent_at = now or datetime.now(UTC)
        item.processing_until = None
        item.processing_token = None
        item.last_error = None
        await self.session.flush()

    async def mark_notification_failed(
        self,
        notification_id: UUID,
        error: str,
        *,
        now: datetime | None = None,
        retry_delay_seconds: float = 60.0,
        max_attempts: int = 3,
        claim_token: str | None = None,
    ) -> bool:
        if retry_delay_seconds < 0:
            raise CommerceError("notification retry delay cannot be negative")
        if max_attempts < 1:
            raise CommerceError("notification max attempts must be positive")
        item = await self.session.get(NotificationOutbox, notification_id)
        if item is None or item.status != "processing":
            raise CommerceError("notification is not processing")
        if claim_token is not None and item.processing_token != claim_token:
            raise CommerceError("notification claim token is stale")
        current = now or datetime.now(UTC)
        item.last_error = (str(error).strip() or "notification delivery failed")[:1000]
        item.processing_until = None
        item.processing_token = None
        if item.attempt_count >= max_attempts:
            item.status = "failed"
            item.available_at = current
            await self.session.flush()
            return False
        item.status = "pending"
        item.available_at = current + timedelta(seconds=retry_delay_seconds)
        await self.session.flush()
        return True

    async def retry_notification(
        self,
        notification_id: UUID,
        *,
        now: datetime | None = None,
    ) -> NotificationOutbox:
        """Requeue a terminal delivery failure without resetting its attempt history."""
        item = await self.session.get(NotificationOutbox, notification_id)
        if item is None:
            raise CommerceError("notification not found")
        if item.status != "failed":
            raise CommerceError("only failed notifications can be retried")
        item.status = "pending"
        item.available_at = now or datetime.now(UTC)
        item.processing_until = None
        item.processing_token = None
        await self.session.flush()
        return item
