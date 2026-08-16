"""Persist owner-scoped physiognomy media metadata without raw bytes.

Revision ID: 0035_physiognomy_media
Revises: 0034_reading_relationship
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_physiognomy_media"
down_revision: str | None = "0034_reading_relationship"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "physiognomy_media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("owner_guest_session_id", sa.Uuid(), nullable=True),
        sa.Column("object_key", sa.String(length=240), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("consent_policy_version", sa.String(length=80), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="ready", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_guest_session_id IS NULL) "
            "OR (owner_user_id IS NULL AND owner_guest_session_id IS NOT NULL)",
            name="ck_physiognomy_media_assets_owner_exactly_one",
        ),
        sa.CheckConstraint(
            "status IN ('ready', 'deleted', 'expired')",
            name="ck_physiognomy_media_assets_status_allowed",
        ),
        sa.CheckConstraint(
            "mode IN ('face', 'palm', 'posture', 'combined')",
            name="ck_physiognomy_media_assets_mode_allowed",
        ),
        sa.CheckConstraint(
            "content_type IN ('image/jpeg', 'image/png', 'image/heic')",
            name="ck_physiognomy_media_assets_content_type_allowed",
        ),
        sa.CheckConstraint(
            "byte_size > 0 AND byte_size <= 10485760",
            name="ck_physiognomy_media_assets_byte_size_allowed",
        ),
        sa.CheckConstraint(
            "width >= 640 AND height >= 640",
            name="ck_physiognomy_media_assets_pixel_dimensions_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_guest_session_id"],
            ["guest_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "object_key",
            name="uq_physiognomy_media_assets_object_key",
        ),
    )
    op.create_index(
        "ix_physiognomy_media_assets_owner_user_id",
        "physiognomy_media_assets",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_physiognomy_media_assets_owner_guest_session_id",
        "physiognomy_media_assets",
        ["owner_guest_session_id"],
    )
    op.create_index(
        "ix_physiognomy_media_assets_status_expires_at",
        "physiognomy_media_assets",
        ["status", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_physiognomy_media_assets_status_expires_at",
        table_name="physiognomy_media_assets",
    )
    op.drop_index(
        "ix_physiognomy_media_assets_owner_guest_session_id",
        table_name="physiognomy_media_assets",
    )
    op.drop_index(
        "ix_physiognomy_media_assets_owner_user_id",
        table_name="physiognomy_media_assets",
    )
    op.drop_table("physiognomy_media_assets")
