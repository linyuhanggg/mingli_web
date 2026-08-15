from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.identity.models import Base


class ProductFamily(Base):
    __tablename__ = "product_families"
    __table_args__ = (UniqueConstraint("key", name="uq_product_families_key"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProductVersion(Base):
    __tablename__ = "product_versions"
    __table_args__ = (
        UniqueConstraint("family_id", "version", name="uq_product_versions_family_version"),
        Index("ix_product_versions_family_id", "family_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    family_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("product_families.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY")
    follow_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    follow_up_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contract_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProductOffer(Base):
    __tablename__ = "product_offers"
    __table_args__ = (
        UniqueConstraint("channel", "channel_sku", name="uq_product_offers_channel_sku"),
        Index("ix_product_offers_product_version_id", "product_version_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    product_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("product_versions.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_sku: Mapped[str] = mapped_column(String(160), nullable=False)
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY")
    enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_owner_user_id", "owner_user_id"),
        Index("ix_orders_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    product_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("product_versions.id", ondelete="RESTRICT"), nullable=False
    )
    purchase_target_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="created")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (
        UniqueConstraint("order_id", "idempotency_key_hash", name="uq_payment_attempts_order_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("attempt_id", name="uq_payments_attempt_id"),
        UniqueConstraint(
            "channel",
            "channel_transaction_id",
            name="uq_payments_channel_transaction",
        ),
        Index("ix_payments_order_id", "order_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False
    )
    attempt_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("payment_attempts.id", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_transaction_id: Mapped[str] = mapped_column(String(180), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="confirmed")
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("channel", "channel_refund_id", name="uq_refunds_channel_refund"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_refund_id: Mapped[str | None] = mapped_column(String(180))
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY")
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FulfillmentRecord(Base):
    """One paid target's immutable delivery boundary and current state."""

    __tablename__ = "fulfillments"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_fulfillments_order_id"),
        UniqueConstraint(
            "order_id",
            "idempotency_key_hash",
            name="uq_fulfillments_order_id_idempotency_key_hash",
        ),
        Index(
            "uq_fulfillments_reading_job_ref",
            "reading_job_ref",
            unique=True,
        ),
        Index("ix_fulfillments_status", "status"),
        Index("ix_fulfillments_target_ref", "purchase_target_ref"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    order_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entitlement_id: Mapped[str] = mapped_column(String(160), nullable=False)
    purchase_target_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="reserved")
    reading_version_ref: Mapped[str | None] = mapped_column(String(160))
    reading_job_ref: Mapped[str | None] = mapped_column(String(160))
    accepted_copy_ref: Mapped[str | None] = mapped_column(String(160))
    reading_document_ref: Mapped[str | None] = mapped_column(String(160))
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class PaymentNotificationReceipt(Base):
    __tablename__ = "payment_notification_receipts"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "external_event_id",
            name="uq_payment_notification_receipts_channel_event",
        ),
        Index("ix_payment_notification_receipts_payment_id", "payment_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    external_event_id: Mapped[str] = mapped_column(String(180), nullable=False)
    channel_transaction_id: Mapped[str | None] = mapped_column(String(180))
    provider_status: Mapped[str] = mapped_column(String(24), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(24), nullable=False)
    payment_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("payments.id", ondelete="SET NULL"),
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentReconciliationRun(Base):
    __tablename__ = "payment_reconciliation_runs"
    __table_args__ = (
        Index(
            "ix_payment_reconciliation_runs_channel_run_at",
            "channel",
            "run_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="matched")
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    difference_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PaymentReconciliationItem(Base):
    __tablename__ = "payment_reconciliation_items"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "kind",
            "reference",
            name="uq_payment_reconciliation_items_run_kind_ref",
        ),
        Index("ix_payment_reconciliation_items_run_id", "run_id"),
        Index("ix_payment_reconciliation_items_discrepancy", "discrepancy"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("payment_reconciliation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    reference: Mapped[str] = mapped_column(String(180), nullable=False)
    payment_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("payments.id", ondelete="RESTRICT"),
    )
    refund_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("refunds.id", ondelete="RESTRICT"),
    )
    local_status: Mapped[str | None] = mapped_column(String(24))
    provider_status: Mapped[str | None] = mapped_column(String(24))
    local_amount_minor: Mapped[int | None] = mapped_column(Integer)
    provider_amount_minor: Mapped[int | None] = mapped_column(Integer)
    local_currency: Mapped[str | None] = mapped_column(String(3))
    provider_currency: Mapped[str | None] = mapped_column(String(3))
    discrepancy: Mapped[str] = mapped_column(String(48), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EntitlementEventRecord(Base):
    __tablename__ = "entitlement_events"
    __table_args__ = (
        Index("ix_entitlement_events_entitlement_id", "entitlement_id"),
        Index("ix_entitlement_events_owner_user_id", "owner_user_id"),
        UniqueConstraint(
            "source_type",
            "source_ref",
            "kind",
            name="uq_entitlement_events_source_kind",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    entitlement_id: Mapped[str] = mapped_column(String(160), nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    target_ref: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_notification_outbox_dedupe_key"),
        Index("ix_notification_outbox_status_available_at", "status", "available_at"),
        Index("ix_notification_outbox_processing_until", "processing_until"),
        Index(
            "ix_notification_outbox_owner_available_at",
            "owner_user_id",
            "available_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(180), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON(), default=dict, nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    processing_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_token: Mapped[str | None] = mapped_column(String(64))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    in_app_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    sms_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
