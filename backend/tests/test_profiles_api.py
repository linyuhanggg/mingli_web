from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


async def create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def create_confirmed_profile(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    label: str = "本人",
    birth_datetime: str = "1994-04-30T05:55:00+08:00",
    location: str = "北京市朝阳区",
) -> dict[str, Any]:
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": label},
    )
    assert draft.status_code == 201, draft.text
    confirmed = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": birth_datetime,
            "timezone": "Asia/Shanghai",
            "location": location,
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "longitude": 116.4074,
            "latitude": 39.9042,
            "coordinate_source": "user_confirmed",
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    assert_private_headers(confirmed)
    return confirmed.json()


async def login_current_guest(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    destination: str = "13800138000",
) -> dict[str, Any]:
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": "phone", "destination": destination},
    )
    assert requested.status_code == 202, requested.text
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers=headers,
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": "246810",
        },
    )
    assert verified.status_code == 200, verified.text
    return verified.json()


def assert_private_headers(response: Any) -> None:
    assert response.headers["cache-control"] == "private, no-store, max-age=0"
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"


async def test_guest_can_create_confirm_and_list_an_encrypted_profile(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)

    listed = await client.get("/api/v1/profiles")

    assert listed.status_code == 200
    assert_private_headers(listed)
    assert listed.json() == {
        "profiles": [
            {
                "profile_id": confirmed["profile_id"],
                "profile_version_id": confirmed["profile_version_id"],
                "subject_ref": f"profile-version:{confirmed['profile_version_id']}",
                "version": 1,
                "display_name": "本人",
                "birth_date": "1994-04-30",
                "created_at": confirmed["created_at"],
            }
        ]
    }
    assert "北京市朝阳区" not in listed.text
    assert "05:55:00" not in listed.text
    assert "Asia/Shanghai" not in listed.text

    models = __import__("app.profiles.models", fromlist=["ProfileVersion"])
    async with database.sessions() as session:
        stored = (await session.scalars(select(models.ProfileVersion))).one()
    assert "北京市朝阳区" not in stored.payload_ciphertext
    assert "1994-04-30" not in stored.payload_ciphertext


@pytest.mark.parametrize("legacy_label", ["", " \t "])
async def test_legacy_blank_profile_labels_are_projected_as_null(
    client: AsyncClient,
    database: Any,
    legacy_label: str,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)

    from app.profiles.models import SubjectProfile

    async with database.sessions() as session:
        profile = (await session.scalars(select(SubjectProfile))).one()
        profile.label = legacy_label
        await session.commit()

    listed = await client.get("/api/v1/profiles")
    history = await client.get(
        f"/api/v1/profiles/{confirmed['profile_id']}/versions"
    )

    assert listed.status_code == 200, listed.text
    assert history.status_code == 200, history.text
    assert_private_headers(listed)
    assert_private_headers(history)
    assert listed.json()["profiles"][0]["display_name"] is None
    assert {item["display_name"] for item in history.json()["versions"]} == {None}


async def test_owned_profile_can_append_an_authorized_other_person_version(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)

    appended = await client.post(
        f"/api/v1/profiles/{confirmed['profile_id']}/versions",
        headers=headers,
        json={
            "birth_datetime": "2001-07-12T09:30:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "gender": "male",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "subject_type": "other",
            "authorization_confirmed": True,
            "difference_acknowledged": True,
        },
    )

    assert appended.status_code == 201, appended.text
    assert_private_headers(appended)
    assert appended.json()["profile_id"] == confirmed["profile_id"]
    assert appended.json()["version"] == 2
    assert appended.json()["profile_version_id"] != confirmed["profile_version_id"]

    from app.profiles.models import ProfileVersion, ProfileVersionAuthorization

    async with database.sessions() as session:
        versions = list(
            await session.scalars(
                select(ProfileVersion).order_by(ProfileVersion.version)
            )
        )
        authorization = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id == versions[1].id
            )
        )
    assert [version.version for version in versions] == [1, 2]
    assert authorization is not None
    assert authorization.profile_version_id == versions[1].id
    assert authorization.subject_type == "other"
    assert authorization.authorization_confirmed is True
    assert authorization.difference_acknowledged is True


async def test_initial_other_person_profile_requires_authorization(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "他人"},
    )
    assert draft.status_code == 201, draft.text

    response = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "2001-07-12T09:30:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "gender": "male",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "subject_type": "other",
            "authorization_confirmed": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Profile authorization is required"
    from app.profiles.models import ProfileVersion

    async with database.sessions() as session:
        assert len(list(await session.scalars(select(ProfileVersion)))) == 0


async def test_other_person_profile_version_requires_authorization_and_difference_ack(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)

    response = await client.post(
        f"/api/v1/profiles/{confirmed['profile_id']}/versions",
        headers=headers,
        json={
            "birth_datetime": "2001-07-12T09:30:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "gender": "male",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "subject_type": "other",
            "authorization_confirmed": False,
            "difference_acknowledged": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Profile authorization is required"
    from app.profiles.models import ProfileVersion

    async with database.sessions() as session:
        assert len(list(await session.scalars(select(ProfileVersion)))) == 1


async def test_minor_profile_version_does_not_require_guardian_confirmation(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)

    response = await client.post(
        f"/api/v1/profiles/{confirmed['profile_id']}/versions",
        headers=headers,
        json={
            "birth_datetime": "2015-07-12T09:30:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "gender": "male",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "subject_type": "other",
            "is_minor": True,
            "authorization_confirmed": True,
            "minor_guardian_confirmed": False,
            "difference_acknowledged": True,
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["profile_id"] == confirmed["profile_id"]
    assert response.json()["version"] == 2
    assert response.json()["profile_version_id"] != confirmed["profile_version_id"]

    from app.profiles.models import ProfileVersion, ProfileVersionAuthorization

    async with database.sessions() as session:
        versions = list(
            await session.scalars(
                select(ProfileVersion).order_by(ProfileVersion.version)
            )
        )
        authorization = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id == versions[1].id
            )
        )
    assert [version.version for version in versions] == [1, 2]
    assert authorization is not None
    assert authorization.is_minor is True
    assert authorization.minor_guardian_confirmed is False


async def test_profile_version_history_returns_all_versions_without_payloads(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    appended = await client.post(
        f"/api/v1/profiles/{confirmed['profile_id']}/versions",
        headers=headers,
        json={
            "birth_datetime": "2001-07-12T09:30:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市",
            "gender": "male",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "difference_acknowledged": True,
        },
    )
    assert appended.status_code == 201, appended.text

    history = await client.get(
        f"/api/v1/profiles/{confirmed['profile_id']}/versions"
    )

    assert history.status_code == 200
    assert_private_headers(history)
    assert [item["version"] for item in history.json()["versions"]] == [1, 2]
    assert [item["birth_date"] for item in history.json()["versions"]] == [
        "1994-04-30",
        "2001-07-12",
    ]
    assert {item["display_name"] for item in history.json()["versions"]} == {"本人"}
    assert "birth_datetime" not in history.text
    assert "09:30:00" not in history.text
    assert "上海市" not in history.text


async def test_duplicate_display_names_are_listed_and_rename_preserves_versions(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    first = await create_confirmed_profile(
        client,
        headers,
        label="家人",
        birth_datetime="1994-04-30T05:55:00+08:00",
    )
    second = await create_confirmed_profile(
        client,
        headers,
        label="家人",
        birth_datetime="2001-07-12T09:30:00+08:00",
        location="上海市",
    )

    listed = await client.get("/api/v1/profiles")
    assert listed.status_code == 200
    by_id = {item["profile_id"]: item for item in listed.json()["profiles"]}
    assert len(by_id) == 2
    assert by_id[first["profile_id"]]["display_name"] == "家人"
    assert by_id[second["profile_id"]]["display_name"] == "家人"
    assert by_id[first["profile_id"]]["birth_date"] == "1994-04-30"
    assert by_id[second["profile_id"]]["birth_date"] == "2001-07-12"

    from app.profiles.models import ProfileVersion

    async with database.sessions() as session:
        stored_before = await session.scalar(
            select(ProfileVersion).where(
                ProfileVersion.id == UUID(first["profile_version_id"])
            )
        )
        assert stored_before is not None
        immutable_before = (
            stored_before.version,
            stored_before.payload_key_id,
            stored_before.payload_nonce,
            stored_before.payload_ciphertext,
            stored_before.payload_fingerprint,
            stored_before.created_at,
        )

    renamed = await client.patch(
        f"/api/v1/profiles/{first['profile_id']}",
        headers=headers,
        json={"display_name": "  家人甲  "},
    )
    assert renamed.status_code == 200, renamed.text
    assert_private_headers(renamed)
    assert renamed.json()["display_name"] == "家人甲"
    assert renamed.json()["birth_date"] == "1994-04-30"
    assert renamed.json()["profile_version_id"] == first["profile_version_id"]

    relisted = await client.get("/api/v1/profiles")
    names = {
        item["profile_id"]: item["display_name"]
        for item in relisted.json()["profiles"]
    }
    assert names == {
        first["profile_id"]: "家人甲",
        second["profile_id"]: "家人",
    }

    async with database.sessions() as session:
        versions = list(await session.scalars(select(ProfileVersion)))
        stored_after = next(
            item for item in versions if str(item.id) == first["profile_version_id"]
        )
    assert len(versions) == 2
    assert (
        stored_after.version,
        stored_after.payload_key_id,
        stored_after.payload_nonce,
        stored_after.payload_ciphertext,
        stored_after.payload_fingerprint,
        stored_after.created_at,
    ) == immutable_before


async def test_rename_rejects_name_and_birth_date_collision(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)
    first = await create_confirmed_profile(client, headers, label="甲")
    second = await create_confirmed_profile(
        client,
        headers,
        label="乙",
        birth_datetime="1994-04-30T09:30:00+08:00",
        location="上海市",
    )

    renamed = await client.patch(
        f"/api/v1/profiles/{second['profile_id']}",
        headers=headers,
        json={"display_name": "甲"},
    )

    assert renamed.status_code == 409, renamed.text
    body = renamed.json()
    assert body["code"] == "profile_name_conflict"
    assert body["existing_profile_id"] == first["profile_id"]
    listed = await client.get("/api/v1/profiles")
    names = {
        item["profile_id"]: item["display_name"]
        for item in listed.json()["profiles"]
    }
    assert names == {
        first["profile_id"]: "甲",
        second["profile_id"]: "乙",
    }


async def test_profile_rename_is_csrf_protected_and_owner_scoped(
    database: Any,
    test_settings: Any,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    application = main.create_app(settings=test_settings, database=database)
    transport = ASGITransport(app=application)
    async with (
        AsyncClient(transport=transport, base_url="https://testserver") as first,
        AsyncClient(transport=transport, base_url="https://testserver") as second,
    ):
        first_headers = await create_guest(first)
        confirmed = await create_confirmed_profile(first, first_headers)
        second_headers = await create_guest(second)

        missing_csrf = await first.patch(
            f"/api/v1/profiles/{confirmed['profile_id']}",
            json={"display_name": "新名字"},
        )
        cross_owner = await second.patch(
            f"/api/v1/profiles/{confirmed['profile_id']}",
            headers=second_headers,
            json={"display_name": "新名字"},
        )
        cross_owner_detail = await second.get(
            f"/api/v1/profiles/{confirmed['profile_id']}/versions"
        )
        second_list = await second.get("/api/v1/profiles")
        extra_profile_field = await first.patch(
            f"/api/v1/profiles/{confirmed['profile_id']}",
            headers=first_headers,
            json={"display_name": "新名字", "birth_date": "2000-01-01"},
        )
        blank_display_name = await first.patch(
            f"/api/v1/profiles/{confirmed['profile_id']}",
            headers=first_headers,
            json={"display_name": "   "},
        )

    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["title"] == "CSRF validation failed"
    assert cross_owner.status_code == 404
    assert cross_owner_detail.status_code == 404
    assert second_list.status_code == 200
    assert second_list.json() == {"profiles": []}
    assert extra_profile_field.status_code == 400
    assert blank_display_name.status_code == 400


async def test_draft_label_is_persisted_not_discarded(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "  本人  "},
    )
    assert draft.status_code == 201, draft.text

    blank = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "   "},
    )
    assert blank.status_code == 400

    from app.profiles.models import SubjectProfile

    async with database.sessions() as session:
        profile = await session.scalar(select(SubjectProfile))
        assert profile is not None
        assert profile.label == "本人"


async def test_profile_writes_require_matching_csrf(client: AsyncClient) -> None:
    await create_guest(client)

    response = await client.post(
        "/api/v1/profiles/drafts",
        json={"label": "本人"},
    )

    assert response.status_code == 403
    assert response.json()["title"] == "CSRF validation failed"


async def test_profile_draft_writes_are_rate_limited(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)

    responses = []
    for _ in range(10):
        response = await client.post(
            "/api/v1/profiles/drafts",
            headers=headers,
            json={"label": "本人"},
        )
        responses.append(response.status_code)
    limited = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "本人"},
    )

    assert responses == [201] * 10
    assert limited.status_code == 429
    assert limited.json()["title"] == "Too many profile write requests"
    assert int(limited.headers["retry-after"]) >= 1


async def test_confirm_rejects_an_unknown_timezone(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "本人"},
    )
    assert draft.status_code == 201, draft.text

    response = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "timezone": "Not/AZone",
            "location": "北京市朝阳区",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid request"


async def test_profile_ids_are_owner_scoped_with_cross_owner_404(
    database: Any,
    test_settings: Any,
) -> None:
    main = __import__("app.main", fromlist=["create_app"])
    application = main.create_app(settings=test_settings, database=database)
    transport = ASGITransport(app=application)
    async with (
        AsyncClient(transport=transport, base_url="https://testserver") as first,
        AsyncClient(transport=transport, base_url="https://testserver") as second,
    ):
        first_headers = await create_guest(first)
        draft = await first.post(
            "/api/v1/profiles/drafts",
            headers=first_headers,
            json={"label": "本人"},
        )
        assert draft.status_code == 201, draft.text
        second_headers = await create_guest(second)

        response = await second.post(
            f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
            headers=second_headers,
            json={
                "birth_datetime": "1994-04-30T05:55:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "上海市",
                "gender": "female",
                "time_basis_policy": "civil",
                "zi_hour_policy": "midnight",
            },
        )

    assert response.status_code == 404


async def test_login_claims_the_current_guest_profile_atomically(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)

    logged_in = await login_current_guest(client, headers)
    listed = await client.get("/api/v1/profiles")

    assert listed.status_code == 200
    assert listed.json()["profiles"][0]["profile_id"] == confirmed["profile_id"]

    identity_models = __import__(
        "app.identity.models", fromlist=["GuestSession"]
    )
    profile_models = __import__(
        "app.profiles.models", fromlist=["SubjectProfile"]
    )
    async with database.sessions() as session:
        guest = (await session.scalars(select(identity_models.GuestSession))).one()
        profile = (await session.scalars(select(profile_models.SubjectProfile))).one()

    assert str(guest.claimed_by_user_id) == logged_in["user_id"]
    assert guest.claimed_at is not None
    assert str(profile.owner_user_id) == logged_in["user_id"]
    assert profile.owner_guest_session_id is None


async def test_double_confirm_of_the_same_draft_returns_409(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "本人"},
    )
    assert draft.status_code == 201, draft.text
    confirm_payload = {
        "birth_datetime": "1994-04-30T05:55:00+08:00",
        "timezone": "Asia/Shanghai",
        "location": "北京市朝阳区",
        "gender": "female",
        "time_basis_policy": "civil",
        "zi_hour_policy": "midnight",
    }

    first = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json=confirm_payload,
    )
    assert first.status_code == 201, first.text
    second = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json=confirm_payload,
    )

    assert second.status_code == 409
    assert second.json()["title"] == "Profile Draft is already confirmed"

    from app.profiles.models import ProfileVersion

    async with database.sessions() as session:
        versions = (await session.scalars(select(ProfileVersion))).all()
    assert len(versions) == 1


async def test_locked_confirm_recheck_rejects_an_already_confirmed_draft(
    database: Any,
    test_settings: Any,
) -> None:
    import importlib

    from app.profiles.repository import ProfileRepository
    from app.security.envelope import EnvelopeCipher

    session_factory = database.sessions
    async with session_factory() as session:
        identity_models = importlib.import_module("app.identity.models")
        user = identity_models.User()
        session.add(user)
        await session.flush()
        repository = ProfileRepository(
            session,
            EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1"),
        )
        profile = await repository.create_profile(owner_user_id=user.id)
        payload = {
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市朝阳区",
        }
        await repository.create_version(profile_id=profile.id, payload=payload)

        from app.profiles.models import ProfileVersion
        from sqlalchemy.exc import IntegrityError

        try:
            await repository.create_version_if_unconfirmed(
                profile_id=profile.id,
                payload=payload,
            )
        except ValueError:
            pass
        except IntegrityError:
            # Locked re-check may also surface as a unique violation when the
            # fast path raced; either way the draft must not gain a version.
            pass
        else:
            raise AssertionError("second confirm unexpectedly allocated a version")

        await session.commit()
        versions = (await session.scalars(select(ProfileVersion))).all()
    assert len(versions) == 1


async def test_overwrite_keeps_corrected_birth_facts_on_existing_profile(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    first = await create_confirmed_profile(client, headers)
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "本人"},
    )
    assert draft.status_code == 201, draft.text
    overwritten = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1994-04-30T06:10:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "上海市黄浦区",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "longitude": 121.4737,
            "latitude": 31.2304,
            "coordinate_source": "user_confirmed",
            "on_name_conflict": "overwrite",
        },
    )

    assert overwritten.status_code == 201, overwritten.text
    body = overwritten.json()
    assert body["profile_id"] == first["profile_id"]
    assert body["version"] == 2
    assert body["profile_version_id"] != first["profile_version_id"]
    assert body["display_name"] == "本人"
    assert body["birth_date"] == "1994-04-30"

    history = await client.get(f"/api/v1/profiles/{first['profile_id']}/versions")
    listed = await client.get("/api/v1/profiles")
    assert history.status_code == 200, history.text
    assert [item["version"] for item in history.json()["versions"]] == [1, 2]
    assert listed.json()["profiles"][0]["profile_version_id"] == body["profile_version_id"]

    from app.profiles.models import SubjectProfile
    from app.profiles.service import ProfileService

    async with database.sessions() as session:
        payload = await ProfileService(session, test_settings).repository.load_version_payload(
            UUID(body["profile_version_id"])
        )
        remaining = list(await session.scalars(select(SubjectProfile)))
    assert payload["birth_datetime"] == "1994-04-30T06:10:00+08:00"
    assert payload["location"] == "上海市黄浦区"
    assert {str(item.id) for item in remaining} == {first["profile_id"]}


async def test_overwrite_appends_when_authorization_facts_change(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    first = await create_confirmed_profile(client, headers)
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "本人"},
    )
    assert draft.status_code == 201, draft.text
    overwritten = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市朝阳区",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "longitude": 116.4074,
            "latitude": 39.9042,
            "coordinate_source": "user_confirmed",
            "subject_type": "other",
            "authorization_confirmed": True,
            "is_minor": True,
            "photo_authorization_confirmed": True,
            "minor_guardian_confirmed": True,
            "on_name_conflict": "overwrite",
        },
    )

    assert overwritten.status_code == 201, overwritten.text
    body = overwritten.json()
    assert body["profile_id"] == first["profile_id"]
    assert body["version"] == 2
    assert body["profile_version_id"] != first["profile_version_id"]

    history = await client.get(f"/api/v1/profiles/{first['profile_id']}/versions")
    assert history.status_code == 200, history.text
    assert [item["version"] for item in history.json()["versions"]] == [1, 2]

    from app.profiles.models import ProfileVersionAuthorization

    async with database.sessions() as session:
        original = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id
                == UUID(first["profile_version_id"])
            )
        )
        appended = await session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id
                == UUID(body["profile_version_id"])
            )
        )
    assert original is not None
    assert original.subject_type == "self"
    assert original.authorization_confirmed is False
    assert appended is not None
    assert appended.subject_type == "other"
    assert appended.authorization_confirmed is True
    assert appended.is_minor is True
    assert appended.photo_authorization_confirmed is True
    assert appended.minor_guardian_confirmed is True
    assert appended.difference_acknowledged is True

    from app.profiles.models import SubjectProfile

    async with database.sessions() as session:
        remaining = list(await session.scalars(select(SubjectProfile)))
    assert {str(item.id) for item in remaining} == {first["profile_id"]}


async def test_save_as_conflict_name_is_truncated_to_label_limit(
    client: AsyncClient,
) -> None:
    long_name = "本" * 80
    headers = await create_guest(client)
    first = await create_confirmed_profile(client, headers, label=long_name)
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": long_name},
    )
    assert draft.status_code == 201, draft.text
    conflict = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市朝阳区",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
        },
    )
    assert conflict.status_code == 409, conflict.text
    suggested = conflict.json()["suggested_save_as_name"]
    assert len(suggested) <= 80
    assert suggested != long_name

    saved = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": "北京市朝阳区",
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "on_name_conflict": "save_as",
        },
    )
    assert saved.status_code == 201, saved.text
    assert saved.json()["profile_id"] != first["profile_id"]
    assert len(saved.json()["display_name"]) <= 80
    assert saved.json()["display_name"] == suggested


async def test_guest_claim_rejects_an_already_claimed_session(
    database: Any,
    test_settings: Any,
) -> None:
    import importlib

    from app.profiles.service import GuestAlreadyClaimedError, ProfileService

    identity_models = importlib.import_module("app.identity.models")
    async with database.sessions() as session:
        guest = identity_models.GuestSession(
            token_hash="t" * 64,
            csrf_token_hash="c" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        user = identity_models.User()
        session.add(guest)
        session.add(user)
        await session.flush()
        service = ProfileService(session, test_settings)

        await service.claim_guest_ownership(guest, user.id)
        with pytest.raises(GuestAlreadyClaimedError):
            await service.claim_guest_ownership(guest, user.id)
        await session.commit()


async def test_guest_claim_renames_same_name_and_birth_date_before_overwrite(
    database: Any,
    test_settings: Any,
) -> None:
    import importlib

    from app.profiles.schemas import ProfileConfirmRequest
    from app.profiles.service import ProfileService

    identity_models = importlib.import_module("app.identity.models")
    async with database.sessions() as session:
        guest = identity_models.GuestSession(
            token_hash="t" * 64,
            csrf_token_hash="c" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        user = identity_models.User()
        session.add_all([guest, user])
        await session.flush()
        service = ProfileService(session, test_settings)
        user_owner = SimpleNamespace(kind="user", id=user.id)
        guest_owner = SimpleNamespace(kind="guest", id=guest.id)
        payload = ProfileConfirmRequest(
            birth_datetime="1994-04-30T05:55:00+08:00",
            timezone="Asia/Shanghai",
            location="北京市朝阳区",
            gender="female",
            time_basis_policy="civil",
            zi_hour_policy="midnight",
        )
        user_draft = await service.create_draft(user_owner, label="本人")
        user_profile = await service.confirm_draft(user_owner, user_draft, payload)
        guest_draft = await service.create_draft(guest_owner, label="本人")
        guest_profile = await service.confirm_draft(
            guest_owner,
            guest_draft,
            payload,
        )

        await service.claim_guest_ownership(guest, user.id)

        claimed = {
            summary.profile_id: summary
            for summary in await service.list_profiles(user_owner)
        }
        assert claimed[user_profile.profile_id].display_name == "本人"
        assert claimed[guest_profile.profile_id].display_name == "本人 (2)"
        overwrite_draft = await service.create_draft(user_owner, label="本人")
        overwritten = await service.confirm_draft(
            user_owner,
            overwrite_draft,
            payload.model_copy(update={"on_name_conflict": "overwrite"}),
        )
        assert overwritten.profile_id == user_profile.profile_id
        await session.commit()


async def test_guest_claim_keeps_same_name_when_birth_dates_differ(
    database: Any,
    test_settings: Any,
) -> None:
    import importlib

    from app.profiles.schemas import ProfileConfirmRequest
    from app.profiles.service import ProfileService

    identity_models = importlib.import_module("app.identity.models")
    async with database.sessions() as session:
        guest = identity_models.GuestSession(
            token_hash="t" * 64,
            csrf_token_hash="c" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        user = identity_models.User()
        session.add_all([guest, user])
        await session.flush()
        service = ProfileService(session, test_settings)
        user_owner = SimpleNamespace(kind="user", id=user.id)
        guest_owner = SimpleNamespace(kind="guest", id=guest.id)
        user_payload = ProfileConfirmRequest(
            birth_datetime="1994-04-30T05:55:00+08:00",
            timezone="Asia/Shanghai",
            location="北京市朝阳区",
            gender="female",
            time_basis_policy="civil",
            zi_hour_policy="midnight",
        )
        guest_payload = user_payload.model_copy(
            update={"birth_datetime": "1995-04-30T05:55:00+08:00"}
        )
        user_draft = await service.create_draft(user_owner, label="本人")
        await service.confirm_draft(user_owner, user_draft, user_payload)
        guest_draft = await service.create_draft(guest_owner, label="本人")
        guest_profile = await service.confirm_draft(
            guest_owner,
            guest_draft,
            guest_payload,
        )

        await service.claim_guest_ownership(guest, user.id)

        claimed = {
            summary.profile_id: summary
            for summary in await service.list_profiles(user_owner)
        }
        assert claimed[guest_profile.profile_id].display_name == "本人"
        overwrite_draft = await service.create_draft(user_owner, label="本人")
        overwritten = await service.confirm_draft(
            user_owner,
            overwrite_draft,
            guest_payload.model_copy(update={"on_name_conflict": "overwrite"}),
        )
        assert overwritten.profile_id == guest_profile.profile_id
        await session.commit()
