"""Add structured public CMS metadata for search and source display.

Revision ID: 0026_content_metadata
Revises: 0025_referral_appeals
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_content_metadata"
down_revision: str | None = "0025_referral_appeals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("content_revisions", sa.Column("title", sa.String(length=240), nullable=True))
    op.add_column("content_revisions", sa.Column("summary", sa.String(length=500), nullable=True))
    op.add_column("content_revisions", sa.Column("topic", sa.String(length=80), nullable=True))
    op.add_column(
        "content_revisions",
        sa.Column("source_title", sa.String(length=240), nullable=True),
    )
    op.add_column(
        "content_revisions",
        sa.Column("source_url", sa.String(length=500), nullable=True),
    )
    op.create_index(
        "ix_content_revisions_locale_topic_state",
        "content_revisions",
        ["locale", "topic", "state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_content_revisions_locale_topic_state", table_name="content_revisions")
    op.drop_column("content_revisions", "source_url")
    op.drop_column("content_revisions", "source_title")
    op.drop_column("content_revisions", "topic")
    op.drop_column("content_revisions", "summary")
    op.drop_column("content_revisions", "title")
