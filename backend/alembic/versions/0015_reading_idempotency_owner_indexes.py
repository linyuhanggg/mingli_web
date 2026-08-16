"""Enforce Idempotency-Key uniqueness for each nullable owner branch.

The original three-column unique constraint included one nullable owner column
for every valid row. PostgreSQL therefore allowed duplicate keys whenever the
other owner column was NULL. Partial indexes enforce the intended invariant
for both user-owned and guest-owned rows.

Revision ID: 0015_idem_owner_indexes
Revises: 0014_reading_delivery
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_idem_owner_indexes"
down_revision: str | None = "0014_reading_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("reading_idempotency_keys") as batch_op:
        batch_op.drop_constraint(
            "uq_reading_idempotency_keys_owner_key",
            type_="unique",
        )
    op.create_index(
        "uq_reading_idempotency_keys_user_key",
        "reading_idempotency_keys",
        ["key_hash", "owner_user_id"],
        unique=True,
        sqlite_where=sa.text("owner_user_id IS NOT NULL"),
        postgresql_where=sa.text("owner_user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_reading_idempotency_keys_guest_key",
        "reading_idempotency_keys",
        ["key_hash", "owner_guest_session_id"],
        unique=True,
        sqlite_where=sa.text("owner_guest_session_id IS NOT NULL"),
        postgresql_where=sa.text("owner_guest_session_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_reading_idempotency_keys_guest_key",
        table_name="reading_idempotency_keys",
    )
    op.drop_index(
        "uq_reading_idempotency_keys_user_key",
        table_name="reading_idempotency_keys",
    )
    with op.batch_alter_table("reading_idempotency_keys") as batch_op:
        batch_op.create_unique_constraint(
            "uq_reading_idempotency_keys_owner_key",
            ["key_hash", "owner_user_id", "owner_guest_session_id"],
        )
