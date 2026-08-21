from __future__ import annotations

import importlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from test_reading_repository import create_reading_graph


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


def _presentation_contract() -> Any:
    presentation = importlib.import_module("app.readings.presentation")
    return presentation.PresentationContract(
        contract_version="bazi-deep-presentation/v1",
        product_version="bazi-deep/v1",
        renderer="bazi-reading/v1",
        sections=(
            presentation.PresentationSection(
                section_id="overview",
                title="总览",
                min_claims=1,
                max_claims=1,
                max_chars_per_claim=40,
                allowed_claim_kind_ids=("kind.tendency",),
            ),
        ),
        fixed_disclosures=("仅供个人参考。",),
    )


def _document_payload(version_id: str, accepted_copy_ref: str) -> dict[str, object]:
    return {
        "schema_version": "reading-document/v1",
        "document_id": f"reading-version:{version_id}",
        "reading_version_id": version_id,
        "accepted_copy_ref": accepted_copy_ref,
        "product_version": "bazi-deep/v1",
        "presentation_contract_version": "bazi-deep-presentation/v1",
        "view_model": {
            "schema_version": "bazi-chart/v1",
            "subject_ref": "profile-version:fixture",
            "pillars": [
                {"position": "year", "stem": "甲", "branch": "子"},
                {"position": "month", "stem": "乙", "branch": "丑"},
                {"position": "day", "stem": "丙", "branch": "寅"},
                {"position": "hour", "stem": "丁", "branch": "卯"},
            ],
            "element_balance": [{"element": "wood", "value": 2, "display_text": "木二"}],
            "time_layers": [
                {
                    "layer_id": "life",
                    "label": "本命",
                    "available": True,
                    "unavailable_reason": None,
                }
            ],
        },
        "answer_summary": "先稳住长期积累。",
        "subject_summaries": [{"subject_ref": "profile-version:fixture", "label": "本人"}],
        "themes": [{"theme_id": "career", "label": "事业"}],
        "claims": [
            {
                "claim_id": "claim:1",
                "section_id": "overview",
                "text": "先稳住长期积累。",
                "subject_ref": "profile-version:fixture",
                "dimension_id": "career",
                "claim_kind_id": "kind.tendency",
                "certainty_id": "certainty.tendency",
                "fact_refs": ["fact:1"],
                "finding_refs": ["finding:1"],
                "evidence_refs": ["evidence:1"],
                "limit_refs": ["limit:1"],
                "verification": {"enabled": True},
            }
        ],
        "evidence": [
            {
                "evidence_ref": "evidence:1",
                "title": "依据",
                "supports_fact_refs": ["fact:1"],
            }
        ],
        "boundaries": [{"limit_ref": "limit:1", "text": "仅供个人参考。"}],
        "actions": {
            "correction": {"enabled": True},
            "follow_up": {"enabled": True},
            "export": {"enabled": True},
            "share": {"enabled": True},
        },
        "versions": {
            "runtime_release": "runtime:v1",
            "view_model_schema": "bazi-chart/v1",
            "reading_document_schema": "reading-document/v1",
        },
    }


async def _accepted_graph(session: AsyncSession) -> tuple[Any, Any, Any, Any, Any, Any]:
    envelope = importlib.import_module("app.security.envelope")
    runtime_contracts = importlib.import_module("app.readings.runtime_contracts")
    cipher = envelope.EnvelopeCipher(key=b"k" * 32, key_id="test-key-v1")
    repository, profile, version, job, _contracts = await create_reading_graph(session)
    await repository.record_completion_intent(str(job.id), "已接纳正文", datetime.now(UTC))
    accepted = runtime_contracts.Accepted(
        state_token="state-token",
        public_copy="已接纳正文",
    )
    await repository.record_accepted(str(job.id), accepted, datetime.now(UTC))
    copy_row = await repository.get_accepted_copy(version.id)
    assert copy_row is not None
    return repository, profile, version, job, cipher, copy_row


@pytest.mark.asyncio
async def test_accepted_copy_and_reading_document_are_atomic_and_immutable(
    delivery_database: Any,
) -> None:
    presentation = importlib.import_module("app.readings.presentation")
    readings = importlib.import_module("app.readings.repository")
    async with delivery_database.sessions() as session, session.begin():
        repository, _profile, version, _job, _cipher, copy_row = await _accepted_graph(session)
        payload = _document_payload(str(version.id), f"accepted-copy:{copy_row.id}")
        document = presentation.build_reading_document(_presentation_contract(), payload)

        saved, created = await repository.save_reading_document(
            version_id=version.id,
            accepted_copy_id=copy_row.id,
            document=document,
        )
        assert created is True
        assert saved.reading_version_id == version.id

        replay, replayed = await repository.save_reading_document(
            version_id=version.id,
            accepted_copy_id=copy_row.id,
            document=document,
        )
        assert replayed is False
        assert replay.id == saved.id
        loaded = await repository.load_reading_document(version.id)
        assert loaded is not None
        assert loaded.answer_summary == "先稳住长期积累。"

        changed = dict(payload)
        changed["answer_summary"] = "不应覆盖旧报告。"
        changed_document = presentation.build_reading_document(_presentation_contract(), changed)
        with pytest.raises(readings.ImmutableRecordError):
            await repository.save_reading_document(
                version_id=version.id,
                accepted_copy_id=copy_row.id,
                document=changed_document,
            )


@pytest.mark.asyncio
async def test_claim_feedback_and_revocable_expiring_share_are_separate_records(
    delivery_database: Any,
) -> None:
    dependencies = importlib.import_module("app.api.dependencies")
    delivery = importlib.import_module("app.readings.delivery")
    presentation = importlib.import_module("app.readings.presentation")
    async with delivery_database.sessions() as session, session.begin():
        repository, _profile, version, _job, cipher, copy_row = await _accepted_graph(session)
        document = presentation.build_reading_document(
            _presentation_contract(),
            _document_payload(str(version.id), f"accepted-copy:{copy_row.id}"),
        )
        await repository.save_reading_document(
            version_id=version.id,
            accepted_copy_id=copy_row.id,
            document=document,
        )
        root_model = importlib.import_module("app.readings.models").ReadingRoot
        root = await session.get(root_model, version.reading_root_id)
        assert root is not None and root.owner_user_id is not None
        owner = dependencies.Owner(
            kind="user",
            id=root.owner_user_id,
            csrf_token_hash="unused",
        )
        service = delivery.ReadingDeliveryService(session, cipher)

        first, created = await service.submit_claim_verification(
            owner,
            version_id=version.id,
            claim_id="claim:1",
            outcome="partial",
            note="部分准确",
        )
        replay, replayed = await service.submit_claim_verification(
            owner,
            version_id=version.id,
            claim_id="claim:1",
            outcome="disagreed",
            note="不能覆盖第一次核对",
        )
        assert created is True
        assert replayed is False
        assert replay.id == first.id
        assert replay.outcome == "partial"

        feedback = await service.submit_feedback(
            owner,
            version_id=version.id,
            outcome="helpful",
            note="结构清楚",
        )
        assert feedback.outcome == "helpful"

        share = await service.create_share(
            owner,
            version_id=version.id,
            ttl=timedelta(hours=2),
        )
        shared = await service.load_share(share.token)
        assert shared.answer_summary == document.answer_summary
        with pytest.raises(delivery.ShareUnavailableError):
            await service.revoke_share(owner, share.snapshot_id, uuid4())
        assert (await service.load_share(share.token)).answer_summary == document.answer_summary
        await service.revoke_share(owner, share.snapshot_id, version.id)
        with pytest.raises(delivery.ShareUnavailableError):
            await service.load_share(share.token)


@pytest.mark.asyncio
async def test_png_and_pdf_exports_are_encrypted_short_lived_and_rebuildable(
    delivery_database: Any,
) -> None:
    dependencies = importlib.import_module("app.api.dependencies")
    delivery = importlib.import_module("app.readings.delivery")
    presentation = importlib.import_module("app.readings.presentation")
    async with delivery_database.sessions() as session, session.begin():
        repository, _profile, version, _job, cipher, copy_row = await _accepted_graph(session)
        document = presentation.build_reading_document(
            _presentation_contract(),
            _document_payload(str(version.id), f"accepted-copy:{copy_row.id}"),
        )
        await repository.save_reading_document(
            version_id=version.id,
            accepted_copy_id=copy_row.id,
            document=document,
        )
        root_model = importlib.import_module("app.readings.models").ReadingRoot
        root = await session.get(root_model, version.reading_root_id)
        assert root is not None and root.owner_user_id is not None
        owner = dependencies.Owner(
            kind="user",
            id=root.owner_user_id,
            csrf_token_hash="unused",
        )
        service = delivery.ReadingDeliveryService(session, cipher)

        png = await service.create_export(
            owner,
            version_id=version.id,
            export_format="png",
            ttl=timedelta(hours=2),
        )
        pdf = await service.create_export(
            owner,
            version_id=version.id,
            export_format="pdf",
            ttl=timedelta(hours=2),
        )
        png_download = await service.load_export(png.token)
        pdf_download = await service.load_export(pdf.token)
        assert png_download.content_type == "image/png"
        assert png_download.payload.startswith(b"\x89PNG\r\n\x1a\n")
        assert pdf_download.content_type == "application/pdf"
        assert pdf_download.payload.startswith(b"%PDF-")
        assert png.file_name.endswith(".png")
        assert pdf.file_name.endswith(".pdf")

        export_model = importlib.import_module("app.readings.models").ReadingExportArtifact
        expired = await session.get(export_model, png.export_id)
        assert expired is not None
        expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        with pytest.raises(delivery.ExportUnavailableError):
            await service.load_export(png.token)
        assert await service.purge_expired_exports() == 1
        rebuilt = await service.create_export(
            owner,
            version_id=version.id,
            export_format="png",
            ttl=timedelta(hours=2),
        )
        assert (await service.load_export(rebuilt.token)).payload.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_create_export_fail_closes_when_reading_document_is_missing(
    delivery_database: Any,
) -> None:
    dependencies = importlib.import_module("app.api.dependencies")
    delivery = importlib.import_module("app.readings.delivery")
    async with delivery_database.sessions() as session, session.begin():
        repository, _profile, version, _job, cipher, _copy_row = await _accepted_graph(session)
        assert await repository.load_reading_document(version.id) is None
        root_model = importlib.import_module("app.readings.models").ReadingRoot
        root = await session.get(root_model, version.reading_root_id)
        assert root is not None and root.owner_user_id is not None
        owner = dependencies.Owner(
            kind="user",
            id=root.owner_user_id,
            csrf_token_hash="unused",
        )
        service = delivery.ReadingDeliveryService(session, cipher)
        with pytest.raises(
            delivery.ReadingDocumentUnavailableError,
            match="ReadingDocument is not available",
        ):
            await service.create_export(
                owner,
                version_id=version.id,
                export_format="png",
                ttl=timedelta(hours=2),
            )
