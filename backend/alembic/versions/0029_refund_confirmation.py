"""Persist explicit referral refund confirmations."""

import sqlalchemy as sa
from alembic import op

revision = "0029_refund_confirmation"
down_revision = "0028_referral_reward_slots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referral_refund_confirmations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_version_id", sa.Uuid(), nullable=False),
        sa.Column("product_version_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.String(length=80), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_session_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id"],
            ["referral_reward_reservations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_version_id"],
            ["referral_campaign_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_version_id"],
            ["product_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payment_id",
            name="uq_referral_refund_confirmations_payment_id",
        ),
    )
    op.create_index(
        "ix_referral_refund_confirmations_user_id",
        "referral_refund_confirmations",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_referral_refund_confirmations_user_id",
        table_name="referral_refund_confirmations",
    )
    op.drop_table("referral_refund_confirmations")
