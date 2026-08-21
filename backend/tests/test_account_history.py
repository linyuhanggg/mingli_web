from typing import Any
from uuid import UUID

from app.identity.models import User
from app.readings.models import ReadingVersion
from app.security.envelope import EnvelopeCipher
from httpx import AsyncClient

from test_profiles_api import create_confirmed_profile, create_guest, login_current_guest
from test_readings_api import advance_to_accepted, seed_runtime_release, start_preview


async def test_account_history_groups_versions_and_keeps_other_users_out(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    logged_in = await login_current_guest(
        client,
        headers,
        destination="13800138000",
    )
    headers = {"X-CSRF-Token": logged_in["csrf_token"]}
    await seed_runtime_release(database, test_settings)

    started = await start_preview(
        client,
        headers,
        confirmed["profile_version_id"],
        idempotency_key="account-history-base",
    )
    await advance_to_accepted(
        database,
        test_settings,
        version_id=started["reading_version_id"],
        subject_ref=f"profile-version:{confirmed['profile_version_id']}",
    )
    followed = await client.post(
        f"/api/v1/readings/{started['reading_version_id']}/follow-up",
        headers={**headers, "Idempotency-Key": "account-history-follow-up"},
        json={},
    )
    assert followed.status_code == 201, followed.text

    async with database.sessions() as session:
        first_version = await session.get(
            ReadingVersion,
            UUID(started["reading_version_id"]),
        )
        assert first_version is not None
        other_user = User()
        session.add(other_user)
        await session.flush()
        repository_module = __import__(
            "app.readings.repository",
            fromlist=["SqlReadingRepository"],
        )
        repository = repository_module.SqlReadingRepository(
            session,
            EnvelopeCipher.from_settings(test_settings),
        )
        other_root = await repository.create_root(
            capability_id=first_version.capability_id,
            owner_user_id=other_user.id,
        )
        await repository.create_version(
            reading_root_id=other_root.id,
            runtime_release_id=first_version.runtime_release_id,
            prepare_command=await repository.load_prepare(first_version.id),
        )
        await session.commit()

    response = await client.get("/api/v1/account/history")

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store, max-age=0"
    body = response.json()
    assert set(body) == {"roots"}
    assert len(body["roots"]) == 1
    root = body["roots"][0]
    assert root["reading_root_id"] == started["reading_root_id"]
    assert [item["version"] for item in root["versions"]] == [2, 1]
    assert {item["reading_root_id"] for item in root["versions"]} == {
        started["reading_root_id"]
    }
    assert "prior_answer" not in response.text
    assert "input_request" not in response.text
    assert str(other_user.id) not in response.text


async def test_account_history_requires_a_verified_device(client: AsyncClient) -> None:
    response = await client.get("/api/v1/account/history")

    assert response.status_code == 401
