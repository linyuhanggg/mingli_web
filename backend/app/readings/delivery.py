from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.security import hash_token, new_opaque_token
from app.profiles.service import OwnerProtocol
from app.readings.models import (
    ClaimVerificationEvent,
    ReadingRoot,
    ReadingShareSnapshot,
    ReadingVersion,
    ReportFeedback,
)
from app.readings.presentation import ReadingDocumentV1
from app.readings.repository import SqlReadingRepository
from app.readings.share_contracts import SharedReadingDocumentV1
from app.security.envelope import EnvelopeCipher

ExportFormat = Literal["png", "pdf"]


class ReadingDeliveryError(RuntimeError):
    """Base class for document, feedback and share delivery failures."""


class ReadingDocumentUnavailableError(ReadingDeliveryError):
    pass


class ShareUnavailableError(ReadingDeliveryError):
    pass


class ExportUnavailableError(ReadingDeliveryError):
    pass


def _reading_export_artifact_model() -> Any:
    try:
        from app.readings.models import ReadingExportArtifact
    except ImportError as error:
        raise ExportUnavailableError("Reading export is unavailable") from error
    return ReadingExportArtifact


@dataclass(frozen=True, slots=True)
class ClaimVerificationResult:
    id: UUID
    reading_version_id: UUID
    claim_id: str
    outcome: Literal["accepted", "partial", "disagreed", "unknown"]
    note: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class FeedbackResult:
    id: UUID
    reading_version_id: UUID
    outcome: Literal["helpful", "not_helpful", "unknown"]
    note: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ShareToken:
    snapshot_id: UUID
    token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ExportToken:
    export_id: UUID
    token: str
    format: ExportFormat
    content_type: str
    file_name: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ExportDownload:
    format: ExportFormat
    content_type: str
    file_name: str
    payload: bytes


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _actor_ref(owner: OwnerProtocol) -> str:
    return f"{owner.kind}:{owner.id}"


def _share_safe_document(document: ReadingDocumentV1) -> SharedReadingDocumentV1:
    """Build the narrow, validated document allowed through a bearer token."""
    return SharedReadingDocumentV1.from_document(document)


class ReadingDeliveryService:
    """Own the persistent public-report delivery boundary."""

    def __init__(self, session: AsyncSession, cipher: EnvelopeCipher) -> None:
        self.session = session
        self.repository = SqlReadingRepository(session, cipher)
        self.cipher = cipher

    async def _owned_version(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> tuple[ReadingRoot, ReadingVersion]:
        owner_column = (
            ReadingRoot.owner_user_id
            if owner.kind == "user"
            else ReadingRoot.owner_guest_session_id
        )
        row = await self.session.execute(
            select(ReadingRoot, ReadingVersion)
            .join(ReadingVersion, ReadingVersion.reading_root_id == ReadingRoot.id)
            .where(ReadingVersion.id == version_id, owner_column == owner.id)
        )
        found = row.first()
        if found is None:
            raise ReadingDocumentUnavailableError("Reading Version not found")
        return found[0], found[1]

    async def _owned_document(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> ReadingDocumentV1:
        _root, version = await self._owned_version(owner, version_id)
        if version.status != "accepted":
            raise ReadingDocumentUnavailableError("Reading is not accepted")
        document = await self.repository.load_reading_document(version_id)
        if document is None:
            raise ReadingDocumentUnavailableError("ReadingDocument is not available")
        return document

    async def submit_claim_verification(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        claim_id: str,
        outcome: Literal["accepted", "partial", "disagreed", "unknown"],
        note: str | None,
    ) -> tuple[ClaimVerificationResult, bool]:
        document = await self._owned_document(owner, version_id)
        if claim_id not in {claim.claim_id for claim in document.claims}:
            raise ReadingDocumentUnavailableError("Claim not found")
        existing = await self.session.scalar(
            select(ClaimVerificationEvent).where(
                ClaimVerificationEvent.reading_version_id == version_id,
                ClaimVerificationEvent.claim_id == claim_id,
            )
        )
        if existing is not None:
            return _claim_result(existing), False
        record = ClaimVerificationEvent(
            id=uuid4(),
            reading_version_id=version_id,
            claim_id=claim_id,
            actor_ref=_actor_ref(owner),
            outcome=outcome,
            note=note,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(record)
                await self.session.flush()
        except IntegrityError:
            existing = await self.session.scalar(
                select(ClaimVerificationEvent).where(
                    ClaimVerificationEvent.reading_version_id == version_id,
                    ClaimVerificationEvent.claim_id == claim_id,
                )
            )
            if existing is None:
                raise
            return _claim_result(existing), False
        return _claim_result(record), True

    async def submit_feedback(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        outcome: Literal["helpful", "not_helpful", "unknown"],
        note: str | None,
    ) -> FeedbackResult:
        await self._owned_document(owner, version_id)
        record = ReportFeedback(
            id=uuid4(),
            reading_version_id=version_id,
            actor_ref=_actor_ref(owner),
            outcome=outcome,
            note=note,
        )
        self.session.add(record)
        await self.session.flush()
        return _feedback_result(record)

    async def create_share(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        ttl: timedelta,
    ) -> ShareToken:
        document = await self._owned_document(owner, version_id)
        if not document.actions.share.enabled:
            raise ReadingDocumentUnavailableError("Sharing is disabled for this document")
        if ttl < timedelta(minutes=5) or ttl > timedelta(days=7):
            raise ValueError("share ttl must be between 5 minutes and 7 days")
        snapshot_id = uuid4()
        token = new_opaque_token()
        expires_at = datetime.now(UTC) + ttl
        share_document = _share_safe_document(document)
        encrypted = self.cipher.encrypt_json(
            share_document.model_dump(mode="json"),
            context=f"reading-share:{snapshot_id}",
        )
        record = ReadingShareSnapshot(
            id=snapshot_id,
            reading_version_id=version_id,
            owner_user_id=owner.id if owner.kind == "user" else None,
            owner_guest_session_id=owner.id if owner.kind == "guest" else None,
            token_hash=hash_token(token),
            payload_key_id=encrypted.key_id,
            payload_nonce=encrypted.nonce,
            payload_ciphertext=encrypted.ciphertext,
            payload_digest=encrypted.fingerprint,
            expires_at=expires_at,
        )
        self.session.add(record)
        await self.session.flush()
        return ShareToken(
            snapshot_id=snapshot_id,
            token=token,
            expires_at=expires_at,
        )

    async def create_export(
        self,
        owner: OwnerProtocol,
        *,
        version_id: UUID,
        export_format: ExportFormat,
        ttl: timedelta,
    ) -> ExportToken:
        document = await self._owned_document(owner, version_id)
        if not document.actions.export.enabled:
            raise ReadingDocumentUnavailableError("Exporting is disabled for this document")
        if ttl < timedelta(minutes=5) or ttl > timedelta(days=1):
            raise ValueError("export ttl must be between 5 minutes and 1 day")
        try:
            from app.readings.export import render_reading_export
        except (ImportError, ModuleNotFoundError) as error:
            raise ExportUnavailableError("Reading export is unavailable") from error
        rendered = render_reading_export(document, export_format)
        export_model = _reading_export_artifact_model()
        export_id = uuid4()
        token = new_opaque_token()
        expires_at = datetime.now(UTC) + ttl
        encoded = base64.b64encode(rendered.payload).decode("ascii")
        encrypted = self.cipher.encrypt_text(
            encoded,
            context=f"reading-export:{export_id}",
        )
        self.session.add(
            export_model(
                id=export_id,
                reading_version_id=version_id,
                owner_user_id=owner.id if owner.kind == "user" else None,
                owner_guest_session_id=owner.id if owner.kind == "guest" else None,
                token_hash=hash_token(token),
                format=rendered.format,
                content_type=rendered.content_type,
                file_name=rendered.file_name,
                payload_key_id=encrypted.key_id,
                payload_nonce=encrypted.nonce,
                payload_ciphertext=encrypted.ciphertext,
                payload_digest=encrypted.fingerprint,
                expires_at=expires_at,
            )
        )
        await self.session.flush()
        return ExportToken(
            export_id=export_id,
            token=token,
            format=rendered.format,
            content_type=rendered.content_type,
            file_name=rendered.file_name,
            expires_at=expires_at,
        )

    async def load_export(self, token: str) -> ExportDownload:
        export_model = _reading_export_artifact_model()
        record = await self.session.scalar(
            select(export_model).where(export_model.token_hash == hash_token(token))
        )
        now = datetime.now(UTC)
        if (
            record is None
            or record.revoked_at is not None
            or _utc(record.expires_at) <= now
        ):
            raise ExportUnavailableError("Reading export is unavailable")
        encoded = self.cipher.decrypt_text(
            self.repository._payload(
                record.payload_key_id,
                record.payload_nonce,
                record.payload_ciphertext,
                record.payload_digest,
            ),
            context=f"reading-export:{record.id}",
        )
        try:
            payload = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ExportUnavailableError("Reading export payload is invalid") from error
        return ExportDownload(
            format=record.format,
            content_type=record.content_type,
            file_name=record.file_name,
            payload=payload,
        )

    async def purge_expired_exports(self, *, now: datetime | None = None) -> int:
        current = datetime.now(UTC) if now is None else _utc(now)
        export_model = _reading_export_artifact_model()
        records = list(
            await self.session.scalars(
                select(export_model).where(
                    or_(
                        export_model.expires_at <= current,
                        export_model.revoked_at.is_not(None),
                    )
                )
            )
        )
        for record in records:
            await self.session.delete(record)
        if records:
            await self.session.flush()
        return len(records)

    async def load_share(self, token: str) -> SharedReadingDocumentV1:
        record = await self.session.scalar(
            select(ReadingShareSnapshot).where(
                ReadingShareSnapshot.token_hash == hash_token(token)
            )
        )
        now = datetime.now(UTC)
        if (
            record is None
            or record.revoked_at is not None
            or _utc(record.expires_at) <= now
        ):
            raise ShareUnavailableError("Share snapshot is unavailable")
        payload = self.cipher.decrypt_json(
            self.repository._payload(
                record.payload_key_id,
                record.payload_nonce,
                record.payload_ciphertext,
                record.payload_digest,
            ),
            context=f"reading-share:{record.id}",
        )
        return SharedReadingDocumentV1.model_validate(payload)

    async def revoke_share(
        self,
        owner: OwnerProtocol,
        snapshot_id: UUID,
        version_id: UUID,
    ) -> None:
        owner_column = (
            ReadingShareSnapshot.owner_user_id
            if owner.kind == "user"
            else ReadingShareSnapshot.owner_guest_session_id
        )
        record = await self.session.scalar(
            select(ReadingShareSnapshot).where(
                ReadingShareSnapshot.id == snapshot_id,
                ReadingShareSnapshot.reading_version_id == version_id,
                owner_column == owner.id,
            )
        )
        if record is None:
            raise ShareUnavailableError("Share snapshot is unavailable")
        if record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
            await self.session.flush()


def _claim_result(record: ClaimVerificationEvent) -> ClaimVerificationResult:
    return ClaimVerificationResult(
        id=record.id,
        reading_version_id=record.reading_version_id,
        claim_id=record.claim_id,
        outcome=record.outcome,  # type: ignore[arg-type]
        note=record.note,
        created_at=record.created_at,
    )


def _feedback_result(record: ReportFeedback) -> FeedbackResult:
    return FeedbackResult(
        id=record.id,
        reading_version_id=record.reading_version_id,
        outcome=record.outcome,  # type: ignore[arg-type]
        note=record.note,
        created_at=record.created_at,
    )
