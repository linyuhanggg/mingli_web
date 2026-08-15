"""Persist account data-rights closure requests.

Revision ID: 0013_privacy_closure
Revises: 0012_referrals_content
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_privacy_closure"
down_revision: str | None = "0012_referrals_content"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_closure_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("cancel_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_account_closure_requests_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_account_closure_requests"),
        sa.UniqueConstraint("id", name="uq_account_closure_requests_id"),
    )
    op.create_index(
        "uq_account_closure_requests_pending_user",
        "account_closure_requests",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("status = 'pending'"),
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_account_closure_requests_status_cancel_until",
        "account_closure_requests",
        ["status", "cancel_until"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_account_closure_requests_status_cancel_until",
        table_name="account_closure_requests",
    )
    op.drop_index(
        "uq_account_closure_requests_pending_user",
        table_name="account_closure_requests",
    )
    op.drop_table("account_closure_requests")
