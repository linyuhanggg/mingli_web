from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.entitlements.models import OwnerCapabilityGrant


class EntitlementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_grant(
        self,
        *,
        owner_user_id: UUID,
        capability_id: str,
    ) -> OwnerCapabilityGrant | None:
        grant: OwnerCapabilityGrant | None = await self.session.scalar(
            select(OwnerCapabilityGrant).where(
                OwnerCapabilityGrant.owner_user_id == owner_user_id,
                OwnerCapabilityGrant.capability_id == capability_id,
                OwnerCapabilityGrant.revoked_at.is_(None),
            )
        )
        return grant

    async def list_active_grants(self, *, owner_user_id: UUID) -> list[OwnerCapabilityGrant]:
        rows = await self.session.scalars(
            select(OwnerCapabilityGrant).where(
                OwnerCapabilityGrant.owner_user_id == owner_user_id,
                OwnerCapabilityGrant.revoked_at.is_(None),
            )
        )
        return list(rows)

    async def upsert_grant(
        self,
        *,
        owner_user_id: UUID,
        capability_id: str,
        granted_by: str,
        note: str | None,
        now: datetime,
    ) -> OwnerCapabilityGrant:
        existing = await self.session.scalar(
            select(OwnerCapabilityGrant).where(
                OwnerCapabilityGrant.owner_user_id == owner_user_id,
                OwnerCapabilityGrant.capability_id == capability_id,
            )
        )
        if existing is None:
            grant = OwnerCapabilityGrant(
                owner_user_id=owner_user_id,
                capability_id=capability_id,
                granted_by=granted_by,
                note=note,
                created_at=now,
                revoked_at=None,
            )
            self.session.add(grant)
            await self.session.flush()
            return grant

        existing.granted_by = granted_by
        existing.note = note
        existing.revoked_at = None
        if existing.created_at is None:
            existing.created_at = now
        await self.session.flush()
        return existing

    async def revoke_grant(
        self,
        *,
        owner_user_id: UUID,
        capability_id: str,
        now: datetime,
    ) -> bool:
        grant = await self.get_active_grant(
            owner_user_id=owner_user_id,
            capability_id=capability_id,
        )
        if grant is None:
            return False
        grant.revoked_at = now
        await self.session.flush()
        return True

    async def revoke_all_for_user(self, *, owner_user_id: UUID, now: datetime) -> int:
        grants = await self.list_active_grants(owner_user_id=owner_user_id)
        for grant in grants:
            grant.revoked_at = now
        await self.session.flush()
        return len(grants)
