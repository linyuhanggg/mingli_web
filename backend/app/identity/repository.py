from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models import (
    AuditEvent,
    DeviceSession,
    GuestSession,
    LoginIdentity,
    User,
)


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def revoke_guest_session(self, token_hash: str, revoked_at: datetime) -> None:
        guest = await self.session.scalar(
            select(GuestSession).where(
                GuestSession.token_hash == token_hash,
                GuestSession.revoked_at.is_(None),
            )
        )
        if guest is not None:
            guest.revoked_at = revoked_at

    def add_guest_session(self, guest: GuestSession) -> None:
        self.session.add(guest)

    async def get_active_guest_session(
        self,
        token_hash: str,
        now: datetime,
    ) -> GuestSession | None:
        guest: GuestSession | None = await self.session.scalar(
            select(GuestSession).where(
                GuestSession.token_hash == token_hash,
                GuestSession.revoked_at.is_(None),
                GuestSession.claimed_at.is_(None),
                GuestSession.expires_at > now,
            )
        )
        return guest

    async def resolve_identity(
        self,
        *,
        provider: str,
        provider_subject_hash: str,
        masked_destination: str,
        verified_at: datetime,
    ) -> tuple[User, LoginIdentity]:
        identity = await self.session.scalar(
            select(LoginIdentity).where(
                LoginIdentity.provider == provider,
                LoginIdentity.provider_subject_hash == provider_subject_hash,
                LoginIdentity.status == "active",
            )
        )
        if identity is not None:
            user = await self.session.get(User, identity.user_id)
            if user is None or user.status != "active":
                raise RuntimeError("Identity points to an unavailable User")
            return user, identity

        user = User()
        self.session.add(user)
        await self.session.flush()
        identity = LoginIdentity(
            user_id=user.id,
            provider=provider,
            provider_subject_hash=provider_subject_hash,
            masked_destination=masked_destination,
            status="active",
            verified_at=verified_at,
        )
        self.session.add(identity)
        await self.session.flush()
        return user, identity

    def add_device_session(self, device_session: DeviceSession) -> None:
        self.session.add(device_session)

    async def get_active_device_session(
        self,
        token_hash: str,
        now: datetime,
    ) -> DeviceSession | None:
        device_session: DeviceSession | None = await self.session.scalar(
            select(DeviceSession).where(
                DeviceSession.token_hash == token_hash,
                DeviceSession.revoked_at.is_(None),
                DeviceSession.expires_at > now,
            )
        )
        return device_session

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def list_identities(self, user_id: UUID) -> list[LoginIdentity]:
        result = await self.session.scalars(
            select(LoginIdentity)
            .where(LoginIdentity.user_id == user_id, LoginIdentity.status == "active")
            .order_by(LoginIdentity.created_at, LoginIdentity.id)
        )
        return list(result)

    def add_audit_event(self, event: AuditEvent) -> None:
        self.session.add(event)
