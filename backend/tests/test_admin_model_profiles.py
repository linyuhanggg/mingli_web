from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.admin.models import StaffUser
from app.identity.models import GuestSession
from app.readings.models import GenerationAttempt, ReadingRoot, ReadingVersion, RuntimeRelease
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_model_profiles_lists_safe_model_receipt_metadata(
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
    attempt = GenerationAttempt(
        id=uuid4(),
        reading_version_id=version.id,
        attempt_number=1,
        guard_errors=["claim_missing_evidence", "claim_unbounded"],
        model_receipt={
            "event": "standalone_model_call",
            "outcome": "succeeded",
            "error_code": None,
            "model_profile_id": "fake-model-p0-v1",
            "model_profile_snapshot_digest": "p" * 64,
            "provider": "fake",
            "provider_model_version": "fake-model-v1",
            "request_fingerprint": "r" * 64,
            "narrative_policy_version": "policy-v1",
            "output_contract_id": "reading-document-v1",
            "latency_ms": 42,
            "usage_known": True,
            "cost_known": True,
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        },
        created_at=now,
    )
    async with database.sessions() as session:
        session.add_all([guest, release, root, version, attempt])
        await session.commit()

    response = await client.get(
        "/api/v1/admin/model-profiles?limit=100",
        headers=await _admin_headers(client),
    )

    assert response.status_code == 200, response.text
    event = response.json()["profiles"][0]
    assert event["generation_attempt_id"] == str(attempt.id)
    assert event["model_profile_id"] == "fake-model-p0-v1"
    assert event["provider"] == "fake"
    assert event["provider_model_version"] == "fake-model-v1"
    assert event["outcome"] == "succeeded"
    assert event["guard_error_count"] == 2
    assert event["usage_known"] is True
    assert event["cost_known"] is True
    assert "request_fingerprint" not in response.text
    assert "model_profile_snapshot_digest" not in response.text
    assert "input_tokens" not in response.text
    assert "encrypted-birth-data" not in response.text


async def test_admin_model_profiles_forbids_finance_staff(
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

    response = await client.get("/api/v1/admin/model-profiles", headers=headers)

    assert response.status_code == 403
