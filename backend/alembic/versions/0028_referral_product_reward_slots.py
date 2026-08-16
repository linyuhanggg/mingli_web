"""Bind referral rewards to immutable ProductVersion slots and payment attempts.

Revision ID: 0028_referral_product_reward_slots
Revises: 0027_identity_destination_cipher
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_referral_reward_slots"
down_revision: str | None = "0027_identity_destination_cipher"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "referral_reward_slots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_version_id", sa.Uuid(), nullable=False),
        sa.Column("product_version_id", sa.Uuid(), nullable=False),
        sa.Column("slot_key", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("total_limit", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_version_id"],
            ["referral_campaign_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_version_id"],
            ["product_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_version_id",
            "product_version_id",
            "slot_key",
            name="uq_referral_reward_slots_campaign_product_slot",
        ),
    )
    op.create_index(
        "ix_referral_reward_slots_campaign_product",
        "referral_reward_slots",
        ["campaign_version_id", "product_version_id"],
    )

    with op.batch_alter_table("referral_reward_reservations") as batch:
        batch.add_column(
            sa.Column("product_version_id", sa.Uuid(), nullable=True),
        )
        batch.add_column(
            sa.Column("payment_attempt_id", sa.Uuid(), nullable=True),
        )
        batch.create_foreign_key(
            "fk_referral_reward_reservations_product_version",
            "product_versions",
            ["product_version_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_referral_reward_reservations_payment_attempt",
            "payment_attempts",
            ["payment_attempt_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_unique_constraint(
            "uq_referral_reward_reservations_payment_attempt",
            ["payment_attempt_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("referral_reward_reservations") as batch:
        batch.drop_constraint(
            "uq_referral_reward_reservations_payment_attempt",
            type_="unique",
        )
        batch.drop_constraint(
            "fk_referral_reward_reservations_payment_attempt",
            type_="foreignkey",
        )
        batch.drop_constraint(
            "fk_referral_reward_reservations_product_version",
            type_="foreignkey",
        )
        batch.drop_column("payment_attempt_id")
        batch.drop_column("product_version_id")

    op.drop_index(
        "ix_referral_reward_slots_campaign_product",
        table_name="referral_reward_slots",
    )
    op.drop_table("referral_reward_slots")
