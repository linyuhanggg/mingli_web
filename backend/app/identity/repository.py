from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models import (
    AuditEvent,
    ConsentRecord,
    DeviceSession,
    GuestSession,
    LoginIdentity,
    User,
    UserPasswordCredential,
)
from app.security.envelope import EnvelopeCipher


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
    ) -> tuple[User, LoginIdentity, bool]:
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
            return user, identity, False

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
        return user, identity, True

    async def store_destination(
        self,
        identity: LoginIdentity,
        destination: str,
        cipher: EnvelopeCipher,
    ) -> None:
        if identity.destination_ciphertext is not None:
            return
        encrypted = cipher.encrypt_text(
            destination,
            context=f"login-identity:{identity.id}",
        )
        identity.destination_key_id = encrypted.key_id
        identity.destination_nonce = encrypted.nonce
        identity.destination_ciphertext = encrypted.ciphertext
        identity.destination_fingerprint = encrypted.fingerprint
        await self.session.flush()

    async def find_identity(
        self,
        *,
        provider: str,
        provider_subject_hash: str,
    ) -> tuple[User, LoginIdentity] | None:
        identity = await self.session.scalar(
            select(LoginIdentity).where(
                LoginIdentity.provider == provider,
                LoginIdentity.provider_subject_hash == provider_subject_hash,
                LoginIdentity.status == "active",
            )
        )
        if identity is None:
            return None
        user = await self.session.get(User, identity.user_id)
        if user is None or user.status != "active":
            return None
        return user, identity

    async def get_password_credential(self, user_id: UUID) -> UserPasswordCredential | None:
        credential: UserPasswordCredential | None = await self.session.scalar(
            select(UserPasswordCredential).where(
                UserPasswordCredential.user_id == user_id,
            )
        )
        return credential

    async def save_password_credential(
        self,
        *,
        user_id: UUID,
        password_hash: str,
        updated_at: datetime,
    ) -> UserPasswordCredential:
        credential = await self.get_password_credential(user_id)
        if credential is None:
            credential = UserPasswordCredential(
                user_id=user_id,
                password_hash=password_hash,
                updated_at=updated_at,
            )
            self.session.add(credential)
        else:
            credential.password_hash = password_hash
            credential.updated_at = updated_at
        await self.session.flush()
        return credential

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

    async def revoke_active_device_sessions(
        self,
        user_id: UUID,
        revoked_at: datetime,
    ) -> int:
        sessions = list(
            await self.session.scalars(
                select(DeviceSession).where(
                    DeviceSession.user_id == user_id,
                    DeviceSession.revoked_at.is_(None),
                )
            )
        )
        for device_session in sessions:
            device_session.revoked_at = revoked_at
        return len(sessions)

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

    def add_consent_record(self, record: ConsentRecord) -> None:
        self.session.add(record)

    async def current_consent_keys(
        self,
        user_id: UUID,
        *,
        contexts: frozenset[str],
    ) -> set[str]:
        from app.identity.policy import CURRENT_POLICY_VERSION

        rows = await self.session.scalars(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.policy_version == CURRENT_POLICY_VERSION,
                ConsentRecord.context.in_(tuple(contexts)),
            )
        )
        return {row.policy_key for row in rows}
