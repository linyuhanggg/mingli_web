"""Store login identity destinations encrypted for authorized Admin reads.

Revision ID: 0027_identity_destination_cipher
Revises: 0026_content_metadata
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_identity_destination_cipher"
down_revision: str | None = "0026_content_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "login_identities",
        sa.Column("destination_key_id", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "login_identities",
        sa.Column("destination_nonce", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "login_identities",
        sa.Column("destination_ciphertext", sa.Text(), nullable=True),
    )
    op.add_column(
        "login_identities",
        sa.Column("destination_fingerprint", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("login_identities", "destination_fingerprint")
    op.drop_column("login_identities", "destination_ciphertext")
    op.drop_column("login_identities", "destination_nonce")
    op.drop_column("login_identities", "destination_key_id")
