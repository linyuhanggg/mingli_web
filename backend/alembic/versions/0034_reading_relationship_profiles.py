"""Persist the two profiles and relationship type for relationship readings.

Revision ID: 0034_reading_relationship_profiles
Revises: 0033_reading_runtime_caps
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034_reading_relationship"
down_revision: str | None = "0033_reading_runtime_caps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reading_roots",
        sa.Column("profile_version_ids", sa.JSON(), nullable=True),
    )
    op.add_column(
        "reading_roots",
        sa.Column("relationship_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "reading_versions",
        sa.Column("relationship_type", sa.String(length=32), nullable=True),
    )
    json_array_function = (
        "json_build_array" if op.get_bind().dialect.name == "postgresql" else "json_array"
    )
    op.execute(
        sa.text(
            "UPDATE reading_roots "
            f"SET profile_version_ids = {json_array_function}(profile_version_id) "
            "WHERE profile_version_id IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("reading_versions", "relationship_type")
    op.drop_column("reading_roots", "relationship_type")
    op.drop_column("reading_roots", "profile_version_ids")
