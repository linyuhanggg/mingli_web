"""Add payment notification receipts and reconciliation facts.

Revision ID: 0019_payment_reconciliation
Revises: 0018_notification_delivery_state
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_payment_reconciliation"
down_revision: str | None = "0018_notification_delivery_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_notification_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("external_event_id", sa.String(length=180), nullable=False),
        sa.Column("channel_transaction_id", sa.String(length=180), nullable=True),
        sa.Column("provider_status", sa.String(length=24), nullable=False),
        sa.Column("processing_status", sa.String(length=24), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="SET NULL",
            name="fk_payment_notification_receipts_payment_id_payments",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_notification_receipts"),
        sa.UniqueConstraint(
            "channel",
            "external_event_id",
            name="uq_payment_notification_receipts_channel_event",
        ),
    )
    op.create_index(
        "ix_payment_notification_receipts_payment_id",
        "payment_notification_receipts",
        ["payment_id"],
        unique=False,
    )

    op.create_table(
        "payment_reconciliation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("matched_count", sa.Integer(), nullable=False),
        sa.Column("difference_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_reconciliation_runs"),
    )
    op.create_index(
        "ix_payment_reconciliation_runs_channel_run_at",
        "payment_reconciliation_runs",
        ["channel", "run_at"],
        unique=False,
    )

    op.create_table(
        "payment_reconciliation_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("reference", sa.String(length=180), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("refund_id", sa.Uuid(), nullable=True),
        sa.Column("local_status", sa.String(length=24), nullable=True),
        sa.Column("provider_status", sa.String(length=24), nullable=True),
        sa.Column("local_amount_minor", sa.Integer(), nullable=True),
        sa.Column("provider_amount_minor", sa.Integer(), nullable=True),
        sa.Column("local_currency", sa.String(length=3), nullable=True),
        sa.Column("provider_currency", sa.String(length=3), nullable=True),
        sa.Column("discrepancy", sa.String(length=48), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="RESTRICT",
            name="fk_payment_reconciliation_items_payment_id_payments",
        ),
        sa.ForeignKeyConstraint(
            ["refund_id"],
            ["refunds.id"],
            ondelete="RESTRICT",
            name="fk_payment_reconciliation_items_refund_id_refunds",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["payment_reconciliation_runs.id"],
            ondelete="CASCADE",
            name="fk_payment_reconciliation_items_run_id_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_reconciliation_items"),
        sa.UniqueConstraint(
            "run_id",
            "kind",
            "reference",
            name="uq_payment_reconciliation_items_run_kind_ref",
        ),
    )
    op.create_index(
        "ix_payment_reconciliation_items_run_id",
        "payment_reconciliation_items",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_payment_reconciliation_items_discrepancy",
        "payment_reconciliation_items",
        ["discrepancy"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_payment_reconciliation_items_discrepancy",
        table_name="payment_reconciliation_items",
    )
    op.drop_index(
        "ix_payment_reconciliation_items_run_id",
        table_name="payment_reconciliation_items",
    )
    op.drop_table("payment_reconciliation_items")
    op.drop_index(
        "ix_payment_reconciliation_runs_channel_run_at",
        table_name="payment_reconciliation_runs",
    )
    op.drop_table("payment_reconciliation_runs")
    op.drop_index(
        "ix_payment_notification_receipts_payment_id",
        table_name="payment_notification_receipts",
    )
    op.drop_table("payment_notification_receipts")
