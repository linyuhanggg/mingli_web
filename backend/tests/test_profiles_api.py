from datetime import UTC, datetime, timedelta
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
    location: str = "北京市朝阳区",
) -> dict[str, Any]:
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "本人"},
    )
    assert draft.status_code == 201, draft.text
    confirmed = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json={
            "birth_datetime": "1994-04-30T05:55:00+08:00",
            "timezone": "Asia/Shanghai",
            "location": location,
            "gender": "female",
            "time_basis_policy": "civil",
            "zi_hour_policy": "midnight",
            "longitude": 116.4074,
            "latitude": 39.9042,
            "coordinate_source": "user_confirmed",
            "coordinate_precision": "city",
        },
    )
    assert confirmed.status_code == 201, confirmed.text
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
                "created_at": confirmed["created_at"],
            }
        ]
    }
    assert "北京市朝阳区" not in listed.text
    assert "1994-04-30" not in listed.text

    models = __import__("app.profiles.models", fromlist=["ProfileVersion"])
    async with database.sessions() as session:
        stored = (await session.scalars(select(models.ProfileVersion))).one()
    assert "北京市朝阳区" not in stored.payload_ciphertext
    assert "1994-04-30" not in stored.payload_ciphertext


async def test_draft_label_is_persisted_not_discarded(
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


def _confirm_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "birth_datetime": "1994-04-30T05:55:00+08:00",
        "timezone": "Asia/Shanghai",
        "location": "北京市朝阳区",
        "gender": "female",
        "time_basis_policy": "civil",
        "zi_hour_policy": "midnight",
    }
    payload.update(overrides)
    return payload


async def test_append_version_keeps_one_root_with_two_immutable_versions(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)

    appended = await client.post(
        f"/api/v1/profiles/{confirmed['profile_id']}/versions",
        headers=headers,
        json=_confirm_payload(location="上海市黄浦区"),
    )

    assert appended.status_code == 201, appended.text
    body = appended.json()
    assert body["profile_id"] == confirmed["profile_id"]
    assert body["profile_version_id"] != confirmed["profile_version_id"]
    assert body["version"] == 2
    assert_private_headers(appended)

    listed = await client.get("/api/v1/profiles")
    assert listed.status_code == 200
    assert [entry["version"] for entry in listed.json()["profiles"]] == [2]
    assert listed.json()["profiles"][0]["profile_id"] == confirmed["profile_id"]

    from app.profiles.models import ProfileVersion

    async with database.sessions() as session:
        versions = (
            await session.scalars(
                select(ProfileVersion).where(
                    ProfileVersion.profile_id == UUID(confirmed["profile_id"])
                )
            )
        ).all()
    assert len(versions) == 2


async def test_append_version_of_unknown_profile_returns_404(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)

    response = await client.post(
        "/api/v1/profiles/00000000-0000-0000-0000-000000000000/versions",
        headers=headers,
        json=_confirm_payload(),
    )

    assert response.status_code == 404


async def test_append_version_is_owner_scoped_with_cross_owner_404(
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

        response = await second.post(
            f"/api/v1/profiles/{confirmed['profile_id']}/versions",
            headers=second_headers,
            json=_confirm_payload(),
        )

    assert response.status_code == 404


async def test_solar_time_basis_requires_explicit_confirmed_coordinates(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "本人"},
    )
    assert draft.status_code == 201, draft.text
    confirm_url = f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm"

    missing_all = await client.post(
        confirm_url,
        headers=headers,
        json=_confirm_payload(time_basis_policy="solar"),
    )
    assert missing_all.status_code == 400

    missing_precision = await client.post(
        confirm_url,
        headers=headers,
        json=_confirm_payload(
            time_basis_policy="solar",
            longitude=116.4074,
            latitude=39.9042,
            coordinate_source="user_confirmed",
        ),
    )
    assert missing_precision.status_code == 400

    complete = await client.post(
        confirm_url,
        headers=headers,
        json=_confirm_payload(
            time_basis_policy="solar",
            longitude=116.4074,
            latitude=39.9042,
            coordinate_source="user_confirmed",
            coordinate_precision="city",
        ),
    )
    assert complete.status_code == 201, complete.text


async def test_coordinates_require_source_and_precision(client: AsyncClient) -> None:
    headers = await create_guest(client)
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "本人"},
    )
    assert draft.status_code == 201, draft.text
    confirm_url = f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm"

    missing_source = await client.post(
        confirm_url,
        headers=headers,
        json=_confirm_payload(longitude=116.4074, latitude=39.9042),
    )
    assert missing_source.status_code == 400

    missing_precision = await client.post(
        confirm_url,
        headers=headers,
        json=_confirm_payload(
            longitude=116.4074,
            latitude=39.9042,
            coordinate_source="user_confirmed",
        ),
    )
    assert missing_precision.status_code == 400


async def test_longitude_and_latitude_must_come_as_a_pair(
    client: AsyncClient,
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
        json=_confirm_payload(longitude=116.4074),
    )

    assert response.status_code == 400


async def test_lunar_leap_month_requires_lunar_calendar(client: AsyncClient) -> None:
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
        json=_confirm_payload(calendar="gregorian", lunar_leap_month=True),
    )

    assert response.status_code == 400


async def test_birth_contract_fields_persist_in_the_version_payload(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    draft = await client.post(
        "/api/v1/profiles/drafts",
        headers=headers,
        json={"label": "本人"},
    )
    assert draft.status_code == 201, draft.text

    confirmed = await client.post(
        f"/api/v1/profiles/drafts/{draft.json()['draft_id']}/confirm",
        headers=headers,
        json=_confirm_payload(
            calendar="lunar",
            lunar_leap_month=True,
            birth_time_certainty="unknown",
        ),
    )
    assert confirmed.status_code == 201, confirmed.text

    from app.profiles.repository import ProfileRepository
    from app.security.envelope import EnvelopeCipher

    async with database.sessions() as session:
        repository = ProfileRepository(
            session,
            EnvelopeCipher.from_settings(test_settings),
        )
        payload = await repository.load_version_payload(
            UUID(confirmed.json()["profile_version_id"])
        )

    assert payload["calendar"] == "lunar"
    assert payload["lunar_leap_month"] is True
    assert payload["birth_time_certainty"] == "unknown"
    assert payload["time_basis_policy"] == "civil"
