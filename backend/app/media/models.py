from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv
from sqlalchemy.types import Uuid

from app.identity.models import Base


class PhysiognomyMediaRecord(Base):
    """Owner-scoped metadata for a private physiognomy media object.

    Raw bytes stay in a private object store. This row deliberately keeps no
    filename, public URL, or derived image data.
    """

    __tablename__ = "physiognomy_media_assets"
    __table_args__ = (
        CheckConstraint(
            "(owner_user_id IS NOT NULL AND owner_guest_session_id IS NULL) "
            "OR (owner_user_id IS NULL AND owner_guest_session_id IS NOT NULL)",
            name=conv("ck_physiognomy_media_assets_ck_physiognomy_media_assets_b727"),
        ),
        CheckConstraint(
            "status IN ('ready', 'deleted', 'expired')",
            name=conv("ck_physiognomy_media_assets_ck_physiognomy_media_assets_efb3"),
        ),
        CheckConstraint(
            "mode IN ('face', 'palm', 'posture', 'combined')",
            name=conv("ck_physiognomy_media_assets_ck_physiognomy_media_assets_79ae"),
        ),
        CheckConstraint(
            "content_type IN ('image/jpeg', 'image/png', 'image/heic')",
            name=conv("ck_physiognomy_media_assets_ck_physiognomy_media_assets_ca93"),
        ),
        CheckConstraint(
            "byte_size > 0 AND byte_size <= 10485760",
            name=conv("ck_physiognomy_media_assets_ck_physiognomy_media_assets_7c59"),
        ),
        CheckConstraint(
            "width >= 640 AND height >= 640",
            name=conv("ck_physiognomy_media_assets_ck_physiognomy_media_assets_88b6"),
        ),
        UniqueConstraint("object_key", name="uq_physiognomy_media_assets_object_key"),
        Index("ix_physiognomy_media_assets_owner_user_id", "owner_user_id"),
        Index("ix_physiognomy_media_assets_owner_guest_session_id", "owner_guest_session_id"),
        Index("ix_physiognomy_media_assets_status_expires_at", "status", "expires_at"),
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
    object_key: Mapped[str] = mapped_column(String(240), nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    consent_policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        default="ready",
        server_default="ready",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
