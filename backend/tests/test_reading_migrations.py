from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[2]


def test_reading_migration_builds_immutable_phase_two_tables(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    database_path = tmp_path / "reading-migration.sqlite3"
    monkeypatch.setenv(
        "MINGLI_DATABASE_URL",
        f"sqlite+aiosqlite:///{database_path}",
    )
    config = Config(str(ROOT / "backend" / "alembic.ini"))

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path}")
    inspector = inspect(engine)
    expected = {
        "subject_profiles",
        "profile_versions",
        "runtime_releases",
        "reading_roots",
        "reading_versions",
        "fact_briefs",
        "generation_attempts",
        "accepted_copies",
        "reading_jobs",
    }
    assert expected <= set(inspector.get_table_names())

    def has_unique(table: str, columns: list[str]) -> bool:
        return any(
            constraint["column_names"] == columns
            for constraint in inspector.get_unique_constraints(table)
        )

    assert has_unique("profile_versions", ["profile_id", "version"])
    assert has_unique("reading_versions", ["reading_root_id", "version"])
    assert has_unique(
        "generation_attempts",
        ["reading_version_id", "attempt_number"],
    )
    assert has_unique("accepted_copies", ["reading_version_id"])
    assert any(
        index["name"] == "uq_reading_jobs_active_version" and index["unique"]
        for index in inspector.get_indexes("reading_jobs")
    )
    engine.dispose()


def test_phase_two_migration_round_trips_down_and_up(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    database_path = tmp_path / "reading-roundtrip.sqlite3"
    monkeypatch.setenv(
        "MINGLI_DATABASE_URL",
        f"sqlite+aiosqlite:///{database_path}",
    )
    config = Config(str(ROOT / "backend" / "alembic.ini"))

    command.upgrade(config, "head")
    command.downgrade(config, "0001_identity_foundation")
    engine = create_engine(f"sqlite:///{database_path}")
    assert "reading_versions" not in inspect(engine).get_table_names()
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path}")
    assert "reading_versions" in inspect(engine).get_table_names()
    engine.dispose()
