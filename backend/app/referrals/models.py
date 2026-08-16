from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.identity.models import Base


class ReferralCampaignVersion(Base):
    __tablename__ = "referral_campaign_versions"
    __table_args__ = (
        UniqueConstraint("campaign_key", "version", name="uq_referral_campaign_key_version"),
        Index("ix_referral_campaign_versions_state", "state"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_key: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_limit: Mapped[int | None] = mapped_column(Integer)
    per_inviter_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    reward_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reward_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=90 * 86400)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReferralRewardSlot(Base):
    """An immutable, product-specific reward rule published with a campaign."""

    __tablename__ = "referral_reward_slots"
    __table_args__ = (
        UniqueConstraint(
            "campaign_version_id",
            "product_version_id",
            "slot_key",
            name="uq_referral_reward_slots_campaign_product_slot",
        ),
        Index(
            "ix_referral_reward_slots_campaign_product",
            "campaign_version_id",
            "product_version_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_campaign_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("product_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    slot_key: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    total_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReferralCode(Base):
    __tablename__ = "referral_codes"
    __table_args__ = (
        UniqueConstraint("code", name="uq_referral_codes_code"),
        Index("ix_referral_codes_campaign_id", "campaign_version_id"),
        Index("ix_referral_codes_inviter_user_id", "inviter_user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_campaign_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    inviter_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReferralTemporaryAttribution(Base):
    __tablename__ = "referral_temporary_attributions"
    __table_args__ = (
        UniqueConstraint(
            "campaign_version_id",
            "visitor_key_hash",
            name="uq_referral_temp_campaign_visitor",
        ),
        Index("ix_referral_temp_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_campaign_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    code_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_codes.id", ondelete="CASCADE"),
        nullable=False,
    )
    visitor_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    inviter_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReferralAttribution(Base):
    __tablename__ = "referral_attributions"
    __table_args__ = (
        UniqueConstraint("referred_user_id", name="uq_referral_attributions_referred_user"),
        Index("ix_referral_attributions_inviter_user_id", "inviter_user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_campaign_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_codes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    referred_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    inviter_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="locked")


class ReferralRewardReservation(Base):
    __tablename__ = "referral_reward_reservations"
    __table_args__ = (
        UniqueConstraint(
            "campaign_version_id",
            "referred_user_id",
            name="uq_referral_reward_campaign_referred",
        ),
        Index("ix_referral_reward_reservations_inviter_user_id", "inviter_user_id"),
        UniqueConstraint(
            "payment_attempt_id",
            name="uq_referral_reward_reservations_payment_attempt",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    campaign_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_campaign_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attribution_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_attributions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    referred_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    inviter_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("product_versions.id", ondelete="RESTRICT"),
    )
    payment_attempt_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("payment_attempts.id", ondelete="RESTRICT"),
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="reserved")
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReferralRefundConfirmation(Base):
    """A user's explicit, versioned confirmation before a voluntary refund."""

    __tablename__ = "referral_refund_confirmations"
    __table_args__ = (
        UniqueConstraint(
            "payment_id",
            name="uq_referral_refund_confirmations_payment_id",
        ),
        Index(
            "ix_referral_refund_confirmations_user_id",
            "user_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
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
    reservation_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_reward_reservations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    campaign_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_campaign_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("product_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_session_id: Mapped[UUID | None] = mapped_column(Uuid)


class ReferralAppeal(Base):
    """One explainable appeal for a locked referral attribution."""

    __tablename__ = "referral_appeals"
    __table_args__ = (
        UniqueConstraint("attribution_id", name="uq_referral_appeals_attribution_id"),
        Index("ix_referral_appeals_status_created_at", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    attribution_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_attributions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requester_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")
    decision_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReferralParticipationRestriction(Base):
    """A durable referral-only participation block created by a correction."""

    __tablename__ = "referral_participation_restrictions"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_referral_participation_restrictions_user_id"),
        Index("ix_referral_participation_restrictions_appeal", "source_appeal_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_appeal_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_appeals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_staff_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("staff_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReferralRiskSignal(Base):
    """A non-deterministic risk hint; it never changes reward state by itself."""

    __tablename__ = "referral_risk_signals"
    __table_args__ = (Index("ix_referral_risk_signals_appeal_id", "appeal_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    appeal_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_appeals.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_staff_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReferralAppealApproval(Base):
    """One distinct staff approval for a correction; uniqueness enforces independence."""

    __tablename__ = "referral_appeal_approvals"
    __table_args__ = (
        UniqueConstraint(
            "appeal_id",
            "staff_user_id",
            name="uq_referral_appeal_approvals_appeal_staff",
        ),
        Index("ix_referral_appeal_approvals_appeal_id", "appeal_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    appeal_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("referral_appeals.id", ondelete="CASCADE"),
        nullable=False,
    )
    staff_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("staff_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
