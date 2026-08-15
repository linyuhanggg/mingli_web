"""Persist referral campaign facts and CMS content revisions.

Revision ID: 0012_referrals_content
Revises: 0011_user_password_consent
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_referrals_content"
down_revision: str | None = "0011_user_password_consent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "referral_campaign_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_limit", sa.Integer(), nullable=True),
        sa.Column("per_inviter_limit", sa.Integer(), nullable=False),
        sa.Column("reward_quantity", sa.Integer(), nullable=False),
        sa.Column("reward_window_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_referral_campaign_versions"),
        sa.UniqueConstraint("campaign_key", "version", name="uq_referral_campaign_key_version"),
    )
    op.create_index(
        "ix_referral_campaign_versions_state",
        "referral_campaign_versions",
        ["state"],
        unique=False,
    )
    op.create_table(
        "referral_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_version_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("inviter_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["campaign_version_id"], ["referral_campaign_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_referral_codes"),
        sa.UniqueConstraint("code", name="uq_referral_codes_code"),
    )
    op.create_index(
        "ix_referral_codes_campaign_id", "referral_codes", ["campaign_version_id"], unique=False
    )
    op.create_index(
        "ix_referral_codes_inviter_user_id", "referral_codes", ["inviter_user_id"], unique=False
    )
    op.create_table(
        "referral_temporary_attributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_version_id", sa.Uuid(), nullable=False),
        sa.Column("code_id", sa.Uuid(), nullable=False),
        sa.Column("visitor_key_hash", sa.String(length=64), nullable=False),
        sa.Column("inviter_user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["campaign_version_id"], ["referral_campaign_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["code_id"], ["referral_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_referral_temporary_attributions"),
        sa.UniqueConstraint(
            "campaign_version_id", "visitor_key_hash", name="uq_referral_temp_campaign_visitor"
        ),
    )
    op.create_index(
        "ix_referral_temp_expires_at",
        "referral_temporary_attributions",
        ["expires_at"],
        unique=False,
    )
    op.create_table(
        "referral_attributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_version_id", sa.Uuid(), nullable=False),
        sa.Column("code_id", sa.Uuid(), nullable=False),
        sa.Column("referred_user_id", sa.Uuid(), nullable=False),
        sa.Column("inviter_user_id", sa.Uuid(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_version_id"], ["referral_campaign_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["code_id"], ["referral_codes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["referred_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_referral_attributions"),
        sa.UniqueConstraint("referred_user_id", name="uq_referral_attributions_referred_user"),
    )
    op.create_index(
        "ix_referral_attributions_inviter_user_id",
        "referral_attributions",
        ["inviter_user_id"],
        unique=False,
    )
    op.create_table(
        "referral_reward_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_version_id", sa.Uuid(), nullable=False),
        sa.Column("attribution_id", sa.Uuid(), nullable=False),
        sa.Column("referred_user_id", sa.Uuid(), nullable=False),
        sa.Column("inviter_user_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["campaign_version_id"], ["referral_campaign_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["attribution_id"], ["referral_attributions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["referred_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_referral_reward_reservations"),
        sa.UniqueConstraint(
            "campaign_version_id", "referred_user_id", name="uq_referral_reward_campaign_referred"
        ),
    )
    op.create_index(
        "ix_referral_reward_reservations_inviter_user_id",
        "referral_reward_reservations",
        ["inviter_user_id"],
        unique=False,
    )
    op.create_table(
        "content_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_key", sa.String(length=160), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_ref", sa.String(length=120), nullable=False),
        sa.Column("author_staff_user_id", sa.Uuid(), nullable=True),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["author_staff_user_id"], ["staff_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_content_revisions"),
        sa.UniqueConstraint(
            "content_key", "locale", "revision", name="uq_content_revisions_key_locale_revision"
        ),
    )
    op.create_index(
        "ix_content_revisions_key_locale_state",
        "content_revisions",
        ["content_key", "locale", "state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_content_revisions_key_locale_state", table_name="content_revisions")
    op.drop_table("content_revisions")
    op.drop_index(
        "ix_referral_reward_reservations_inviter_user_id", table_name="referral_reward_reservations"
    )
    op.drop_table("referral_reward_reservations")
    op.drop_index("ix_referral_attributions_inviter_user_id", table_name="referral_attributions")
    op.drop_table("referral_attributions")
    op.drop_index("ix_referral_temp_expires_at", table_name="referral_temporary_attributions")
    op.drop_table("referral_temporary_attributions")
    op.drop_index("ix_referral_codes_inviter_user_id", table_name="referral_codes")
    op.drop_index("ix_referral_codes_campaign_id", table_name="referral_codes")
    op.drop_table("referral_codes")
    op.drop_index("ix_referral_campaign_versions_state", table_name="referral_campaign_versions")
    op.drop_table("referral_campaign_versions")
