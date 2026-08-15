"""Align persisted PostgreSQL constraint names with migration metadata.

Revision ID: 0032_postgres_schema_alignment
Revises: 0031_notification_in_app_state
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0032_postgres_schema_alignment"
down_revision: str | None = "0031_notification_in_app_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CHECK_CONSTRAINT_RENAMES = (
    (
        "claim_verification_events",
        "ck_claim_verification_events_ck_claim_verification_even_f740",
        "ck_claim_verification_events_outcome_allowed",
    ),
    (
        "profile_version_authorizations",
        "ck_profile_version_authorizations_ck_profile_version_au_3b85",
        "ck_profile_version_authorizations_subject_type_allowed",
    ),
    (
        "profile_version_authorizations",
        "ck_profile_version_authorizations_ck_profile_version_au_3f4e",
        "ck_profile_version_authorizations_minor_guardian_confirmed",
    ),
    (
        "profile_version_authorizations",
        "ck_profile_version_authorizations_ck_profile_version_au_3f87",
        "ck_profile_version_authorizations_authorization_matches_subject",
    ),
    (
        "reading_documents",
        "ck_reading_documents_ck_reading_documents_schema_versio_c837",
        "ck_reading_documents_schema_version_allowed",
    ),
    (
        "reading_share_snapshots",
        "ck_reading_share_snapshots_ck_reading_share_snapshots_o_110d",
        "ck_reading_share_snapshots_owner_exactly_one",
    ),
)


def _rename_existing_check_constraints() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = inspect(bind)
    for table_name, old_name, new_name in _CHECK_CONSTRAINT_RENAMES:
        names = {
            item["name"]
            for item in inspector.get_check_constraints(table_name)
            if item.get("name")
        }
        if new_name in names or old_name not in names:
            continue
        op.execute(
            sa.text(
                f'ALTER TABLE "{table_name}" '
                f'RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
            )
        )


def _add_missing_primary_key_unique() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = inspect(bind)
    names = {
        item["name"]
        for item in inspector.get_unique_constraints("account_closure_requests")
        if item.get("name")
    }
    if "uq_account_closure_requests_id" not in names:
        op.create_unique_constraint(
            "uq_account_closure_requests_id",
            "account_closure_requests",
            ["id"],
        )


def upgrade() -> None:
    _rename_existing_check_constraints()
    _add_missing_primary_key_unique()


def downgrade() -> None:
    # The target names are the names used by the preceding migration files.
    # Keeping them on downgrade preserves the migration-defined schema.
    pass
