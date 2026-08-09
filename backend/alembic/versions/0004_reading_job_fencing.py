"""Add fencing tokens to reading job leases.

Revision ID: 0004_reading_job_fencing
Revises: 0003_reading_integrity
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_reading_job_fencing"
down_revision: str | None = "0003_reading_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEASE_ALL_OR_NONE = (
    "(lease_owner IS NULL AND lease_token IS NULL AND lease_expires_at IS NULL) "
    "OR (lease_owner IS NOT NULL AND lease_token IS NOT NULL "
    "AND lease_expires_at IS NOT NULL)"
)


def upgrade() -> None:
    with op.batch_alter_table("reading_jobs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "lease_generation",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("lease_token", sa.String(length=64), nullable=True))
    op.execute(
        "UPDATE reading_jobs SET status = 'queued', lease_owner = NULL, "
        "lease_token = NULL, lease_expires_at = NULL "
        "WHERE lease_owner IS NOT NULL OR lease_expires_at IS NOT NULL"
    )
    with op.batch_alter_table("reading_jobs") as batch_op:
        batch_op.create_check_constraint(
            op.f("ck_reading_jobs_lease_envelope_all_or_none"),
            LEASE_ALL_OR_NONE,
        )


def downgrade() -> None:
    with op.batch_alter_table("reading_jobs") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_reading_jobs_lease_envelope_all_or_none"),
            type_="check",
        )
        batch_op.drop_column("lease_token")
        batch_op.drop_column("lease_generation")
