"""Dogfood entitlement gates and daily ceilings."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from test_profiles_api import create_confirmed_profile, create_guest, login_current_guest
from test_readings_api import advance_to_accepted, seed_runtime_release, start_preview


@pytest.fixture
def dogfood_settings(test_settings: Any):  # type: ignore[no-untyped-def]
    return test_settings.model_copy(
        update={
            "dogfood_entitlement_gates_enabled": True,
            "dogfood_daily_reading_limit": 10,
            "dogfood_daily_paid_reading_limit": 6,
        }
    )


@pytest.fixture
async def dogfood_client(database: Any, dogfood_settings: Any) -> Any:
    main = __import__("app.main", fromlist=["create_app"])
    application = main.create_app(settings=dogfood_settings, database=database)
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as http_client:
        yield http_client


async def _login(client: AsyncClient) -> tuple[dict[str, str], str]:
    headers = await create_guest(client)
    session = await login_current_guest(client, headers, destination="13900139000")
    csrf = session["csrf_token"]
    return {"X-CSRF-Token": csrf}, str(session["user_id"])


async def test_preview_stays_open_without_grant(
    dogfood_client: AsyncClient,
    database: Any,
    dogfood_settings: Any,
) -> None:
    headers, _user_id = await _login(dogfood_client)
    confirmed = await create_confirmed_profile(dogfood_client, headers)
    await seed_runtime_release(database, dogfood_settings)

    response = await dogfood_client.post(
        "/api/v1/readings/preview",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    assert response.status_code == 201, response.text


async def test_today_denied_without_grant(
    dogfood_client: AsyncClient,
    database: Any,
    dogfood_settings: Any,
) -> None:
    headers, _user_id = await _login(dogfood_client)
    confirmed = await create_confirmed_profile(dogfood_client, headers)
    await seed_runtime_release(database, dogfood_settings)

    response = await dogfood_client.post(
        "/api/v1/readings/today",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    assert response.status_code == 403, response.text
    assert response.json()["title"] == "Paid reading not granted"


async def test_recast_week_denied_without_week_grant(
    dogfood_client: AsyncClient,
    database: Any,
    dogfood_settings: Any,
) -> None:
    headers, _user_id = await _login(dogfood_client)
    confirmed = await create_confirmed_profile(dogfood_client, headers)
    await seed_runtime_release(database, dogfood_settings)
    source = await start_preview(
        dogfood_client,
        headers,
        confirmed["profile_version_id"],
        idempotency_key="dogfood-recast-source",
    )
    await advance_to_accepted(
        database,
        dogfood_settings,
        version_id=source["reading_version_id"],
        subject_ref=f"profile-version:{confirmed['profile_version_id']}",
    )

    response = await dogfood_client.post(
        f"/api/v1/readings/{source['reading_version_id']}/recast",
        headers={**headers, "Idempotency-Key": "dogfood-recast-week"},
        json={
            "action": "week",
            "profile_version_id": confirmed["profile_version_id"],
        },
    )

    assert response.status_code == 403, response.text
    assert response.json()["title"] == "Paid reading not granted"


async def test_today_allowed_after_grant(
    dogfood_client: AsyncClient,
    database: Any,
    dogfood_settings: Any,
) -> None:
    headers, user_id = await _login(dogfood_client)
    confirmed = await create_confirmed_profile(dogfood_client, headers)
    await seed_runtime_release(database, dogfood_settings)

    from app.entitlements.service import EntitlementService

    async with database.sessions() as session:
        service = EntitlementService(session, dogfood_settings)
        await service.grant_capabilities(
            owner_user_id=UUID(user_id),
            capability_ids=["today"],
            granted_by="test",
        )
        await session.commit()

    response = await dogfood_client.post(
        "/api/v1/readings/today",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    assert response.status_code == 201, response.text


async def test_daily_paid_limit_returns_429(
    database: Any,
    test_settings: Any,
) -> None:
    settings = test_settings.model_copy(
        update={
            "dogfood_entitlement_gates_enabled": True,
            "dogfood_daily_reading_limit": 10,
            "dogfood_daily_paid_reading_limit": 1,
        }
    )
    main = __import__("app.main", fromlist=["create_app"])
    application = main.create_app(settings=settings, database=database)
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as client:
        headers, user_id = await _login(client)
        confirmed = await create_confirmed_profile(client, headers)
        await seed_runtime_release(database, settings)
        from app.entitlements.service import EntitlementService

        async with database.sessions() as session:
            service = EntitlementService(session, settings)
            await service.grant_capabilities(
                owner_user_id=UUID(user_id),
                capability_ids=["today", "week"],
                granted_by="test",
            )
            await session.commit()

        first = await client.post(
            "/api/v1/readings/today",
            headers=headers,
            json={"profile_version_id": confirmed["profile_version_id"]},
        )
        second = await client.post(
            "/api/v1/readings/week",
            headers=headers,
            json={"profile_version_id": confirmed["profile_version_id"]},
        )
        assert first.status_code == 201, first.text
        assert second.status_code == 429, second.text
        assert second.json()["title"] == "Daily paid reading limit reached"
