from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[2]


def _upgraded_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "physiognomy-media.sqlite3"
    monkeypatch.setenv(
        "MINGLI_DATABASE_URL",
        f"sqlite+aiosqlite:///{database_path}",
    )
    command.upgrade(Config(str(ROOT / "backend" / "alembic.ini")), "head")
    return create_engine(f"sqlite:///{database_path}")


def test_physiognomy_media_migration_has_private_metadata_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _upgraded_engine(tmp_path, monkeypatch)
    inspector = inspect(engine)

    assert "physiognomy_media_assets" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("physiognomy_media_assets")}
    assert {
        "id",
        "owner_user_id",
        "owner_guest_session_id",
        "object_key",
        "content_type",
        "byte_size",
        "width",
        "height",
        "mode",
        "consent_policy_version",
        "consented_at",
        "status",
        "created_at",
        "expires_at",
        "deleted_at",
    } <= columns
    assert {
        "uq_physiognomy_media_assets_object_key",
    } <= {
        item["name"] for item in inspector.get_unique_constraints("physiognomy_media_assets")
    }
    assert {
        "ix_physiognomy_media_assets_owner_user_id",
        "ix_physiognomy_media_assets_owner_guest_session_id",
        "ix_physiognomy_media_assets_status_expires_at",
    } <= {item["name"] for item in inspector.get_indexes("physiognomy_media_assets")}
    assert "filename" not in columns
    engine.dispose()


@pytest.mark.parametrize(
    ("owner_user_id", "owner_guest_session_id"),
    [(uuid4().hex, uuid4().hex), (None, None)],
)
def test_physiognomy_media_owner_xor_is_enforced_by_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    owner_user_id: str | None,
    owner_guest_session_id: str | None,
) -> None:
    engine = _upgraded_engine(tmp_path, monkeypatch)
    user_id = uuid4().hex
    guest_id = uuid4().hex
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, status) VALUES (:id, 'active')"),
            {"id": user_id},
        )
        connection.execute(
            text(
                "INSERT INTO guest_sessions "
                "(id, token_hash, csrf_token_hash, expires_at) "
                "VALUES (:id, 'token', 'csrf', '2099-01-01 00:00:00')"
            ),
            {"id": guest_id},
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO physiognomy_media_assets "
                "(id, owner_user_id, owner_guest_session_id, object_key, "
                "content_type, byte_size, width, height, mode, "
                "consent_policy_version, consented_at, expires_at) "
                "VALUES (:id, :owner_user_id, :owner_guest_session_id, :object_key, "
                "'image/jpeg', 100, 640, 640, 'face', 'v1', "
                "'2026-08-15 00:00:00', '2026-08-16 00:00:00')"
            ),
            {
                "id": uuid4().hex,
                "owner_user_id": user_id if owner_user_id is not None else None,
                "owner_guest_session_id": (
                    guest_id if owner_guest_session_id is not None else None
                ),
                "object_key": f"private/physiognomy/{uuid4().hex}",
            },
        )
    engine.dispose()
