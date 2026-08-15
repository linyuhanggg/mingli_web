"""Persist the frozen paid Reading follow-up contract snapshot.

Revision ID: 0022_followup_contract
Revises: 0021_fulfillment_scope
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_followup_contract"
down_revision: str | None = "0021_fulfillment_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reading_roots",
        sa.Column("product_version_snapshot_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "reading_roots",
        sa.Column("follow_up_count_snapshot", sa.Integer(), nullable=True),
    )
    op.add_column(
        "reading_roots",
        sa.Column("follow_up_window_seconds_snapshot", sa.Integer(), nullable=True),
    )
    op.add_column(
        "reading_roots",
        sa.Column("follow_up_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reading_roots", "follow_up_started_at")
    op.drop_column("reading_roots", "follow_up_window_seconds_snapshot")
    op.drop_column("reading_roots", "follow_up_count_snapshot")
    op.drop_column("reading_roots", "product_version_snapshot_id")
