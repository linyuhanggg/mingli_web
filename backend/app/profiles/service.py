from collections import Counter
from datetime import UTC, date, datetime
from typing import Literal, Protocol
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.identity.models import GuestSession
from app.profiles.models import ProfileVersion, ProfileVersionAuthorization, SubjectProfile
from app.profiles.repository import ProfileRepository
from app.profiles.schemas import (
    ProfileConfirmRequest,
    ProfileSummary,
    ProfileVersionRequest,
)
from app.readings.models import ReadingIdempotencyKey, ReadingRoot
from app.security.envelope import EnvelopeCipher

_DISPLAY_NAME_MAX_LENGTH = 80
_VERSION_FACT_KEYS = (
    "birth_datetime",
    "timezone",
    "location",
    "gender",
    "time_basis_policy",
    "zi_hour_policy",
    "longitude",
    "latitude",
    "coordinate_source",
)
_AUTHORIZATION_FACT_KEYS = (
    "subject_type",
    "is_minor",
    "authorization_confirmed",
    "photo_authorization_confirmed",
    "minor_guardian_confirmed",
)


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


class ProfileNameConflictError(ValueError):
    """An owner already has a confirmed profile with this name and birth date."""

    def __init__(
        self,
        *,
        existing_profile_id: UUID,
        existing_profile_version_id: UUID,
        display_name: str,
        suggested_save_as_name: str,
    ) -> None:
        super().__init__("a profile with this name and birth date already exists")
        self.existing_profile_id = existing_profile_id
        self.existing_profile_version_id = existing_profile_version_id
        self.display_name = display_name
        self.suggested_save_as_name = suggested_save_as_name


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
        birth_date = _birth_date_from_datetime(payload.birth_datetime)
        resolved_label = _resolved_display_name(draft.label, birth_date)
        conflict = await self._name_birth_conflict(
            owner,
            display_name=resolved_label,
            birth_date=birth_date,
            exclude_profile_id=draft.id,
        )
        if conflict is not None:
            existing_profile, existing_version = conflict
            suggested = await self._unique_save_as_name(
                owner,
                resolved_label,
                exclude_profile_id=draft.id,
            )
            if payload.on_name_conflict == "reject":
                raise ProfileNameConflictError(
                    existing_profile_id=existing_profile.id,
                    existing_profile_version_id=existing_version.id,
                    display_name=resolved_label,
                    suggested_save_as_name=suggested,
                )
            if payload.on_name_conflict == "overwrite":
                return await self._overwrite_existing_profile(
                    draft=draft,
                    existing_profile=existing_profile,
                    existing_version=existing_version,
                    payload=payload,
                )
            resolved_label = suggested
        draft.label = resolved_label
        try:
            version = await self.repository.create_version_if_unconfirmed(
                profile_id=draft.id,
                payload=_version_facts(payload),
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
            payload=_version_facts(payload),
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
        current = self._summary(profile, latest_version)
        conflict = await self._name_birth_conflict(
            owner,
            display_name=display_name,
            birth_date=current.birth_date,
            exclude_profile_id=profile.id,
        )
        if conflict is not None:
            existing_profile, existing_version = conflict
            suggested = await self._unique_save_as_name(
                owner,
                display_name,
                exclude_profile_id=profile.id,
            )
            raise ProfileNameConflictError(
                existing_profile_id=existing_profile.id,
                existing_profile_version_id=existing_version.id,
                display_name=display_name,
                suggested_save_as_name=suggested,
            )
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
        await self._rename_claimed_profile_conflicts(
            guest_id=guest.id,
            user_id=user_id,
        )
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

    async def _rename_claimed_profile_conflicts(
        self,
        *,
        guest_id: UUID,
        user_id: UUID,
    ) -> None:
        user_rows = await self.repository.list_latest_versions(
            owner_user_id=user_id,
            owner_guest_session_id=None,
        )
        guest_rows = await self.repository.list_latest_versions(
            owner_user_id=None,
            owner_guest_session_id=guest_id,
        )
        user_summaries = [
            self._summary(profile, version) for profile, version in user_rows
        ]
        guest_summaries = [
            (profile, self._summary(profile, version))
            for profile, version in guest_rows
        ]
        user_pairs = {
            (summary.display_name, summary.birth_date)
            for summary in user_summaries
            if summary.display_name is not None and summary.birth_date is not None
        }
        guest_pair_counts = Counter(
            (summary.display_name, summary.birth_date)
            for _, summary in guest_summaries
            if summary.display_name is not None and summary.birth_date is not None
        )
        taken_names = {
            summary.display_name
            for summary in user_summaries
            if summary.display_name is not None
        }
        taken_names.update(
            summary.display_name
            for _, summary in guest_summaries
            if summary.display_name is not None
        )
        conflicts: list[tuple[SubjectProfile, str]] = []
        for profile, summary in guest_summaries:
            display_name = summary.display_name
            birth_date = summary.birth_date
            if display_name is None or birth_date is None:
                continue
            pair = (display_name, birth_date)
            if pair in user_pairs or guest_pair_counts[pair] > 1:
                conflicts.append((profile, display_name))

        for profile, display_name in sorted(
            conflicts,
            key=lambda item: item[0].id.int,
        ):
            index = 2
            candidate = _save_as_candidate(display_name, index)
            while candidate in taken_names:
                index += 1
                candidate = _save_as_candidate(display_name, index)
            profile.label = candidate
            taken_names.add(candidate)
        if conflicts:
            await self.session.flush()

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

    async def _overwrite_existing_profile(
        self,
        *,
        draft: SubjectProfile,
        existing_profile: SubjectProfile,
        existing_version: ProfileVersion,
        payload: ProfileConfirmRequest,
    ) -> ProfileSummary:
        incoming = _version_facts(payload)
        stored = self.repository.decrypt_version_payload(existing_version)
        existing_authorization = await self.session.scalar(
            select(ProfileVersionAuthorization).where(
                ProfileVersionAuthorization.profile_version_id == existing_version.id
            )
        )
        if _facts_match(stored, incoming) and _authorization_facts_match(
            existing_authorization,
            payload,
        ):
            await self.session.delete(draft)
            await self.session.flush()
            return self._summary(existing_profile, existing_version)
        version = await self.repository.create_version(
            profile_id=existing_profile.id,
            payload=incoming,
        )
        await self.repository.create_version_authorization(
            profile_version_id=version.id,
            subject_type=payload.subject_type,
            is_minor=payload.is_minor,
            authorization_confirmed=payload.authorization_confirmed,
            photo_authorization_confirmed=payload.photo_authorization_confirmed,
            minor_guardian_confirmed=payload.minor_guardian_confirmed,
            difference_acknowledged=True,
        )
        await self.session.delete(draft)
        await self.session.flush()
        await self.session.refresh(version)
        return self._summary(existing_profile, version)

    async def _name_birth_conflict(
        self,
        owner: OwnerProtocol,
        *,
        display_name: str,
        birth_date: date | None,
        exclude_profile_id: UUID,
    ) -> tuple[SubjectProfile, ProfileVersion] | None:
        if birth_date is None:
            return None
        user_id, guest_id = owner_ids(owner)
        rows = await self.repository.list_latest_versions(
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        for profile, version in rows:
            if profile.id == exclude_profile_id:
                continue
            summary = self._summary(profile, version)
            if summary.display_name == display_name and summary.birth_date == birth_date:
                return profile, version
        return None

    async def _unique_save_as_name(
        self,
        owner: OwnerProtocol,
        display_name: str,
        *,
        exclude_profile_id: UUID,
    ) -> str:
        user_id, guest_id = owner_ids(owner)
        rows = await self.repository.list_latest_versions(
            owner_user_id=user_id,
            owner_guest_session_id=guest_id,
        )
        taken = {
            self._summary(profile, version).display_name
            for profile, version in rows
            if profile.id != exclude_profile_id
        }
        index = 2
        candidate = _save_as_candidate(display_name, index)
        while candidate in taken:
            index += 1
            candidate = _save_as_candidate(display_name, index)
        return candidate

    def _summary(
        self,
        profile: SubjectProfile,
        version: ProfileVersion,
    ) -> ProfileSummary:
        payload = self.repository.decrypt_version_payload(version)
        return _summary(profile, version, payload)


def _version_facts(payload: ProfileConfirmRequest) -> dict[str, object]:
    return {
        "birth_datetime": payload.birth_datetime,
        "timezone": payload.timezone,
        "location": payload.location,
        "gender": payload.gender,
        "time_basis_policy": payload.time_basis_policy,
        "zi_hour_policy": payload.zi_hour_policy,
        "longitude": payload.longitude,
        "latitude": payload.latitude,
        "coordinate_source": payload.coordinate_source,
    }


def _facts_match(stored: dict[str, object], incoming: dict[str, object]) -> bool:
    return all(stored.get(key) == incoming.get(key) for key in _VERSION_FACT_KEYS)


def _authorization_facts(payload: ProfileConfirmRequest) -> dict[str, object]:
    return {
        "subject_type": payload.subject_type,
        "is_minor": payload.is_minor,
        "authorization_confirmed": payload.authorization_confirmed,
        "photo_authorization_confirmed": payload.photo_authorization_confirmed,
        "minor_guardian_confirmed": payload.minor_guardian_confirmed,
    }


def _authorization_facts_match(
    stored: ProfileVersionAuthorization | None,
    payload: ProfileConfirmRequest,
) -> bool:
    if stored is None:
        return False
    incoming = _authorization_facts(payload)
    return all(
        getattr(stored, key) == incoming[key] for key in _AUTHORIZATION_FACT_KEYS
    )


def _save_as_candidate(
    display_name: str,
    index: int,
    max_length: int = _DISPLAY_NAME_MAX_LENGTH,
) -> str:
    suffix = f" ({index})"
    if len(suffix) >= max_length:
        return suffix[:max_length]
    return f"{display_name[: max_length - len(suffix)]}{suffix}"


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


def _resolved_display_name(label: str | None, birth_date: date | None) -> str:
    projected = _display_name_projection(label)
    if projected is not None:
        return projected
    if birth_date is not None:
        return f"档案 · {birth_date.isoformat()}"
    return "未命名档案"


def _birth_date_from_datetime(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _birth_date_projection(payload: dict[str, object]) -> date | None:
    value = payload.get("birth_datetime")
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
