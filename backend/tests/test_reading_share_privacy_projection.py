from __future__ import annotations

import importlib
import json
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from test_reading_delivery import (
    _accepted_graph,
    _document_payload,
    _presentation_contract,
)


@pytest.fixture
async def delivery_database() -> AsyncIterator[Any]:
    database_module = importlib.import_module("app.database")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
    database = database_module.Database("sqlite+aiosqlite:///:memory:")
    async with database.engine.begin() as connection:
        await connection.run_sync(identity_models.Base.metadata.create_all)
    yield database
    await database.dispose()


def _payload_with_effective_datetime(version_id: str, accepted_copy_ref: str) -> dict[str, object]:
    payload = _document_payload(version_id, accepted_copy_ref)
    view_model = dict(payload["view_model"])  # type: ignore[arg-type]
    view_model["core_facts"] = {
        "calendar_normalization": {
            "status": "effective",
            "algorithm_version": "calendar/v1",
            "time_basis": {
                "policy": "civil",
                "algorithm": {},
                "boundary": {},
            },
            "true_solar_time": {"status": "not_applied"},
            "calendar_convention": {},
            "effective_datetime": "2026-08-18T01:02:03+08:00",
        }
    }
    payload["view_model"] = view_model
    return payload


async def _owner_for(session: AsyncSession, version: Any) -> Any:
    dependencies = importlib.import_module("app.api.dependencies")
    root_model = importlib.import_module("app.readings.models").ReadingRoot
    root = await session.get(root_model, version.reading_root_id)
    assert root is not None and root.owner_user_id is not None
    return dependencies.Owner(
        kind="user",
        id=root.owner_user_id,
        csrf_token_hash="unused",
    )


@pytest.mark.asyncio
async def test_share_snapshot_redacts_effective_datetime_but_keeps_shared_surface(
    delivery_database: Any,
) -> None:
    delivery = importlib.import_module("app.readings.delivery")
    models = importlib.import_module("app.readings.models")
    presentation = importlib.import_module("app.readings.presentation")

    async with delivery_database.sessions() as session, session.begin():
        repository, _profile, version, _job, cipher, copy_row = await _accepted_graph(session)
        document = presentation.build_reading_document(
            _presentation_contract(),
            _payload_with_effective_datetime(
                str(version.id),
                f"accepted-copy:{copy_row.id}",
            ),
        )
        await repository.save_reading_document(
            version_id=version.id,
            accepted_copy_id=copy_row.id,
            document=document,
        )
        owner = await _owner_for(session, version)
        service = delivery.ReadingDeliveryService(session, cipher)

        share = await service.create_share(
            owner,
            version_id=version.id,
            ttl=timedelta(hours=2),
        )
        record = await session.get(models.ReadingShareSnapshot, share.snapshot_id)
        assert record is not None
        snapshot_payload = cipher.decrypt_json(
            service.repository._payload(
                record.payload_key_id,
                record.payload_nonce,
                record.payload_ciphertext,
                record.payload_digest,
            ),
            context=f"reading-share:{record.id}",
        )

        # This is the privacy boundary: the bearer snapshot is a narrow
        # public document, not an encrypted copy of ReadingDocumentV1.
        assert set(snapshot_payload) == {
            "schema_version",
            "document_id",
            "reading_version_id",
            "accepted_copy_ref",
            "product_version",
            "presentation_contract_version",
            "answer_summary",
            "themes",
            "claims",
            "evidence",
            "boundaries",
            "versions",
        }
        assert snapshot_payload["schema_version"] == "shared-reading-document/v1"
        assert "view_model" not in snapshot_payload
        assert "subject_summaries" not in snapshot_payload
        assert "actions" not in snapshot_payload
        assert "2026-08-18T01:02:03+08:00" not in json.dumps(
            snapshot_payload,
            ensure_ascii=False,
        )

        shared = await service.load_share(share.token)
        assert shared.schema_version == "shared-reading-document/v1"
        assert shared.answer_summary == document.answer_summary
        assert [claim.claim_id for claim in shared.claims] == ["claim:1"]
        assert [claim.text for claim in shared.claims] == ["先稳住长期积累。"]
        assert [evidence.evidence_ref for evidence in shared.evidence] == ["evidence:1"]
        assert [evidence.title for evidence in shared.evidence] == ["依据"]
        assert [boundary.limit_ref for boundary in shared.boundaries] == ["limit:1"]
        assert [boundary.text for boundary in shared.boundaries] == ["仅供个人参考。"]
        assert shared.versions.runtime_release == document.versions.runtime_release
        assert shared.versions.view_model_schema == document.versions.view_model_schema
        assert (
            shared.versions.reading_document_schema
            == document.versions.reading_document_schema
        )
        assert set(shared.model_dump(mode="json")) == set(snapshot_payload)

        # Creating a bearer snapshot must not mutate the owner-only document.
        owner_document = await repository.load_reading_document(version.id)
        assert owner_document == document
        assert (
            owner_document is not None
            and owner_document.view_model.core_facts is not None
            and owner_document.view_model.core_facts.calendar_normalization is not None
            and owner_document.view_model.core_facts.calendar_normalization.effective_datetime
            == "2026-08-18T01:02:03+08:00"
        )
