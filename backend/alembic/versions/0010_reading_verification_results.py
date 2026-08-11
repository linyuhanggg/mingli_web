"""Store three independent fact_ref-level Verification results.

Task 2 Step 4 replaces the single overall outcome with three per-fact results
validated against the reading's public fact panel. The four-value outcome
whitelist moves to the API contract, so the DB check constraint is dropped and
the results payload becomes a JSON column. Verification still lives outside
the runtime/model command path and never feeds the Prepare/Complete stream.

Revision ID: 0010_verification_results
Revises: 0009_idem_owner_unique
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0010_verification_results"
down_revision: str | None = "0009_idem_owner_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_TYPE = sa.JSON().with_variant(JSONB, "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("reading_verifications") as batch_op:
        batch_op.drop_constraint(
            "outcome_allowed",
            type_="check",
        )
        batch_op.add_column(
            sa.Column(
                "results",
                JSON_TYPE,
                server_default=sa.text("'[]'"),
                nullable=False,
            )
        )
        batch_op.drop_column("outcome")


def downgrade() -> None:
    with op.batch_alter_table("reading_verifications") as batch_op:
        batch_op.add_column(
            sa.Column(
                "outcome",
                sa.String(length=16),
                server_default=sa.text("'unknown'"),
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "outcome_allowed",
            "outcome IN ('accepted', 'partial', 'disagreed', 'unknown')",
        )
        batch_op.drop_column("results")
