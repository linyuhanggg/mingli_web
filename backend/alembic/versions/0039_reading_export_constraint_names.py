"""Align reading export check-constraint names with ORM metadata.

Revision ID: 0039_export_ck_names
Revises: 0038_reading_waiting_timeout
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0039_export_ck_names"
down_revision: str | None = "0038_reading_waiting_timeout"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rename_export_checks() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    table_name = "reading_export_artifacts"
    checks = inspect(bind).get_check_constraints(table_name)
    for item in checks:
        old_name = item.get("name")
        definition = str(item.get("sqltext") or "").lower()
        if not old_name:
            continue
        if "owner_user_id" in definition and "owner_guest_session_id" in definition:
            new_name = "ck_reading_export_artifacts_owner_exactly_one"
        elif "format" in definition and "'png'" in definition and "'pdf'" in definition:
            new_name = "ck_reading_export_artifacts_format_allowed"
        else:
            continue
        if old_name == new_name:
            continue
        quoted_old = old_name.replace('"', '""')
        op.execute(
            sa.text(
                f'ALTER TABLE "{table_name}" '
                f'RENAME CONSTRAINT "{quoted_old}" TO "{new_name}"'
            )
        )


def upgrade() -> None:
    _rename_export_checks()


def downgrade() -> None:
    # The previous names were dialect-truncated and cannot be reconstructed
    # safely from the migration file.  Keeping the canonical names is safer
    # than renaming them to a guessed identifier during rollback.
    pass
