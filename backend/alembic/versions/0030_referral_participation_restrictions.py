"""Persist referral participation restrictions created by approved corrections.

Revision ID: 0030_referral_restrictions
Revises: 0029_refund_confirmation
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_referral_restrictions"
down_revision: str | None = "0029_refund_confirmation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "referral_participation_restrictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_appeal_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_by_staff_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_appeal_id"],
            ["referral_appeals.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_staff_user_id"],
            ["staff_users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            name="uq_referral_participation_restrictions_user_id",
        ),
    )
    op.create_index(
        "ix_referral_participation_restrictions_appeal",
        "referral_participation_restrictions",
        ["source_appeal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_referral_participation_restrictions_appeal",
        table_name="referral_participation_restrictions",
    )
    op.drop_table("referral_participation_restrictions")
