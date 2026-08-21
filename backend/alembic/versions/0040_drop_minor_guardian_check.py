"""Stop rejecting minor profiles without guardian confirmation.

Revision ID: 0040_drop_minor_guardian_ck
Revises: 0039_export_ck_names
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0040_drop_minor_guardian_ck"
down_revision: str | None = "0039_export_ck_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAMES = (
    "ck_profile_version_authorizations_minor_guardian_confirmed",
    "minor_guardian_confirmed",
)
TABLE = "profile_version_authorizations"


def _existing_check_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return {item["name"] for item in inspector.get_check_constraints(TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Inspector names can disagree with the live PostgreSQL identifier;
        # drop the two historical names by exact SQL instead of alembic's
        # compiled DropConstraint.
        for name in CONSTRAINT_NAMES:
            op.execute(sa.text(f'ALTER TABLE {TABLE} DROP CONSTRAINT IF EXISTS "{name}"'))
        return
    to_drop = [name for name in CONSTRAINT_NAMES if name in _existing_check_names(bind)]
    if not to_drop:
        return
    with op.batch_alter_table(TABLE) as batch:
        for name in to_drop:
            batch.drop_constraint(name, type_="check")


def downgrade() -> None:
    bind = op.get_bind()
    # SQLite cannot emit ALTER TABLE ADD CONSTRAINT CHECK
    # (op.create_check_constraint raises NotImplementedError). The upgrade
    # drop is already a no-op when the constraint is missing, so leaving
    # SQLite without the CHECK on the way back to 0039 still round-trips.
    if bind.dialect.name != "postgresql":
        return
    if CONSTRAINT_NAMES[0] in _existing_check_names(bind):
        return
    op.create_check_constraint(
        CONSTRAINT_NAMES[0],
        TABLE,
        "is_minor = false OR minor_guardian_confirmed = true",
    )
