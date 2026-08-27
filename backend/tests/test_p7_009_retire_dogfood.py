"""P7-009: formal ledger GRANT takes over; dogfood is only the no-GRANT path."""

from __future__ import annotations

import importlib
import os
from typing import Any
from uuid import UUID

import pytest
from app.commerce.service import CommerceService
from app.entitlements.models import OwnerCapabilityGrant
from app.entitlements.service import formal_capability_entitlement_id
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from test_profiles_api import create_confirmed_profile, create_guest, login_current_guest
from test_readings_api import seed_runtime_release


@pytest.fixture
def p7_009_settings(monkeypatch: pytest.MonkeyPatch) -> Any:
    for key in [name for name in os.environ if name.startswith("MINGLI_")]:
        monkeypatch.delenv(key, raising=False)
    config = importlib.import_module("app.config")
    return config.Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="fake",
        admin_bootstrap_email="ops@example.com",
        admin_bootstrap_password="correct-horse",
        dogfood_entitlement_gates_enabled=True,
        dogfood_daily_reading_limit=10,
        dogfood_daily_paid_reading_limit=6,
    )


@pytest.fixture
async def p7_009_client(database: Any, p7_009_settings: Any) -> Any:
    main = importlib.import_module("app.main")
    application = main.create_app(settings=p7_009_settings, database=database)
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as http_client:
        yield http_client


async def _login(client: AsyncClient) -> tuple[dict[str, str], str]:
    headers = await create_guest(client)
    session = await login_current_guest(client, headers, destination="13900139009")
    return {"X-CSRF-Token": session["csrf_token"]}, str(session["user_id"])


async def _grant_formal(
    database: Any,
    *,
    owner_user_id: str,
    capability_id: str,
    source_ref: str,
) -> None:
    async with database.sessions() as session:
        commerce = CommerceService(session)
        await commerce.append_entitlement_event(
            owner_user_id=UUID(owner_user_id),
            entitlement_id=formal_capability_entitlement_id(capability_id),
            kind="GRANT",
            quantity=1,
            source_type="admin_grant",
            source_ref=source_ref,
            target_ref=capability_id,
        )
        await session.commit()


async def _consume_formal(
    database: Any,
    *,
    owner_user_id: str,
    capability_id: str,
    source_ref: str,
) -> None:
    async with database.sessions() as session:
        commerce = CommerceService(session)
        entitlement_id = formal_capability_entitlement_id(capability_id)
        await commerce.append_entitlement_event(
            owner_user_id=UUID(owner_user_id),
            entitlement_id=entitlement_id,
            kind="RESERVE",
            quantity=1,
            source_type="fulfillment",
            source_ref=f"{source_ref}:reserve",
            target_ref=capability_id,
        )
        await commerce.append_entitlement_event(
            owner_user_id=UUID(owner_user_id),
            entitlement_id=entitlement_id,
            kind="CONSUME",
            quantity=1,
            source_type="fulfillment",
            source_ref=f"{source_ref}:consume",
            target_ref=capability_id,
        )
        await session.commit()


async def test_without_formal_grant_preview_stays_open_today_and_week_denied(
    p7_009_client: AsyncClient,
    database: Any,
    p7_009_settings: Any,
) -> None:
    headers, _user_id = await _login(p7_009_client)
    confirmed = await create_confirmed_profile(p7_009_client, headers)
    await seed_runtime_release(database, p7_009_settings)

    preview = await p7_009_client.post(
        "/api/v1/readings/preview",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    today = await p7_009_client.post(
        "/api/v1/readings/today",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    week = await p7_009_client.post(
        "/api/v1/readings/week",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )

    assert preview.status_code == 201, preview.text
    assert today.status_code == 403, today.text
    assert today.json()["title"] == "Paid reading not granted"
    assert week.status_code == 403, week.text
    assert week.json()["title"] == "Paid reading not granted"


async def test_formal_today_grant_skips_dogfood_and_does_not_open_week(
    p7_009_client: AsyncClient,
    database: Any,
    p7_009_settings: Any,
) -> None:
    headers, user_id = await _login(p7_009_client)
    confirmed = await create_confirmed_profile(p7_009_client, headers)
    await seed_runtime_release(database, p7_009_settings)
    await _grant_formal(
        database,
        owner_user_id=user_id,
        capability_id="today",
        source_ref="p7-009-today-grant",
    )

    today = await p7_009_client.post(
        "/api/v1/readings/today",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    week = await p7_009_client.post(
        "/api/v1/readings/week",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )

    assert today.status_code == 201, today.text
    assert week.status_code == 403, week.text
    assert week.json()["title"] == "Paid reading not granted"

    async with database.sessions() as session:
        dogfood_count = await session.scalar(select(func.count()).select_from(OwnerCapabilityGrant))
    assert dogfood_count == 0


async def test_consumed_formal_grant_falls_back_to_dogfood_deny(
    p7_009_client: AsyncClient,
    database: Any,
    p7_009_settings: Any,
) -> None:
    headers, user_id = await _login(p7_009_client)
    confirmed = await create_confirmed_profile(p7_009_client, headers)
    await seed_runtime_release(database, p7_009_settings)
    await _grant_formal(
        database,
        owner_user_id=user_id,
        capability_id="today",
        source_ref="p7-009-today-consumed",
    )
    await _consume_formal(
        database,
        owner_user_id=user_id,
        capability_id="today",
        source_ref="p7-009-today-consumed",
    )

    today = await p7_009_client.post(
        "/api/v1/readings/today",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )
    preview = await p7_009_client.post(
        "/api/v1/readings/preview",
        headers=headers,
        json={"profile_version_id": confirmed["profile_version_id"]},
    )

    assert today.status_code == 403, today.text
    assert today.json()["title"] == "Paid reading not granted"
    assert preview.status_code == 201, preview.text
