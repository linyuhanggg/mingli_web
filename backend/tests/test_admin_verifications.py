from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.admin.models import StaffUser
from app.identity.models import GuestSession
from app.readings.models import (
    ClaimVerificationEvent,
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


async def test_admin_verifications_merges_safe_events_and_forbids_finance(
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
        object_id="natal",
        dimension_ids=["career"],
        horizon={"kind_id": "natal", "start": None, "end": None},
        prepare_key_id="prepare-key",
        prepare_nonce="prepare-nonce",
        prepare_ciphertext="encrypted-birth-data",
        prepare_digest="prepare-digest",
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
            [guest, release, root, version, reading_verification, claim_event, feedback]
        )
        await session.commit()

    headers = await _admin_headers(client)
    listed = await client.get("/api/v1/admin/verifications", headers=headers)
    assert listed.status_code == 200, listed.text
    events = listed.json()["events"]
    assert len(events) == 3
    assert {event["source"] for event in events} == {"reading", "claim", "feedback"}
    assert "private reading note" not in listed.text
    assert "private claim note" not in listed.text
    assert "private feedback note" not in listed.text
    assert "note" not in listed.text

    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "finance"
        await session.commit()
    assert (await client.get("/api/v1/admin/verifications")).status_code == 403
