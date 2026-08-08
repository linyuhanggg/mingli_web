from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[2]


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
