"""Keep product identity and ordered Runtime capability membership on readings.

Revision ID: 0033_reading_product_runtime_capabilities
Revises: 0032_postgres_schema_alignment
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_reading_runtime_caps"
down_revision: str | None = "0032_postgres_schema_alignment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reading_roots", sa.Column("product_id", sa.String(length=80), nullable=True))
    op.add_column(
        "reading_roots",
        sa.Column("runtime_capability_ids", sa.JSON(), nullable=True),
    )
    op.add_column("reading_versions", sa.Column("product_id", sa.String(length=80), nullable=True))
    op.add_column(
        "reading_versions",
        sa.Column("runtime_capability_ids", sa.JSON(), nullable=True),
    )
    json_array_function = (
        "json_build_array" if op.get_bind().dialect.name == "postgresql" else "json_array"
    )
    for table in ("reading_roots", "reading_versions"):
        op.execute(
            sa.text(
                f"UPDATE {table} "
                f"SET product_id = capability_id, "
                f"runtime_capability_ids = {json_array_function}(capability_id) "
                "WHERE product_id IS NULL"
            )
        )


def downgrade() -> None:
    op.drop_column("reading_versions", "runtime_capability_ids")
    op.drop_column("reading_versions", "product_id")
    op.drop_column("reading_roots", "runtime_capability_ids")
    op.drop_column("reading_roots", "product_id")
