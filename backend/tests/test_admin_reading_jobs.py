from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.admin.models import StaffUser
from app.identity.models import GuestSession
from app.readings.models import ReadingJobRecord, ReadingRoot, ReadingVersion, RuntimeRelease
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_reading_jobs_lists_safe_metadata_and_keeps_finance_out(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    now = datetime.now(UTC)
    guest = GuestSession(
        id=uuid4(),
        token_hash="g" * 64,
        csrf_token_hash="c" * 64,
        expires_at=now + timedelta(hours=2),
    )
    release = RuntimeRelease(
        id=uuid4(),
        name="test-runtime",
        version="1.0",
        source_commit="source-commit",
        release_manifest_digest="manifest-digest",
        protocol_version="protocol-v1",
        describe_manifest_digest="describe-digest",
        production_ready=False,
    )
    root = ReadingRoot(
        id=uuid4(),
        owner_guest_session_id=guest.id,
        capability_id="bazi",
    )
    version = ReadingVersion(
        id=uuid4(),
        reading_root_id=root.id,
        runtime_release_id=release.id,
        version=1,
        status="input_ready",
        capability_id="bazi",
        object_id="natal",
        dimension_ids=["career"],
        horizon={"kind_id": "natal", "start": None, "end": None},
        prepare_key_id="prepare-key",
        prepare_nonce="prepare-nonce",
        prepare_ciphertext="encrypted-birth-data",
        prepare_digest="prepare-digest",
    )
    job = ReadingJobRecord(
        id=uuid4(),
        reading_version_id=version.id,
        status="queued",
        narrative_policy_version="narrative-v1",
        output_contract={"schema": "reading-document/v1"},
        language="zh-CN",
        max_output_chars=12000,
        max_attempts=3,
        available_at=now,
    )
    async with database.sessions() as session:
        session.add_all([guest, release, root, version, job])
        await session.commit()

    headers = await _admin_headers(client)
    listed = await client.get("/api/v1/admin/reading-jobs", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["jobs"][0]["id"] == str(job.id)
    assert listed.json()["jobs"][0]["job_status"] == "queued"
    assert listed.json()["jobs"][0]["capability_id"] == "bazi"
    assert "encrypted-birth-data" not in listed.text
    assert "output_contract" not in listed.text
    assert "lease_token" not in listed.text

    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        await session.commit()
    assert (await client.get("/api/v1/admin/reading-jobs")).status_code == 200

    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "finance"
        await session.commit()
    assert (await client.get("/api/v1/admin/reading-jobs")).status_code == 403
