from __future__ import annotations

from typing import Any
from uuid import UUID

from app.readings.presentation import build_reading_document
from app.readings.repository import SqlReadingRepository
from app.security.envelope import EnvelopeCipher
from httpx import AsyncClient
from test_profiles_api import assert_private_headers, create_confirmed_profile, create_guest
from test_reading_delivery import _document_payload, _presentation_contract
from test_readings_api import (
    advance_to_accepted,
    seed_runtime_release,
)


async def test_export_http_route_creates_and_downloads_png_and_pdf(
    client: AsyncClient,
    database: Any,
    test_settings: Any,
) -> None:
    headers = await create_guest(client)
    confirmed = await create_confirmed_profile(client, headers)
    await seed_runtime_release(database, test_settings)
    started = await client.post(
        "/api/v1/readings/preview",
        headers=headers,
        json={
            "profile_version_id": confirmed["profile_version_id"],
            "dimension_ids": ["career"],
        },
    )
    assert started.status_code == 201
    version_id = UUID(started.json()["reading_version_id"])
    await advance_to_accepted(
        database,
        test_settings,
        version_id=str(version_id),
        subject_ref=f"profile-version:{confirmed['profile_version_id']}",
    )

    cipher = EnvelopeCipher.from_settings(test_settings)
    async with database.sessions() as session:
        repository = SqlReadingRepository(session, cipher)
        accepted_copy = await repository.get_accepted_copy(version_id)
        assert accepted_copy is not None
        document = build_reading_document(
            _presentation_contract(),
            _document_payload(str(version_id), f"accepted-copy:{accepted_copy.id}"),
        )
        await repository.save_reading_document(
            version_id=version_id,
            accepted_copy_id=accepted_copy.id,
            document=document,
        )
        await session.commit()

    for export_format, content_type, signature in (
        ("png", "image/png", b"\x89PNG\r\n\x1a\n"),
        ("pdf", "application/pdf", b"%PDF-"),
    ):
        created = await client.post(
            f"/api/v1/readings/{version_id}/export",
            headers=headers,
            json={"format": export_format},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["format"] == export_format
        assert body["content_type"] == content_type
        assert body["file_name"].endswith(f".{export_format}")

        downloaded = await client.get(f"/api/v1/exports/{body['token']}")
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"].startswith(content_type)
        assert downloaded.content.startswith(signature)
        assert downloaded.headers["cache-control"] == "private, no-store, max-age=0"
        assert downloaded.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
        assert_private_headers(created)
