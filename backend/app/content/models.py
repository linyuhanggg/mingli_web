from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.identity.models import Base


class ContentRevisionRecord(Base):
    __tablename__ = "content_revisions"
    __table_args__ = (
        UniqueConstraint(
            "content_key",
            "locale",
            "revision",
            name="uq_content_revisions_key_locale_revision",
        ),
        Index("ix_content_revisions_key_locale_state", "content_key", "locale", "state"),
        Index(
            "ix_content_revisions_locale_topic_state",
            "locale",
            "topic",
            "state",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    content_key: Mapped[str] = mapped_column(String(160), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False, default="zh-CN")
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    author_staff_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("staff_users.id", ondelete="SET NULL"),
    )
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
