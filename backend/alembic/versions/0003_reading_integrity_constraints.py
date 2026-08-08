"""Enforce owner and encrypted-envelope integrity in the database.

Revision ID: 0003_reading_integrity_constraints
Revises: 0002_profiles_and_readings
Create Date: 2026-08-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_reading_integrity_constraints"
down_revision: str | None = "0002_profiles_and_readings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNER_EXACTLY_ONE = (
    "(owner_user_id IS NOT NULL AND owner_guest_session_id IS NULL) "
    "OR (owner_user_id IS NULL AND owner_guest_session_id IS NOT NULL)"
)
STATE_TOKEN_ALL_OR_NONE = (
    "(state_token_key_id IS NULL AND state_token_nonce IS NULL "
    "AND state_token_ciphertext IS NULL AND state_token_fingerprint IS NULL) "
    "OR (state_token_key_id IS NOT NULL AND state_token_nonce IS NOT NULL "
    "AND state_token_ciphertext IS NOT NULL AND state_token_fingerprint IS NOT NULL)"
)
LAST_RESULT_ALL_OR_NONE = (
    "(last_result_key_id IS NULL AND last_result_nonce IS NULL "
    "AND last_result_ciphertext IS NULL AND last_result_digest IS NULL) "
    "OR (last_result_key_id IS NOT NULL AND last_result_nonce IS NOT NULL "
    "AND last_result_ciphertext IS NOT NULL AND last_result_digest IS NOT NULL)"
)
COMPLETION_ALL_OR_NONE = (
    "(completion_key_id IS NULL AND completion_nonce IS NULL "
    "AND completion_ciphertext IS NULL AND completion_digest IS NULL) "
    "OR (completion_key_id IS NOT NULL AND completion_nonce IS NOT NULL "
    "AND completion_ciphertext IS NOT NULL AND completion_digest IS NOT NULL)"
)
CANDIDATE_ALL_OR_NONE = (
    "(candidate_key_id IS NULL AND candidate_nonce IS NULL "
    "AND candidate_ciphertext IS NULL AND candidate_digest IS NULL) "
    "OR (candidate_key_id IS NOT NULL AND candidate_nonce IS NOT NULL "
    "AND candidate_ciphertext IS NOT NULL AND candidate_digest IS NOT NULL)"
)


def upgrade() -> None:
    with op.batch_alter_table("subject_profiles") as batch_op:
        batch_op.create_check_constraint(
            op.f("ck_subject_profiles_owner_exactly_one"),
            OWNER_EXACTLY_ONE,
        )
    with op.batch_alter_table("reading_roots") as batch_op:
        batch_op.create_check_constraint(
            op.f("ck_reading_roots_owner_exactly_one"),
            OWNER_EXACTLY_ONE,
        )
    with op.batch_alter_table("reading_versions") as batch_op:
        batch_op.drop_constraint(
            "ck_reading_versions_state_token_ciphertext_has_fingerprint",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_reading_versions_completion_ciphertext_has_digest",
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f("ck_reading_versions_state_token_envelope_all_or_none"),
            STATE_TOKEN_ALL_OR_NONE,
        )
        batch_op.create_check_constraint(
            op.f("ck_reading_versions_last_result_envelope_all_or_none"),
            LAST_RESULT_ALL_OR_NONE,
        )
        batch_op.create_check_constraint(
            op.f("ck_reading_versions_completion_envelope_all_or_none"),
            COMPLETION_ALL_OR_NONE,
        )
    with op.batch_alter_table("generation_attempts") as batch_op:
        batch_op.drop_constraint(
            "ck_generation_attempts_candidate_ciphertext_has_digest",
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f("ck_generation_attempts_candidate_envelope_all_or_none"),
            CANDIDATE_ALL_OR_NONE,
        )


def downgrade() -> None:
    with op.batch_alter_table("generation_attempts") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_generation_attempts_candidate_envelope_all_or_none"),
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_generation_attempts_candidate_ciphertext_has_digest",
            "(candidate_ciphertext IS NULL AND candidate_digest IS NULL) "
            "OR (candidate_ciphertext IS NOT NULL AND candidate_digest IS NOT NULL)",
        )
    with op.batch_alter_table("reading_versions") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_reading_versions_completion_envelope_all_or_none"),
            type_="check",
        )
        batch_op.drop_constraint(
            op.f("ck_reading_versions_last_result_envelope_all_or_none"),
            type_="check",
        )
        batch_op.drop_constraint(
            op.f("ck_reading_versions_state_token_envelope_all_or_none"),
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_reading_versions_state_token_ciphertext_has_fingerprint",
            "(state_token_ciphertext IS NULL AND state_token_fingerprint IS NULL) "
            "OR (state_token_ciphertext IS NOT NULL "
            "AND state_token_fingerprint IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "ck_reading_versions_completion_ciphertext_has_digest",
            "(completion_ciphertext IS NULL AND completion_digest IS NULL) "
            "OR (completion_ciphertext IS NOT NULL AND completion_digest IS NOT NULL)",
        )
    with op.batch_alter_table("reading_roots") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_reading_roots_owner_exactly_one"),
            type_="check",
        )
    with op.batch_alter_table("subject_profiles") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_subject_profiles_owner_exactly_one"),
            type_="check",
        )
