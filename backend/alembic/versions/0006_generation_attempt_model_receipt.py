"""Persist the immutable standalone-model receipt with its Generation Attempt.

Revision ID: 0006_generation_attempt_model_receipt
Revises: 0005_prepare_token_replay_safety
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_generation_attempt_model_receipt"
down_revision: str | None = "0005_prepare_token_replay_safety"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("generation_attempts") as batch_op:
        batch_op.add_column(sa.Column("model_receipt", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("generation_attempts") as batch_op:
        batch_op.drop_column("model_receipt")
