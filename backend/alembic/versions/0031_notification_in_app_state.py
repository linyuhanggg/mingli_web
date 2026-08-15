"""Persist read and soft-delete state for in-app notifications.

Revision ID: 0031_notification_in_app_state
Revises: 0030_referral_restrictions
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_notification_in_app_state"
down_revision: str | None = "0030_referral_restrictions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notification_outbox",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_outbox",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notification_outbox_owner_available_at",
        "notification_outbox",
        ["owner_user_id", "available_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_outbox_owner_available_at",
        table_name="notification_outbox",
    )
    op.drop_column("notification_outbox", "deleted_at")
    op.drop_column("notification_outbox", "read_at")
