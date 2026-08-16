"""Persist encrypted short-lived PNG/PDF reading exports.

Revision ID: 0036_reading_exports
Revises: 0035_physiognomy_media
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_reading_exports"
down_revision: str | None = "0035_physiognomy_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reading_export_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("owner_guest_session_id", sa.Uuid(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("file_name", sa.String(length=180), nullable=False),
        sa.Column("payload_key_id", sa.String(length=120), nullable=False),
        sa.Column("payload_nonce", sa.String(length=64), nullable=False),
        sa.Column("payload_ciphertext", sa.Text(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_guest_session_id IS NULL) "
            "OR (owner_user_id IS NULL AND owner_guest_session_id IS NOT NULL)",
            name="owner_exactly_one",
        ),
        sa.CheckConstraint(
            "format IN ('png', 'pdf')",
            name="format_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["reading_version_id"],
            ["reading_versions.id"],
            ondelete="CASCADE",
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
            "token_hash",
            name="uq_reading_export_artifacts_token_hash",
        ),
    )
    op.create_index(
        "ix_reading_export_artifacts_expiry",
        "reading_export_artifacts",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reading_export_artifacts_expiry",
        table_name="reading_export_artifacts",
    )
    op.drop_table("reading_export_artifacts")
