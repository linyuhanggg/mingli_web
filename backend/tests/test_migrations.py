from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[2]

# Alembic's default alembic_version.version_num column is VARCHAR(32).
ALEMBIC_DEFAULT_VERSION_NUM_LENGTH = 32


def test_every_revision_id_fits_alembic_default_version_num() -> None:
    """Every revision ID in the real graph must fit VARCHAR(32)."""
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    script_dir = ScriptDirectory.from_config(config)

    revision_ids = [
        script.revision for script in script_dir.walk_revisions()
    ]
    assert revision_ids, "no revisions found in the Alembic script directory"

    too_long = sorted(
        f"{revision_id!r} ({len(revision_id)} chars)"
        for revision_id in revision_ids
        if len(revision_id) > ALEMBIC_DEFAULT_VERSION_NUM_LENGTH
    )
    assert not too_long, (
        "Alembic's default version_num column is VARCHAR(32); these "
        f"revision IDs are too long: {', '.join(too_long)}"
    )


def test_identity_migration_builds_the_phase_one_tables(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    database_path = tmp_path / "migration.sqlite3"
    async_url = f"sqlite+aiosqlite:///{database_path}"
    monkeypatch.setenv("MINGLI_DATABASE_URL", async_url)

    config = Config(str(ROOT / "backend" / "alembic.ini"))
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path}")
    inspector = inspect(engine)
    expected = {
        "users",
        "login_identities",
        "device_sessions",
        "guest_sessions",
        "audit_events",
        "staff_users",
        "staff_sessions",
        "admin_audit_events",
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
        "user_password_credentials",
        "consent_records",
        "referral_campaign_versions",
        "referral_codes",
        "referral_temporary_attributions",
        "referral_attributions",
        "referral_reward_slots",
        "referral_reward_reservations",
        "referral_refund_confirmations",
        "referral_participation_restrictions",
        "content_revisions",
        "account_closure_requests",
        "profile_version_authorizations",
    }

    assert expected <= set(inspector.get_table_names())
    identity_constraints = inspector.get_unique_constraints("login_identities")
    assert any(
        constraint["column_names"] == ["provider", "provider_subject_hash"]
        for constraint in identity_constraints
    )
    authorization_constraints = inspector.get_unique_constraints(
        "profile_version_authorizations"
    )
    assert any(
        constraint["column_names"] == ["profile_version_id"]
        for constraint in authorization_constraints
    )
    payment_constraints = inspector.get_unique_constraints("payments")
    assert any(
        constraint["column_names"] == ["attempt_id"]
        for constraint in payment_constraints
    )
    reward_slot_constraints = inspector.get_unique_constraints("referral_reward_slots")
    assert any(
        constraint["column_names"]
        == ["campaign_version_id", "product_version_id", "slot_key"]
        for constraint in reward_slot_constraints
    )
    reward_reservation_constraints = inspector.get_unique_constraints(
        "referral_reward_reservations"
    )
    assert any(
        constraint["column_names"] == ["payment_attempt_id"]
        for constraint in reward_reservation_constraints
    )
    refund_confirmation_constraints = inspector.get_unique_constraints(
        "referral_refund_confirmations"
    )
    assert any(
        constraint["column_names"] == ["payment_id"]
        for constraint in refund_confirmation_constraints
    )
    restriction_constraints = inspector.get_unique_constraints(
        "referral_participation_restrictions"
    )
    assert any(
        constraint["column_names"] == ["user_id"]
        for constraint in restriction_constraints
    )
    engine.dispose()
