from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[2]


def upgraded_engine(tmp_path: Path, monkeypatch, name: str):  # type: ignore[no-untyped-def]
    database_path = tmp_path / name
    monkeypatch.setenv(
        "MINGLI_DATABASE_URL",
        f"sqlite+aiosqlite:///{database_path}",
    )
    command.upgrade(Config(str(ROOT / "backend" / "alembic.ini")), "head")
    return create_engine(f"sqlite:///{database_path}")


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
        "reading_idempotency_keys",
        "reading_verifications",
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
    assert has_unique(
        "reading_idempotency_keys",
        ["key_hash", "owner_user_id", "owner_guest_session_id"],
    )
    assert has_unique("reading_verifications", ["reading_version_id"])
    assert any(
        index["name"] == "uq_reading_jobs_active_version" and index["unique"]
        for index in inspector.get_indexes("reading_jobs")
    )
    reading_job_columns = {
        column["name"]: column for column in inspector.get_columns("reading_jobs")
    }
    assert reading_job_columns["lease_generation"]["nullable"] is False
    assert reading_job_columns["lease_token"]["nullable"] is True
    assert {"ck_reading_jobs_lease_envelope_all_or_none"} <= {
        constraint["name"] for constraint in inspector.get_check_constraints("reading_jobs")
    }
    reading_version_columns = {
        column["name"]: column for column in inspector.get_columns("reading_versions")
    }
    assert reading_version_columns["prepare_has_state_token"]["nullable"] is False
    generation_attempt_columns = {
        column["name"]: column for column in inspector.get_columns("generation_attempts")
    }
    assert generation_attempt_columns["model_receipt"]["nullable"] is True

    expected_checks = {
        "subject_profiles": {"ck_subject_profiles_owner_exactly_one"},
        "reading_roots": {"ck_reading_roots_owner_exactly_one"},
        "reading_idempotency_keys": {
            "ck_reading_idempotency_keys_owner_exactly_one",
        },
        "reading_verifications": {
            "ck_reading_verifications_outcome_allowed",
        },
        "reading_versions": {
            "ck_reading_versions_state_token_envelope_all_or_none",
            "ck_reading_versions_last_result_envelope_all_or_none",
            "ck_reading_versions_completion_envelope_all_or_none",
        },
        "generation_attempts": {"ck_generation_attempts_candidate_envelope_all_or_none"},
    }
    for table, names in expected_checks.items():
        assert names <= {
            constraint["name"] for constraint in inspector.get_check_constraints(table)
        }

    accepted_columns = {
        column["name"]: column for column in inspector.get_columns("accepted_copies")
    }
    for name in (
        "payload_key_id",
        "payload_nonce",
        "payload_ciphertext",
        "public_copy_digest",
    ):
        assert accepted_columns[name]["nullable"] is False
    idempotency_columns = {
        column["name"]: column for column in inspector.get_columns("reading_idempotency_keys")
    }
    for name in ("key_hash", "action", "request_fingerprint", "reading_version_id"):
        assert idempotency_columns[name]["nullable"] is False
    verification_columns = {
        column["name"]: column for column in inspector.get_columns("reading_verifications")
    }
    assert verification_columns["outcome"]["nullable"] is False
    assert verification_columns["note"]["nullable"] is True
    subject_profile_columns = {
        column["name"]: column for column in inspector.get_columns("subject_profiles")
    }
    assert subject_profile_columns["label"]["nullable"] is True
    engine.dispose()


@pytest.mark.parametrize("table", ["subject_profiles", "reading_roots"])
@pytest.mark.parametrize(
    ("owner_user_id", "owner_guest_session_id"),
    [(None, None), (uuid4().hex, uuid4().hex)],
)
def test_owner_xor_is_enforced_by_the_migrated_database(
    tmp_path: Path,
    monkeypatch,
    table: str,
    owner_user_id: str | None,
    owner_guest_session_id: str | None,
) -> None:  # type: ignore[no-untyped-def]
    engine = upgraded_engine(tmp_path, monkeypatch, f"owner-{table}.sqlite3")
    columns = "id, owner_user_id, owner_guest_session_id"
    values = ":id, :owner_user_id, :owner_guest_session_id"
    if table == "subject_profiles":
        columns += ", status"
        values += ", 'active'"
    else:
        columns += ", capability_id"
        values += ", 'bazi'"

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(f"INSERT INTO {table} ({columns}) VALUES ({values})"),
            {
                "id": uuid4().hex,
                "owner_user_id": owner_user_id,
                "owner_guest_session_id": owner_guest_session_id,
            },
        )
    engine.dispose()


def test_idempotency_key_owner_xor_is_enforced_by_the_migrated_database(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    engine = upgraded_engine(tmp_path, monkeypatch, "idempotency-owner.sqlite3")
    user_id, root_id, release_id = _seed_reading_parent_rows(engine)
    version_id = uuid4().hex
    with engine.begin() as connection:
        _insert_reading_version(
            connection,
            root_id=root_id,
            release_id=release_id,
            version_id=version_id,
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO reading_idempotency_keys "
                "(id, key_hash, action, request_fingerprint, owner_user_id, "
                "owner_guest_session_id, reading_version_id) "
                "VALUES (:id, 'hash', 'preview', 'fingerprint', :user_id, "
                ":user_id, :version_id)"
            ),
            {"id": uuid4().hex, "user_id": user_id, "version_id": version_id},
        )
    engine.dispose()


def test_verification_outcome_whitelist_is_enforced_by_the_migrated_database(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    engine = upgraded_engine(tmp_path, monkeypatch, "verification-outcome.sqlite3")
    _user_id, root_id, release_id = _seed_reading_parent_rows(engine)
    version_id = uuid4().hex
    with engine.begin() as connection:
        _insert_reading_version(
            connection,
            root_id=root_id,
            release_id=release_id,
            version_id=version_id,
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO reading_verifications "
                "(id, reading_version_id, outcome) "
                "VALUES (:id, :version_id, 'maybe')"
            ),
            {"id": uuid4().hex, "version_id": version_id},
        )
    engine.dispose()


def test_0007_migration_round_trips_between_0006_and_head(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    database_path = tmp_path / "reading-0007-roundtrip.sqlite3"
    monkeypatch.setenv(
        "MINGLI_DATABASE_URL",
        f"sqlite+aiosqlite:///{database_path}",
    )
    config = Config(str(ROOT / "backend" / "alembic.ini"))

    command.upgrade(config, "head")
    command.downgrade(config, "0006_model_receipt")
    engine = create_engine(f"sqlite:///{database_path}")
    inspector = inspect(engine)
    assert "reading_idempotency_keys" not in inspector.get_table_names()
    assert "reading_verifications" not in inspector.get_table_names()
    subject_profile_columns = {
        column["name"] for column in inspector.get_columns("subject_profiles")
    }
    assert "label" not in subject_profile_columns
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path}")
    inspector = inspect(engine)
    assert "reading_idempotency_keys" in inspector.get_table_names()
    assert "reading_verifications" in inspector.get_table_names()
    subject_profile_columns = {
        column["name"] for column in inspector.get_columns("subject_profiles")
    }
    assert "label" in subject_profile_columns
    engine.dispose()


def _seed_reading_parent_rows(engine) -> tuple[str, str, str]:  # type: ignore[no-untyped-def]
    user_id = uuid4().hex
    root_id = uuid4().hex
    release_id = uuid4().hex
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO users (id, status) VALUES (:id, 'active')"),
            {"id": user_id},
        )
        connection.execute(
            text(
                "INSERT INTO reading_roots "
                "(id, owner_user_id, owner_guest_session_id, capability_id) "
                "VALUES (:id, :user_id, NULL, 'bazi')"
            ),
            {"id": root_id, "user_id": user_id},
        )
        connection.execute(
            text(
                "INSERT INTO runtime_releases "
                "(id, name, version, source_commit, release_manifest_digest, "
                "protocol_version, describe_manifest_digest, production_ready) "
                "VALUES (:id, 'runtime', '5.1', 'source', :manifest, "
                "'protocol-v2', :describe, 0)"
            ),
            {
                "id": release_id,
                "manifest": uuid4().hex,
                "describe": uuid4().hex,
            },
        )
    return user_id, root_id, release_id


def _insert_reading_version(
    connection,  # type: ignore[no-untyped-def]
    *,
    root_id: str,
    release_id: str,
    version_id: str,
    extra_column: str | None = None,
) -> None:
    columns = (
        "id, reading_root_id, runtime_release_id, version, status, capability_id, "
        "object_id, dimension_ids, horizon, prepare_key_id, prepare_nonce, "
        "prepare_ciphertext, prepare_digest"
    )
    values = (
        ":id, :root_id, :release_id, 1, 'input_ready', 'bazi', "
        "'natal', '[]', '{}', 'key', 'nonce', 'ciphertext', 'digest'"
    )
    if extra_column is not None:
        columns += f", {extra_column}"
        values += ", 'partial'"
    connection.execute(
        text(f"INSERT INTO reading_versions ({columns}) VALUES ({values})"),
        {"id": version_id, "root_id": root_id, "release_id": release_id},
    )


def test_prepare_token_presence_cannot_be_null_in_the_migrated_database(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    engine = upgraded_engine(tmp_path, monkeypatch, "prepare-token-presence.sqlite3")
    _user_id, root_id, release_id = _seed_reading_parent_rows(engine)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO reading_versions "
                "(id, reading_root_id, runtime_release_id, version, status, capability_id, "
                "object_id, dimension_ids, horizon, prepare_key_id, prepare_nonce, "
                "prepare_ciphertext, prepare_digest, prepare_has_state_token) "
                "VALUES (:id, :root_id, :release_id, 1, 'input_ready', 'bazi', "
                "'natal', '[]', '{}', 'key', 'nonce', 'ciphertext', 'digest', NULL)"
            ),
            {"id": uuid4().hex, "root_id": root_id, "release_id": release_id},
        )
    engine.dispose()


@pytest.mark.parametrize(
    "partial_column",
    [
        "state_token_key_id",
        "state_token_nonce",
        "state_token_ciphertext",
        "state_token_fingerprint",
        "last_result_key_id",
        "last_result_nonce",
        "last_result_ciphertext",
        "last_result_digest",
        "completion_key_id",
        "completion_nonce",
        "completion_ciphertext",
        "completion_digest",
    ],
)
def test_reading_version_rejects_every_partial_nullable_envelope(
    tmp_path: Path,
    monkeypatch,
    partial_column: str,
) -> None:  # type: ignore[no-untyped-def]
    engine = upgraded_engine(tmp_path, monkeypatch, "partial-reading-version.sqlite3")
    _user_id, root_id, release_id = _seed_reading_parent_rows(engine)

    with pytest.raises(IntegrityError), engine.begin() as connection:
        _insert_reading_version(
            connection,
            root_id=root_id,
            release_id=release_id,
            version_id=uuid4().hex,
            extra_column=partial_column,
        )
    engine.dispose()


@pytest.mark.parametrize(
    "partial_column",
    [
        "candidate_key_id",
        "candidate_nonce",
        "candidate_ciphertext",
        "candidate_digest",
    ],
)
def test_generation_attempt_rejects_every_partial_candidate_envelope(
    tmp_path: Path,
    monkeypatch,
    partial_column: str,
) -> None:  # type: ignore[no-untyped-def]
    engine = upgraded_engine(tmp_path, monkeypatch, "partial-attempt.sqlite3")
    _user_id, root_id, release_id = _seed_reading_parent_rows(engine)
    version_id = uuid4().hex
    with engine.begin() as connection:
        _insert_reading_version(
            connection,
            root_id=root_id,
            release_id=release_id,
            version_id=version_id,
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO generation_attempts "
                f"(id, reading_version_id, attempt_number, guard_errors, {partial_column}) "
                "VALUES (:id, :version_id, 1, '[]', 'partial')"
            ),
            {"id": uuid4().hex, "version_id": version_id},
        )
    engine.dispose()


def test_accepted_copy_rejects_an_incomplete_envelope(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    engine = upgraded_engine(tmp_path, monkeypatch, "partial-accepted-copy.sqlite3")
    _user_id, root_id, release_id = _seed_reading_parent_rows(engine)
    version_id = uuid4().hex
    with engine.begin() as connection:
        _insert_reading_version(
            connection,
            root_id=root_id,
            release_id=release_id,
            version_id=version_id,
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO accepted_copies "
                "(id, reading_version_id, payload_key_id, payload_nonce, "
                "payload_ciphertext, public_copy_digest, accepted_at) "
                "VALUES (:id, :version_id, 'key', NULL, 'ciphertext', 'digest', "
                "CURRENT_TIMESTAMP)"
            ),
            {"id": uuid4().hex, "version_id": version_id},
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
