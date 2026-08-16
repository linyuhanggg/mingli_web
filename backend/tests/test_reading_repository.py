from __future__ import annotations

import hashlib
import importlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql

# isort: split
from orchestrator_fakes import make_candidate
from test_narrative_guard import build_brief


@pytest.fixture
async def reading_database() -> AsyncIterator[Any]:
    database_module = importlib.import_module("app.database")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
    importlib.import_module("app.commerce.models")
    database = database_module.Database("sqlite+aiosqlite:///:memory:")
    async with database.engine.begin() as connection:
        await connection.run_sync(identity_models.Base.metadata.create_all)
    yield database
    await database.dispose()


async def create_reading_graph(
    session: Any,
    *,
    prepare_state_token: str | None = None,
    available_at: datetime | None = None,
) -> tuple[Any, Any, Any, Any, Any]:
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
        state_token=prepare_state_token,
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
        available_at=available_at,
    )
    return repository, profile_version, version, job, runtime_contracts


@pytest.mark.parametrize(
    ("prepare_state_token", "expected"),
    [(None, False), ("accepted-parent-token", True)],
)
async def test_repository_persists_prepare_token_presence_without_exposing_it(
    reading_database: Any,
    prepare_state_token: str | None,
    expected: bool,
) -> None:
    models = importlib.import_module("app.readings.models")
    async with reading_database.sessions() as session, session.begin():
        _repository, _profile, version, _job, _contracts = await create_reading_graph(
            session,
            prepare_state_token=prepare_state_token,
        )
        version_id = version.id

    async with reading_database.sessions() as session:
        persisted = await session.get(models.ReadingVersion, version_id)
        assert persisted is not None
        assert persisted.prepare_has_state_token is expected
        raw_rows = (
            await session.execute(
                text("SELECT prepare_has_state_token, prepare_ciphertext FROM reading_versions")
            )
        ).all()
        if prepare_state_token is not None:
            assert prepare_state_token not in repr(raw_rows)


async def test_waiting_input_timestamp_clears_when_prepare_is_resumed(
    reading_database: Any,
) -> None:
    models = importlib.import_module("app.readings.models")
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    async with reading_database.sessions() as session, session.begin():
        repository, _profile, version, job, contracts = await create_reading_graph(session)
        await repository.record_waiting_input(
            str(job.id),
            contracts.Stopped(
                reason="need_input",
                public_copy="还需要补充资料。",
                state_token="waiting-input-token",
                input_request={
                    "requirements": [
                        {
                            "any_of": [
                                {
                                    "id": "birth_datetime",
                                    "label": "出生时间",
                                    "type_id": "datetime",
                                    "description": None,
                                    "choices": [],
                                }
                            ]
                        }
                    ]
                },
            ),
            now,
        )
        assert version.waiting_input_at == now
        prepare = await repository.load_prepare(version.id)
        await repository.replace_prepare(
            version.id,
            contracts.Prepare(
                query=prepare.query,
                intent=prepare.intent,
                facts=prepare.facts,
                state_token="waiting-input-token",
                transition="correct",
            ),
        )
        refreshed = await session.get(models.ReadingVersion, version.id)
        assert refreshed is not None
        assert refreshed.status == "input_ready"
        assert refreshed.waiting_input_at is None


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

        loaded_candidate = await repository.load_successful_candidate(str(job.id))
        assert loaded_candidate == candidate
        accepted_copy_ref = await repository.load_accepted_copy_ref(str(job.id))
        assert accepted_copy_ref is not None
        assert accepted_copy_ref.startswith("accepted-copy:")

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


async def test_load_job_uses_the_immutable_product_version_contract_snapshot(
    reading_database: Any,
) -> None:
    commerce = importlib.import_module("app.commerce.models")
    readings = importlib.import_module("app.readings.models")

    async with reading_database.sessions() as session, session.begin():
        repository, _profile, version, job, _contracts = await create_reading_graph(session)
        family = commerce.ProductFamily(key="bazi", label="八字")
        session.add(family)
        await session.flush()
        product = commerce.ProductVersion(
            family_id=family.id,
            version="v7",
            price_minor=19900,
            currency="CNY",
            follow_up_count=1,
            follow_up_window_seconds=86_400,
            contract_version="bazi-presentation/v7",
            status="active",
        )
        session.add(product)
        await session.flush()
        root = await session.get(readings.ReadingRoot, version.reading_root_id)
        assert root is not None
        root.product_version_snapshot_id = product.id

        loaded = await repository.load_job(str(job.id))

    assert loaded.product_version == "bazi-reading/v7"
    assert loaded.presentation_contract_version == "bazi-presentation/v7"


async def test_generation_attempt_persists_the_safe_model_receipt(
    reading_database: Any,
) -> None:
    model = importlib.import_module("app.adapters.model")
    models = importlib.import_module("app.readings.models")
    narrative = importlib.import_module("app.readings.narrative_contracts")
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    usage = model.ModelTokenUsage(input_tokens=3, output_tokens=7, total_tokens=10)
    price_digest = model.model_price_snapshot_digest(
        version="fixture-price-v1",
        currency="CNY",
        input_microunits_per_million_tokens=2_000_000,
        output_microunits_per_million_tokens=4_000_000,
    )
    audit = model.ModelCallReceipt(
        outcome="succeeded",
        error_code=None,
        model_profile_id="deepseek-v4-flash-p0-v1",
        model_profile_snapshot_digest="a" * 64,
        provider="deepseek",
        provider_model_version="deepseek-v4-flash",
        provider_request_fingerprint=hashlib.sha256(b"provider-request-fixture").hexdigest(),
        request_fingerprint="b" * 64,
        latency_ms=125,
        narrative_policy_version="policy-v1",
        output_contract_id="repository-test-v1",
        price_snapshot=model.ModelPriceReceipt(
            version="fixture-price-v1",
            currency="CNY",
            snapshot_digest=price_digest,
            input_microunits_per_million_tokens=2_000_000,
            output_microunits_per_million_tokens=4_000_000,
        ),
        usage=usage,
        cost=model.ModelCost(
            currency="CNY",
            microunits=34,
            price_snapshot_version="fixture-price-v1",
            price_snapshot_digest=price_digest,
            input_microunits_per_million_tokens=2_000_000,
            output_microunits_per_million_tokens=4_000_000,
        ),
    )

    async with reading_database.sessions() as session, session.begin():
        repository, _profile, _version, job, contracts = await create_reading_graph(session)
        await repository.record_prepared(
            str(job.id),
            contracts.Prepared(state_token="runtime-secret-token", brief=build_brief()),
            now,
        )
        await repository.record_generation_attempt(
            str(job.id),
            1,
            make_candidate(narrative),
            (),
            now,
            model_receipt=audit,
        )
        attempt = await session.scalar(
            select(models.GenerationAttempt).where(
                models.GenerationAttempt.reading_version_id == job.reading_version_id
            )
        )

    assert attempt is not None
    assert attempt.model_receipt == audit.to_dict()
    serialized = repr(attempt.model_receipt)
    assert "runtime-secret-token" not in serialized
    assert "事业上最该先抓住哪条主线" not in serialized


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


def test_profile_version_numbers_are_serialized_by_a_postgresql_profile_lock() -> None:
    profiles = importlib.import_module("app.profiles.repository")

    compiled = str(
        profiles.subject_profile_version_lock_statement(uuid4()).compile(
            dialect=postgresql.dialect()
        )
    ).upper()

    assert "FOR UPDATE" in compiled


async def test_profile_version_requires_an_existing_locked_profile(
    reading_database: Any,
) -> None:
    profiles = importlib.import_module("app.profiles.repository")
    envelope = importlib.import_module("app.security.envelope")
    cipher = envelope.EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1")

    async with reading_database.sessions() as session, session.begin():
        repository = profiles.ProfileRepository(session, cipher)
        with pytest.raises(LookupError, match="Profile"):
            await repository.create_version(
                profile_id=uuid4(),
                payload={"birth_datetime": "1994-04-30T05:55:00+08:00"},
            )


async def test_reading_root_rejects_a_profile_version_owned_by_another_user(
    reading_database: Any,
) -> None:
    identity_models = importlib.import_module("app.identity.models")
    profiles = importlib.import_module("app.profiles.repository")
    readings = importlib.import_module("app.readings.repository")
    envelope = importlib.import_module("app.security.envelope")
    cipher = envelope.EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1")

    async with reading_database.sessions() as session, session.begin():
        profile_owner = identity_models.User()
        other_user = identity_models.User()
        session.add_all((profile_owner, other_user))
        await session.flush()
        profile_repository = profiles.ProfileRepository(session, cipher)
        profile = await profile_repository.create_profile(owner_user_id=profile_owner.id)
        profile_version = await profile_repository.create_version(
            profile_id=profile.id,
            payload={"birth_datetime": "1994-04-30T05:55:00+08:00"},
        )

        with pytest.raises(ValueError, match="owner"):
            await readings.SqlReadingRepository(session, cipher).create_root(
                owner_user_id=other_user.id,
                profile_version_id=profile_version.id,
                capability_id="bazi",
            )


async def test_save_verification_handles_a_concurrent_duplicate_insert(
    reading_database: Any,
) -> None:
    async with reading_database.sessions() as session, session.begin():
        repository, _profile, version, _job, _contracts = await create_reading_graph(
            session
        )
        first, created_first = await repository.save_verification(
            version_id=version.id,
            outcome="partial",
            note="部分准确",
        )
        assert created_first is True

        # Simulate the lost-update window: the racing transaction read no
        # verification before the other transaction committed, so the pre-check
        # misses and the INSERT must be absorbed by the unique constraint
        # instead of surfacing as a 500.
        real_load = repository.load_verification
        pre_check = {"missed": True}

        async def racing_load(target_version_id: Any) -> Any:
            # Only the pre-check sees a stale "no verification" view; the
            # post-IntegrityError reload must see the committed row.
            if target_version_id == version.id and pre_check["missed"]:
                pre_check["missed"] = False
                return None
            return await real_load(target_version_id)

        repository.load_verification = racing_load  # type: ignore[method-assign]
        try:
            second, created_second = await repository.save_verification(
                version_id=version.id,
                outcome="disagreed",
                note="另一并发请求",
            )
        finally:
            repository.load_verification = real_load  # type: ignore[method-assign]

        assert created_second is False
        assert second.id == first.id
        assert second.outcome == "partial"
        assert second.note == "部分准确"

        models = importlib.import_module("app.readings.models")
        stored = list(
            await session.scalars(
                select(models.ReadingVerification).where(
                    models.ReadingVerification.reading_version_id == version.id
                )
            )
        )
        assert len(stored) == 1
        assert stored[0].outcome == "partial"
