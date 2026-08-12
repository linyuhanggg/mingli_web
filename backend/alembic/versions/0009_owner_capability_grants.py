"""Add dogfood owner capability grant switches.

Revision ID: 0009_owner_grants
Revises: 0008_admin_staff
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_owner_grants"
down_revision: str | None = "0008_admin_staff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "owner_capability_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("capability_id", sa.String(length=32), nullable=False),
        sa.Column("granted_by", sa.String(length=120), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_owner_capability_grants_owner_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_owner_capability_grants"),
        sa.UniqueConstraint(
            "owner_user_id",
            "capability_id",
            name="uq_owner_capability_grants_owner_capability",
        ),
    )
    op.create_index(
        "ix_owner_capability_grants_owner_user_id",
        "owner_capability_grants",
        ["owner_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_owner_capability_grants_owner_user_id",
        table_name="owner_capability_grants",
    )
    op.drop_table("owner_capability_grants")
