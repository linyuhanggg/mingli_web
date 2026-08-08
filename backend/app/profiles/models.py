from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.identity.models import Base
from app.persistence import ImmutableRecordError


class SubjectProfile(Base):
    __tablename__ = "subject_profiles"
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
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ProfileVersion(Base):
    __tablename__ = "profile_versions"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "version",
            name="uq_profile_versions_profile_id_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("subject_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    payload_key_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    payload_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


@event.listens_for(ProfileVersion, "before_update")
def _profile_versions_are_immutable(*_: object) -> None:
    raise ImmutableRecordError("ProfileVersion rows are immutable")
