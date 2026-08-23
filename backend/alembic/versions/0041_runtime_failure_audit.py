"""Persist closed, non-PII Runtime failure classifications.

Revision ID: 0041_runtime_failure_audit
Revises: 0040_drop_minor_guardian_ck
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0041_runtime_failure_audit"
down_revision: str | None = "0040_drop_minor_guardian_ck"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "reading_versions"
CHECK = (
    "(runtime_failure_schema_version IS NULL AND runtime_failure_code IS NULL "
    "AND runtime_failure_category IS NULL AND runtime_failure_retryable IS NULL) "
    "OR (runtime_failure_schema_version IS NOT NULL "
    "AND runtime_failure_code IS NOT NULL "
    "AND runtime_failure_category IS NOT NULL "
    "AND runtime_failure_retryable IS NOT NULL)"
)
CHECK_NAME = "ck_reading_versions_runtime_failure_audit_all_or_none"


def upgrade() -> None:
    with op.batch_alter_table(TABLE) as batch:
        batch.add_column(sa.Column("runtime_failure_schema_version", sa.String(length=40)))
        batch.add_column(sa.Column("runtime_failure_code", sa.String(length=80)))
        batch.add_column(sa.Column("runtime_failure_category", sa.String(length=40)))
        batch.add_column(sa.Column("runtime_failure_retryable", sa.Boolean()))
        batch.create_check_constraint(CHECK_NAME, CHECK)


def downgrade() -> None:
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_constraint(CHECK_NAME, type_="check")
        batch.drop_column("runtime_failure_retryable")
        batch.drop_column("runtime_failure_category")
        batch.drop_column("runtime_failure_code")
        batch.drop_column("runtime_failure_schema_version")
