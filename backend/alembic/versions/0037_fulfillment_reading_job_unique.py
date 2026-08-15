"""Prevent two paid fulfillments from sharing one Reading Job.

Revision ID: 0037_fulfillment_job_unique
Revises: 0036_reading_exports
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0037_fulfillment_job_unique"
down_revision: str | None = "0036_reading_exports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_fulfillments_reading_job_ref",
        "fulfillments",
        ["reading_job_ref"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_fulfillments_reading_job_ref",
        table_name="fulfillments",
    )
