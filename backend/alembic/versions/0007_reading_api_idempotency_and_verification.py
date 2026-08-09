"""Persist reading Idempotency-Key mapping and user Verification feedback.

Task 11 requires Idempotency-Key replay to be durable in PostgreSQL and
Verification to live outside the runtime/model command path. These two tables
are additive: the reading job queue keeps working unchanged, and Verification
never feeds the Prepare/Complete command stream.

Revision ID: 0007_api_idem_verify
Revises: 0006_model_receipt
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_api_idem_verify"
down_revision: str | None = "0006_model_receipt"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reading_idempotency_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("owner_guest_session_id", sa.Uuid(), nullable=True),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_guest_session_id"],
            ["guest_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reading_version_id"],
            ["reading_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "key_hash",
            "owner_user_id",
            "owner_guest_session_id",
            name=op.f("uq_reading_idempotency_keys_owner_key"),
        ),
        sa.CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_guest_session_id IS NULL) "
            "OR (owner_user_id IS NULL AND owner_guest_session_id IS NOT NULL)",
            name=op.f("ck_reading_idempotency_keys_owner_exactly_one"),
        ),
    )
    op.create_index(
        "ix_reading_idempotency_keys_reading_version_id",
        "reading_idempotency_keys",
        ["reading_version_id"],
        unique=False,
    )
    op.create_table(
        "reading_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["reading_version_id"],
            ["reading_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reading_version_id",
            name=op.f("uq_reading_verifications_reading_version_id"),
        ),
        sa.CheckConstraint(
            "outcome IN ('accepted', 'partial', 'disagreed', 'unknown')",
            name=op.f("ck_reading_verifications_outcome_allowed"),
        ),
    )
    op.add_column(
        "subject_profiles",
        sa.Column("label", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subject_profiles", "label")
    op.drop_table("reading_verifications")
    op.drop_index(
        "ix_reading_idempotency_keys_reading_version_id",
        table_name="reading_idempotency_keys",
    )
    op.drop_table("reading_idempotency_keys")
