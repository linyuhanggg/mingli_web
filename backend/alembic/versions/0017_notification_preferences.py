"""Persist per-user notification channel preferences.

Revision ID: 0017_notification_preferences
Revises: 0016_profile_version_auth
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_notification_preferences"
down_revision: str | None = "0016_profile_version_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sms_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_notification_preferences"),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user_id"),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
