from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.identity.models import Base
from app.persistence import ImmutableRecordError

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class RuntimeRelease(Base):
    __tablename__ = "runtime_releases"
    __table_args__ = (
        UniqueConstraint(
            "release_manifest_digest",
            name="uq_runtime_releases_release_manifest_digest",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    source_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    release_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    protocol_version: Mapped[str] = mapped_column(String(80), nullable=False)
    describe_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    image_digest: Mapped[str | None] = mapped_column(String(160))
    production_ready: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ReadingRoot(Base):
    __tablename__ = "reading_roots"
    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_guest_session_id IS NULL) "
            "OR (owner_user_id IS NULL AND owner_guest_session_id IS NOT NULL)",
            name="owner_exactly_one",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    owner_guest_session_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("guest_sessions.id", ondelete="CASCADE"),
    )
    profile_version_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("profile_versions.id", ondelete="RESTRICT"),
    )
    capability_id: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ReadingVersion(Base):
    __tablename__ = "reading_versions"
    __table_args__ = (
        UniqueConstraint(
            "reading_root_id",
            "version",
            name="uq_reading_versions_reading_root_id_version",
        ),
        CheckConstraint(
            "(state_token_key_id IS NULL AND state_token_nonce IS NULL "
            "AND state_token_ciphertext IS NULL AND state_token_fingerprint IS NULL) "
            "OR (state_token_key_id IS NOT NULL AND state_token_nonce IS NOT NULL "
            "AND state_token_ciphertext IS NOT NULL "
            "AND state_token_fingerprint IS NOT NULL)",
            name="state_token_envelope_all_or_none",
        ),
        CheckConstraint(
            "(last_result_key_id IS NULL AND last_result_nonce IS NULL "
            "AND last_result_ciphertext IS NULL AND last_result_digest IS NULL) "
            "OR (last_result_key_id IS NOT NULL AND last_result_nonce IS NOT NULL "
            "AND last_result_ciphertext IS NOT NULL AND last_result_digest IS NOT NULL)",
            name="last_result_envelope_all_or_none",
        ),
        CheckConstraint(
            "(completion_key_id IS NULL AND completion_nonce IS NULL "
            "AND completion_ciphertext IS NULL AND completion_digest IS NULL) "
            "OR (completion_key_id IS NOT NULL AND completion_nonce IS NOT NULL "
            "AND completion_ciphertext IS NOT NULL AND completion_digest IS NOT NULL)",
            name="completion_envelope_all_or_none",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reading_root_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("reading_roots.id", ondelete="CASCADE"),
        nullable=False,
    )
    runtime_release_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("runtime_releases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="input_ready", nullable=False)
    capability_id: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[str] = mapped_column(String(80), nullable=False)
    dimension_ids: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    horizon: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    prepare_key_id: Mapped[str] = mapped_column(String(120), nullable=False)
    prepare_nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    prepare_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    prepare_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    prepare_has_state_token: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    state_token_key_id: Mapped[str | None] = mapped_column(String(120))
    state_token_nonce: Mapped[str | None] = mapped_column(String(64))
    state_token_ciphertext: Mapped[str | None] = mapped_column(Text)
    state_token_fingerprint: Mapped[str | None] = mapped_column(String(64))
    last_result_key_id: Mapped[str | None] = mapped_column(String(120))
    last_result_nonce: Mapped[str | None] = mapped_column(String(64))
    last_result_ciphertext: Mapped[str | None] = mapped_column(Text)
    last_result_digest: Mapped[str | None] = mapped_column(String(64))
    completion_key_id: Mapped[str | None] = mapped_column(String(120))
    completion_nonce: Mapped[str | None] = mapped_column(String(64))
    completion_ciphertext: Mapped[str | None] = mapped_column(Text)
    completion_digest: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class FactBrief(Base):
    __tablename__ = "fact_briefs"
    __table_args__ = (
        UniqueConstraint(
            "reading_version_id",
            name="uq_fact_briefs_reading_version_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reading_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("reading_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    payload_key_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class GenerationAttempt(Base):
    __tablename__ = "generation_attempts"
    __table_args__ = (
        UniqueConstraint(
            "reading_version_id",
            "attempt_number",
            name="uq_generation_attempts_reading_version_id_attempt_number",
        ),
        CheckConstraint(
            "(candidate_key_id IS NULL AND candidate_nonce IS NULL "
            "AND candidate_ciphertext IS NULL AND candidate_digest IS NULL) "
            "OR (candidate_key_id IS NOT NULL AND candidate_nonce IS NOT NULL "
            "AND candidate_ciphertext IS NOT NULL AND candidate_digest IS NOT NULL)",
            name="candidate_envelope_all_or_none",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reading_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("reading_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(nullable=False)
    candidate_key_id: Mapped[str | None] = mapped_column(String(120))
    candidate_nonce: Mapped[str | None] = mapped_column(String(64))
    candidate_ciphertext: Mapped[str | None] = mapped_column(Text)
    candidate_digest: Mapped[str | None] = mapped_column(String(64))
    guard_errors: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    model_receipt: Mapped[dict[str, object] | None] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class AcceptedCopy(Base):
    __tablename__ = "accepted_copies"
    __table_args__ = (
        UniqueConstraint(
            "reading_version_id",
            name="uq_accepted_copies_reading_version_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reading_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("reading_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    payload_key_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    public_copy_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReadingJobRecord(Base):
    __tablename__ = "reading_jobs"
    __table_args__ = (
        Index(
            "uq_reading_jobs_active_version",
            "reading_version_id",
            unique=True,
            sqlite_where=text("status IN ('queued', 'claimed', 'running')"),
            postgresql_where=text("status IN ('queued', 'claimed', 'running')"),
        ),
        Index("ix_reading_jobs_claim", "status", "available_at"),
        CheckConstraint(
            "(lease_owner IS NULL AND lease_token IS NULL AND lease_expires_at IS NULL) "
            "OR (lease_owner IS NOT NULL AND lease_token IS NOT NULL "
            "AND lease_expires_at IS NOT NULL)",
            name="lease_envelope_all_or_none",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reading_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("reading_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    narrative_policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    output_contract: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    max_output_chars: Mapped[int] = mapped_column(nullable=False)
    max_attempts: Mapped[int] = mapped_column(nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_generation: Mapped[int] = mapped_column(
        default=0,
        server_default=text("0"),
        nullable=False,
    )
    lease_owner: Mapped[str | None] = mapped_column(String(120))
    lease_token: Mapped[str | None] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ReadingIdempotencyKey(Base):
    """One persisted Idempotency-Key maps to one Reading Version per owner."""

    __tablename__ = "reading_idempotency_keys"
    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_guest_session_id IS NULL) "
            "OR (owner_user_id IS NULL AND owner_guest_session_id IS NOT NULL)",
            name="owner_exactly_one",
        ),
        Index(
            "uq_reading_idem_user_key",
            "key_hash",
            "owner_user_id",
            unique=True,
            sqlite_where=text("owner_user_id IS NOT NULL"),
            postgresql_where=text("owner_user_id IS NOT NULL"),
        ),
        Index(
            "uq_reading_idem_guest_key",
            "key_hash",
            "owner_guest_session_id",
            unique=True,
            sqlite_where=text("owner_guest_session_id IS NOT NULL"),
            postgresql_where=text("owner_guest_session_id IS NOT NULL"),
        ),
        Index(
            "ix_reading_idempotency_keys_reading_version_id",
            "reading_version_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    owner_guest_session_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("guest_sessions.id", ondelete="SET NULL"),
    )
    reading_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("reading_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ReadingVerification(Base):
    """User feedback kept outside the model and runtime command path."""

    __tablename__ = "reading_verifications"
    __table_args__ = (
        UniqueConstraint(
            "reading_version_id",
            name="uq_reading_verifications_reading_version_id",
        ),
        CheckConstraint(
            "outcome IN ('accepted', 'partial', 'disagreed', 'unknown')",
            name="outcome_allowed",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reading_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("reading_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


for immutable_model in (RuntimeRelease, FactBrief, GenerationAttempt, AcceptedCopy):
    event.listen(
        immutable_model,
        "before_update",
        lambda *_: (_ for _ in ()).throw(
            ImmutableRecordError("append-only reading records are immutable")
        ),
    )
