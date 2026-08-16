from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.admin.models import StaffUser
from app.readings.models import RuntimeRelease
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_runtime_lists_safe_release_metadata(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    release = RuntimeRelease(
        id=uuid4(),
        name="mingli-runtime",
        version="2026.08.14",
        source_commit="source-commit",
        release_manifest_digest="manifest-secret-like",
        protocol_version="reading-runtime-v1",
        describe_manifest_digest="describe-secret-like",
        image_digest="image-secret-like",
        production_ready=True,
        created_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    async with database.sessions() as session:
        session.add(release)
        await session.commit()

    response = await client.get(
        "/api/v1/admin/runtime-releases?limit=100",
        headers=await _admin_headers(client),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["releases"][0] == {
        "id": str(release.id),
        "name": "mingli-runtime",
        "version": "2026.08.14",
        "source_commit": "source-commit",
        "protocol_version": "reading-runtime-v1",
        "production_ready": True,
        "created_at": payload["releases"][0]["created_at"],
    }
    assert "manifest-secret-like" not in response.text
    assert "image-secret-like" not in response.text


async def test_admin_runtime_forbids_non_operations_staff(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()

    response = await client.get("/api/v1/admin/runtime-releases", headers=headers)

    assert response.status_code == 403
