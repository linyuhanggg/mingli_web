from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.admin.models import StaffUser
from app.identity.models import GuestSession
from app.readings.models import (
    ClaimVerificationEvent,
    ReadingJobRecord,
    ReadingRoot,
    ReadingVerification,
    ReadingVersion,
    ReportFeedback,
    RuntimeRelease,
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


async def test_admin_readings_lists_safe_versions_and_forbids_finance(
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
        status="accepted",
        capability_id="bazi",
        product_id="hecan",
        object_id="natal",
        dimension_ids=["career", "relationship"],
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
    reading_verification = ReadingVerification(
        id=uuid4(),
        reading_version_id=version.id,
        outcome="partial",
        note="private reading note",
    )
    claim_event = ClaimVerificationEvent(
        id=uuid4(),
        reading_version_id=version.id,
        claim_id="claim:career",
        actor_ref="user-1",
        outcome="accepted",
        note="private claim note",
    )
    feedback = ReportFeedback(
        id=uuid4(),
        reading_version_id=version.id,
        actor_ref="user-1",
        outcome="helpful",
        note="private feedback note",
    )
    async with database.sessions() as session:
        session.add_all(
            [
                guest,
                release,
                root,
                version,
                job,
                reading_verification,
                claim_event,
                feedback,
            ]
        )
        await session.commit()

    headers = await _admin_headers(client)
    listed = await client.get("/api/v1/admin/readings", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["readings"][0]["reading_version_id"] == str(version.id)
    assert listed.json()["readings"][0]["dimension_count"] == 2
    assert listed.json()["readings"][0]["status"] == "accepted"
    assert listed.json()["readings"][0]["product_id"] == "hecan"
    assert "encrypted-birth-data" not in listed.text
    assert "natal" not in listed.text
    assert "horizon" not in listed.text

    detail = await client.get(
        f"/api/v1/admin/readings/{version.id}",
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["reading_version_id"] == str(version.id)
    assert detail.json()["product_id"] == "hecan"
    assert detail.json()["job_count"] == 1
    assert detail.json()["verification_event_count"] == 3
    assert detail.json()["document_available"] is False
    assert "private reading note" not in detail.text
    assert "output_contract" not in detail.text

    jobs = await client.get("/api/v1/admin/reading-jobs", headers=headers)
    assert jobs.status_code == 200, jobs.text
    assert jobs.json()["jobs"][0]["product_id"] == "hecan"

    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "finance"
        await session.commit()
    assert (await client.get("/api/v1/admin/readings")).status_code == 403
