"""Track when a Reading Version starts waiting for supplemental input.

Revision ID: 0038_reading_waiting_timeout
Revises: 0037_fulfillment_job_unique
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_reading_waiting_timeout"
down_revision: str | None = "0037_fulfillment_job_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reading_versions",
        sa.Column("waiting_input_at", sa.DateTime(timezone=True), nullable=True),
    )
    # The historical transition time was not persisted before this revision.
    # Start those existing waits at migration time instead of inventing an
    # earlier deadline or leaving them permanently invisible to the scanner.
    op.execute(
        sa.text(
            "UPDATE reading_versions "
            "SET waiting_input_at = CURRENT_TIMESTAMP "
            "WHERE status = 'waiting_input' AND waiting_input_at IS NULL"
        )
    )
    op.create_index(
        "ix_reading_versions_waiting_at",
        "reading_versions",
        ["status", "waiting_input_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reading_versions_waiting_at",
        table_name="reading_versions",
    )
    op.drop_column("reading_versions", "waiting_input_at")
