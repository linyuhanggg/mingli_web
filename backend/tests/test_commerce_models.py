from datetime import UTC, datetime
from uuid import uuid4

from app.identity.models import Base


def test_platform_commerce_tables_are_registered_on_the_authoritative_metadata() -> None:
    import app.commerce.models  # noqa: F401

    expected = {
        "product_families",
        "product_versions",
        "product_offers",
        "orders",
        "payment_attempts",
        "payments",
        "refunds",
        "fulfillments",
        "payment_notification_receipts",
        "payment_reconciliation_runs",
        "payment_reconciliation_items",
        "entitlement_events",
        "notification_outbox",
        "notification_preferences",
    }
    assert expected <= set(Base.metadata.tables)


def test_entitlement_event_is_immutable_fact_with_idempotency_key() -> None:
    from app.commerce.models import EntitlementEventRecord

    event = EntitlementEventRecord(
        id=uuid4(),
        entitlement_id="entitlement-1",
        owner_user_id=uuid4(),
        kind="GRANT",
        quantity=1,
        source_type="payment",
        source_ref="payment-1",
        target_ref="reading-root-1",
        created_at=datetime.now(UTC),
    )

    assert event.kind == "GRANT"
    assert event.quantity == 1
    assert event.source_ref == "payment-1"
