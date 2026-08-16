from app.admin.models import StaffUser
from app.readings.capability_policy import (
    P0_EXPOSED_CAPABILITY_IDS,
    V53_TIME_CHECK_RELEASE_CAPABILITY_IDS,
)
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_capabilities_exposes_policy_without_claiming_runtime_health(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/admin/capabilities?limit=100",
        headers=await _admin_headers(client),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["environment"] == "test"
    assert payload["runtime_adapter"] == "fake"
    assert [item["capability_id"] for item in payload["capabilities"]] == list(
        V53_TIME_CHECK_RELEASE_CAPABILITY_IDS
    )
    states = {
        item["capability_id"]: item["release_state"] for item in payload["capabilities"]
    }
    assert {key for key, value in states.items() if value == "PUBLIC"} == set(
        P0_EXPOSED_CAPABILITY_IDS
    )
    assert states["physiognomy"] == "INTERNAL_TEST"
    assert states["time-check"] == "INTERNAL_TEST"
    assert "time_check_preview" in next(
        item["product_actions"]
        for item in payload["capabilities"]
        if item["capability_id"] == "time-check"
    )
    assert payload["runtime_health"] == "unverified"
    assert payload["production_ready"] is False
    assert "api_key" not in response.text
    assert "secret" not in response.text.lower()


async def test_admin_capabilities_forbids_finance_staff(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "finance"
        await session.commit()

    response = await client.get("/api/v1/admin/capabilities", headers=headers)

    assert response.status_code == 403
