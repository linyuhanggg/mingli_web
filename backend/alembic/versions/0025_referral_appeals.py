"""Persist referral appeal, risk signal, and independent correction approval facts.

Revision ID: 0025_referral_appeals
Revises: 0024_support_cases
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_referral_appeals"
down_revision: str | None = "0024_support_cases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "referral_appeals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attribution_id", sa.Uuid(), nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["attribution_id"], ["referral_attributions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attribution_id", name="uq_referral_appeals_attribution_id"),
    )
    op.create_index(
        "ix_referral_appeals_status_created_at",
        "referral_appeals",
        ["status", "created_at"],
    )

    op.create_table(
        "referral_risk_signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appeal_id", sa.Uuid(), nullable=False),
        sa.Column("signal_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_by_staff_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["appeal_id"], ["referral_appeals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_staff_user_id"], ["staff_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_referral_risk_signals_appeal_id",
        "referral_risk_signals",
        ["appeal_id"],
    )

    op.create_table(
        "referral_appeal_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("appeal_id", sa.Uuid(), nullable=False),
        sa.Column("staff_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["appeal_id"], ["referral_appeals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["staff_user_id"], ["staff_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "appeal_id",
            "staff_user_id",
            name="uq_referral_appeal_approvals_appeal_staff",
        ),
    )
    op.create_index(
        "ix_referral_appeal_approvals_appeal_id",
        "referral_appeal_approvals",
        ["appeal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_referral_appeal_approvals_appeal_id",
        table_name="referral_appeal_approvals",
    )
    op.drop_table("referral_appeal_approvals")
    op.drop_index("ix_referral_risk_signals_appeal_id", table_name="referral_risk_signals")
    op.drop_table("referral_risk_signals")
    op.drop_index("ix_referral_appeals_status_created_at", table_name="referral_appeals")
    op.drop_table("referral_appeals")
