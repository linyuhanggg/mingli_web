"""API-level full journey regression for the email register/login flow.

Walks one fictional email through the real FastAPI app, real repositories,
and the in-memory SQLite database with the Fake OTP adapter (code 246810):
guest session -> email OTP -> first-login account creation -> fictional
profile -> Fake preview reading to the accepted terminal state -> reading
history -> second login with a fresh client resolving to the same user ->
negative OTP and cross-account isolation checks -> CSRF transition from the
guest token to the device token.  No network access and no real personal data.
"""

from typing import Any
from uuid import UUID

import pytest
from app.identity.models import DeviceSession, LoginIdentity, User
from app.main import create_app
from app.security.envelope import EnvelopeCipher
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from worker.readings import build_reading_worker

EMAIL_RAW = "  Mingli.Journey.User@Example.COM "
EMAIL_NORMALIZED = "mingli.journey.user@example.com"
EMAIL_MASKED = "m***@example.com"
OTHER_EMAIL = "another.person@example.com"
FAKE_OTP_CODE = "246810"

# Fictional profile payload, deliberately not real personal data.
FICTIONAL_PROFILE = {
    "birth_datetime": "1994-04-30T05:55:00+08:00",
    "timezone": "Asia/Shanghai",
    "location": "福建省福州市",
    "gender": "female",
    "time_basis_policy": "civil",
    "zi_hour_policy": "midnight",
    "longitude": 119.2965,
    "latitude": 26.0745,
    "coordinate_source": "user_confirmed",
}


async def create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def request_email_otp(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    destination: str = EMAIL_RAW,
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": "email", "destination": destination},
    )
    assert response.status_code == 202, response.text
    return response.json()


async def verify_email_otp(
    client: AsyncClient,
    headers: dict[str, str],
    challenge_id: str,
    *,
    code: str = FAKE_OTP_CODE,
) -> Any:
    return await client.post(
        "/api/v1/auth/otp/verify",
        headers=headers,
        json={"challenge_id": challenge_id, "code": code},
    )


async def email_login(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    destination: str = EMAIL_RAW,
) -> tuple[Any, dict[str, Any]]:
    challenge = await request_email_otp(client, headers, destination=destination)
    assert challenge["development_code"] == FAKE_OTP_CODE
    verified = await verify_email_otp(client, headers, challenge["challenge_id"])
    assert verified.status_code == 200, verified.text
    return verified, verified.json()


async def create_confirmed_profile(
    client: AsyncClient,
    headers: dict[str, str],
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
        json=FICTIONAL_PROFILE,
    )
    assert confirmed.status_code == 201, confirmed.text
    return confirmed.json()


def assert_private_headers(response: Any) -> None:
    assert response.headers["cache-control"] == "private, no-store, max-age=0"
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"


async def seed_runtime_release(database: Any, settings: Any) -> None:
    readings = __import__("app.readings.repository", fromlist=["SqlReadingRepository"])
    cipher = EnvelopeCipher.from_settings(settings)
    async with database.sessions() as session:
        repository = readings.SqlReadingRepository(session, cipher)
        await repository.create_runtime_release(
            name="mingli-master-portable-core",
            version="5.1",
            source_commit="494ce0bba174a77800daf9b9c38ce9c9166d9a94",
            release_manifest_digest="e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68",
            protocol_version="mingli-portable-interface-v2",
            describe_manifest_digest="7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342",
            image_digest=None,
            production_ready=True,
        )
        await session.commit()


async def drive_worker_to_quiescence(database: Any, settings: Any) -> None:
    """Poll the real worker once per iteration until no job is claimable."""
    worker = build_reading_worker(
        settings=settings,
        database=database,
        worker_id="email-journey-test-worker",
    )
    for _ in range(8):
        if not await worker.run_once():
            return
    pytest.fail("reading jobs did not quiesce within eight worker iterations")


async def test_email_registration_login_full_journey(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    # 1. Guest session: keep the opaque guest cookie and its CSRF partner.
    guest_headers = await create_guest(client)
    assert client.cookies["mingli_guest"]
    assert client.cookies["mingli_csrf"] == guest_headers["X-CSRF-Token"]

    # 2. Email OTP with the Fake code; first login creates the account.
    first_response, first = await email_login(client, guest_headers)
    first_user_id = UUID(first["user_id"])
    device_headers = {"X-CSRF-Token": first["csrf_token"]}
    assert first["csrf_token"] != guest_headers["X-CSRF-Token"]
    assert client.cookies["mingli_session"]
    assert client.cookies["mingli_csrf"] == first["csrf_token"]
    session_cookie = next(
        value
        for value in first_response.headers.get_list("set-cookie")
        if value.startswith("mingli_session=")
    )
    for flag in ("HttpOnly", "Secure", "SameSite=lax", "Max-Age=2592000"):
        assert flag in session_cookie

    async with database.sessions() as session:
        users = list(await session.scalars(select(User)))
        identities = list(await session.scalars(select(LoginIdentity)))
        device_sessions = list(await session.scalars(select(DeviceSession)))
    assert len(users) == 1
    assert len(identities) == 1
    assert len(device_sessions) == 1
    assert device_sessions[0].user_id == users[0].id
    assert UUID(str(users[0].id)) == first_user_id

    # 3. Account is reachable and leaks neither the raw email nor secrets.
    account = await client.get("/api/v1/account")
    assert account.status_code == 200
    account_body = account.json()
    assert UUID(account_body["user_id"]) == first_user_id
    assert account_body["identities"] == [
        {
            "id": account_body["identities"][0]["id"],
            "provider": "email",
            "masked_destination": EMAIL_MASKED,
            "verified_at": account_body["identities"][0]["verified_at"],
        }
    ]
    for banned in (
        "mingli.journey.user",
        "Mingli.Journey.User",
        "provider_subject_hash",
        "identity_hash_key",
        "local-only-identity-hash-key",
        "development_code",
        FAKE_OTP_CODE,
    ):
        assert banned not in account.text

    # 4. Fictional profile, then a real Fake preview reading to terminal state.
    confirmed = await create_confirmed_profile(client, device_headers)
    await seed_runtime_release(database, test_settings)
    started = await client.post(
        "/api/v1/readings/preview",
        headers=device_headers,
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )
    assert started.status_code == 201, started.text
    version_id = started.json()["reading_version_id"]
    await drive_worker_to_quiescence(database, test_settings)

    result = await client.get(f"/api/v1/readings/{version_id}/result")
    assert result.status_code == 200
    result_body = result.json()
    assert result_body["status"] == "accepted"
    assert result_body["accepted_copy"].startswith("这是合同测试候选稿")
    assert "仅供传统文化参考" in result_body["accepted_copy"]
    assert result_body["fact_panel"]["facts"]
    assert any(
        limit["kind_id"] == "limit:traditional"
        for limit in result_body["fact_panel"]["limits"]
    )
    assert result_body["verification"] is None
    assert_private_headers(result)
    for banned in (
        "state_token",
        "candidate",
        "ciphertext",
        "1994-04-30",
        "福建省福州市",
        EMAIL_NORMALIZED,
    ):
        assert banned not in result.text

    # 5. The reading is visible in the history and stays publicly readable.
    listed = await client.get("/api/v1/readings")
    assert listed.status_code == 200
    assert_private_headers(listed)
    assert version_id in [
        item["reading_version_id"] for item in listed.json()["readings"]
    ]
    summary = await client.get(f"/api/v1/readings/{version_id}")
    assert summary.status_code == 200
    assert summary.json()["status"] == "accepted"
    for banned in ("state_token", "ciphertext", "candidate"):
        assert banned not in summary.text

    # 6. A brand-new client logging in with the same email is the same User.
    second_app = create_app(settings=test_settings, database=database)
    async with AsyncClient(
        transport=ASGITransport(app=second_app),
        base_url="https://testserver",
    ) as second_client:
        second_guest = await create_guest(second_client)
        _, second = await email_login(
            second_client,
            second_guest,
            destination=EMAIL_NORMALIZED,
        )
        assert UUID(second["user_id"]) == first_user_id
        assert second_client.cookies["mingli_session"]

        account_again = await second_client.get("/api/v1/account")
        assert account_again.status_code == 200
        assert UUID(account_again.json()["user_id"]) == first_user_id

        profiles_again = await second_client.get("/api/v1/profiles")
        assert profiles_again.status_code == 200
        assert profiles_again.json() == {
            "profiles": [
                {
                    "profile_id": confirmed["profile_id"],
                    "profile_version_id": confirmed["profile_version_id"],
                    "subject_ref": confirmed["subject_ref"],
                    "version": 1,
                    "created_at": confirmed["created_at"],
                }
            ]
        }

        readings_again = await second_client.get("/api/v1/readings")
        assert readings_again.status_code == 200
        assert version_id in [
            item["reading_version_id"] for item in readings_again.json()["readings"]
        ]

    async with database.sessions() as session:
        users = list(await session.scalars(select(User)))
        identities = list(await session.scalars(select(LoginIdentity)))
        device_sessions = list(await session.scalars(select(DeviceSession)))
    assert len(users) == 1
    assert len(identities) == 1
    assert len(device_sessions) == 2

    # The first device session still works alongside the second one.
    still_ok = await client.get("/api/v1/account")
    assert still_ok.status_code == 200
    assert UUID(still_ok.json()["user_id"]) == first_user_id


async def test_invalid_email_code_does_not_establish_a_session(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    challenge = await request_email_otp(client, headers)

    rejected = await verify_email_otp(
        client,
        headers,
        challenge["challenge_id"],
        code="111111",
    )

    assert rejected.status_code == 400
    assert rejected.json()["title"] == "Invalid or expired code"
    assert "mingli_session" not in client.cookies
    assert not any(
        value.startswith("mingli_session=")
        for value in rejected.headers.get_list("set-cookie")
    )
    account = await client.get("/api/v1/account")
    assert account.status_code == 401

    async with database.sessions() as session:
        users = list(await session.scalars(select(User)))
        device_sessions = list(await session.scalars(select(DeviceSession)))
    assert users == []
    assert device_sessions == []


async def test_cross_account_cannot_read_another_users_data(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    # Owner A: email account with a profile and a reading.
    guest_a = await create_guest(client)
    _, login_a = await email_login(client, guest_a)
    user_a = UUID(login_a["user_id"])
    device_a = {"X-CSRF-Token": login_a["csrf_token"]}
    draft_a = await client.post(
        "/api/v1/profiles/drafts",
        headers=device_a,
        json={"label": "本人"},
    )
    assert draft_a.status_code == 201, draft_a.text
    confirmed_a = await client.post(
        f"/api/v1/profiles/drafts/{draft_a.json()['draft_id']}/confirm",
        headers=device_a,
        json=FICTIONAL_PROFILE,
    )
    assert confirmed_a.status_code == 201, confirmed_a.text
    await seed_runtime_release(database, test_settings)
    started_a = await client.post(
        "/api/v1/readings/preview",
        headers=device_a,
        json={
            "profile_version_id": confirmed_a.json()["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )
    assert started_a.status_code == 201, started_a.text
    version_a = started_a.json()["reading_version_id"]

    # Owner B: a different email can log in but must not see A's data.
    second_app = create_app(settings=test_settings, database=database)
    async with AsyncClient(
        transport=ASGITransport(app=second_app),
        base_url="https://testserver",
    ) as intruder:
        guest_b = await create_guest(intruder)
        _, login_b = await email_login(
            intruder,
            guest_b,
            destination=OTHER_EMAIL,
        )
        user_b = UUID(login_b["user_id"])
        assert user_b != user_a
        device_b = {"X-CSRF-Token": login_b["csrf_token"]}

        account_b = await intruder.get("/api/v1/account")
        assert UUID(account_b.json()["user_id"]) == user_b

        foreign_version = await intruder.get(f"/api/v1/readings/{version_a}")
        assert foreign_version.status_code == 404
        foreign_result = await intruder.get(f"/api/v1/readings/{version_a}/result")
        assert foreign_result.status_code == 404

        readings_b = await intruder.get("/api/v1/readings")
        assert readings_b.json() == {"readings": []}
        profiles_b = await intruder.get("/api/v1/profiles")
        assert profiles_b.json() == {"profiles": []}

        stolen_confirm = await intruder.post(
            f"/api/v1/profiles/drafts/{draft_a.json()['draft_id']}/confirm",
            headers=device_b,
            json=FICTIONAL_PROFILE,
        )
        assert stolen_confirm.status_code == 404
        foreign_preview = await intruder.post(
            "/api/v1/readings/preview",
            headers=device_b,
            json={
                "profile_version_id": confirmed_a.json()["profile_version_id"],
                "dimension_ids": ["career"],
            },
        )
        assert foreign_preview.status_code == 404


async def test_csrf_transition_from_guest_to_device(client: AsyncClient) -> None:
    guest_headers = await create_guest(client)
    guest_csrf = guest_headers["X-CSRF-Token"]
    challenge = await request_email_otp(client, guest_headers)
    verified = await verify_email_otp(client, guest_headers, challenge["challenge_id"])
    assert verified.status_code == 200, verified.text
    device_csrf = verified.json()["csrf_token"]
    assert device_csrf != guest_csrf
    assert client.cookies["mingli_csrf"] == device_csrf

    # The old guest CSRF no longer authorizes writes against the device session.
    stale = await client.post(
        "/api/v1/profiles/drafts",
        headers={"X-CSRF-Token": guest_csrf},
        json={"label": "本人"},
    )
    assert stale.status_code == 403
    assert stale.json()["title"] == "CSRF validation failed"

    # The device CSRF from the login response works for the same write.
    device_headers = {"X-CSRF-Token": device_csrf}
    accepted = await client.post(
        "/api/v1/profiles/drafts",
        headers=device_headers,
        json={"label": "本人"},
    )
    assert accepted.status_code == 201, accepted.text

    # Reads need no CSRF and still resolve the device session after the switch.
    account = await client.get("/api/v1/account")
    assert account.status_code == 200

    # A forged header against the device CSRF cookie is still rejected.
    forged = await client.post(
        "/api/v1/profiles/drafts",
        headers={"X-CSRF-Token": "f" * 40},
        json={"label": "本人"},
    )
    assert forged.status_code == 403
