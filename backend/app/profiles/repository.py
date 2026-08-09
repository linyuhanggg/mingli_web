from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import cast
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
        label: str | None = None,
    ) -> SubjectProfile:
        if (owner_user_id is None) == (owner_guest_session_id is None):
            raise ValueError("a profile must have exactly one User or Guest owner")
        profile = SubjectProfile(
            id=uuid4(),
            owner_user_id=owner_user_id,
            owner_guest_session_id=owner_guest_session_id,
            label=label,
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
        return await self._insert_version(profile_id, payload)

    async def create_version_if_unconfirmed(
        self,
        *,
        profile_id: UUID,
        payload: Mapping[str, object],
    ) -> ProfileVersion:
        """Serialize version allocation with a FOR UPDATE row lock and re-check.

        The Subject Profile row lock is taken before the existing-version
        check so two concurrent confirms of the same Draft cannot both pass
        the pre-check and allocate two versions for one Draft.
        """
        profile = await self.session.scalar(subject_profile_version_lock_statement(profile_id))
        if profile is None:
            raise LookupError("Subject Profile not found")
        existing = await self.session.scalar(
            select(ProfileVersion.id).where(ProfileVersion.profile_id == profile_id).limit(1)
        )
        if existing is not None:
            raise ValueError("Subject Profile is already confirmed")
        return await self._insert_version(profile_id, payload)

    async def _insert_version(
        self,
        profile_id: UUID,
        payload: Mapping[str, object],
    ) -> ProfileVersion:
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

    async def get_owned_draft(
        self,
        draft_id: UUID,
        *,
        owner_user_id: UUID | None,
        owner_guest_session_id: UUID | None,
    ) -> SubjectProfile | None:
        profile = await self.session.scalar(
            select(SubjectProfile).where(
                SubjectProfile.id == draft_id,
                SubjectProfile.owner_user_id == owner_user_id,
                SubjectProfile.owner_guest_session_id == owner_guest_session_id,
            )
        )
        return profile

    async def get_owned_profile_version(
        self,
        version_id: UUID,
        *,
        owner_user_id: UUID | None,
        owner_guest_session_id: UUID | None,
    ) -> tuple[SubjectProfile, ProfileVersion] | None:
        version = await self.session.scalar(
            select(ProfileVersion).where(ProfileVersion.id == version_id)
        )
        if version is None:
            return None
        profile = await self.session.scalar(
            select(SubjectProfile).where(
                SubjectProfile.id == version.profile_id,
                SubjectProfile.owner_user_id == owner_user_id,
                SubjectProfile.owner_guest_session_id == owner_guest_session_id,
            )
        )
        if profile is None:
            return None
        return profile, version

    async def list_latest_versions(
        self,
        *,
        owner_user_id: UUID | None,
        owner_guest_session_id: UUID | None,
    ) -> list[tuple[SubjectProfile, ProfileVersion]]:
        latest_ids = (
            select(
                ProfileVersion.profile_id,
                func.max(ProfileVersion.version).label("latest_version"),
            )
            .join(
                SubjectProfile,
                SubjectProfile.id == ProfileVersion.profile_id,
            )
            .where(
                SubjectProfile.owner_user_id == owner_user_id,
                SubjectProfile.owner_guest_session_id == owner_guest_session_id,
            )
            .group_by(ProfileVersion.profile_id)
            .subquery()
        )
        result = await self.session.execute(
            select(SubjectProfile, ProfileVersion)
            .join(
                ProfileVersion,
                ProfileVersion.profile_id == SubjectProfile.id,
            )
            .join(
                latest_ids,
                (latest_ids.c.profile_id == ProfileVersion.profile_id)
                & (latest_ids.c.latest_version == ProfileVersion.version),
            )
            .order_by(ProfileVersion.created_at.desc(), ProfileVersion.id.desc())
        )
        return list(
            cast(Iterable[tuple[SubjectProfile, ProfileVersion]], result.all())
        )

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
