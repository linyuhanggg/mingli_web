from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import Text, delete, func, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.commerce.models import ProductFamily, ProductVersion
from app.persistence import ImmutableRecordError as ImmutableRecordError
from app.profiles.models import ProfileVersion, SubjectProfile
from app.readings.model_contracts import ModelCallReceipt
from app.readings.models import (
    AcceptedCopy,
    FactBrief,
    GenerationAttempt,
    ReadingDocumentRecord,
    ReadingIdempotencyKey,
    ReadingJobRecord,
    ReadingRoot,
    ReadingVerification,
    ReadingVersion,
    RuntimeRelease,
)
from app.readings.narrative_contracts import NarrativeCandidate, OutputContract
from app.readings.orchestrator import ReadingCheckpoint, ReadingJob
from app.readings.presentation import ReadingDocumentV1
from app.readings.runtime_contracts import (
    Accepted,
    Prepare,
    Prepared,
    ReadingBrief,
    Stopped,
    command_from_dict,
    result_from_dict,
)
from app.readings.status import ReadingStatus
from app.security.envelope import EncryptedPayload, EnvelopeCipher

READING_HISTORY_LIMIT = 50
HOST_LIFECYCLE_KIND = "host_lifecycle"
HOST_LIFECYCLE_INPUT_WAIT_EXPIRED = "input_wait_expired"


class ReadingJobAlreadyQueuedError(ValueError):
    """A waiting version already has another active Job."""


def reading_root_version_lock_statement(
    reading_root_id: UUID,
) -> Select[tuple[ReadingRoot]]:
    """Serialize version allocation for one Reading Root on PostgreSQL."""
    return select(ReadingRoot).where(ReadingRoot.id == reading_root_id).with_for_update()


class SqlReadingRepository:
    def __init__(self, session: AsyncSession, cipher: EnvelopeCipher) -> None:
        self.session = session
        self.cipher = cipher

    async def create_runtime_release(
        self,
        *,
        name: str,
        version: str,
        source_commit: str,
        release_manifest_digest: str,
        protocol_version: str,
        describe_manifest_digest: str,
        image_digest: str | None,
        production_ready: bool,
    ) -> RuntimeRelease:
        release = RuntimeRelease(
            id=uuid4(),
            name=name,
            version=version,
            source_commit=source_commit,
            release_manifest_digest=release_manifest_digest,
            protocol_version=protocol_version,
            describe_manifest_digest=describe_manifest_digest,
            image_digest=image_digest,
            production_ready=production_ready,
        )
        self.session.add(release)
        await self.session.flush()
        return release

    async def create_root(
        self,
        *,
        capability_id: str,
        product_id: str | None = None,
        runtime_capability_ids: tuple[str, ...] | None = None,
        owner_user_id: UUID | None = None,
        owner_guest_session_id: UUID | None = None,
        profile_version_id: UUID | None = None,
        profile_version_ids: tuple[UUID, ...] | None = None,
        relationship_type: str | None = None,
    ) -> ReadingRoot:
        if (owner_user_id is None) == (owner_guest_session_id is None):
            raise ValueError("a Reading Root must have exactly one User or Guest owner")
        resolved_profile_version_ids = profile_version_ids
        if resolved_profile_version_ids is None:
            resolved_profile_version_ids = (
                (profile_version_id,) if profile_version_id is not None else ()
            )
        if len(set(resolved_profile_version_ids)) != len(resolved_profile_version_ids):
            raise ValueError("Reading Root profile versions must be distinct")
        if profile_version_id is not None and (
            not resolved_profile_version_ids
            or resolved_profile_version_ids[0] != profile_version_id
        ):
            raise ValueError("primary ProfileVersion must be the first relationship profile")
        resolved_profile_ids: list[UUID] = []
        for resolved_profile_version_id in resolved_profile_version_ids:
            profile_version = await self.session.get(ProfileVersion, resolved_profile_version_id)
            if profile_version is None:
                raise LookupError("ProfileVersion not found")
            profile = await self.session.scalar(
                select(SubjectProfile)
                .where(SubjectProfile.id == profile_version.profile_id)
                .with_for_update()
            )
            if profile is None:
                raise ImmutableRecordError("ProfileVersion points to a missing SubjectProfile")
            if (
                profile.owner_user_id != owner_user_id
                or profile.owner_guest_session_id != owner_guest_session_id
            ):
                raise ValueError("ProfileVersion owner must match the Reading Root owner")
            resolved_profile_ids.append(profile.id)
        if (
            relationship_type is not None
            and len(resolved_profile_ids) == 2
            and len(set(resolved_profile_ids)) != 2
        ):
            raise ValueError("relationship profiles must belong to distinct SubjectProfiles")
        root = ReadingRoot(
            id=uuid4(),
            owner_user_id=owner_user_id,
            owner_guest_session_id=owner_guest_session_id,
            profile_version_id=profile_version_id,
            profile_version_ids=[str(value) for value in resolved_profile_version_ids] or None,
            capability_id=capability_id,
            product_id=product_id or capability_id,
            relationship_type=relationship_type,
            runtime_capability_ids=list(runtime_capability_ids or (capability_id,)),
        )
        self.session.add(root)
        await self.session.flush()
        return root

    async def create_version(
        self,
        *,
        reading_root_id: UUID,
        runtime_release_id: UUID,
        prepare_command: Prepare,
        relationship_type: str | None = None,
    ) -> ReadingVersion:
        root = await self.session.scalar(reading_root_version_lock_statement(reading_root_id))
        if root is None:
            raise LookupError("Reading Root not found")
        capability_id = str(prepare_command.intent["capability_id"])
        if root.capability_id != capability_id:
            raise ValueError("Prepare capability_id must match the locked Reading Root capability")
        comparisons = prepare_command.intent.get("comparisons", [])
        if not isinstance(comparisons, (list, tuple)):
            raise ValueError("Prepare comparisons must be a list or tuple")
        runtime_capability_ids = [capability_id]
        for comparison in comparisons:
            if not isinstance(comparison, Mapping):
                raise ValueError("Prepare comparison must be an object")
            comparison_capability_id = comparison.get("capability_id")
            if not isinstance(comparison_capability_id, str) or not comparison_capability_id:
                raise ValueError("Prepare comparison capability_id must be a non-empty string")
            runtime_capability_ids.append(comparison_capability_id)
        if len(runtime_capability_ids) != len(set(runtime_capability_ids)):
            raise ValueError("Prepare runtime capabilities must be unique")
        expected_runtime_capability_ids = root.runtime_capability_ids or [root.capability_id]
        if runtime_capability_ids != expected_runtime_capability_ids:
            raise ValueError(
                "Prepare runtime capabilities must match the locked Reading Root"
            )
        current = await self.session.scalar(
            select(func.max(ReadingVersion.version)).where(
                ReadingVersion.reading_root_id == reading_root_id
            )
        )
        version_id = uuid4()
        encrypted = self.cipher.encrypt_json(
            prepare_command.to_dict(),
            context=f"reading-version:{version_id}:prepare",
        )
        intent = prepare_command.intent
        horizon_value = intent["horizon"]
        if not isinstance(horizon_value, Mapping):
            raise ValueError("Prepare horizon must be an object")
        horizon = cast(Mapping[str, object], horizon_value)
        dimension_ids = cast(tuple[object, ...], intent["dimension_ids"])
        version = ReadingVersion(
            id=version_id,
            reading_root_id=reading_root_id,
            runtime_release_id=runtime_release_id,
            version=(current or 0) + 1,
            status=ReadingStatus.INPUT_READY.value,
            capability_id=capability_id,
            product_id=root.product_id or root.capability_id,
            relationship_type=relationship_type or root.relationship_type,
            runtime_capability_ids=list(expected_runtime_capability_ids),
            object_id=str(intent["object_id"]),
            dimension_ids=[str(value) for value in dimension_ids],
            horizon={str(key): value for key, value in horizon.items()},
            prepare_key_id=encrypted.key_id,
            prepare_nonce=encrypted.nonce,
            prepare_ciphertext=encrypted.ciphertext,
            prepare_digest=encrypted.fingerprint,
            prepare_has_state_token=prepare_command.state_token is not None,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def replace_prepare(
        self,
        version_id: UUID,
        prepare: Prepare,
        *,
        available_at: datetime | None = None,
    ) -> ReadingJobRecord:
        """Resume the existing Job for a waiting_input Reading Version."""
        version = await self.session.scalar(
            select(ReadingVersion)
            .where(ReadingVersion.id == version_id)
            .with_for_update()
        )
        if version is None:
            raise LookupError("Reading Version not found")
        if version.status != ReadingStatus.WAITING_INPUT.value:
            raise ValueError("Reading Version is not waiting for input")
        job = await self.session.scalar(
            select(ReadingJobRecord)
            .where(
                ReadingJobRecord.reading_version_id == version_id,
                ReadingJobRecord.status == "waiting_input",
            )
            .with_for_update()
        )
        if job is None:
            raise ValueError("Reading Job is not waiting for input")
        active_job = await self.session.scalar(
            select(ReadingJobRecord)
            .where(
                ReadingJobRecord.reading_version_id == version_id,
                ReadingJobRecord.status.in_(("queued", "claimed", "running")),
                ReadingJobRecord.id != job.id,
            )
            .with_for_update()
        )
        if active_job is not None:
            raise ReadingJobAlreadyQueuedError(
                "Reading Version already has an active Job"
            )
        encrypted = self.cipher.encrypt_json(
            prepare.to_dict(),
            context=f"reading-version:{version.id}:prepare",
        )
        version.prepare_key_id = encrypted.key_id
        version.prepare_nonce = encrypted.nonce
        version.prepare_ciphertext = encrypted.ciphertext
        version.prepare_digest = encrypted.fingerprint
        version.prepare_has_state_token = prepare.state_token is not None
        version.status = ReadingStatus.INPUT_READY.value
        version.waiting_input_at = None
        version.last_result_key_id = None
        version.last_result_nonce = None
        version.last_result_ciphertext = None
        version.last_result_digest = None
        self._clear_runtime_failure_audit(version)
        job.status = "queued"
        job.available_at = available_at or datetime.now(UTC)
        job.lease_owner = None
        job.lease_token = None
        job.lease_expires_at = None
        await self.session.flush()
        return job

    async def create_job(
        self,
        *,
        reading_version_id: UUID,
        narrative_policy_version: str,
        output_contract: OutputContract,
        language: str,
        max_output_chars: int,
        max_attempts: int,
        status: str = "queued",
        available_at: datetime | None = None,
    ) -> ReadingJobRecord:
        job = ReadingJobRecord(
            id=uuid4(),
            reading_version_id=reading_version_id,
            status=status,
            narrative_policy_version=narrative_policy_version,
            output_contract=output_contract.to_dict(),
            language=language,
            max_output_chars=max_output_chars,
            max_attempts=max_attempts,
            available_at=available_at or datetime.now(UTC),
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def resolve_runtime_release(self) -> RuntimeRelease:
        release = await self.session.scalar(
            select(RuntimeRelease)
            .where(RuntimeRelease.production_ready.is_(True))
            .order_by(
                RuntimeRelease.created_at.desc(),
                RuntimeRelease.id.desc(),
            )
        )
        if release is None:
            raise LookupError("no production-ready Runtime Release is registered")
        return release

    async def load_owned_version(
        self,
        version_id: UUID,
        *,
        owner_user_id: UUID | None,
        owner_guest_session_id: UUID | None,
    ) -> tuple[ReadingRoot, ReadingVersion]:
        row = await self.session.execute(
            select(ReadingRoot, ReadingVersion)
            .join(ReadingVersion, ReadingVersion.reading_root_id == ReadingRoot.id)
            .where(
                ReadingVersion.id == version_id,
                ReadingRoot.owner_user_id == owner_user_id,
                ReadingRoot.owner_guest_session_id == owner_guest_session_id,
            )
        )
        found = row.first()
        if found is None:
            raise LookupError("Reading Version not found")
        return found[0], found[1]

    async def list_owned_versions(
        self,
        *,
        owner_user_id: UUID | None,
        owner_guest_session_id: UUID | None,
        limit: int = READING_HISTORY_LIMIT,
    ) -> list[tuple[ReadingRoot, ReadingVersion]]:
        rows = await self.session.execute(
            select(ReadingRoot, ReadingVersion)
            .join(ReadingVersion, ReadingVersion.reading_root_id == ReadingRoot.id)
            .where(
                ReadingRoot.owner_user_id == owner_user_id,
                ReadingRoot.owner_guest_session_id == owner_guest_session_id,
            )
            .order_by(
                ReadingVersion.created_at.desc(),
                ReadingVersion.id.desc(),
            )
            .limit(limit)
        )
        found = rows.all()
        return [(root, version) for root, version in found]

    async def list_owned_profile_versions(
        self,
        profile_id: UUID,
        *,
        owner_user_id: UUID | None,
        owner_guest_session_id: UUID | None,
    ) -> list[tuple[ReadingRoot, ReadingVersion, UUID]]:
        """List every Reading Version linked through any version of one Profile.

        This intentionally has no history-window limit.  Profile lookup must be
        able to recover an older successful chart even after an owner creates
        more than the account-history projection's newest 50 versions.
        """

        profile_version_ids = tuple(
            await self.session.scalars(
                select(ProfileVersion.id)
                .join(SubjectProfile, SubjectProfile.id == ProfileVersion.profile_id)
                .where(
                    SubjectProfile.id == profile_id,
                    SubjectProfile.status == "active",
                    SubjectProfile.owner_user_id == owner_user_id,
                    SubjectProfile.owner_guest_session_id == owner_guest_session_id,
                )
            )
        )
        if not profile_version_ids:
            return []
        profile_version_id_set = set(profile_version_ids)
        secondary_membership = tuple(
            sql_cast(ReadingRoot.profile_version_ids, Text).contains(f'"{version_id}"')
            for version_id in profile_version_ids
        )
        rows = await self.session.execute(
            select(ReadingRoot, ReadingVersion)
            .join(ReadingVersion, ReadingVersion.reading_root_id == ReadingRoot.id)
            .where(
                ReadingRoot.owner_user_id == owner_user_id,
                ReadingRoot.owner_guest_session_id == owner_guest_session_id,
                or_(
                    ReadingRoot.profile_version_id.in_(profile_version_ids),
                    *secondary_membership,
                ),
            )
            .order_by(
                ReadingVersion.created_at.desc(),
                ReadingVersion.id.desc(),
            )
        )
        found: list[tuple[ReadingRoot, ReadingVersion, UUID]] = []
        for root, version in rows.all():
            linked_ids = (
                UUID(str(value))
                for value in (
                    root.profile_version_ids
                    or ([root.profile_version_id] if root.profile_version_id else [])
                )
            )
            matched_profile_version_id = next(
                (value for value in linked_ids if value in profile_version_id_set),
                None,
            )
            if matched_profile_version_id is not None:
                found.append((root, version, matched_profile_version_id))
        return found

    async def load_prepare(self, version_id: UUID) -> Prepare:
        version = await self.session.get(ReadingVersion, version_id)
        if version is None:
            raise LookupError("Reading Version not found")
        payload = self.cipher.decrypt_json(
            self._payload(
                version.prepare_key_id,
                version.prepare_nonce,
                version.prepare_ciphertext,
                version.prepare_digest,
            ),
            context=f"reading-version:{version.id}:prepare",
        )
        command = command_from_dict(payload)
        if not isinstance(command, Prepare):
            raise ImmutableRecordError("ReadingVersion does not contain Prepare")
        return command

    async def load_waiting_input(self, version_id: UUID) -> Stopped | None:
        version = await self.session.get(ReadingVersion, version_id)
        if version is None:
            raise LookupError("Reading Version not found")
        payload = self._decrypt_last_result_payload(version)
        if payload is None or payload.get("kind") == HOST_LIFECYCLE_KIND:
            return None
        result = result_from_dict(payload)
        if not isinstance(result, Stopped) or result.reason != "need_input":
            return None
        return result

    async def load_state_token(self, version_id: UUID) -> str:
        version = await self.session.get(ReadingVersion, version_id)
        if version is None:
            raise LookupError("Reading Version not found")
        token = self._decrypt_optional_text(
            version.state_token_key_id,
            version.state_token_nonce,
            version.state_token_ciphertext,
            version.state_token_fingerprint,
            context=f"reading-version:{version.id}:state-token",
        )
        if token is None:
            raise ImmutableRecordError("Reading Version has no state token")
        return token

    async def load_fact_brief(self, version_id: UUID) -> ReadingBrief | None:
        fact_brief = await self.get_fact_brief(version_id)
        if fact_brief is None:
            return None
        payload = self.cipher.decrypt_json(
            self._payload(
                fact_brief.payload_key_id,
                fact_brief.payload_nonce,
                fact_brief.payload_ciphertext,
                fact_brief.payload_digest,
            ),
            context=f"reading-version:{version_id}:brief",
        )
        return ReadingBrief.from_dict(payload)

    async def load_accepted_copy(self, version_id: UUID) -> str | None:
        accepted_copy = await self.get_accepted_copy(version_id)
        if accepted_copy is None:
            return None
        return self.cipher.decrypt_text(
            self._payload(
                accepted_copy.payload_key_id,
                accepted_copy.payload_nonce,
                accepted_copy.payload_ciphertext,
                accepted_copy.public_copy_digest,
            ),
            context=f"reading-version:{version_id}:accepted-copy",
        )

    async def load_successful_candidate(self, job_id: str) -> NarrativeCandidate | None:
        _job, version = await self._job_and_version(job_id)
        attempts = (
            await self.session.scalars(
                select(GenerationAttempt)
                .where(
                    GenerationAttempt.reading_version_id == version.id,
                    GenerationAttempt.candidate_ciphertext.is_not(None),
                )
                .order_by(GenerationAttempt.attempt_number.desc())
            )
        ).all()
        attempt = next(
            (
                candidate_attempt
                for candidate_attempt in attempts
                if not candidate_attempt.guard_errors
            ),
            None,
        )
        if attempt is None:
            return None
        payload = self.cipher.decrypt_json(
            self._payload(
                attempt.candidate_key_id,
                attempt.candidate_nonce,
                attempt.candidate_ciphertext,
                attempt.candidate_digest,
            ),
            context=f"reading-version:{version.id}:candidate:{attempt.attempt_number}",
        )
        return NarrativeCandidate.from_dict(payload)

    async def load_accepted_copy_ref(self, job_id: str) -> str | None:
        _job, version = await self._job_and_version(job_id)
        accepted_copy = await self.get_accepted_copy(version.id)
        return None if accepted_copy is None else f"accepted-copy:{accepted_copy.id}"

    async def save_reading_document_for_job(
        self,
        job_id: str,
        document: ReadingDocumentV1,
    ) -> None:
        _job, version = await self._job_and_version(job_id)
        accepted_copy = await self.get_accepted_copy(version.id)
        if accepted_copy is None:
            raise ImmutableRecordError("AcceptedCopy is required before ReadingDocument")
        await self.save_reading_document(
            version_id=version.id,
            accepted_copy_id=accepted_copy.id,
            document=document,
        )

    async def load_verification(
        self,
        version_id: UUID,
    ) -> ReadingVerification | None:
        return cast(
            ReadingVerification | None,
            await self.session.scalar(
                select(ReadingVerification).where(
                    ReadingVerification.reading_version_id == version_id
                )
            )
        )

    async def save_verification(
        self,
        *,
        version_id: UUID,
        outcome: str,
        note: str | None,
    ) -> tuple[ReadingVerification, bool]:
        existing = await self.load_verification(version_id)
        if existing is not None:
            return existing, False
        verification = ReadingVerification(
            id=uuid4(),
            reading_version_id=version_id,
            outcome=outcome,
            note=note,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(verification)
                await self.session.flush()
        except IntegrityError:
            existing = await self.load_verification(version_id)
            if existing is None:
                raise
            return existing, False
        await self.session.refresh(verification)
        return verification, True

    async def find_idempotency(
        self,
        key_hash: str,
        *,
        owner_user_id: UUID | None,
        owner_guest_session_id: UUID | None,
    ) -> ReadingIdempotencyKey | None:
        return cast(
            ReadingIdempotencyKey | None,
            await self.session.scalar(
                select(ReadingIdempotencyKey).where(
                    ReadingIdempotencyKey.key_hash == key_hash,
                    ReadingIdempotencyKey.owner_user_id == owner_user_id,
                    ReadingIdempotencyKey.owner_guest_session_id
                    == owner_guest_session_id,
                )
            )
        )

    async def save_idempotency(
        self,
        *,
        key_hash: str,
        action: str,
        request_fingerprint: str,
        owner_user_id: UUID | None,
        owner_guest_session_id: UUID | None,
        reading_version_id: UUID,
    ) -> ReadingIdempotencyKey:
        record = ReadingIdempotencyKey(
            id=uuid4(),
            key_hash=key_hash,
            action=action,
            request_fingerprint=request_fingerprint,
            owner_user_id=owner_user_id,
            owner_guest_session_id=owner_guest_session_id,
            reading_version_id=reading_version_id,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def load_start_claim(
        self,
        version_id: UUID,
    ) -> tuple[ReadingRoot, ReadingVersion, ReadingJobRecord]:
        """Lock one provisional direct-start claim and its only Job."""

        version = await self.session.scalar(
            select(ReadingVersion)
            .where(ReadingVersion.id == version_id)
            .with_for_update()
        )
        if version is None:
            raise LookupError("Reading Version claim not found")
        root = await self.session.scalar(
            select(ReadingRoot)
            .where(ReadingRoot.id == version.reading_root_id)
            .with_for_update()
        )
        if root is None:
            raise LookupError("Reading Root claim not found")
        jobs = list(
            await self.session.scalars(
                select(ReadingJobRecord)
                .where(ReadingJobRecord.reading_version_id == version.id)
                .with_for_update()
            )
        )
        if len(jobs) != 1:
            raise LookupError("Reading Version claim must have exactly one Job")
        return root, version, jobs[0]

    async def attach_start_claim_profile(
        self,
        version_id: UUID,
        profile_version_id: UUID,
    ) -> tuple[ReadingRoot, ReadingVersion, ReadingJobRecord]:
        """Attach a durable provisional claim to the transaction's ProfileVersion."""

        root, version, job = await self.load_start_claim(version_id)
        profile_version = await self.session.get(ProfileVersion, profile_version_id)
        if profile_version is None:
            raise LookupError("ProfileVersion not found")
        profile = await self.session.scalar(
            select(SubjectProfile)
            .where(SubjectProfile.id == profile_version.profile_id)
            .with_for_update()
        )
        if profile is None:
            raise LookupError("SubjectProfile not found")
        if (
            profile.owner_user_id != root.owner_user_id
            or profile.owner_guest_session_id != root.owner_guest_session_id
        ):
            raise ValueError("ProfileVersion owner must match the Reading Root owner")
        root.profile_version_id = profile_version.id
        root.profile_version_ids = [str(profile_version.id)]
        await self.session.flush()
        return root, version, job

    async def replace_start_claim_prepare(
        self,
        version_id: UUID,
        prepare: Prepare,
    ) -> ReadingVersion:
        """Replace a provisional claim payload before its sole Runtime call."""

        version = await self.session.scalar(
            select(ReadingVersion)
            .where(ReadingVersion.id == version_id)
            .with_for_update()
        )
        if version is None:
            raise LookupError("Reading Version claim not found")
        if version.status != ReadingStatus.INPUT_READY.value:
            raise ValueError("Reading Version claim is no longer input-ready")
        encrypted = self.cipher.encrypt_json(
            prepare.to_dict(),
            context=f"reading-version:{version.id}:prepare",
        )
        version.prepare_key_id = encrypted.key_id
        version.prepare_nonce = encrypted.nonce
        version.prepare_ciphertext = encrypted.ciphertext
        version.prepare_digest = encrypted.fingerprint
        version.prepare_has_state_token = prepare.state_token is not None
        await self.session.flush()
        return version

    async def delete_start_claim(self, version_id: UUID) -> None:
        """Release a provisional claim after a known-safe terminal response."""

        root, version, _job = await self.load_start_claim(version_id)
        await self.session.execute(
            delete(ReadingIdempotencyKey).where(
                ReadingIdempotencyKey.reading_version_id == version.id
            )
        )
        await self.session.execute(
            delete(ReadingJobRecord).where(
                ReadingJobRecord.reading_version_id == version.id
            )
        )
        await self.session.execute(
            delete(ReadingVersion).where(ReadingVersion.id == version.id)
        )
        await self.session.execute(delete(ReadingRoot).where(ReadingRoot.id == root.id))
        await self.session.flush()

    async def load_job(self, job_id: str) -> ReadingJob:
        job, version = await self._job_and_version(job_id)
        command_payload = self.cipher.decrypt_json(
            self._payload(
                version.prepare_key_id,
                version.prepare_nonce,
                version.prepare_ciphertext,
                version.prepare_digest,
            ),
            context=f"reading-version:{version.id}:prepare",
        )
        command = command_from_dict(command_payload)
        if not isinstance(command, Prepare):
            raise ImmutableRecordError("ReadingVersion does not contain Prepare")
        release = await self.session.get(RuntimeRelease, version.runtime_release_id)
        product_version: str | None = None
        presentation_contract_version: str | None = None
        follow_up_count = 0
        follow_up_window_seconds = 0
        root = await self.session.get(ReadingRoot, version.reading_root_id)
        if root is None:
            raise ImmutableRecordError("Reading Version points to a missing Reading Root")
        if root.product_version_snapshot_id is not None:
            snapshot = await self.session.get(ProductVersion, root.product_version_snapshot_id)
            if snapshot is None:
                raise ImmutableRecordError(
                    "Reading Root points to a missing ProductVersion snapshot"
                )
            family = await self.session.get(ProductFamily, snapshot.family_id)
            if family is None:
                raise ImmutableRecordError(
                    "ProductVersion snapshot points to a missing ProductFamily"
                )
            product_version = f"{family.key}-reading/{snapshot.version}"
            presentation_contract_version = snapshot.contract_version
            follow_up_count = snapshot.follow_up_count
            follow_up_window_seconds = snapshot.follow_up_window_seconds
        return ReadingJob(
            id=str(job.id),
            prepare_command=command,
            narrative_policy_version=job.narrative_policy_version,
            output_contract=OutputContract.from_dict(job.output_contract),
            language=job.language,
            max_output_chars=job.max_output_chars,
            max_attempts=job.max_attempts,
            reading_version_id=version.id,
            product_id=version.product_id,
            relationship_type=version.relationship_type,
            runtime_release=(
                f"{release.name}@{release.version}"
                if release is not None
                else "runtime:unknown"
            ),
            product_version=product_version,
            presentation_contract_version=presentation_contract_version,
            follow_up_count=follow_up_count,
            follow_up_window_seconds=follow_up_window_seconds,
        )

    async def load_checkpoint(self, job_id: str) -> ReadingCheckpoint:
        _job, version = await self._job_and_version(job_id)
        stopped: Stopped | None = None
        host_lifecycle_copy: str | None = None
        result_payload = self._decrypt_last_result_payload(version)
        if result_payload is not None:
            if result_payload.get("kind") == HOST_LIFECYCLE_KIND:
                copy = result_payload.get("public_copy")
                host_lifecycle_copy = copy if isinstance(copy, str) else None
            else:
                result = result_from_dict(result_payload)
                if isinstance(result, Stopped):
                    stopped = result

        token = self._decrypt_optional_text(
            version.state_token_key_id,
            version.state_token_nonce,
            version.state_token_ciphertext,
            version.state_token_fingerprint,
            context=f"reading-version:{version.id}:state-token",
        )
        fact_brief = await self.get_fact_brief(version.id)
        prepared: Prepared | None = None
        if fact_brief is not None and token is not None:
            brief_payload = self.cipher.decrypt_json(
                self._payload(
                    fact_brief.payload_key_id,
                    fact_brief.payload_nonce,
                    fact_brief.payload_ciphertext,
                    fact_brief.payload_digest,
                ),
                context=f"reading-version:{version.id}:brief",
            )
            prepared = Prepared(
                state_token=token,
                brief=ReadingBrief.from_dict(brief_payload),
            )
        attempt_count = await self.session.scalar(
            select(func.max(GenerationAttempt.attempt_number)).where(
                GenerationAttempt.reading_version_id == version.id
            )
        )
        completion_copy = self._decrypt_optional_text(
            version.completion_key_id,
            version.completion_nonce,
            version.completion_ciphertext,
            version.completion_digest,
            context=f"reading-version:{version.id}:completion",
        )
        accepted_row = await self.get_accepted_copy(version.id)
        accepted: Accepted | None = None
        if accepted_row is not None:
            if token is None:
                raise ImmutableRecordError("AcceptedCopy exists without a state token")
            accepted = Accepted(
                state_token=token,
                public_copy=self.cipher.decrypt_text(
                    self._payload(
                        accepted_row.payload_key_id,
                        accepted_row.payload_nonce,
                        accepted_row.payload_ciphertext,
                        accepted_row.public_copy_digest,
                    ),
                    context=f"reading-version:{version.id}:accepted-copy",
                ),
            )
        status = ReadingStatus(version.status)
        return ReadingCheckpoint(
            status=status,
            waiting_input=(
                stopped if stopped is not None and stopped.reason == "need_input" else None
            ),
            terminal_stopped=(
                stopped if stopped is not None and stopped.reason != "need_input" else None
            ),
            prepared=prepared,
            attempt_count=attempt_count or 0,
            completion_copy=completion_copy,
            accepted=accepted,
            host_lifecycle_copy=host_lifecycle_copy,
        )

    async def record_waiting_input(
        self,
        job_id: str,
        stopped: Stopped,
        at: datetime,
    ) -> None:
        job, version = await self._job_and_version(job_id)
        if stopped.state_token is not None:
            self._set_state_token(version, stopped.state_token)
        self._set_last_result(version, stopped)
        version.status = ReadingStatus.WAITING_INPUT.value
        version.waiting_input_at = at
        job.status = "waiting_input"
        await self.session.flush()

    async def expire_waiting_input(
        self,
        *,
        now: datetime,
        max_age: timedelta = timedelta(days=7),
    ) -> ReadingJobRecord | None:
        """Cancel one stale input wait while holding the row lock."""
        if max_age <= timedelta(0):
            raise ValueError("waiting input timeout must be positive")
        cutoff = now - max_age
        row = (
            await self.session.execute(
                select(ReadingJobRecord, ReadingVersion)
                .join(
                    ReadingVersion,
                    ReadingVersion.id == ReadingJobRecord.reading_version_id,
                )
                .where(
                    ReadingJobRecord.status == "waiting_input",
                    ReadingVersion.status == ReadingStatus.WAITING_INPUT.value,
                    ReadingVersion.waiting_input_at.is_not(None),
                    ReadingVersion.waiting_input_at <= cutoff,
                )
                .order_by(ReadingVersion.waiting_input_at, ReadingJobRecord.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).one_or_none()
        if row is None:
            return None
        job = cast(ReadingJobRecord, row[0])
        version = cast(ReadingVersion, row[1])
        public_copy = (
            "Supplemental input was not provided within 7 days; this reading was canceled."
            if job.language.lower().startswith("en")
            else "补充资料超过 7 天，任务已取消。"
        )
        self._set_host_lifecycle_terminal(
            version,
            reason=HOST_LIFECYCLE_INPUT_WAIT_EXPIRED,
            public_copy=public_copy,
        )
        version.status = ReadingStatus.TERMINAL_STOPPED.value
        job.status = "stopped"
        job.lease_owner = None
        job.lease_token = None
        job.lease_expires_at = None
        await self.session.flush()
        return job

    async def record_terminal_stopped(
        self,
        job_id: str,
        stopped: Stopped,
        at: datetime,
    ) -> None:
        del at
        job, version = await self._job_and_version(job_id)
        self._set_last_result(version, stopped)
        version.status = ReadingStatus.TERMINAL_STOPPED.value
        version.waiting_input_at = None
        job.status = "stopped"
        await self.session.flush()

    async def record_prepared(
        self,
        job_id: str,
        prepared: Prepared,
        at: datetime,
    ) -> None:
        del at
        job, version = await self._job_and_version(job_id)
        self._set_state_token(version, prepared.state_token)
        existing = await self.get_fact_brief(version.id)
        brief = cast(ReadingBrief, prepared.brief)
        encrypted = self.cipher.encrypt_json(
            brief.to_dict(),
            context=f"reading-version:{version.id}:brief",
        )
        if existing is None:
            self.session.add(
                FactBrief(
                    id=uuid4(),
                    reading_version_id=version.id,
                    payload_key_id=encrypted.key_id,
                    payload_nonce=encrypted.nonce,
                    payload_ciphertext=encrypted.ciphertext,
                    payload_digest=encrypted.fingerprint,
                )
            )
        elif existing.payload_digest != encrypted.fingerprint:
            raise ImmutableRecordError("Prepared brief cannot change after persistence")
        version.status = ReadingStatus.PREPARED.value
        job.status = "running"
        await self.session.flush()

    async def record_generation_attempt(
        self,
        job_id: str,
        attempt_number: int,
        candidate: NarrativeCandidate | None,
        guard_errors: tuple[str, ...],
        at: datetime,
        *,
        model_receipt: ModelCallReceipt | None = None,
    ) -> None:
        del at
        _job, version = await self._job_and_version(job_id)
        await self._insert_attempt(
            version,
            attempt_number,
            candidate,
            guard_errors,
            model_receipt,
        )
        await self.session.flush()

    async def record_successful_attempt(
        self,
        job_id: str,
        attempt_number: int,
        candidate: NarrativeCandidate,
        public_copy: str,
        at: datetime,
        *,
        model_receipt: ModelCallReceipt | None = None,
    ) -> None:
        del at
        job, version = await self._job_and_version(job_id)
        await self._insert_attempt(
            version,
            attempt_number,
            candidate,
            (),
            model_receipt,
        )
        self._set_completion(version, public_copy)
        version.status = ReadingStatus.COMPLETING.value
        job.status = "running"
        await self.session.flush()

    async def record_completion_intent(
        self,
        job_id: str,
        public_copy: str,
        at: datetime,
    ) -> None:
        del at
        job, version = await self._job_and_version(job_id)
        self._set_completion(version, public_copy)
        version.status = ReadingStatus.COMPLETING.value
        job.status = "running"
        await self.session.flush()

    async def record_accepted(
        self,
        job_id: str,
        accepted: Accepted,
        at: datetime,
    ) -> Accepted:
        job, version = await self._job_and_version(job_id)
        existing = await self.get_accepted_copy(version.id)
        if existing is not None:
            existing_copy = self.cipher.decrypt_text(
                self._payload(
                    existing.payload_key_id,
                    existing.payload_nonce,
                    existing.payload_ciphertext,
                    existing.public_copy_digest,
                ),
                context=f"reading-version:{version.id}:accepted-copy",
            )
            if existing_copy != accepted.public_copy:
                raise ImmutableRecordError("Accepted Copy is first-write-wins")
            return Accepted(
                state_token=accepted.state_token,
                public_copy=existing_copy,
            )
        encrypted = self.cipher.encrypt_text(
            accepted.public_copy,
            context=f"reading-version:{version.id}:accepted-copy",
        )
        self.session.add(
            AcceptedCopy(
                id=uuid4(),
                reading_version_id=version.id,
                payload_key_id=encrypted.key_id,
                payload_nonce=encrypted.nonce,
                payload_ciphertext=encrypted.ciphertext,
                public_copy_digest=encrypted.fingerprint,
                accepted_at=at,
            )
        )
        version.status = ReadingStatus.ACCEPTED.value
        job.status = "complete"
        await self.session.flush()
        return accepted

    async def save_reading_document(
        self,
        *,
        version_id: UUID,
        accepted_copy_id: UUID,
        document: ReadingDocumentV1,
    ) -> tuple[ReadingDocumentRecord, bool]:
        """Persist the validated document paired with its first Accepted Copy."""

        if document.reading_version_id != str(version_id):
            raise ValueError("ReadingDocument must point to the supplied Reading Version")
        accepted_copy = await self.session.get(AcceptedCopy, accepted_copy_id)
        if accepted_copy is None or accepted_copy.reading_version_id != version_id:
            raise ValueError("ReadingDocument must point to an Accepted Copy of the version")
        expected_ref = f"accepted-copy:{accepted_copy.id}"
        if document.accepted_copy_ref != expected_ref:
            raise ValueError("ReadingDocument accepted_copy_ref does not match the Accepted Copy")

        existing = await self.get_reading_document(version_id)
        if existing is not None:
            current = await self.load_reading_document(version_id)
            if current != document:
                raise ImmutableRecordError("ReadingDocument is first-write-wins") from None
            return existing, False

        encrypted = self.cipher.encrypt_json(
            document.model_dump(mode="json"),
            context=f"reading-version:{version_id}:reading-document",
        )
        record = ReadingDocumentRecord(
            id=uuid4(),
            reading_version_id=version_id,
            accepted_copy_id=accepted_copy_id,
            schema_version=document.schema_version,
            payload_key_id=encrypted.key_id,
            payload_nonce=encrypted.nonce,
            payload_ciphertext=encrypted.ciphertext,
            payload_digest=encrypted.fingerprint,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(record)
                await self.session.flush()
        except IntegrityError:
            existing = await self.get_reading_document(version_id)
            if existing is None:
                raise
            current = await self.load_reading_document(version_id)
            if current != document:
                raise ImmutableRecordError("ReadingDocument is first-write-wins") from None
            return existing, False
        return record, True

    async def get_reading_document(self, version_id: UUID) -> ReadingDocumentRecord | None:
        return cast(
            ReadingDocumentRecord | None,
            await self.session.scalar(
                select(ReadingDocumentRecord).where(
                    ReadingDocumentRecord.reading_version_id == version_id
                )
            ),
        )

    async def load_reading_document(self, version_id: UUID) -> ReadingDocumentV1 | None:
        record = await self.get_reading_document(version_id)
        if record is None:
            return None
        payload = self.cipher.decrypt_json(
            self._payload(
                record.payload_key_id,
                record.payload_nonce,
                record.payload_ciphertext,
                record.payload_digest,
            ),
            context=f"reading-version:{version_id}:reading-document",
        )
        return ReadingDocumentV1.model_validate(payload)

    async def mark_delayed(self, job_id: str, at: datetime) -> None:
        del at
        job, version = await self._job_and_version(job_id)
        version.status = ReadingStatus.DELAYED.value
        job.status = "delayed"
        await self.session.flush()

    async def mark_runtime_unknown(self, job_id: str, at: datetime) -> None:
        del at
        job, version = await self._job_and_version(job_id)
        version.status = ReadingStatus.RUNTIME_UNKNOWN.value
        job.status = "runtime_unknown"
        await self.session.flush()

    async def get_fact_brief(self, version_id: UUID) -> FactBrief | None:
        fact_brief: FactBrief | None = await self.session.scalar(
            select(FactBrief).where(FactBrief.reading_version_id == version_id)
        )
        return fact_brief

    async def get_accepted_copy(self, version_id: UUID) -> AcceptedCopy | None:
        accepted_copy: AcceptedCopy | None = await self.session.scalar(
            select(AcceptedCopy).where(AcceptedCopy.reading_version_id == version_id)
        )
        return accepted_copy

    async def _job_and_version(
        self,
        job_id: str,
    ) -> tuple[ReadingJobRecord, ReadingVersion]:
        job = await self.session.get(ReadingJobRecord, UUID(job_id))
        if job is None:
            raise LookupError("Reading Job not found")
        version = await self.session.get(ReadingVersion, job.reading_version_id)
        if version is None:
            raise ImmutableRecordError("Reading Job points to a missing version")
        return job, version

    async def _insert_attempt(
        self,
        version: ReadingVersion,
        attempt_number: int,
        candidate: NarrativeCandidate | None,
        guard_errors: tuple[str, ...],
        model_receipt: ModelCallReceipt | None,
    ) -> None:
        existing = await self.session.scalar(
            select(GenerationAttempt).where(
                GenerationAttempt.reading_version_id == version.id,
                GenerationAttempt.attempt_number == attempt_number,
            )
        )
        if existing is not None:
            raise ImmutableRecordError("Generation Attempt already exists")
        encrypted: EncryptedPayload | None = None
        if candidate is not None:
            encrypted = self.cipher.encrypt_json(
                candidate.to_dict(),
                context=(f"reading-version:{version.id}:candidate:{attempt_number}"),
            )
        self.session.add(
            GenerationAttempt(
                id=uuid4(),
                reading_version_id=version.id,
                attempt_number=attempt_number,
                candidate_key_id=None if encrypted is None else encrypted.key_id,
                candidate_nonce=None if encrypted is None else encrypted.nonce,
                candidate_ciphertext=(None if encrypted is None else encrypted.ciphertext),
                candidate_digest=(None if encrypted is None else encrypted.fingerprint),
                guard_errors=list(guard_errors),
                model_receipt=None if model_receipt is None else model_receipt.to_dict(),
            )
        )

    def _set_state_token(self, version: ReadingVersion, token: str) -> None:
        encrypted = self.cipher.encrypt_text(
            token,
            context=f"reading-version:{version.id}:state-token",
        )
        if (
            version.state_token_fingerprint is not None
            and version.state_token_fingerprint != encrypted.fingerprint
        ):
            raise ImmutableRecordError("state token cannot change for a Reading Version")
        version.state_token_key_id = encrypted.key_id
        version.state_token_nonce = encrypted.nonce
        version.state_token_ciphertext = encrypted.ciphertext
        version.state_token_fingerprint = encrypted.fingerprint

    def _set_last_result(self, version: ReadingVersion, stopped: Stopped) -> None:
        encrypted = self.cipher.encrypt_json(
            stopped.to_dict(),
            context=f"reading-version:{version.id}:last-result",
        )
        version.last_result_key_id = encrypted.key_id
        version.last_result_nonce = encrypted.nonce
        version.last_result_ciphertext = encrypted.ciphertext
        version.last_result_digest = encrypted.fingerprint
        if stopped.failure is None:
            self._clear_runtime_failure_audit(version)
            return
        version.runtime_failure_schema_version = stopped.failure.schema_version
        version.runtime_failure_code = stopped.failure.code
        version.runtime_failure_category = stopped.failure.category
        version.runtime_failure_retryable = stopped.failure.retryable

    def _set_host_lifecycle_terminal(
        self,
        version: ReadingVersion,
        *,
        reason: str,
        public_copy: str,
    ) -> None:
        encrypted = self.cipher.encrypt_json(
            {
                "kind": HOST_LIFECYCLE_KIND,
                "reason": reason,
                "public_copy": public_copy,
            },
            context=f"reading-version:{version.id}:last-result",
        )
        version.last_result_key_id = encrypted.key_id
        version.last_result_nonce = encrypted.nonce
        version.last_result_ciphertext = encrypted.ciphertext
        version.last_result_digest = encrypted.fingerprint
        self._clear_runtime_failure_audit(version)

    def _decrypt_last_result_payload(
        self, version: ReadingVersion
    ) -> dict[str, Any] | None:
        if version.last_result_ciphertext is None:
            return None
        return self.cipher.decrypt_json(
            self._payload(
                version.last_result_key_id,
                version.last_result_nonce,
                version.last_result_ciphertext,
                version.last_result_digest,
            ),
            context=f"reading-version:{version.id}:last-result",
        )

    @staticmethod
    def _clear_runtime_failure_audit(version: ReadingVersion) -> None:
        version.runtime_failure_schema_version = None
        version.runtime_failure_code = None
        version.runtime_failure_category = None
        version.runtime_failure_retryable = None

    def _set_completion(self, version: ReadingVersion, public_copy: str) -> None:
        encrypted = self.cipher.encrypt_text(
            public_copy,
            context=f"reading-version:{version.id}:completion",
        )
        if version.completion_digest is not None:
            if version.completion_digest != encrypted.fingerprint:
                raise ImmutableRecordError("completion intent is first-write-wins")
            return
        version.completion_key_id = encrypted.key_id
        version.completion_nonce = encrypted.nonce
        version.completion_ciphertext = encrypted.ciphertext
        version.completion_digest = encrypted.fingerprint

    @staticmethod
    def _payload(
        key_id: str | None,
        nonce: str | None,
        ciphertext: str | None,
        fingerprint: str | None,
    ) -> EncryptedPayload:
        if None in (key_id, nonce, ciphertext, fingerprint):
            raise ImmutableRecordError("encrypted payload columns are incomplete")
        return EncryptedPayload(
            key_id=str(key_id),
            nonce=str(nonce),
            ciphertext=str(ciphertext),
            fingerprint=str(fingerprint),
        )

    def _decrypt_optional_text(
        self,
        key_id: str | None,
        nonce: str | None,
        ciphertext: str | None,
        fingerprint: str | None,
        *,
        context: str,
    ) -> str | None:
        if all(value is None for value in (key_id, nonce, ciphertext, fingerprint)):
            return None
        return self.cipher.decrypt_text(
            self._payload(key_id, nonce, ciphertext, fingerprint),
            context=context,
        )
