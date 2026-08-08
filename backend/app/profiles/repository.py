from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.profiles.models import ProfileVersion, SubjectProfile
from app.security.envelope import EncryptedPayload, EnvelopeCipher


def subject_profile_version_lock_statement(
    profile_id: UUID,
) -> Select[tuple[SubjectProfile]]:
    """Serialize immutable Profile Version allocation per Subject Profile."""
    return select(SubjectProfile).where(SubjectProfile.id == profile_id).with_for_update()


class ProfileRepository:
    def __init__(self, session: AsyncSession, cipher: EnvelopeCipher) -> None:
        self.session = session
        self.cipher = cipher

    async def create_profile(
        self,
        *,
        owner_user_id: UUID | None = None,
        owner_guest_session_id: UUID | None = None,
    ) -> SubjectProfile:
        if (owner_user_id is None) == (owner_guest_session_id is None):
            raise ValueError("a profile must have exactly one User or Guest owner")
        profile = SubjectProfile(
            id=uuid4(),
            owner_user_id=owner_user_id,
            owner_guest_session_id=owner_guest_session_id,
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def create_version(
        self,
        *,
        profile_id: UUID,
        payload: Mapping[str, object],
    ) -> ProfileVersion:
        profile = await self.session.scalar(subject_profile_version_lock_statement(profile_id))
        if profile is None:
            raise LookupError("Subject Profile not found")
        current = await self.session.scalar(
            select(func.max(ProfileVersion.version)).where(ProfileVersion.profile_id == profile_id)
        )
        version_number = (current or 0) + 1
        version_id = uuid4()
        encrypted = self.cipher.encrypt_json(
            payload,
            context=f"profile-version:{version_id}",
        )
        version = ProfileVersion(
            id=version_id,
            profile_id=profile_id,
            version=version_number,
            payload_key_id=encrypted.key_id,
            payload_nonce=encrypted.nonce,
            payload_ciphertext=encrypted.ciphertext,
            payload_fingerprint=encrypted.fingerprint,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def load_version_payload(self, version_id: UUID) -> dict[str, object]:
        version = await self.session.get(ProfileVersion, version_id)
        if version is None:
            raise LookupError("ProfileVersion not found")
        payload = EncryptedPayload(
            key_id=version.payload_key_id,
            nonce=version.payload_nonce,
            ciphertext=version.payload_ciphertext,
            fingerprint=version.payload_fingerprint,
        )
        return self.cipher.decrypt_json(
            payload,
            context=f"profile-version:{version.id}",
        )
