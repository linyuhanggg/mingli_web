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
    }

    assert expected <= set(inspector.get_table_names())
    identity_constraints = inspector.get_unique_constraints("login_identities")
    assert any(
        constraint["column_names"] == ["provider", "provider_subject_hash"]
        for constraint in identity_constraints
    )
    engine.dispose()
