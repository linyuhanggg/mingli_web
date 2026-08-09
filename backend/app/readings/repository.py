from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.persistence import ImmutableRecordError as ImmutableRecordError
from app.profiles.models import ProfileVersion, SubjectProfile
from app.readings.model_contracts import ModelCallReceipt
from app.readings.models import (
    AcceptedCopy,
    FactBrief,
    GenerationAttempt,
    ReadingIdempotencyKey,
    ReadingJobRecord,
    ReadingRoot,
    ReadingVerification,
    ReadingVersion,
    RuntimeRelease,
)
from app.readings.narrative_contracts import NarrativeCandidate, OutputContract
from app.readings.orchestrator import ReadingCheckpoint, ReadingJob
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
        owner_user_id: UUID | None = None,
        owner_guest_session_id: UUID | None = None,
        profile_version_id: UUID | None = None,
    ) -> ReadingRoot:
        if (owner_user_id is None) == (owner_guest_session_id is None):
            raise ValueError("a Reading Root must have exactly one User or Guest owner")
        if profile_version_id is not None:
            profile_version = await self.session.get(ProfileVersion, profile_version_id)
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
        root = ReadingRoot(
            id=uuid4(),
            owner_user_id=owner_user_id,
            owner_guest_session_id=owner_guest_session_id,
            profile_version_id=profile_version_id,
            capability_id=capability_id,
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
    ) -> ReadingVersion:
        root = await self.session.scalar(reading_root_version_lock_statement(reading_root_id))
        if root is None:
            raise LookupError("Reading Root not found")
        capability_id = str(prepare_command.intent["capability_id"])
        if root.capability_id != capability_id:
            raise ValueError("Prepare capability_id must match the locked Reading Root capability")
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
    ) -> None:
        """Persist the resumed Prepare for a waiting_input Reading Version."""
        version = await self.session.scalar(
            select(ReadingVersion)
            .where(ReadingVersion.id == version_id)
            .with_for_update()
        )
        if version is None:
            raise LookupError("Reading Version not found")
        if version.status != ReadingStatus.WAITING_INPUT.value:
            raise ValueError("Reading Version is not waiting for input")
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
        version.last_result_key_id = None
        version.last_result_nonce = None
        version.last_result_ciphertext = None
        version.last_result_digest = None
        await self.session.flush()

    async def create_job(
        self,
        *,
        reading_version_id: UUID,
        narrative_policy_version: str,
        output_contract: OutputContract,
        language: str,
        max_output_chars: int,
        max_attempts: int,
        available_at: datetime | None = None,
    ) -> ReadingJobRecord:
        job = ReadingJobRecord(
            id=uuid4(),
            reading_version_id=reading_version_id,
            status="queued",
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
        if version.last_result_ciphertext is None:
            return None
        payload = self.cipher.decrypt_json(
            self._payload(
                version.last_result_key_id,
                version.last_result_nonce,
                version.last_result_ciphertext,
                version.last_result_digest,
            ),
            context=f"reading-version:{version.id}:last-result",
        )
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
        return ReadingJob(
            id=str(job.id),
            prepare_command=command,
            narrative_policy_version=job.narrative_policy_version,
            output_contract=OutputContract.from_dict(job.output_contract),
            language=job.language,
            max_output_chars=job.max_output_chars,
            max_attempts=job.max_attempts,
        )

    async def load_checkpoint(self, job_id: str) -> ReadingCheckpoint:
        _job, version = await self._job_and_version(job_id)
        stopped: Stopped | None = None
        if version.last_result_ciphertext is not None:
            result_payload = self.cipher.decrypt_json(
                self._payload(
                    version.last_result_key_id,
                    version.last_result_nonce,
                    version.last_result_ciphertext,
                    version.last_result_digest,
                ),
                context=f"reading-version:{version.id}:last-result",
            )
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
        )

    async def record_waiting_input(
        self,
        job_id: str,
        stopped: Stopped,
        at: datetime,
    ) -> None:
        del at
        job, version = await self._job_and_version(job_id)
        if stopped.state_token is not None:
            self._set_state_token(version, stopped.state_token)
        self._set_last_result(version, stopped)
        version.status = ReadingStatus.WAITING_INPUT.value
        job.status = "waiting_input"
        await self.session.flush()

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
