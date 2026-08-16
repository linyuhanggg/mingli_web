"""Add notification delivery attempts and claim fencing.

Revision ID: 0018_notification_delivery_state
Revises: 0017_notification_preferences
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_notification_delivery_state"
down_revision: str | None = "0017_notification_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notification_outbox",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "notification_outbox",
        sa.Column("processing_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_outbox",
        sa.Column("processing_token", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_notification_outbox_processing_until",
        "notification_outbox",
        ["processing_until"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_outbox_processing_until",
        table_name="notification_outbox",
    )
    op.drop_column("notification_outbox", "processing_token")
    op.drop_column("notification_outbox", "processing_until")
    op.drop_column("notification_outbox", "attempt_count")
