"""Create immutable encrypted profiles and reading state.

Revision ID: 0002_profiles_and_readings
Revises: 0001_identity_foundation
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_profiles_and_readings"
down_revision: str | None = "0001_identity_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _created_at() -> sa.Column[object]:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "subject_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("owner_guest_session_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_subject_profiles_owner_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_guest_session_id"],
            ["guest_sessions.id"],
            name="fk_subject_profiles_owner_guest_session_id_guest_sessions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_subject_profiles"),
    )
    op.create_table(
        "profile_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload_key_id", sa.String(length=120), nullable=False),
        sa.Column("payload_nonce", sa.String(length=64), nullable=False),
        sa.Column("payload_ciphertext", sa.Text(), nullable=False),
        sa.Column("payload_fingerprint", sa.String(length=64), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["subject_profiles.id"],
            name="fk_profile_versions_profile_id_subject_profiles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_profile_versions"),
        sa.UniqueConstraint(
            "profile_id",
            "version",
            name="uq_profile_versions_profile_id_version",
        ),
    )
    op.create_table(
        "runtime_releases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("source_commit", sa.String(length=64), nullable=False),
        sa.Column("release_manifest_digest", sa.String(length=64), nullable=False),
        sa.Column("protocol_version", sa.String(length=80), nullable=False),
        sa.Column("describe_manifest_digest", sa.String(length=64), nullable=False),
        sa.Column("image_digest", sa.String(length=160), nullable=True),
        sa.Column(
            "production_ready",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_runtime_releases"),
        sa.UniqueConstraint(
            "release_manifest_digest",
            name="uq_runtime_releases_release_manifest_digest",
        ),
    )
    op.create_table(
        "reading_roots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=True),
        sa.Column("owner_guest_session_id", sa.Uuid(), nullable=True),
        sa.Column("profile_version_id", sa.Uuid(), nullable=True),
        sa.Column("capability_id", sa.String(length=80), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_reading_roots_owner_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_guest_session_id"],
            ["guest_sessions.id"],
            name="fk_reading_roots_owner_guest_session_id_guest_sessions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["profile_version_id"],
            ["profile_versions.id"],
            name="fk_reading_roots_profile_version_id_profile_versions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reading_roots"),
    )
    op.create_table(
        "reading_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_root_id", sa.Uuid(), nullable=False),
        sa.Column("runtime_release_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("capability_id", sa.String(length=80), nullable=False),
        sa.Column("object_id", sa.String(length=80), nullable=False),
        sa.Column("dimension_ids", sa.JSON(), nullable=False),
        sa.Column("horizon", sa.JSON(), nullable=False),
        sa.Column("prepare_key_id", sa.String(length=120), nullable=False),
        sa.Column("prepare_nonce", sa.String(length=64), nullable=False),
        sa.Column("prepare_ciphertext", sa.Text(), nullable=False),
        sa.Column("prepare_digest", sa.String(length=64), nullable=False),
        sa.Column("state_token_key_id", sa.String(length=120), nullable=True),
        sa.Column("state_token_nonce", sa.String(length=64), nullable=True),
        sa.Column("state_token_ciphertext", sa.Text(), nullable=True),
        sa.Column("state_token_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("last_result_key_id", sa.String(length=120), nullable=True),
        sa.Column("last_result_nonce", sa.String(length=64), nullable=True),
        sa.Column("last_result_ciphertext", sa.Text(), nullable=True),
        sa.Column("last_result_digest", sa.String(length=64), nullable=True),
        sa.Column("completion_key_id", sa.String(length=120), nullable=True),
        sa.Column("completion_nonce", sa.String(length=64), nullable=True),
        sa.Column("completion_ciphertext", sa.Text(), nullable=True),
        sa.Column("completion_digest", sa.String(length=64), nullable=True),
        _created_at(),
        sa.CheckConstraint(
            "(state_token_ciphertext IS NULL AND state_token_fingerprint IS NULL) "
            "OR (state_token_ciphertext IS NOT NULL AND state_token_fingerprint IS NOT NULL)",
            name="ck_reading_versions_state_token_ciphertext_has_fingerprint",
        ),
        sa.CheckConstraint(
            "(completion_ciphertext IS NULL AND completion_digest IS NULL) "
            "OR (completion_ciphertext IS NOT NULL AND completion_digest IS NOT NULL)",
            name="ck_reading_versions_completion_ciphertext_has_digest",
        ),
        sa.ForeignKeyConstraint(
            ["reading_root_id"],
            ["reading_roots.id"],
            name="fk_reading_versions_reading_root_id_reading_roots",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["runtime_release_id"],
            ["runtime_releases.id"],
            name="fk_reading_versions_runtime_release_id_runtime_releases",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reading_versions"),
        sa.UniqueConstraint(
            "reading_root_id",
            "version",
            name="uq_reading_versions_reading_root_id_version",
        ),
    )
    op.create_table(
        "fact_briefs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column("payload_key_id", sa.String(length=120), nullable=False),
        sa.Column("payload_nonce", sa.String(length=64), nullable=False),
        sa.Column("payload_ciphertext", sa.Text(), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["reading_version_id"],
            ["reading_versions.id"],
            name="fk_fact_briefs_reading_version_id_reading_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fact_briefs"),
        sa.UniqueConstraint(
            "reading_version_id",
            name="uq_fact_briefs_reading_version_id",
        ),
    )
    op.create_table(
        "generation_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("candidate_key_id", sa.String(length=120), nullable=True),
        sa.Column("candidate_nonce", sa.String(length=64), nullable=True),
        sa.Column("candidate_ciphertext", sa.Text(), nullable=True),
        sa.Column("candidate_digest", sa.String(length=64), nullable=True),
        sa.Column("guard_errors", sa.JSON(), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "(candidate_ciphertext IS NULL AND candidate_digest IS NULL) "
            "OR (candidate_ciphertext IS NOT NULL AND candidate_digest IS NOT NULL)",
            name="ck_generation_attempts_candidate_ciphertext_has_digest",
        ),
        sa.ForeignKeyConstraint(
            ["reading_version_id"],
            ["reading_versions.id"],
            name="fk_generation_attempts_reading_version_id_reading_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_generation_attempts"),
        sa.UniqueConstraint(
            "reading_version_id",
            "attempt_number",
            name="uq_generation_attempts_reading_version_id_attempt_number",
        ),
    )
    op.create_table(
        "accepted_copies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column("payload_key_id", sa.String(length=120), nullable=False),
        sa.Column("payload_nonce", sa.String(length=64), nullable=False),
        sa.Column("payload_ciphertext", sa.Text(), nullable=False),
        sa.Column("public_copy_digest", sa.String(length=64), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reading_version_id"],
            ["reading_versions.id"],
            name="fk_accepted_copies_reading_version_id_reading_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_accepted_copies"),
        sa.UniqueConstraint(
            "reading_version_id",
            name="uq_accepted_copies_reading_version_id",
        ),
    )
    op.create_table(
        "reading_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("narrative_policy_version", sa.String(length=80), nullable=False),
        sa.Column("output_contract", sa.JSON(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("max_output_chars", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(length=120), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["reading_version_id"],
            ["reading_versions.id"],
            name="fk_reading_jobs_reading_version_id_reading_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reading_jobs"),
    )
    active = sa.text("status IN ('queued', 'claimed', 'running')")
    op.create_index(
        "uq_reading_jobs_active_version",
        "reading_jobs",
        ["reading_version_id"],
        unique=True,
        sqlite_where=active,
        postgresql_where=active,
    )
    op.create_index(
        "ix_reading_jobs_claim",
        "reading_jobs",
        ["status", "available_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reading_jobs_claim", table_name="reading_jobs")
    op.drop_index("uq_reading_jobs_active_version", table_name="reading_jobs")
    op.drop_table("reading_jobs")
    op.drop_table("accepted_copies")
    op.drop_table("generation_attempts")
    op.drop_table("fact_briefs")
    op.drop_table("reading_versions")
    op.drop_table("reading_roots")
    op.drop_table("runtime_releases")
    op.drop_table("profile_versions")
    op.drop_table("subject_profiles")
