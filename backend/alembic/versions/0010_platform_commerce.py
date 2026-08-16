"""Add catalog, payment, ledger, and notification facts.

Revision ID: 0010_platform_commerce
Revises: 0009_owner_grants
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_platform_commerce"
down_revision: str | None = "0009_owner_grants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_families",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_families"),
        sa.UniqueConstraint("key", name="uq_product_families_key"),
    )
    op.create_table(
        "product_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("follow_up_count", sa.Integer(), nullable=False),
        sa.Column("follow_up_window_seconds", sa.Integer(), nullable=False),
        sa.Column("contract_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["family_id"],
            ["product_families.id"],
            ondelete="RESTRICT",
            name="fk_product_versions_family_id_product_families",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_versions"),
        sa.UniqueConstraint("family_id", "version", name="uq_product_versions_family_version"),
    )
    op.create_index(
        "ix_product_versions_family_id", "product_versions", ["family_id"], unique=False
    )
    op.create_table(
        "product_offers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_version_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("channel_sku", sa.String(length=160), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_version_id"],
            ["product_versions.id"],
            ondelete="CASCADE",
            name="fk_product_offers_product_version_id_product_versions",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_product_offers"),
        sa.UniqueConstraint("channel", "channel_sku", name="uq_product_offers_channel_sku"),
    )
    op.create_index(
        "ix_product_offers_product_version_id",
        "product_offers",
        ["product_version_id"],
        unique=False,
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("product_version_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_target_ref", sa.String(length=160), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
            name="fk_orders_owner_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["product_version_id"],
            ["product_versions.id"],
            ondelete="RESTRICT",
            name="fk_orders_product_version_id_product_versions",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
    )
    op.create_index("ix_orders_owner_user_id", "orders", ["owner_user_id"], unique=False)
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)
    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
            name="fk_payment_attempts_order_id_orders",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_attempts"),
        sa.UniqueConstraint(
            "order_id", "idempotency_key_hash", name="uq_payment_attempts_order_key"
        ),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("channel_transaction_id", sa.String(length=180), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["payment_attempts.id"],
            ondelete="RESTRICT",
            name="fk_payments_attempt_id_payment_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], ondelete="RESTRICT", name="fk_payments_order_id_orders"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        sa.UniqueConstraint(
            "channel", "channel_transaction_id", name="uq_payments_channel_transaction"
        ),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"], unique=False)
    op.create_table(
        "refunds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("channel_refund_id", sa.String(length=180), nullable=True),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="RESTRICT",
            name="fk_refunds_payment_id_payments",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refunds"),
        sa.UniqueConstraint("channel", "channel_refund_id", name="uq_refunds_channel_refund"),
    )
    op.create_table(
        "entitlement_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entitlement_id", sa.String(length=160), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=160), nullable=False),
        sa.Column("target_ref", sa.String(length=160), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
            name="fk_entitlement_events_owner_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_entitlement_events"),
        sa.UniqueConstraint(
            "source_type", "source_ref", "kind", name="uq_entitlement_events_source_kind"
        ),
    )
    op.create_index(
        "ix_entitlement_events_entitlement_id",
        "entitlement_events",
        ["entitlement_id"],
        unique=False,
    )
    op.create_index(
        "ix_entitlement_events_owner_user_id", "entitlement_events", ["owner_user_id"], unique=False
    )
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("dedupe_key", sa.String(length=180), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_notification_outbox_owner_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notification_outbox"),
        sa.UniqueConstraint("dedupe_key", name="uq_notification_outbox_dedupe_key"),
    )
    op.create_index(
        "ix_notification_outbox_status_available_at",
        "notification_outbox",
        ["status", "available_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_status_available_at", table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_index("ix_entitlement_events_owner_user_id", table_name="entitlement_events")
    op.drop_index("ix_entitlement_events_entitlement_id", table_name="entitlement_events")
    op.drop_table("entitlement_events")
    op.drop_table("refunds")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")
    op.drop_table("payment_attempts")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_owner_user_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_product_offers_product_version_id", table_name="product_offers")
    op.drop_table("product_offers")
    op.drop_index("ix_product_versions_family_id", table_name="product_versions")
    op.drop_table("product_versions")
    op.drop_table("product_families")
