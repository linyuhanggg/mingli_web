from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.identity.models import GuestSession
from app.profiles.models import ProfileVersion, SubjectProfile
from app.profiles.repository import ProfileRepository
from app.profiles.schemas import ProfileConfirmRequest, ProfileSummary
from app.readings.models import ReadingIdempotencyKey, ReadingRoot
from app.security.envelope import EnvelopeCipher


class ProfileNotFoundError(LookupError):
    """A Draft or Profile Version is missing or belongs to another owner."""


class ProfileAlreadyConfirmedError(ValueError):
    """A Draft already owns an immutable Profile Version."""


class GuestAlreadyClaimedError(ValueError):
    """The Guest Session is already bound to a verified User."""


class OwnerProtocol(Protocol):
    @property
    def kind(self) -> Literal["user", "guest"]: ...

    @property
    def id(self) -> UUID: ...


def owner_ids(owner: OwnerProtocol) -> tuple[UUID | None, UUID | None]:
    if owner.kind == "user":
        return owner.id, None
    return None, owner.id


class ProfileService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.repository = ProfileRepository(
            session,
            EnvelopeCipher.from_settings(settings),
        )

    async def create_draft(
        self,
        owner: OwnerProtocol,
        label: str | None = None,
    ) -> UUID:
        user_id, guest_id = owner_ids(owner)
        profile = await self.repository.create_profile(
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
            label=label,
        )
        return profile.id

    async def confirm_draft(
        self,
        owner: OwnerProtocol,
        draft_id: UUID,
        payload: ProfileConfirmRequest,
    ) -> ProfileSummary:
        user_id, guest_id = owner_ids(owner)
        draft = await self.repository.get_owned_draft(
            draft_id,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        if draft is None:
            raise ProfileNotFoundError("Profile Draft not found")
        try:
            version = await self.repository.create_version_if_unconfirmed(
                profile_id=draft.id,
                payload=_version_payload(payload),
            )
        except LookupError as error:
            raise ProfileNotFoundError("Profile Draft not found") from error
        except ValueError as error:
            raise ProfileAlreadyConfirmedError(
                "Profile Draft is already confirmed"
            ) from error
        except IntegrityError as error:
            raise ProfileAlreadyConfirmedError(
                "Profile Draft is already confirmed"
            ) from error
        await self.session.refresh(version)
        return _summary(draft.id, version)

    async def append_version(
        self,
        owner: OwnerProtocol,
        profile_id: UUID,
        payload: ProfileConfirmRequest,
    ) -> ProfileSummary:
        """Edit a Profile: append a new immutable Version under the same Root."""
        user_id, guest_id = owner_ids(owner)
        profile = await self.repository.get_owned_draft(
            profile_id,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        if profile is None:
            raise ProfileNotFoundError("Subject Profile not found")
        try:
            version = await self.repository.create_version(
                profile_id=profile.id,
                payload=_version_payload(payload),
            )
        except LookupError as error:
            raise ProfileNotFoundError("Subject Profile not found") from error
        await self.session.refresh(version)
        return _summary(profile.id, version)

    async def list_profiles(self, owner: OwnerProtocol) -> list[ProfileSummary]:
        user_id, guest_id = owner_ids(owner)
        rows = await self.repository.list_latest_versions(
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        return [_summary(profile.id, version) for profile, version in rows]

    async def get_owned_profile_version(
        self,
        owner: OwnerProtocol,
        version_id: UUID,
    ) -> tuple[SubjectProfile, ProfileVersion]:
        user_id, guest_id = owner_ids(owner)
        found = await self.repository.get_owned_profile_version(
            version_id,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        if found is None:
            raise ProfileNotFoundError("Profile Version not found")
        return found

    async def claim_guest_ownership(
        self,
        guest: GuestSession,
        user_id: UUID,
    ) -> None:
        """Atomically move every Guest-owned resource onto the verified User."""
        locked_guest = await self.session.scalar(
            select(GuestSession)
            .where(GuestSession.id == guest.id)
            .with_for_update()
        )
        if locked_guest is None or locked_guest.claimed_at is not None:
            raise GuestAlreadyClaimedError("Guest Session is already claimed")
        now = datetime.now(UTC)
        guest.claimed_at = now
        guest.claimed_by_user_id = user_id
        await self.session.execute(
            update(SubjectProfile)
            .where(SubjectProfile.owner_guest_session_id == guest.id)
            .values(
                owner_user_id=user_id,
                owner_guest_session_id=None,
            )
        )
        await self.session.execute(
            update(ReadingRoot)
            .where(ReadingRoot.owner_guest_session_id == guest.id)
            .values(
                owner_user_id=user_id,
                owner_guest_session_id=None,
            )
        )
        guest_key_hashes = select(ReadingIdempotencyKey.key_hash).where(
            ReadingIdempotencyKey.owner_guest_session_id == guest.id
        )
        await self.session.execute(
            delete(ReadingIdempotencyKey).where(
                ReadingIdempotencyKey.owner_user_id == user_id,
                ReadingIdempotencyKey.key_hash.in_(guest_key_hashes),
            )
        )
        await self.session.execute(
            update(ReadingIdempotencyKey)
            .where(ReadingIdempotencyKey.owner_guest_session_id == guest.id)
            .values(
                owner_user_id=user_id,
                owner_guest_session_id=None,
            )
        )


def _version_payload(payload: ProfileConfirmRequest) -> dict[str, object]:
    return {
        "birth_datetime": payload.birth_datetime,
        "timezone": payload.timezone,
        "location": payload.location,
        "gender": payload.gender,
        "calendar": payload.calendar,
        "lunar_leap_month": payload.lunar_leap_month,
        "birth_time_certainty": payload.birth_time_certainty,
        "time_basis_policy": payload.time_basis_policy,
        "zi_hour_policy": payload.zi_hour_policy,
        "longitude": payload.longitude,
        "latitude": payload.latitude,
        "coordinate_source": payload.coordinate_source,
        "coordinate_precision": payload.coordinate_precision,
    }


def _summary(profile_id: UUID, version: ProfileVersion) -> ProfileSummary:
    return ProfileSummary(
        profile_id=profile_id,
        profile_version_id=version.id,
        subject_ref=f"profile-version:{version.id}",
        version=version.version,
        created_at=version.created_at,
    )
