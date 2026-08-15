import struct
from typing import Any
from uuid import UUID

from app.media.models import PhysiognomyMediaRecord
from app.readings.models import ReadingVersion
from app.readings.repository import SqlReadingRepository
from app.security.envelope import EnvelopeCipher
from httpx import AsyncClient
from test_profiles_api import create_guest
from test_readings_api import seed_runtime_release


def png_payload(width: int = 1200, height: int = 1600) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I4sIIBBBBB", 13, b"IHDR", width, height, 8, 2, 0, 0, 0)
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


async def upload_face(client: AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/physiognomy/media",
        headers=headers,
        data={"mode": "face", "consent": "true"},
        files={"file": ("face.png", png_payload(), "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_upload_persists_owner_scoped_metadata_without_filename_or_public_url(
    client: AsyncClient,
    database: Any,
) -> None:
    headers = await create_guest(client)
    uploaded = await upload_face(client, headers)

    assert uploaded["mode"] == "face"
    assert uploaded["width"] == 1200
    assert uploaded["height"] == 1600
    assert "filename" not in uploaded
    assert "object_key" not in uploaded

    async with database.sessions() as session:
        record = await session.get(PhysiognomyMediaRecord, UUID(uploaded["asset_id"]))
        assert record is not None
        assert record.owner_guest_session_id is not None
        assert record.owner_user_id is None
        assert record.object_key.startswith("private/physiognomy/")


async def test_start_physiognomy_binds_asset_and_compiles_media_blind_prepare(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    await seed_runtime_release(database, test_settings)
    headers = await create_guest(client)
    uploaded = await upload_face(client, headers)
    idempotency_key = "physiognomy-api-test-001"

    started = await client.post(
        "/api/v1/readings/physiognomy",
        headers={**headers, "Idempotency-Key": idempotency_key},
        json={
            "asset_id": uploaded["asset_id"],
            "subject_ref": "subject:fixture",
            "dimension_ids": ["state"],
            "observations": [
                {
                    "region": "forehead",
                    "feature_kind": "visible_morphology",
                    "descriptor": "region_visible",
                    "visibility": "full",
                    "uncertainty": 0.1,
                }
            ],
        },
    )
    assert started.status_code == 201, started.text
    body = started.json()
    assert body["capability_id"] == "physiognomy"
    assert body["product_id"] == "jianxiang"
    assert body["runtime_capability_ids"] == ["physiognomy"]

    async with database.sessions() as session:
        version = await session.get(ReadingVersion, UUID(body["reading_version_id"]))
        assert version is not None
        prepare = await SqlReadingRepository(
            session,
            EnvelopeCipher.from_settings(test_settings),
        ).load_prepare(version.id)
        payload = prepare.to_dict()
        subject_ref = f"sid-{UUID(uploaded['asset_id']).hex}"
        assert "physiognomy_spec" in payload["facts"][subject_ref]
        assert uploaded["asset_id"] not in str(payload)
        assert "private/physiognomy/" not in str(payload)


async def test_upload_rejects_unverifiable_quality_and_delete_is_owner_scoped(
    client: AsyncClient,
) -> None:
    headers = await create_guest(client)
    response = await client.post(
        "/api/v1/physiognomy/media",
        headers=headers,
        data={"mode": "face", "consent": "true"},
        files={"file": ("small.png", png_payload(320, 320), "image/png")},
    )
    assert response.status_code == 400

    uploaded = await upload_face(client, headers)
    deleted = await client.delete(
        f"/api/v1/physiognomy/media/{uploaded['asset_id']}",
        headers=headers,
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["status"] == "deleted"

    started = await client.post(
        "/api/v1/readings/physiognomy",
        headers={**headers, "Idempotency-Key": "physiognomy-deleted-test"},
        json={
            "asset_id": uploaded["asset_id"],
            "subject_ref": "subject:fixture",
            "observations": [
                {
                    "region": "forehead",
                    "feature_kind": "visible_morphology",
                    "descriptor": "region_visible",
                    "visibility": "full",
                }
            ],
        },
    )
    assert started.status_code == 404
