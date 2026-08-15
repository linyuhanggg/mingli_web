"""Persist explicit ProfileVersion subject and authorization facts.

Revision ID: 0016_profile_version_auth
Revises: 0015_idem_owner_indexes
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_profile_version_auth"
down_revision: str | None = "0015_idem_owner_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profile_version_authorizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_version_id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=16), nullable=False),
        sa.Column("is_minor", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "authorization_confirmed",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "photo_authorization_confirmed",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "minor_guardian_confirmed",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "difference_acknowledged",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["profile_version_id"],
            ["profile_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_profile_version_authorizations"),
        sa.UniqueConstraint(
            "profile_version_id",
            name="uq_profile_version_authorizations_profile_version_id",
        ),
        sa.CheckConstraint(
            "subject_type IN ('self', 'other')",
            name="ck_profile_version_authorizations_subject_type_allowed",
        ),
        sa.CheckConstraint(
            "(subject_type = 'self' AND authorization_confirmed = false) "
            "OR (subject_type = 'other' AND authorization_confirmed = true)",
            name="ck_profile_version_authorizations_authorization_matches_subject",
        ),
        sa.CheckConstraint(
            "is_minor = false OR minor_guardian_confirmed = true",
            name="ck_profile_version_authorizations_minor_guardian_confirmed",
        ),
    )
    op.execute(
        sa.text(
            "INSERT INTO profile_version_authorizations "
            "(id, profile_version_id, subject_type, is_minor, "
            "authorization_confirmed, photo_authorization_confirmed, "
            "minor_guardian_confirmed, difference_acknowledged) "
            "SELECT id, id, 'self', false, false, false, false, false "
            "FROM profile_versions"
        )
    )


def downgrade() -> None:
    op.drop_table("profile_version_authorizations")
