from app.admin.models import StaffUser
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_settings_returns_safe_runtime_flags_without_secrets(
    client: AsyncClient,
) -> None:
    await _admin_headers(client)

    response = await client.get("/api/v1/admin/settings")

    assert response.status_code == 200, response.text
    assert response.json()["environment"] == "test"
    assert response.json()["otp_adapter"] == "fake"
    assert response.json()["runtime_adapter"] == "fake"
    assert response.json()["runtime_release_profile"] == "v51"
    assert "database_url" not in response.text
    assert "identity_hash_key" not in response.text


async def test_admin_settings_forbids_support(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    response = await client.get("/api/v1/admin/settings")

    assert response.status_code == 403
