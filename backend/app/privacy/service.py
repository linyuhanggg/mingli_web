from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.commerce.models import NotificationPreference
from app.config import Settings
from app.identity.models import ConsentRecord, DeviceSession, LoginIdentity, User
from app.privacy.models import AccountClosureRequest, ClosureStatus
from app.profiles.models import ProfileVersion, SubjectProfile
from app.profiles.repository import ProfileRepository
from app.readings.models import ReadingRoot, ReadingVersion
from app.security.envelope import EnvelopeCipher

CLOSURE_GRACE_PERIOD = timedelta(days=7)


class ClosureNotFoundError(LookupError):
    """The requested closure does not exist for this owner."""


class ClosureNotReadyError(ValueError):
    """The seven-day cancellation period has not elapsed."""


class ClosureAlreadyExecutedError(ValueError):
    """The account has already been closed."""


def _utc(value: datetime) -> datetime:
    """SQLite returns timezone columns without tzinfo; treat them as UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class DataRightsService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.profile_repository = ProfileRepository(
            session,
            EnvelopeCipher.from_settings(settings),
        )

    async def export_user(self, user_id: UUID, *, now: datetime | None = None) -> dict[str, Any]:
        user = await self.session.get(User, user_id)
        if user is None or user.status != "active":
            raise ClosureNotFoundError("active user not found")

        identities = list(
            await self.session.scalars(
                select(LoginIdentity)
                .where(LoginIdentity.user_id == user_id)
                .order_by(LoginIdentity.created_at, LoginIdentity.id)
            )
        )
        profile_rows = list(
            (
                await self.session.execute(
                    select(SubjectProfile, ProfileVersion)
                    .join(ProfileVersion, ProfileVersion.profile_id == SubjectProfile.id)
                    .where(SubjectProfile.owner_user_id == user_id)
                    .order_by(ProfileVersion.created_at, ProfileVersion.id)
                )
            ).all()
        )
        profiles: list[dict[str, Any]] = []
        for profile, version in profile_rows:
            profiles.append(
                {
                    "profile_id": str(profile.id),
                    "label": profile.label,
                    "status": profile.status,
                    "version": version.version,
                    "profile_version_id": str(version.id),
                    "created_at": version.created_at.isoformat(),
                    "payload": await self.profile_repository.load_version_payload(version.id),
                }
            )

        reading_rows = list(
            (
                await self.session.execute(
                    select(ReadingRoot, ReadingVersion)
                    .join(ReadingVersion, ReadingVersion.reading_root_id == ReadingRoot.id)
                    .where(ReadingRoot.owner_user_id == user_id)
                    .order_by(ReadingVersion.created_at, ReadingVersion.id)
                )
            ).all()
        )
        readings = [
            {
                "reading_root_id": str(root.id),
                "reading_version_id": str(version.id),
                "capability_id": version.capability_id,
                "version": version.version,
                "status": version.status,
                "object_id": version.object_id,
                "dimension_ids": list(version.dimension_ids),
                "horizon": dict(version.horizon),
                "created_at": version.created_at.isoformat(),
            }
            for root, version in reading_rows
        ]
        consents = list(
            await self.session.scalars(
                select(ConsentRecord)
                .where(ConsentRecord.user_id == user_id)
                .order_by(ConsentRecord.accepted_at, ConsentRecord.id)
            )
        )
        notification_preferences = await self.session.scalar(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        generated_at = now or datetime.now(UTC)
        return {
            "user": {
                "user_id": str(user.id),
                "status": user.status,
                "created_at": user.created_at.isoformat(),
            },
            "identities": [
                {
                    "provider": item.provider,
                    "masked_destination": item.masked_destination,
                    "verified_at": item.verified_at.isoformat(),
                    "status": item.status,
                }
                for item in identities
            ],
            "profiles": profiles,
            "readings": readings,
            "consents": [
                {
                    "policy_key": item.policy_key,
                    "policy_version": item.policy_version,
                    "context": item.context,
                    "accepted_at": item.accepted_at.isoformat(),
                }
                for item in consents
            ],
            "notification_preferences": {
                "in_app_enabled": (
                    notification_preferences.in_app_enabled
                    if notification_preferences is not None
                    else True
                ),
                "email_enabled": (
                    notification_preferences.email_enabled
                    if notification_preferences is not None
                    else False
                ),
                "sms_enabled": (
                    notification_preferences.sms_enabled
                    if notification_preferences is not None
                    else False
                ),
            },
            "generated_at": generated_at.isoformat(),
        }

    async def delete_profile(self, user_id: UUID, profile_id: UUID) -> bool:
        profile = await self.session.scalar(
            select(SubjectProfile).where(
                SubjectProfile.id == profile_id,
                SubjectProfile.owner_user_id == user_id,
                SubjectProfile.status == "active",
            )
        )
        if profile is None:
            return False
        profile.status = "deleted"
        return True

    async def active_closure(self, user_id: UUID) -> AccountClosureRequest | None:
        return cast(
            AccountClosureRequest | None,
            await self.session.scalar(
                select(AccountClosureRequest).where(
                    AccountClosureRequest.user_id == user_id,
                    AccountClosureRequest.status == ClosureStatus.PENDING,
                )
            ),
        )

    async def request_closure(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
    ) -> tuple[AccountClosureRequest, bool]:
        user = await self.session.get(User, user_id)
        if user is None or user.status != "active":
            raise ClosureNotFoundError("active user not found")
        existing = await self.active_closure(user_id)
        if existing is not None:
            return existing, False
        requested_at = now or datetime.now(UTC)
        closure = AccountClosureRequest(
            user_id=user_id,
            status=ClosureStatus.PENDING,
            requested_at=requested_at,
            cancel_until=requested_at + CLOSURE_GRACE_PERIOD,
        )
        self.session.add(closure)
        await self.session.flush()
        return closure, True

    async def cancel_closure(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
    ) -> AccountClosureRequest:
        closure = await self.active_closure(user_id)
        if closure is None:
            raise ClosureNotFoundError("active closure not found")
        cancelled_at = now or datetime.now(UTC)
        if cancelled_at >= _utc(closure.cancel_until):
            raise ClosureNotReadyError("closure cancellation window has elapsed")
        closure.status = ClosureStatus.CANCELLED
        closure.cancelled_at = cancelled_at
        await self.session.flush()
        return closure

    async def list_pending_closures(self) -> list[AccountClosureRequest]:
        return list(
            await self.session.scalars(
                select(AccountClosureRequest)
                .where(AccountClosureRequest.status == ClosureStatus.PENDING)
                .order_by(AccountClosureRequest.cancel_until, AccountClosureRequest.id)
            )
        )

    async def execute_closure(
        self,
        closure_id: UUID,
        *,
        now: datetime | None = None,
    ) -> AccountClosureRequest:
        closure = await self.session.get(AccountClosureRequest, closure_id)
        if closure is None:
            raise ClosureNotFoundError("closure not found")
        if closure.status != ClosureStatus.PENDING:
            raise ClosureAlreadyExecutedError("closure is not pending")
        executed_at = now or datetime.now(UTC)
        if executed_at < _utc(closure.cancel_until):
            raise ClosureNotReadyError("closure cancellation window has not elapsed")
        user = await self.session.get(User, closure.user_id)
        if user is None:
            raise ClosureNotFoundError("user not found")

        await self.session.execute(
            update(DeviceSession)
            .where(DeviceSession.user_id == user.id, DeviceSession.revoked_at.is_(None))
            .values(revoked_at=executed_at)
        )
        await self.session.execute(
            update(LoginIdentity)
            .where(LoginIdentity.user_id == user.id)
            .values(status="revoked", masked_destination="[已删除]")
        )
        await self.session.execute(
            delete(ReadingRoot).where(ReadingRoot.owner_user_id == user.id)
        )
        await self.session.execute(
            delete(SubjectProfile).where(SubjectProfile.owner_user_id == user.id)
        )
        user.status = "closed"
        closure.status = ClosureStatus.EXECUTED
        closure.executed_at = executed_at
        await self.session.flush()
        return closure
