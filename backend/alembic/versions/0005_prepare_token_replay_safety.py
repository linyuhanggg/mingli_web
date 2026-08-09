"""Persist whether Prepare carries a replay-safe state token.

Revision ID: 0005_prepare_token_replay_safety
Revises: 0004_reading_job_fencing
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_prepare_token_replay_safety"
down_revision: str | None = "0004_reading_job_fencing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing encrypted rows cannot be classified without decrypting Prepare.
    # Defaulting them to false preserves the fail-closed recovery boundary.
    with op.batch_alter_table("reading_versions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "prepare_has_state_token",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("reading_versions") as batch_op:
        batch_op.drop_column("prepare_has_state_token")
