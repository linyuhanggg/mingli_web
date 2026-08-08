from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from orchestrator_fakes import make_candidate
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from test_narrative_guard import build_brief


@pytest.fixture
async def reading_database() -> AsyncIterator[Any]:
    database_module = importlib.import_module("app.database")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
    database = database_module.Database("sqlite+aiosqlite:///:memory:")
    async with database.engine.begin() as connection:
        await connection.run_sync(identity_models.Base.metadata.create_all)
    yield database
    await database.dispose()


async def create_reading_graph(session: Any) -> tuple[Any, Any, Any, Any, Any]:
    identity_models = importlib.import_module("app.identity.models")
    profiles = importlib.import_module("app.profiles.repository")
    readings = importlib.import_module("app.readings.repository")
    runtime_contracts = importlib.import_module("app.readings.runtime_contracts")
    narrative = importlib.import_module("app.readings.narrative_contracts")
    envelope = importlib.import_module("app.security.envelope")
    cipher = envelope.EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1")
    user = identity_models.User()
    session.add(user)
    await session.flush()

    profile_repository = profiles.ProfileRepository(session, cipher)
    profile = await profile_repository.create_profile(owner_user_id=user.id)
    profile_version = await profile_repository.create_version(
        profile_id=profile.id,
        payload={
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "location": "福建省福州市",
            "timezone": "Asia/Shanghai",
        },
    )

    repository = readings.SqlReadingRepository(session, cipher)
    release = await repository.create_runtime_release(
        name="mingli-master-portable-core",
        version="5.1",
        source_commit="494ce0bba174a77800daf9b9c38ce9c9166d9a94",
        release_manifest_digest="e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68",
        protocol_version="mingli-portable-interface-v2",
        describe_manifest_digest="7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342",
        image_digest=None,
        production_ready=False,
    )
    root = await repository.create_root(
        owner_user_id=user.id,
        profile_version_id=profile_version.id,
        capability_id="bazi",
    )
    prepare = runtime_contracts.Prepare(
        query="事业上最该先抓住哪条主线？",
        intent={
            "subject_refs": [f"profile-version:{profile_version.id}"],
            "object_id": "natal",
            "dimension_ids": ["career"],
            "horizon": {"kind_id": "life", "start": None, "end": None},
            "capability_id": "bazi",
            "comparisons": [],
        },
        facts={
            f"profile-version:{profile_version.id}": {
                "birth_datetime_or_four_pillars": "1994-04-30T05:55:00+08:00",
                "location": "福建省福州市",
            }
        },
    )
    version = await repository.create_version(
        reading_root_id=root.id,
        runtime_release_id=release.id,
        prepare_command=prepare,
    )
    output_contract = narrative.OutputContract(
        contract_id="repository-test-v1",
        language="zh-CN",
        min_blocks=1,
        max_blocks=4,
        max_output_chars=1200,
        required_dimension_ids=("career",),
        required_limit_kind_ids=("limit:traditional",),
        disclosure_text="AI 辅助生成，仅供传统文化参考。",
    )
    job = await repository.create_job(
        reading_version_id=version.id,
        narrative_policy_version="policy-v1",
        output_contract=output_contract,
        language="zh-CN",
        max_output_chars=1200,
        max_attempts=2,
    )
    return repository, profile_version, version, job, runtime_contracts


async def test_repository_round_trips_encrypted_orchestrator_checkpoints(
    reading_database: Any,
) -> None:
    narrative = importlib.import_module("app.readings.narrative_contracts")
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    async with reading_database.sessions() as session, session.begin():
        repository, _profile_version, version, job, contracts = await create_reading_graph(session)
        prepared = contracts.Prepared(
            state_token="runtime-secret-token",
            brief=build_brief(),
        )
        candidate = make_candidate(narrative)
        await repository.record_prepared(str(job.id), prepared, now)
        await repository.record_generation_attempt(
            str(job.id),
            1,
            candidate,
            (),
            now,
        )
        await repository.record_completion_intent(
            str(job.id),
            "最终 Accepted 私密正文",
            now,
        )
        await repository.record_accepted(
            str(job.id),
            contracts.Accepted(
                state_token="runtime-secret-token",
                public_copy="最终 Accepted 私密正文",
            ),
            now,
        )

        loaded_job = await repository.load_job(str(job.id))
        checkpoint = await repository.load_checkpoint(str(job.id))
        assert loaded_job.prepare_command.query == "事业上最该先抓住哪条主线？"
        assert checkpoint.prepared.state_token == "runtime-secret-token"
        assert checkpoint.attempt_count == 1
        assert checkpoint.accepted.public_copy == "最终 Accepted 私密正文"

        raw_rows: list[object] = []
        for table in (
            "profile_versions",
            "reading_versions",
            "fact_briefs",
            "generation_attempts",
            "accepted_copies",
        ):
            raw_rows.extend((await session.execute(text(f"SELECT * FROM {table}"))).all())
        serialized_rows = repr(raw_rows)
        for secret in (
            "1994-04-30T05:55:00+08:00",
            "福建省福州市",
            "事业上最该先抓住哪条主线？",
            "当前结构更支持持续积累。",
            "事业主线更适合先抓住可持续积累",
            "最终 Accepted 私密正文",
            "runtime-secret-token",
        ):
            assert secret not in serialized_rows

        fact_brief = await repository.get_fact_brief(version.id)
        accepted_copy = await repository.get_accepted_copy(version.id)
        assert fact_brief.payload_digest
        assert accepted_copy.public_copy_digest


async def test_immutable_records_and_first_write_wins_are_enforced(
    reading_database: Any,
) -> None:
    readings = importlib.import_module("app.readings.repository")
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    async with reading_database.sessions() as session, session.begin():
        repository, profile_version, _version, job, contracts = await create_reading_graph(session)
        prepared = contracts.Prepared(
            state_token="runtime-secret-token",
            brief=build_brief(),
        )
        await repository.record_prepared(str(job.id), prepared, now)
        accepted = contracts.Accepted(
            state_token="runtime-secret-token",
            public_copy="first accepted copy",
        )
        await repository.record_completion_intent(
            str(job.id),
            accepted.public_copy,
            now,
        )
        await repository.record_accepted(str(job.id), accepted, now)

        replay = await repository.record_accepted(str(job.id), accepted, now)
        assert replay.public_copy == "first accepted copy"
        with pytest.raises(readings.ImmutableRecordError):
            await repository.record_accepted(
                str(job.id),
                contracts.Accepted(
                    state_token="runtime-secret-token",
                    public_copy="different second copy",
                ),
                now,
            )

        profile_version.payload_ciphertext = "tampered"
        with pytest.raises(readings.ImmutableRecordError):
            await session.flush()


async def test_reading_version_capability_must_match_its_locked_root(
    reading_database: Any,
) -> None:
    async with reading_database.sessions() as session, session.begin():
        repository, _profile, version, job, contracts = await create_reading_graph(session)
        original = (await repository.load_job(str(job.id))).prepare_command.to_dict()
        original["intent"]["capability_id"] = "fortune"
        mismatched = contracts.command_from_dict(original)
        assert isinstance(mismatched, contracts.Prepare)

        with pytest.raises(ValueError, match="capability"):
            await repository.create_version(
                reading_root_id=version.reading_root_id,
                runtime_release_id=version.runtime_release_id,
                prepare_command=mismatched,
            )


def test_reading_version_numbers_are_serialized_by_a_postgresql_root_lock() -> None:
    readings = importlib.import_module("app.readings.repository")

    compiled = str(
        readings.reading_root_version_lock_statement(uuid4()).compile(dialect=postgresql.dialect())
    ).upper()

    assert "FOR UPDATE" in compiled
