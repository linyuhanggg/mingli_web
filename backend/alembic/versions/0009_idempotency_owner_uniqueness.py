"""Enforce owner-scoped reading idempotency with partial unique indexes.

A single UNIQUE constraint on (key_hash, owner_user_id, owner_guest_session_id)
never fires because exactly one owner column is always NULL and NULLs are
distinct. Replace it with two partial unique indexes, one per owner kind.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_idem_owner_unique"
down_revision: str | None = "0008_admin_staff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_USER_OWNED = sa.text("owner_user_id IS NOT NULL")
_GUEST_OWNED = sa.text("owner_guest_session_id IS NOT NULL")


def upgrade() -> None:
    with op.batch_alter_table("reading_idempotency_keys") as batch_op:
        batch_op.drop_constraint(
            "uq_reading_idempotency_keys_owner_key",
            type_="unique",
        )
        batch_op.create_index(
            "uq_reading_idem_user_key",
            ["key_hash", "owner_user_id"],
            unique=True,
            sqlite_where=_USER_OWNED,
            postgresql_where=_USER_OWNED,
        )
        batch_op.create_index(
            "uq_reading_idem_guest_key",
            ["key_hash", "owner_guest_session_id"],
            unique=True,
            sqlite_where=_GUEST_OWNED,
            postgresql_where=_GUEST_OWNED,
        )


def downgrade() -> None:
    with op.batch_alter_table("reading_idempotency_keys") as batch_op:
        batch_op.drop_index("uq_reading_idem_guest_key")
        batch_op.drop_index("uq_reading_idem_user_key")
        batch_op.create_unique_constraint(
            "uq_reading_idempotency_keys_owner_key",
            ["key_hash", "owner_user_id", "owner_guest_session_id"],
        )
