"""Persist Admin support case applications.

Revision ID: 0024_support_cases
Revises: 0023_payment_attempt_unique
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_support_cases"
down_revision: str | None = "0023_payment_attempt_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("subject_ref", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_by_staff_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["created_by_staff_user_id"],
            ["staff_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_cases_status_created_at",
        "support_cases",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_support_cases_owner_user_id",
        "support_cases",
        ["owner_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_support_cases_owner_user_id", table_name="support_cases")
    op.drop_index("ix_support_cases_status_created_at", table_name="support_cases")
    op.drop_table("support_cases")
