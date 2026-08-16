"""Prevent more than one Payment fact for one PaymentAttempt.

Revision ID: 0023_payment_attempt_unique
Revises: 0022_followup_contract
Create Date: 2026-08-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0023_payment_attempt_unique"
down_revision: str | None = "0022_followup_contract"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("payments") as batch:
        batch.create_unique_constraint("uq_payments_attempt_id", ["attempt_id"])


def downgrade() -> None:
    with op.batch_alter_table("payments") as batch:
        batch.drop_constraint("uq_payments_attempt_id", type_="unique")
