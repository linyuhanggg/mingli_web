import asyncio
import importlib
import os
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.identity.models import User
from app.persistence import ImmutableRecordError
from app.profiles.models import ProfileVersion, ProfileVersionAuthorization, SubjectProfile
from app.profiles.schemas import ProfileConfirmRequest, ProfileVersionRequest
from app.profiles.service import (
    ProfileAuthorizationPayloadError,
    ProfileAuthorizationRequiredError,
    ProfileDifferenceNotAcknowledgedError,
    ProfileNameConflictError,
    ProfileService,
)
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


class PostgresProfileDatabaseHarness:
    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def dispose(self) -> None:
        await self.engine.dispose()


@pytest.fixture
async def postgres_profile_database() -> AsyncIterator[Any]:
    url = os.environ.get("MINGLI_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("MINGLI_TEST_POSTGRES_URL is required for PostgreSQL concurrency tests")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
    importlib.import_module("app.admin.models")
    importlib.import_module("app.support.models")
    importlib.import_module("app.entitlements.models")
    importlib.import_module("app.commerce.models")
    importlib.import_module("app.referrals.models")
    importlib.import_module("app.content.models")
    importlib.import_module("app.privacy.models")
    importlib.import_module("app.media.models")
    schema = f"mingli_profile_test_{uuid4().hex}"
    admin_engine = create_async_engine(url, pool_pre_ping=True)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        url,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": schema}},
    )
    database = PostgresProfileDatabaseHarness(engine)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(identity_models.Base.metadata.create_all)
        yield database
    finally:
        await database.dispose()
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


def _owner(user_id: UUID) -> SimpleNamespace:
    return SimpleNamespace(kind="user", id=user_id)


def _confirm_payload(**overrides: Any) -> ProfileConfirmRequest:
    payload: dict[str, Any] = {
        "birth_datetime": "1994-04-30T05:55:00+08:00",
        "timezone": "Asia/Shanghai",
        "location": "北京市朝阳区",
        "gender": "female",
        "time_basis_policy": "civil",
        "zi_hour_policy": "midnight",
    }
    payload.update(overrides)
    return ProfileConfirmRequest(**payload)


def _version_payload(**overrides: Any) -> ProfileVersionRequest:
    payload: dict[str, Any] = {
        "birth_datetime": "2001-07-12T09:30:00+08:00",
        "timezone": "Asia/Shanghai",
        "location": "上海市",
        "gender": "male",
        "time_basis_policy": "civil",
        "zi_hour_policy": "midnight",
        "difference_acknowledged": True,
    }
    payload.update(overrides)
    return ProfileVersionRequest(**payload)


async def test_same_subject_profile_only_appends_immutable_versions(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        draft_id = await service.create_draft(owner, label="本人")
        first = await service.confirm_draft(owner, draft_id, _confirm_payload())
        stored = await session.get(ProfileVersion, first.profile_version_id)
        assert stored is not None
        original_ciphertext = stored.payload_ciphertext
        original_fingerprint = stored.payload_fingerprint

        second = await service.append_version(
            owner,
            first.profile_id,
            _version_payload(difference_acknowledged=True),
        )

        assert second.profile_id == first.profile_id
        assert second.version == 2
        assert second.profile_version_id != first.profile_version_id
        unchanged = await session.get(ProfileVersion, first.profile_version_id)
        assert unchanged is not None
        assert unchanged.version == 1
        assert unchanged.payload_ciphertext == original_ciphertext
        assert unchanged.payload_fingerprint == original_fingerprint
        versions = list(
            await session.scalars(
                select(ProfileVersion)
                .where(ProfileVersion.profile_id == first.profile_id)
                .order_by(ProfileVersion.version)
            )
        )
        assert [item.version for item in versions] == [1, 2]
        assert [item.id for item in versions] == [
            first.profile_version_id,
            second.profile_version_id,
        ]


async def test_identical_identity_fields_do_not_auto_merge_profiles(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        first_id = await service.create_draft(owner, label="档案甲")
        second_id = await service.create_draft(owner, label="档案乙")
        same_facts = _confirm_payload()
        first = await service.confirm_draft(owner, first_id, same_facts)
        second = await service.confirm_draft(owner, second_id, same_facts)

        assert first.profile_id != second.profile_id
        assert first.profile_version_id != second.profile_version_id
        profiles = list(await session.scalars(select(SubjectProfile)))
        versions = list(await session.scalars(select(ProfileVersion)))
        assert {item.id for item in profiles} == {first.profile_id, second.profile_id}
        assert len(versions) == 2
        assert {item.profile_id for item in versions} == {
            first.profile_id,
            second.profile_id,
        }
        first_payload = await service.repository.load_version_payload(first.profile_version_id)
        second_payload = await service.repository.load_version_payload(second.profile_version_id)
        assert first_payload["birth_datetime"] == second_payload["birth_datetime"]
        assert first_payload["location"] == second_payload["location"]


async def test_append_without_difference_ack_is_rejected(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        draft_id = await service.create_draft(owner, label="本人")
        confirmed = await service.confirm_draft(owner, draft_id, _confirm_payload())

        with pytest.raises(ProfileDifferenceNotAcknowledgedError):
            await service.append_version(
                owner,
                confirmed.profile_id,
                _version_payload(difference_acknowledged=False),
            )
        assert await session.scalar(select(func.count(ProfileVersion.id))) == 1


async def test_other_person_without_authorization_is_rejected(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        draft_id = await service.create_draft(owner, label="他人")

        with pytest.raises(ProfileAuthorizationRequiredError):
            await service.confirm_draft(
                owner,
                draft_id,
                _confirm_payload(subject_type="other", authorization_confirmed=False),
            )
        assert await session.scalar(select(func.count(ProfileVersion.id))) == 0


async def test_minor_without_guardian_is_allowed_and_self_photo_claim_is_rejected(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        photo_draft_id = await service.create_draft(owner, label="本人")
        with pytest.raises(ProfileAuthorizationPayloadError):
            await service.confirm_draft(
                owner,
                photo_draft_id,
                _confirm_payload(photo_authorization_confirmed=True),
            )
        minor_draft_id = await service.create_draft(owner, label="未成年人")
        confirmed = await service.confirm_draft(
            owner,
            minor_draft_id,
            _confirm_payload(
                subject_type="other",
                is_minor=True,
                authorization_confirmed=True,
                minor_guardian_confirmed=False,
            ),
        )
        assert confirmed.version == 1
        authorization = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id
                == confirmed.profile_version_id
            )
        )
        assert authorization is not None
        assert authorization.is_minor is True
        assert authorization.minor_guardian_confirmed is False


async def test_authorized_other_append_persists_photo_and_guardian_facts(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        draft_id = await service.create_draft(owner, label="他人")
        first = await service.confirm_draft(
            owner,
            draft_id,
            _confirm_payload(
                subject_type="other",
                authorization_confirmed=True,
                photo_authorization_confirmed=True,
                is_minor=True,
                minor_guardian_confirmed=True,
            ),
        )
        second = await service.append_version(
            owner,
            first.profile_id,
            _version_payload(
                subject_type="other",
                authorization_confirmed=True,
                photo_authorization_confirmed=True,
                is_minor=True,
                minor_guardian_confirmed=True,
                difference_acknowledged=True,
            ),
        )

        authorization = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id == second.profile_version_id
            )
        )
        assert authorization is not None
        assert authorization.subject_type == "other"
        assert authorization.authorization_confirmed is True
        assert authorization.photo_authorization_confirmed is True
        assert authorization.minor_guardian_confirmed is True
        assert authorization.difference_acknowledged is True
        assert authorization.is_minor is True


async def test_profile_version_and_authorization_rows_cannot_be_updated(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        draft_id = await service.create_draft(owner, label="本人")
        confirmed = await service.confirm_draft(owner, draft_id, _confirm_payload())
        await session.commit()

    async with database.sessions() as session:
        version = await session.get(ProfileVersion, confirmed.profile_version_id)
        assert version is not None
        version.payload_ciphertext = "tampered"
        with pytest.raises(ImmutableRecordError):
            await session.flush()
        await session.rollback()

    async with database.sessions() as session:
        authorization = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id == confirmed.profile_version_id
            )
        )
        assert authorization is not None
        authorization.authorization_confirmed = True
        with pytest.raises(ImmutableRecordError):
            await session.flush()


async def test_overwrite_appends_corrected_facts_to_existing_profile(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        first_id = await service.create_draft(owner, label="本人")
        first = await service.confirm_draft(owner, first_id, _confirm_payload())
        stored = await session.get(ProfileVersion, first.profile_version_id)
        assert stored is not None
        original_ciphertext = stored.payload_ciphertext
        original_fingerprint = stored.payload_fingerprint

        correction_id = await service.create_draft(owner, label="本人")
        overwritten = await service.confirm_draft(
            owner,
            correction_id,
            _confirm_payload(
                birth_datetime="1994-04-30T06:10:00+08:00",
                location="上海市黄浦区",
                longitude=121.4737,
                latitude=31.2304,
                on_name_conflict="overwrite",
            ),
        )

        assert overwritten.profile_id == first.profile_id
        assert overwritten.version == 2
        assert overwritten.profile_version_id != first.profile_version_id
        assert overwritten.display_name == "本人"
        assert overwritten.birth_date == first.birth_date
        unchanged = await session.get(ProfileVersion, first.profile_version_id)
        assert unchanged is not None
        assert unchanged.payload_ciphertext == original_ciphertext
        assert unchanged.payload_fingerprint == original_fingerprint
        corrected = await service.repository.load_version_payload(
            overwritten.profile_version_id
        )
        assert corrected["birth_datetime"] == "1994-04-30T06:10:00+08:00"
        assert corrected["location"] == "上海市黄浦区"
        assert corrected["longitude"] == 121.4737
        assert corrected["latitude"] == 31.2304
        authorization = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id
                == overwritten.profile_version_id
            )
        )
        assert authorization is not None
        assert authorization.difference_acknowledged is True
        remaining_profiles = list(await session.scalars(select(SubjectProfile)))
        assert {item.id for item in remaining_profiles} == {first.profile_id}


async def test_overwrite_reuses_existing_version_when_facts_are_identical(
    database: Any,
    test_settings: Any,
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        first_id = await service.create_draft(owner, label="本人")
        first = await service.confirm_draft(
            owner,
            first_id,
            _confirm_payload(longitude=116.4074, latitude=39.9042),
        )

        duplicate_id = await service.create_draft(owner, label="本人")
        reused = await service.confirm_draft(
            owner,
            duplicate_id,
            _confirm_payload(
                longitude=116.4074,
                latitude=39.9042,
                on_name_conflict="overwrite",
            ),
        )

        assert reused.profile_id == first.profile_id
        assert reused.profile_version_id == first.profile_version_id
        assert reused.version == 1
        assert await session.scalar(select(func.count(ProfileVersion.id))) == 1
        remaining_profiles = list(await session.scalars(select(SubjectProfile)))
        assert {item.id for item in remaining_profiles} == {first.profile_id}


@pytest.mark.parametrize(
    "authorization_overrides",
    [
        {"subject_type": "other", "authorization_confirmed": True},
        {"is_minor": True},
        {
            "subject_type": "other",
            "authorization_confirmed": True,
            "photo_authorization_confirmed": True,
        },
        {"is_minor": True, "minor_guardian_confirmed": True},
    ],
)
async def test_overwrite_appends_when_authorization_facts_change(
    database: Any,
    test_settings: Any,
    authorization_overrides: dict[str, Any],
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        first_id = await service.create_draft(owner, label="本人")
        first = await service.confirm_draft(owner, first_id, _confirm_payload())
        original = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id == first.profile_version_id
            )
        )
        assert original is not None
        original_subject_type = original.subject_type
        original_is_minor = original.is_minor
        original_photo = original.photo_authorization_confirmed
        original_guardian = original.minor_guardian_confirmed

        correction_id = await service.create_draft(owner, label="本人")
        overwritten = await service.confirm_draft(
            owner,
            correction_id,
            _confirm_payload(
                on_name_conflict="overwrite",
                **authorization_overrides,
            ),
        )

        assert overwritten.profile_id == first.profile_id
        assert overwritten.version == 2
        assert overwritten.profile_version_id != first.profile_version_id
        appended = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id
                == overwritten.profile_version_id
            )
        )
        assert appended is not None
        assert appended.subject_type == authorization_overrides.get(
            "subject_type", "self"
        )
        assert appended.is_minor is authorization_overrides.get("is_minor", False)
        assert appended.authorization_confirmed is authorization_overrides.get(
            "authorization_confirmed", False
        )
        assert appended.photo_authorization_confirmed is authorization_overrides.get(
            "photo_authorization_confirmed", False
        )
        assert appended.minor_guardian_confirmed is authorization_overrides.get(
            "minor_guardian_confirmed", False
        )
        assert appended.difference_acknowledged is True
        unchanged = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id == first.profile_version_id
            )
        )
        assert unchanged is not None
        assert unchanged.subject_type == original_subject_type
        assert unchanged.is_minor is original_is_minor
        assert unchanged.photo_authorization_confirmed is original_photo
        assert unchanged.minor_guardian_confirmed is original_guardian
        remaining_profiles = list(await session.scalars(select(SubjectProfile)))
        assert {item.id for item in remaining_profiles} == {first.profile_id}


async def test_save_as_name_stays_within_label_limit(
    database: Any,
    test_settings: Any,
) -> None:
    long_name = "本" * 80
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        first_id = await service.create_draft(owner, label=long_name)
        first = await service.confirm_draft(owner, first_id, _confirm_payload())
        conflicting_id = await service.create_draft(owner, label=long_name)
        with pytest.raises(ProfileNameConflictError) as conflicted:
            await service.confirm_draft(
                owner,
                conflicting_id,
                _confirm_payload(),
            )
        assert len(conflicted.value.suggested_save_as_name) <= 80
        assert conflicted.value.suggested_save_as_name != long_name

        saved = await service.confirm_draft(
            owner,
            conflicting_id,
            _confirm_payload(on_name_conflict="save_as"),
        )
        assert saved.profile_id != first.profile_id
        assert saved.display_name is not None
        assert len(saved.display_name) <= 80
        assert saved.display_name != long_name
        stored = await session.get(SubjectProfile, saved.profile_id)
        assert stored is not None
        assert stored.label is not None
        assert len(stored.label) <= 80


async def test_profile_rename_locks_owner_before_reading_profile(
    database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        draft_id = await service.create_draft(owner, label="旧名字")
        confirmed = await service.confirm_draft(owner, draft_id, _confirm_payload())
        calls: list[str] = []
        original_lock = service.repository.lock_profile_owner
        original_get = service.repository.get_owned_profile

        async def tracked_lock(**kwargs: Any) -> None:
            calls.append("lock")
            await original_lock(**kwargs)

        async def tracked_get(*args: Any, **kwargs: Any) -> SubjectProfile | None:
            calls.append("read")
            return await original_get(*args, **kwargs)

        monkeypatch.setattr(service.repository, "lock_profile_owner", tracked_lock)
        monkeypatch.setattr(service.repository, "get_owned_profile", tracked_get)

        renamed = await service.update_display_name(
            owner,
            confirmed.profile_id,
            "新名字",
        )

        assert renamed.display_name == "新名字"
        assert calls[:2] == ["lock", "read"]


def _delay_first_profile_conflict_check(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[asyncio.Event, asyncio.Event, asyncio.Event]:
    first_check_finished = asyncio.Event()
    second_check_started = asyncio.Event()
    release_first = asyncio.Event()
    original_check = ProfileService._name_birth_conflict
    check_count = 0

    async def delayed_conflict_check(
        self: ProfileService,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        nonlocal check_count
        conflict = await original_check(self, *args, **kwargs)
        check_count += 1
        if check_count == 1:
            first_check_finished.set()
            await release_first.wait()
        else:
            second_check_started.set()
        return conflict

    monkeypatch.setattr(
        ProfileService,
        "_name_birth_conflict",
        delayed_conflict_check,
    )
    return first_check_finished, second_check_started, release_first


async def _profile_conflict_call_was_blocked(
    second_check_started: asyncio.Event,
) -> bool:
    try:
        await asyncio.wait_for(second_check_started.wait(), timeout=0.2)
    except TimeoutError:
        return True
    return False


async def test_postgresql_owner_lock_serializes_concurrent_profile_renames(
    postgres_profile_database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with postgres_profile_database.sessions() as session, session.begin():
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        first_draft = await service.create_draft(owner, label="甲")
        second_draft = await service.create_draft(owner, label="乙")
        first = await service.confirm_draft(owner, first_draft, _confirm_payload())
        second = await service.confirm_draft(owner, second_draft, _confirm_payload())
        user_id = user.id

    first_check_finished, second_check_started, release_first = (
        _delay_first_profile_conflict_check(monkeypatch)
    )

    async def rename(profile_id: UUID) -> str:
        async with postgres_profile_database.sessions() as session, session.begin():
            service = ProfileService(session, test_settings)
            try:
                await service.update_display_name(
                    _owner(user_id),
                    profile_id,
                    "同名目标",
                )
            except ProfileNameConflictError:
                return "conflict"
        return "renamed"

    first_task = asyncio.create_task(rename(first.profile_id))
    await asyncio.wait_for(first_check_finished.wait(), timeout=2)
    second_task = asyncio.create_task(rename(second.profile_id))
    second_was_blocked = await _profile_conflict_call_was_blocked(second_check_started)
    release_first.set()
    outcomes = await asyncio.wait_for(
        asyncio.gather(first_task, second_task),
        timeout=5,
    )

    assert second_was_blocked is True
    assert sorted(outcomes) == ["conflict", "renamed"]
    async with postgres_profile_database.sessions() as session:
        confirmed_target_count = await session.scalar(
            select(func.count())
            .select_from(SubjectProfile)
            .join(ProfileVersion, ProfileVersion.profile_id == SubjectProfile.id)
            .where(
                SubjectProfile.owner_user_id == user_id,
                SubjectProfile.label == "同名目标",
            )
        )
    assert confirmed_target_count == 1


async def test_postgresql_owner_lock_serializes_rename_with_draft_confirmation(
    postgres_profile_database: Any,
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with postgres_profile_database.sessions() as session, session.begin():
        user = User()
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)
        owner = _owner(user.id)
        confirmed_draft = await service.create_draft(owner, label="原名字")
        confirmed = await service.confirm_draft(
            owner,
            confirmed_draft,
            _confirm_payload(),
        )
        competing_draft = await service.create_draft(owner, label="同名目标")
        user_id = user.id

    first_check_finished, second_check_started, release_first = (
        _delay_first_profile_conflict_check(monkeypatch)
    )

    async def rename() -> str:
        async with postgres_profile_database.sessions() as session, session.begin():
            service = ProfileService(session, test_settings)
            await service.update_display_name(
                _owner(user_id),
                confirmed.profile_id,
                "同名目标",
            )
        return "renamed"

    async def confirm() -> str:
        async with postgres_profile_database.sessions() as session, session.begin():
            service = ProfileService(session, test_settings)
            try:
                await service.confirm_draft(
                    _owner(user_id),
                    competing_draft,
                    _confirm_payload(),
                )
            except ProfileNameConflictError:
                return "conflict"
        return "confirmed"

    rename_task = asyncio.create_task(rename())
    await asyncio.wait_for(first_check_finished.wait(), timeout=2)
    confirm_task = asyncio.create_task(confirm())
    confirm_was_blocked = await _profile_conflict_call_was_blocked(
        second_check_started
    )
    release_first.set()
    outcomes = await asyncio.wait_for(
        asyncio.gather(rename_task, confirm_task),
        timeout=5,
    )

    assert confirm_was_blocked is True
    assert sorted(outcomes) == ["conflict", "renamed"]
    async with postgres_profile_database.sessions() as session:
        confirmed_target_count = await session.scalar(
            select(func.count())
            .select_from(SubjectProfile)
            .join(ProfileVersion, ProfileVersion.profile_id == SubjectProfile.id)
            .where(
                SubjectProfile.owner_user_id == user_id,
                SubjectProfile.label == "同名目标",
            )
        )
    assert confirmed_target_count == 1
