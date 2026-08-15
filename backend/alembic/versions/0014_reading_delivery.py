"""Persist ReadingDocument, claim feedback, report feedback and share snapshots.

Revision ID: 0014_reading_delivery
Revises: 0013_privacy_closure
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_reading_delivery"
down_revision: str | None = "0013_privacy_closure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reading_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_copy_id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("payload_key_id", sa.String(length=120), nullable=False),
        sa.Column("payload_nonce", sa.String(length=64), nullable=False),
        sa.Column("payload_ciphertext", sa.Text(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "schema_version = 'reading-document/v1'",
            name="ck_reading_documents_schema_version_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["reading_version_id"],
            ["reading_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_copy_id"],
            ["accepted_copies.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reading_documents"),
        sa.UniqueConstraint(
            "reading_version_id",
            name="uq_reading_documents_reading_version_id",
        ),
    )
    op.create_table(
        "claim_verification_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.String(length=160), nullable=False),
        sa.Column("actor_ref", sa.String(length=180), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "outcome IN ('accepted', 'partial', 'disagreed', 'unknown')",
            name="ck_claim_verification_events_outcome_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["reading_version_id"],
            ["reading_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_claim_verification_events"),
        sa.UniqueConstraint(
            "reading_version_id",
            "claim_id",
            name="uq_claim_verification_events_version_claim",
        ),
    )
    op.create_table(
        "report_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column("actor_ref", sa.String(length=180), nullable=False),
        sa.Column("outcome", sa.String(length=24), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "outcome IN ('helpful', 'not_helpful', 'unknown')",
            name="ck_report_feedback_outcome_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["reading_version_id"],
            ["reading_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_report_feedback"),
    )
    op.create_index(
        "ix_report_feedback_reading_version_id",
        "report_feedback",
        ["reading_version_id"],
        unique=False,
    )
    op.create_table(
        "reading_share_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("owner_guest_session_id", sa.Uuid(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_key_id", sa.String(length=120), nullable=False),
        sa.Column("payload_nonce", sa.String(length=64), nullable=False),
        sa.Column("payload_ciphertext", sa.Text(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_guest_session_id IS NULL) "
            "OR (owner_user_id IS NULL AND owner_guest_session_id IS NOT NULL)",
            name="ck_reading_share_snapshots_owner_exactly_one",
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
        sa.PrimaryKeyConstraint("id", name="pk_reading_share_snapshots"),
        sa.UniqueConstraint("token_hash", name="uq_reading_share_snapshots_token_hash"),
    )
    op.create_index(
        "ix_reading_share_snapshots_expiry",
        "reading_share_snapshots",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reading_share_snapshots_expiry", table_name="reading_share_snapshots")
    op.drop_table("reading_share_snapshots")
    op.drop_index("ix_report_feedback_reading_version_id", table_name="report_feedback")
    op.drop_table("report_feedback")
    op.drop_table("claim_verification_events")
    op.drop_table("reading_documents")
