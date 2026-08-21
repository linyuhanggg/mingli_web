from typing import Any

from app.admin.passwords import verify_password
from app.identity.models import ConsentRecord, DeviceSession, UserPasswordCredential
from app.identity.policy import CURRENT_POLICY_VERSION
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


async def _create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def _otp_login(
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


async def _record_reaccept(client: AsyncClient, csrf_token: str) -> None:
    for policy_key in ("privacy", "terms"):
        recorded = await client.post(
            "/api/v1/auth/consents",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "policy_key": policy_key,
                "policy_version": CURRENT_POLICY_VERSION,
                "context": "reaccept",
            },
        )
        assert recorded.status_code == 201, recorded.text


async def test_otp_user_can_set_a_password_and_login_from_a_new_guest(
    client: AsyncClient,
    database: Any,
) -> None:
    first_guest = await _create_guest(client)
    first_session = await _otp_login(client, first_guest)
    await _record_reaccept(client, first_session["csrf_token"])
    set_password = await client.put(
        "/api/v1/auth/password",
        headers={"X-CSRF-Token": first_session["csrf_token"]},
        json={"password": "correct-password"},
    )
    assert set_password.status_code == 204, set_password.text
    for policy_key in ("privacy", "terms"):
        accepted = await client.post(
            "/api/v1/auth/consents",
            headers={"X-CSRF-Token": first_session["csrf_token"]},
            json={
                "policy_key": policy_key,
                "policy_version": CURRENT_POLICY_VERSION,
                "context": "reaccept",
            },
        )
        assert accepted.status_code == 201, accepted.text
    await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": first_session["csrf_token"]},
    )

    second_guest = await _create_guest(client)
    logged_in = await client.post(
        "/api/v1/auth/password/login",
        headers=second_guest,
        json={
            "channel": "phone",
            "destination": "13800138000",
            "password": "correct-password",
        },
    )
    assert logged_in.status_code == 200, logged_in.text
    assert logged_in.json()["user_id"] == first_session["user_id"]

    async with database.sessions() as session:
        credential = await session.scalar(select(UserPasswordCredential))
    assert credential is not None
    assert "correct-password" not in credential.password_hash
    assert verify_password("correct-password", credential.password_hash)


async def test_password_login_does_not_disclose_whether_the_identity_exists(
    client: AsyncClient,
) -> None:
    headers = await _create_guest(client)
    response = await client.post(
        "/api/v1/auth/password/login",
        headers=headers,
        json={
            "channel": "phone",
            "destination": "13800138000",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401
    assert response.json()["title"] == "Invalid credentials"


async def test_policy_consent_is_recorded_with_version_and_context(
    client: AsyncClient,
    database: Any,
) -> None:
    guest = await _create_guest(client)
    logged_in = await _otp_login(client, guest)
    response = await client.post(
        "/api/v1/auth/consents",
        headers={"X-CSRF-Token": logged_in["csrf_token"]},
        json={
            "policy_key": "privacy",
            "policy_version": CURRENT_POLICY_VERSION,
            "context": "registration",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["policy_key"] == "privacy"
    assert body["policy_version"] == CURRENT_POLICY_VERSION
    assert body["context"] == "registration"

    async with database.sessions() as session:
        record = await session.scalar(select(ConsentRecord))
    assert record is not None
    assert str(record.user_id) == logged_in["user_id"]


async def test_otp_recovery_resets_password_and_revokes_existing_devices(
    database: Any,
) -> None:
    config = __import__("app.config", fromlist=["Settings"])
    main = __import__("app.main", fromlist=["create_app"])
    settings = config.Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="fake",
        otp_cooldown_seconds=0,
        otp_guest_window_limit=10,
        otp_network_window_limit=10,
        otp_destination_window_limit=10,
    )
    application = main.create_app(settings=settings, database=database)

    async with (
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as first_client,
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as recovery_client,
        AsyncClient(
            transport=ASGITransport(app=application),
            base_url="https://testserver",
        ) as login_client,
    ):
        first_guest = await _create_guest(first_client)
        first_session = await _otp_login(first_client, first_guest)
        await _record_reaccept(first_client, first_session["csrf_token"])
        set_password = await first_client.put(
            "/api/v1/auth/password",
            headers={"X-CSRF-Token": first_session["csrf_token"]},
            json={"password": "old-password"},
        )
        assert set_password.status_code == 204, set_password.text
        for policy_key in ("privacy", "terms"):
            consent = await first_client.post(
                "/api/v1/auth/consents",
                headers={"X-CSRF-Token": first_session["csrf_token"]},
                json={
                    "policy_key": policy_key,
                    "policy_version": CURRENT_POLICY_VERSION,
                    "context": "reaccept",
                },
            )
            assert consent.status_code == 201, consent.text

        recovery_guest = await _create_guest(recovery_client)
        requested = await recovery_client.post(
            "/api/v1/auth/otp/request",
            headers=recovery_guest,
            json={"channel": "phone", "destination": "13800138000"},
        )
        assert requested.status_code == 202, requested.text

        recovered = await recovery_client.post(
            "/api/v1/auth/password/recover",
            headers=recovery_guest,
            json={
                "challenge_id": requested.json()["challenge_id"],
                "code": "246810",
                "password": "new-password",
            },
        )
        assert recovered.status_code == 200, recovered.text
        assert recovered.json()["user_id"] == first_session["user_id"]
        for policy_key in ("privacy", "terms"):
            accepted = await recovery_client.post(
                "/api/v1/auth/consents",
                headers={"X-CSRF-Token": recovered.json()["csrf_token"]},
                json={
                    "policy_key": policy_key,
                    "policy_version": CURRENT_POLICY_VERSION,
                    "context": "reaccept",
                },
            )
            assert accepted.status_code == 201, accepted.text

        old_account = await first_client.get("/api/v1/account")
        assert old_account.status_code == 401

        fresh_guest = await _create_guest(login_client)
        logged_in = await login_client.post(
            "/api/v1/auth/password/login",
            headers=fresh_guest,
            json={
                "channel": "phone",
                "destination": "13800138000",
                "password": "new-password",
            },
        )
        assert logged_in.status_code == 200, logged_in.text
        assert logged_in.json()["user_id"] == first_session["user_id"]


async def test_otp_registration_sets_password_and_records_both_policy_consents(
    client: AsyncClient,
    database: Any,
) -> None:
    guest = await _create_guest(client)
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=guest,
        json={"channel": "email", "destination": "new-user@example.com"},
    )
    assert requested.status_code == 202, requested.text

    registered = await client.post(
        "/api/v1/auth/register",
        headers=guest,
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": "246810",
            "password": "correct-password",
            "policy_version": "development-preview-v0.1",
        },
    )
    assert registered.status_code == 200, registered.text

    async with database.sessions() as session:
        credentials = list(await session.scalars(select(UserPasswordCredential)))
        consents = list(
            await session.scalars(
                select(ConsentRecord).order_by(ConsentRecord.policy_key)
            )
        )

    assert len(credentials) == 1
    assert {record.policy_key for record in consents} == {"privacy", "terms"}
    assert {record.policy_version for record in consents} == {"development-preview-v0.1"}
    assert {record.context for record in consents} == {"registration"}


async def test_otp_registration_rejects_a_stale_policy_version(
    client: AsyncClient,
    database: Any,
) -> None:
    guest = await _create_guest(client)
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=guest,
        json={"channel": "email", "destination": "stale-policy@example.com"},
    )
    assert requested.status_code == 202, requested.text

    response = await client.post(
        "/api/v1/auth/register",
        headers=guest,
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": "246810",
            "password": "correct-password",
            "policy_version": "old-policy-v0.0",
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Policy version is not current"
    async with database.sessions() as session:
        assert list(await session.scalars(select(UserPasswordCredential))) == []
        assert list(await session.scalars(select(ConsentRecord))) == []


async def test_reaccept_rejects_a_stale_policy_version(
    client: AsyncClient,
) -> None:
    guest = await _create_guest(client)
    logged_in = await _otp_login(client, guest)
    response = await client.post(
        "/api/v1/auth/consents",
        headers={"X-CSRF-Token": logged_in["csrf_token"]},
        json={
            "policy_key": "privacy",
            "policy_version": "old-policy-v0.0",
            "context": "reaccept",
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Policy version is not current"


async def test_password_login_rejects_when_current_policy_consent_is_missing(
    client: AsyncClient,
) -> None:
    first_guest = await _create_guest(client)
    first_session = await _otp_login(client, first_guest, destination="13800138001")
    set_password = await client.put(
        "/api/v1/auth/password",
        headers={"X-CSRF-Token": first_session["csrf_token"]},
        json={"password": "correct-password"},
    )
    assert set_password.status_code == 204, set_password.text
    await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": first_session["csrf_token"]},
    )

    second_guest = await _create_guest(client)
    logged_in = await client.post(
        "/api/v1/auth/password/login",
        headers=second_guest,
        json={
            "channel": "phone",
            "destination": "13800138001",
            "password": "correct-password",
        },
    )
    assert logged_in.status_code == 400, logged_in.text
    assert logged_in.json()["title"] == "Policy version is not current"


async def test_password_login_rejects_stale_registration_consent(
    client: AsyncClient,
    database: Any,
) -> None:
    guest = await _create_guest(client)
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=guest,
        json={"channel": "email", "destination": "stale-login@example.com"},
    )
    assert requested.status_code == 202, requested.text
    registered = await client.post(
        "/api/v1/auth/register",
        headers=guest,
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": "246810",
            "password": "correct-password",
            "policy_version": CURRENT_POLICY_VERSION,
        },
    )
    assert registered.status_code == 200, registered.text
    await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": registered.json()["csrf_token"]},
    )

    async with database.sessions() as session:
        consents = list(await session.scalars(select(ConsentRecord)))
        for record in consents:
            record.policy_version = "old-policy-v0.0"
        await session.commit()

    second_guest = await _create_guest(client)
    logged_in = await client.post(
        "/api/v1/auth/password/login",
        headers=second_guest,
        json={
            "channel": "email",
            "destination": "stale-login@example.com",
            "password": "correct-password",
        },
    )
    assert logged_in.status_code == 400, logged_in.text
    assert logged_in.json()["title"] == "Policy version is not current"


async def test_otp_verify_existing_user_rejects_stale_policy_consent(
    client: AsyncClient,
    database: Any,
) -> None:
    guest = await _create_guest(client)
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=guest,
        json={"channel": "email", "destination": "stale-otp@example.com"},
    )
    assert requested.status_code == 202, requested.text
    registered = await client.post(
        "/api/v1/auth/register",
        headers=guest,
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": "246810",
            "password": "correct-password",
            "policy_version": CURRENT_POLICY_VERSION,
        },
    )
    assert registered.status_code == 200, registered.text
    await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": registered.json()["csrf_token"]},
    )

    async with database.sessions() as session:
        consents = list(await session.scalars(select(ConsentRecord)))
        for record in consents:
            record.policy_version = "old-policy-v0.0"
        await session.commit()

    second_guest = await _create_guest(client)
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=second_guest,
        json={"channel": "email", "destination": "stale-otp@example.com"},
    )
    assert requested.status_code == 202, requested.text
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers=second_guest,
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": "246810",
        },
    )
    assert verified.status_code == 400, verified.text
    assert verified.json()["title"] == "Policy version is not current"
    async with database.sessions() as session:
        sessions = list(await session.scalars(select(DeviceSession)))
        assert all(item.revoked_at is not None for item in sessions)
        assert len(sessions) == 1
        consents = list(await session.scalars(select(ConsentRecord)))
        assert {record.policy_version for record in consents} == {"old-policy-v0.0"}
        for record in consents:
            record.policy_version = CURRENT_POLICY_VERSION
        await session.commit()

    retry = await client.post(
        "/api/v1/auth/otp/verify",
        headers=second_guest,
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": "246810",
        },
    )
    assert retry.status_code == 200, retry.text
