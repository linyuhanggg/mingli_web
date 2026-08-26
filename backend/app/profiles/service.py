from datetime import UTC, date, datetime
from typing import Literal, Protocol
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.identity.models import GuestSession
from app.profiles.models import ProfileVersion, SubjectProfile
from app.profiles.repository import ProfileRepository
from app.profiles.schemas import (
    ProfileConfirmRequest,
    ProfileSummary,
    ProfileVersionRequest,
)
from app.readings.models import ReadingIdempotencyKey, ReadingRoot
from app.security.envelope import EnvelopeCipher


class ProfileNotFoundError(LookupError):
    """A Draft or Profile Version is missing or belongs to another owner."""


class ProfileAlreadyConfirmedError(ValueError):
    """A Draft already owns an immutable Profile Version."""


class GuestAlreadyClaimedError(ValueError):
    """The Guest Session is already bound to a verified User."""


class ProfileAuthorizationRequiredError(ValueError):
    """An explicitly authorized other-person profile was not confirmed."""


class ProfileAuthorizationPayloadError(ValueError):
    """Authorization flags contradict the selected subject type."""


class MinorGuardianConfirmationRequiredError(ValueError):
    """A minor profile is missing the required guardian confirmation."""


class ProfileDifferenceNotAcknowledgedError(ValueError):
    """An appended ProfileVersion was not confirmed as a visible difference."""


class ProfileNotConfirmedError(ValueError):
    """An append was requested for a SubjectProfile with no first version."""


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
        self._validate_authorization(payload)
        try:
            version = await self.repository.create_version_if_unconfirmed(
                profile_id=draft.id,
                payload={
                    "birth_datetime": payload.birth_datetime,
                    "timezone": payload.timezone,
                    "location": payload.location,
                    "gender": payload.gender,
                    "time_basis_policy": payload.time_basis_policy,
                    "zi_hour_policy": payload.zi_hour_policy,
                    "longitude": payload.longitude,
                    "latitude": payload.latitude,
                    "coordinate_source": payload.coordinate_source,
                },
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
        await self.repository.create_version_authorization(
            profile_version_id=version.id,
            subject_type=payload.subject_type,
            is_minor=payload.is_minor,
            authorization_confirmed=payload.authorization_confirmed,
            photo_authorization_confirmed=payload.photo_authorization_confirmed,
            minor_guardian_confirmed=payload.minor_guardian_confirmed,
            difference_acknowledged=False,
        )
        await self.session.refresh(version)
        return self._summary(draft, version)

    async def append_version(
        self,
        owner: OwnerProtocol,
        profile_id: UUID,
        payload: ProfileVersionRequest,
    ) -> ProfileSummary:
        user_id, guest_id = owner_ids(owner)
        profile = await self.repository.get_owned_profile(
            profile_id,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        if profile is None:
            raise ProfileNotFoundError("Subject Profile not found")
        has_version = await self.session.scalar(
            select(ProfileVersion.id).where(ProfileVersion.profile_id == profile.id).limit(1)
        )
        if has_version is None:
            raise ProfileNotConfirmedError("Subject Profile has no confirmed version")
        self._validate_version_authorization(payload)
        version = await self.repository.create_version(
            profile_id=profile.id,
            payload={
                "birth_datetime": payload.birth_datetime,
                "timezone": payload.timezone,
                "location": payload.location,
                "gender": payload.gender,
                "time_basis_policy": payload.time_basis_policy,
                "zi_hour_policy": payload.zi_hour_policy,
                "longitude": payload.longitude,
                "latitude": payload.latitude,
                "coordinate_source": payload.coordinate_source,
            },
        )
        await self.repository.create_version_authorization(
            profile_version_id=version.id,
            subject_type=payload.subject_type,
            is_minor=payload.is_minor,
            authorization_confirmed=payload.authorization_confirmed,
            photo_authorization_confirmed=payload.photo_authorization_confirmed,
            minor_guardian_confirmed=payload.minor_guardian_confirmed,
            difference_acknowledged=payload.difference_acknowledged,
        )
        await self.session.refresh(version)
        return self._summary(profile, version)

    async def list_profile_versions(
        self,
        owner: OwnerProtocol,
        profile_id: UUID,
    ) -> list[ProfileSummary]:
        user_id, guest_id = owner_ids(owner)
        profile = await self.repository.get_owned_profile(
            profile_id,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        if profile is None:
            raise ProfileNotFoundError("Subject Profile not found")
        versions = await self.repository.list_versions(profile.id)
        return [self._summary(profile, version) for version in versions]

    async def list_profiles(self, owner: OwnerProtocol) -> list[ProfileSummary]:
        user_id, guest_id = owner_ids(owner)
        rows = await self.repository.list_latest_versions(
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        return [self._summary(profile, version) for profile, version in rows]

    async def update_display_name(
        self,
        owner: OwnerProtocol,
        profile_id: UUID,
        display_name: str,
    ) -> ProfileSummary:
        user_id, guest_id = owner_ids(owner)
        profile = await self.repository.get_owned_profile(
            profile_id,
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        if profile is None:
            raise ProfileNotFoundError("Subject Profile not found")
        latest_version = await self.repository.get_latest_version(profile.id)
        if latest_version is None:
            raise ProfileNotConfirmedError("Subject Profile has no confirmed version")
        profile.label = display_name
        await self.session.flush()
        return self._summary(profile, latest_version)

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

    @staticmethod
    def _validate_authorization(payload: ProfileConfirmRequest) -> None:
        if payload.subject_type == "other" and not payload.authorization_confirmed:
            raise ProfileAuthorizationRequiredError(
                "authorization for the other person's profile is required"
            )
        if payload.subject_type == "self" and payload.authorization_confirmed:
            raise ProfileAuthorizationPayloadError(
                "a self profile cannot be marked as authorized for another person"
            )
        if payload.subject_type == "self" and payload.photo_authorization_confirmed:
            raise ProfileAuthorizationPayloadError(
                "a self profile cannot be marked as authorized for another person's photo"
            )
        # P6-004 user correction: do not reject minors without guardian confirmation.

    @staticmethod
    def _validate_version_authorization(payload: ProfileVersionRequest) -> None:
        ProfileService._validate_authorization(payload)
        if not payload.difference_acknowledged:
            raise ProfileDifferenceNotAcknowledgedError(
                "the visible difference from the previous ProfileVersion must be acknowledged"
            )

    def _summary(
        self,
        profile: SubjectProfile,
        version: ProfileVersion,
    ) -> ProfileSummary:
        payload = self.repository.decrypt_version_payload(version)
        return _summary(profile, version, payload)


def _summary(
    profile: SubjectProfile,
    version: ProfileVersion,
    payload: dict[str, object],
) -> ProfileSummary:
    return ProfileSummary(
        profile_id=profile.id,
        profile_version_id=version.id,
        subject_ref=f"profile-version:{version.id}",
        version=version.version,
        display_name=_display_name_projection(profile.label),
        birth_date=_birth_date_projection(payload),
        created_at=version.created_at,
    )


def _display_name_projection(label: str | None) -> str | None:
    if label is None or not label.strip():
        return None
    return label


def _birth_date_projection(payload: dict[str, object]) -> date | None:
    value = payload.get("birth_datetime")
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
