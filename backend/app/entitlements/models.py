"""Minimal owner capability switches for internal dogfood.

Not a payment ledger: no SKU, no quantity burn, no refunds.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.identity.models import Base


class OwnerCapabilityGrant(Base):
    __tablename__ = "owner_capability_grants"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "capability_id",
            name="uq_owner_capability_grants_owner_capability",
        ),
        Index("ix_owner_capability_grants_owner_user_id", "owner_user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    capability_id: Mapped[str] = mapped_column(String(32), nullable=False)
    granted_by: Mapped[str] = mapped_column(String(120), nullable=False, default="dogfood-script")
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
