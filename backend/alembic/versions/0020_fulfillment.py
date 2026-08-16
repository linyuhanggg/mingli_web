"""Add the paid-target fulfillment boundary.

Revision ID: 0020_fulfillment
Revises: 0019_payment_reconciliation
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_fulfillment"
down_revision: str | None = "0019_payment_reconciliation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fulfillments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("entitlement_id", sa.String(length=160), nullable=False),
        sa.Column("purchase_target_ref", sa.String(length=160), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reading_version_ref", sa.String(length=160), nullable=True),
        sa.Column("reading_job_ref", sa.String(length=160), nullable=True),
        sa.Column("accepted_copy_ref", sa.String(length=160), nullable=True),
        sa.Column("reading_document_ref", sa.String(length=160), nullable=True),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "reserved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
            name="fk_fulfillments_owner_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="RESTRICT",
            name="fk_fulfillments_order_id_orders",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="RESTRICT",
            name="fk_fulfillments_payment_id_payments",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_fulfillments"),
        sa.UniqueConstraint("order_id", name="uq_fulfillments_order_id"),
        sa.UniqueConstraint(
            "idempotency_key_hash",
            name="uq_fulfillments_idempotency_key_hash",
        ),
    )
    op.create_index(
        "ix_fulfillments_status",
        "fulfillments",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_fulfillments_target_ref",
        "fulfillments",
        ["purchase_target_ref"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_fulfillments_target_ref", table_name="fulfillments")
    op.drop_index("ix_fulfillments_status", table_name="fulfillments")
    op.drop_table("fulfillments")
