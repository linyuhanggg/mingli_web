from types import SimpleNamespace
from typing import Any
from uuid import UUID

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
from sqlalchemy import func, select


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
