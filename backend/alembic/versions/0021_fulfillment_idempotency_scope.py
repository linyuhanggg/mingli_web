"""Scope fulfillment idempotency keys to an order.

Revision ID: 0021_fulfillment_scope
Revises: 0020_fulfillment
Create Date: 2026-08-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0021_fulfillment_scope"
down_revision: str | None = "0020_fulfillment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("fulfillments") as batch:
        batch.drop_constraint("uq_fulfillments_idempotency_key_hash", type_="unique")
        batch.create_unique_constraint(
            "uq_fulfillments_order_id_idempotency_key_hash",
            ["order_id", "idempotency_key_hash"],
        )


def downgrade() -> None:
    with op.batch_alter_table("fulfillments") as batch:
        batch.drop_constraint(
            "uq_fulfillments_order_id_idempotency_key_hash",
            type_="unique",
        )
        batch.create_unique_constraint(
            "uq_fulfillments_idempotency_key_hash",
            ["idempotency_key_hash"],
        )
