"""Persistence helpers for staff admin."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_staff_users(self) -> int:
        result = await self.session.scalar(select(func.count()).select_from(StaffUser))
        return int(result or 0)

    async def get_staff_by_email(self, email: str) -> StaffUser | None:
        result: StaffUser | None = await self.session.scalar(
            select(StaffUser).where(
                StaffUser.email == email,
                StaffUser.status == "active",
            )
        )
        return result

    async def get_staff(self, staff_id: UUID) -> StaffUser | None:
        return await self.session.get(StaffUser, staff_id)

    def add_staff(self, staff: StaffUser) -> None:
        self.session.add(staff)

    def add_session(self, session: StaffSession) -> None:
        self.session.add(session)

    def add_audit(self, event: AdminAuditEvent) -> None:
        self.session.add(event)

    async def get_active_session(
        self,
        token_hash: str,
        now: datetime,
    ) -> StaffSession | None:
        result: StaffSession | None = await self.session.scalar(
            select(StaffSession).where(
                StaffSession.token_hash == token_hash,
                StaffSession.revoked_at.is_(None),
                StaffSession.expires_at > now,
            )
        )
        return result

    async def revoke_session(self, session: StaffSession, revoked_at: datetime) -> None:
        session.revoked_at = revoked_at
