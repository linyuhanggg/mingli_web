from typing import Any
from uuid import UUID

import pytest
from app.adapters.otp import OtpDeliveryUnavailable
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


async def create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def request_otp(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    channel: str = "phone",
    destination: str = "13800138000",
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": channel, "destination": destination},
    )
    assert response.status_code == 202, response.text
    return response.json()


async def verify_otp(
    client: AsyncClient,
    headers: dict[str, str],
    challenge_id: str,
    code: str = "246810",
):  # type: ignore[no-untyped-def]
    return await client.post(
        "/api/v1/auth/otp/verify",
        headers=headers,
        json={"challenge_id": challenge_id, "code": code},
    )


async def login_with_phone(client: AsyncClient) -> tuple[dict[str, Any], dict[str, str]]:
    headers = await create_guest(client)
    challenge = await request_otp(client, headers)
    response = await verify_otp(client, headers, challenge["challenge_id"])
    assert response.status_code == 200, response.text
    return response.json(), {"X-CSRF-Token": response.json()["csrf_token"]}


async def test_verified_phone_otp_creates_user_identity_and_device_session(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)
    challenge = await request_otp(client, headers)

    assert challenge["development_code"] == "246810"
    verified = await verify_otp(client, headers, challenge["challenge_id"])

    assert verified.status_code == 200
    body = verified.json()
    UUID(body["user_id"])
    UUID(body["session_id"])
    session_cookie = next(
        value
        for value in verified.headers.get_list("set-cookie")
        if value.startswith("mingli_session=")
    )
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=lax" in session_cookie
    assert "Max-Age=2592000" in session_cookie

    account = await client.get("/api/v1/account")
    assert account.status_code == 200
    assert account.json() == {
        "user_id": body["user_id"],
        "identities": [
            {
                "id": account.json()["identities"][0]["id"],
                "provider": "phone",
                "masked_destination": "+86 138****8000",
                "verified_at": account.json()["identities"][0]["verified_at"],
            }
        ],
    }


async def test_repeat_login_resolves_the_same_user(
    client: AsyncClient,
    database: Any,
) -> None:
    first, csrf_headers = await login_with_phone(client)
    logout = await client.post("/api/v1/auth/logout", headers=csrf_headers)
    assert logout.status_code == 204

    second_headers = await create_guest(client)
    challenge = await request_otp(client, second_headers)
    second = await verify_otp(client, second_headers, challenge["challenge_id"])

    assert second.status_code == 200
    assert second.json()["user_id"] == first["user_id"]

    models = __import__("app.identity.models", fromlist=["User", "LoginIdentity", "DeviceSession"])
    async with database.sessions() as session:
        users = list(await session.scalars(select(models.User)))
        identities = list(await session.scalars(select(models.LoginIdentity)))
        device_sessions = list(await session.scalars(select(models.DeviceSession)))

    assert len(users) == 1
    assert len(identities) == 1
    assert len(device_sessions) == 2
    assert sum(item.revoked_at is not None for item in device_sessions) == 1


async def test_email_is_normalized_and_raw_destination_is_not_persisted(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    challenge = await request_otp(
        client,
        headers,
        channel="email",
        destination="  Cherry@Example.COM ",
    )
    response = await verify_otp(client, headers, challenge["challenge_id"])
    assert response.status_code == 200

    models = __import__("app.identity.models", fromlist=["LoginIdentity", "AuditEvent"])
    async with database.sessions() as session:
        identity = (await session.scalars(select(models.LoginIdentity))).one()
        audit = (await session.scalars(select(models.AuditEvent))).one()

    assert identity.provider == "email"
    assert identity.masked_destination == "c***@example.com"
    assert len(identity.provider_subject_hash) == 64
    assert "cherry@example.com" not in identity.provider_subject_hash
    assert "Cherry@Example.COM" not in str(audit.event_metadata)


async def test_invalid_code_does_not_create_a_user(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    challenge = await request_otp(client, headers)
    response = await verify_otp(client, headers, challenge["challenge_id"], "111111")

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid or expired code"

    models = __import__("app.identity.models", fromlist=["User"])
    async with database.sessions() as session:
        users = list(await session.scalars(select(models.User)))
    assert users == []


async def test_request_rate_limit_is_generic(client: AsyncClient) -> None:
    headers = await create_guest(client)
    first = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": "phone", "destination": "13800138000"},
    )
    second = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": "phone", "destination": "13800138000"},
    )

    assert first.status_code == 202
    assert second.status_code == 429
    assert second.json()["title"] == "Please wait before requesting another code"


async def test_logout_revokes_the_current_device_session(
    client: AsyncClient,
) -> None:
    _, csrf_headers = await login_with_phone(client)

    logout = await client.post("/api/v1/auth/logout", headers=csrf_headers)
    account = await client.get("/api/v1/account")

    assert logout.status_code == 204
    assert "Max-Age=0" in "\n".join(logout.headers.get_list("set-cookie"))
    assert account.status_code == 401


async def test_account_requires_a_device_session(client: AsyncClient) -> None:
    response = await client.get("/api/v1/account")

    assert response.status_code == 401
    assert response.json()["title"] == "Authentication required"


async def test_nonlocal_fake_response_omits_the_development_code(database: Any) -> None:
    config = __import__("app.config", fromlist=["Settings"])
    main = __import__("app.main", fromlist=["create_app"])
    settings = config.Settings(
        environment="staging",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="fake",
    )
    application = main.create_app(settings=settings, database=database)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as staging_client:
        headers = await create_guest(staging_client)
        response = await staging_client.post(
            "/api/v1/auth/otp/request",
            headers=headers,
            json={"channel": "phone", "destination": "13900139000"},
        )

    assert response.status_code == 202
    assert "development_code" not in response.json()


async def test_otp_requests_are_limited_across_destinations_for_one_guest(
    database: Any,
) -> None:
    config = __import__("app.config", fromlist=["Settings"])
    main = __import__("app.main", fromlist=["create_app"])
    settings = config.Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="fake",
        otp_guest_window_limit=2,
        otp_network_window_limit=10,
    )
    application = main.create_app(settings=settings, database=database)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as limited_client:
        headers = await create_guest(limited_client)
        responses = [
            await limited_client.post(
                "/api/v1/auth/otp/request",
                headers=headers,
                json={"channel": "phone", "destination": destination},
            )
            for destination in ("13800138000", "13900139000", "13700137000")
        ]

    assert [response.status_code for response in responses] == [202, 202, 429]


async def test_otp_requests_are_limited_across_rotating_guest_sessions(
    database: Any,
) -> None:
    config = __import__("app.config", fromlist=["Settings"])
    main = __import__("app.main", fromlist=["create_app"])
    settings = config.Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="fake",
        otp_guest_window_limit=10,
        otp_network_window_limit=2,
    )
    application = main.create_app(settings=settings, database=database)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as limited_client:
        responses = []
        for destination in ("13800138000", "13900139000", "13700137000"):
            headers = await create_guest(limited_client)
            responses.append(
                await limited_client.post(
                    "/api/v1/auth/otp/request",
                    headers=headers,
                    json={"channel": "phone", "destination": destination},
                )
            )

    assert [response.status_code for response in responses] == [202, 202, 429]


async def test_network_limiter_distinguishes_clients_behind_trusted_proxies(
    database: Any,
) -> None:
    config = __import__("app.config", fromlist=["Settings"])
    main = __import__("app.main", fromlist=["create_app"])
    settings = config.Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="fake",
        otp_guest_window_limit=10,
        otp_network_window_limit=2,
        trusted_proxy_cidrs="127.0.0.0/8,10.0.0.0/8",
    )
    application = main.create_app(settings=settings, database=database)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as limited_client:
        csrf_headers = await create_guest(limited_client)
        cases = (
            ("203.0.113.10, 10.2.0.4", "13800138000"),
            ("203.0.113.10, 10.2.0.4", "13900139000"),
            ("203.0.113.11, 10.2.0.4", "13700137000"),
            ("203.0.113.10, 10.2.0.4", "13600136000"),
        )
        responses = [
            await limited_client.post(
                "/api/v1/auth/otp/request",
                headers={**csrf_headers, "X-Forwarded-For": forwarded_for},
                json={"channel": "phone", "destination": destination},
            )
            for forwarded_for, destination in cases
        ]

    assert [response.status_code for response in responses] == [202, 202, 202, 429]


async def test_production_otp_delivery_fails_closed_with_durable_store_message(
    database: Any,
) -> None:
    config = __import__("app.config", fromlist=["Settings"])
    main = __import__("app.main", fromlist=["create_app"])
    settings = config.Settings(
        environment="production",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="disabled",
        identity_hash_key="production-identity-key",
        content_encryption_key_b64="eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg=",
        content_encryption_key_id="production-content-v1",
        runtime_adapter="one-shot",
        runtime_launcher_path="/opt/mingli-master/scripts/run_reading_transaction.sh",
        runtime_python_path="/opt/mingli-runtime/venv/bin/python",
        runtime_release_root="/opt/mingli-master",
        runtime_state_root="/var/lib/mingli",
        runtime_expected_manifest_digest=(
            "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
        ),
        runtime_expected_capability_shape_sha256=(
            "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
        ),
        model_adapter="deepseek",
        deepseek_api_key="test-only-obviously-not-a-real-key",
        model_price_snapshot_version="fixture-price-v1",
        model_input_price_microunits_per_million_tokens=1,
        model_output_price_microunits_per_million_tokens=1,
    )
    application = main.create_app(settings=settings, database=database)

    with pytest.raises(OtpDeliveryUnavailable, match="durable challenge store"):
        await application.state.otp_delivery.deliver(
            channel="email",
            destination="someone@example.com",
            code="246810",
        )


async def test_non_fake_app_emits_random_six_digit_codes(database: Any) -> None:
    config = __import__("app.config", fromlist=["Settings"])
    main = __import__("app.main", fromlist=["create_app"])
    settings = config.Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="disabled",
    )
    application = main.create_app(settings=settings, database=database)
    factory = application.state.otp_code_factory

    code = factory()

    assert factory is main.random_six_digit_otp_code
    assert len(code) == 6
    assert code.isdigit()


class _FlakyOtpDelivery:
    """Fails the first delivery attempt, then records later deliveries."""

    def __init__(self) -> None:
        self.fail_times = 1
        self.deliveries: list[tuple[str, str, str]] = []

    async def deliver(self, *, channel: str, destination: str, code: str) -> None:
        if self.fail_times > 0:
            self.fail_times -= 1
            raise OtpDeliveryUnavailable("vendor unavailable")
        self.deliveries.append((channel, destination, code))


class _AlwaysFailingOtpDelivery:
    async def deliver(self, *, channel: str, destination: str, code: str) -> None:
        del channel, destination, code
        raise OtpDeliveryUnavailable("vendor unavailable")


async def test_failed_delivery_releases_challenge_and_cooldown_for_immediate_retry(
    database: Any,
) -> None:
    config = __import__("app.config", fromlist=["Settings"])
    main = __import__("app.main", fromlist=["create_app"])
    settings = config.Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="fake",
    )
    application = main.create_app(settings=settings, database=database)
    flaky = _FlakyOtpDelivery()
    application.state.otp_delivery = flaky

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as limited_client:
        headers = await create_guest(limited_client)
        failed = await limited_client.post(
            "/api/v1/auth/otp/request",
            headers=headers,
            json={"channel": "email", "destination": "retry@example.com"},
        )
        assert failed.status_code == 503
        assert failed.json()["title"] == "OTP delivery unavailable"
        # The failed attempt must not leave an orphaned challenge behind.
        assert application.state.otp_challenge_store._challenges == {}

        # The cooldown claim of the failed challenge is gone, so the retry
        # succeeds immediately instead of waiting out the cooldown window.
        retried = await limited_client.post(
            "/api/v1/auth/otp/request",
            headers=headers,
            json={"channel": "email", "destination": "retry@example.com"},
        )
        assert retried.status_code == 202
        verified = await verify_otp(limited_client, headers, retried.json()["challenge_id"])
        assert verified.status_code == 200

    assert flaky.deliveries == [("email", "retry@example.com", "246810")]


async def test_otp_destination_window_limits_across_guests_without_storing_raw_destination(
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
        otp_destination_window_limit=2,
    )
    application = main.create_app(settings=settings, database=database)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as limited_client:
        responses = []
        for _ in range(3):
            headers = await create_guest(limited_client)
            responses.append(
                await limited_client.post(
                    "/api/v1/auth/otp/request",
                    headers=headers,
                    json={"channel": "phone", "destination": "13800138000"},
                )
            )

    assert [response.status_code for response in responses] == [202, 202, 429]
    assert responses[2].json()["title"] == "Please wait before requesting another code"
    # The rolling window is keyed by a destination hash, never the raw address.
    limiter_state = str(application.state.otp_request_limiter._destination_windows)
    assert "13800138000" not in limiter_state


async def test_delivery_failures_keep_network_limit_but_free_guest_and_destination_slots(
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
        otp_guest_window_limit=3,
        otp_network_window_limit=3,
        otp_destination_window_limit=3,
    )
    application = main.create_app(settings=settings, database=database)
    application.state.otp_delivery = _AlwaysFailingOtpDelivery()

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as limited_client:
        responses = []
        for _ in range(5):
            headers = await create_guest(limited_client)
            responses.append(
                await limited_client.post(
                    "/api/v1/auth/otp/request",
                    headers=headers,
                    json={"channel": "phone", "destination": "13800138000"},
                )
            )

    # The first three failures consume the network window (delivery never
    # happened, so the provider-outage protection must stay); the fourth and
    # fifth requests are rejected by the per-IP limit before delivery is tried.
    assert [response.status_code for response in responses] == [503, 503, 503, 429, 429]
    assert all(response.json()["title"] == "OTP delivery unavailable" for response in responses[:3])
    assert all(
        response.json()["title"] == "Please wait before requesting another code"
        for response in responses[3:]
    )
    # Guest and destination windows are rolled back after each failure...
    limiter = application.state.otp_request_limiter
    assert limiter._guest_windows == {}
    assert limiter._destination_windows == {}
    # ...while the network window still holds the three failed attempts.
    assert [window.count for window in limiter._network_windows.values()] == [3]
    assert application.state.otp_challenge_store._challenges == {}
