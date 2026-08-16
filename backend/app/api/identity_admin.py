"""Authorized Admin reads for identity and Subject profile business facts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import ValidationError
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import StaffSession, StaffUser
from app.admin.schemas import (
    AdminSubjectAuthorizationResponse,
    AdminSubjectProfileResponse,
    AdminSubjectResponse,
    AdminSubjectsResponse,
    AdminSubjectSummary,
    AdminSubjectVersionResponse,
    AdminUserConsentResponse,
    AdminUserIdentityResponse,
    AdminUserResponse,
    AdminUserSessionResponse,
    AdminUsersResponse,
    AdminUserSubjectSummary,
    AdminUserSummary,
)
from app.api.admin import require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.identity.models import ConsentRecord, DeviceSession, LoginIdentity, User
from app.profiles.models import ProfileVersion, ProfileVersionAuthorization, SubjectProfile
from app.profiles.repository import ProfileRepository
from app.security.envelope import EncryptedPayload, EnvelopeCipher, EnvelopeDecryptionError

router = APIRouter(prefix="/admin", tags=["Admin Identity"])


def _require_identity_reader(staff: StaffUser) -> None:
    if staff.role not in {"support", "finance", "ops", "superadmin"}:
        raise ApiProblem(status=403, title="Identity reader permission required")


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _session_status(item: DeviceSession, now: datetime) -> str:
    if item.revoked_at is not None:
        return "revoked"
    if _utc(item.expires_at) <= now:
        return "expired"
    return "active"


def _identity_destination(
    identity: LoginIdentity,
    cipher: EnvelopeCipher,
) -> str | None:
    encrypted_fields = (
        identity.destination_key_id,
        identity.destination_nonce,
        identity.destination_ciphertext,
        identity.destination_fingerprint,
    )
    if all(value is None for value in encrypted_fields):
        return None
    if any(value is None for value in encrypted_fields):
        raise ApiProblem(status=503, title="Login identity data unavailable")
    assert identity.destination_key_id is not None
    assert identity.destination_nonce is not None
    assert identity.destination_ciphertext is not None
    assert identity.destination_fingerprint is not None
    try:
        return cipher.decrypt_text(
            EncryptedPayload(
                key_id=identity.destination_key_id,
                nonce=identity.destination_nonce,
                ciphertext=identity.destination_ciphertext,
                fingerprint=identity.destination_fingerprint,
            ),
            context=f"login-identity:{identity.id}",
        )
    except EnvelopeDecryptionError as error:
        raise ApiProblem(status=503, title="Login identity data unavailable") from error


async def _subject_summary(
    session: AsyncSession,
    subject: SubjectProfile,
) -> AdminUserSubjectSummary:
    versions = list(
        await session.scalars(
            select(ProfileVersion)
            .where(ProfileVersion.profile_id == subject.id)
            .order_by(desc(ProfileVersion.version))
        )
    )
    return AdminUserSubjectSummary(
        id=subject.id,
        label=subject.label,
        status=subject.status,
        created_at=subject.created_at,
        version_count=len(versions),
        latest_version=versions[0].version if versions else None,
    )


async def _subject_summary_for_list(
    session: AsyncSession,
    subject: SubjectProfile,
) -> AdminSubjectSummary:
    versions = list(
        await session.scalars(
            select(ProfileVersion)
            .where(ProfileVersion.profile_id == subject.id)
            .order_by(desc(ProfileVersion.version))
        )
    )
    return AdminSubjectSummary(
        id=subject.id,
        owner_user_id=subject.owner_user_id,
        label=subject.label,
        status=subject.status,
        created_at=subject.created_at,
        version_count=len(versions),
        latest_version=versions[0].version if versions else None,
    )


@router.get(
    "/users",
    operation_id="listAdminUsers",
    response_model=AdminUsersResponse,
)
async def list_admin_users(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminUsersResponse:
    _require_identity_reader(principal[1])
    now = datetime.now(UTC)
    identity_count = (
        select(func.count(LoginIdentity.id))
        .where(LoginIdentity.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    consent_count = (
        select(func.count(ConsentRecord.id))
        .where(ConsentRecord.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    subject_count = (
        select(func.count(SubjectProfile.id))
        .where(SubjectProfile.owner_user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    active_session_count = (
        select(func.count(DeviceSession.id))
        .where(
            DeviceSession.user_id == User.id,
            DeviceSession.revoked_at.is_(None),
            DeviceSession.expires_at > now,
        )
        .correlate(User)
        .scalar_subquery()
    )
    rows = (
        await session.execute(
            select(
                User,
                identity_count,
                consent_count,
                subject_count,
                active_session_count,
            )
            .order_by(desc(User.created_at), desc(User.id))
            .limit(limit)
        )
    ).all()
    mark_private(response)
    return AdminUsersResponse(
        users=[
            AdminUserSummary(
                id=user.id,
                status=user.status,
                created_at=user.created_at,
                identity_count=int(identity_total),
                consent_count=int(consent_total),
                subject_count=int(subject_total),
                active_session_count=int(active_sessions),
            )
            for user, identity_total, consent_total, subject_total, active_sessions in rows
        ]
    )


@router.get(
    "/users/{user_id}",
    operation_id="getAdminUser",
    response_model=AdminUserResponse,
)
async def get_admin_user(
    user_id: UUID,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminUserResponse:
    _require_identity_reader(principal[1])
    user = await session.get(User, user_id)
    if user is None:
        raise ApiProblem(status=404, title="User not found")
    now = datetime.now(UTC)
    identity_cipher = EnvelopeCipher.from_settings(request.app.state.settings)
    identities = list(
        await session.scalars(
            select(LoginIdentity)
            .where(LoginIdentity.user_id == user.id)
            .order_by(LoginIdentity.created_at, LoginIdentity.id)
        )
    )
    consents = list(
        await session.scalars(
            select(ConsentRecord)
            .where(ConsentRecord.user_id == user.id)
            .order_by(ConsentRecord.accepted_at, ConsentRecord.id)
        )
    )
    sessions = list(
        await session.scalars(
            select(DeviceSession)
            .where(DeviceSession.user_id == user.id)
            .order_by(desc(DeviceSession.last_seen_at), desc(DeviceSession.id))
        )
    )
    subjects = list(
        await session.scalars(
            select(SubjectProfile)
            .where(SubjectProfile.owner_user_id == user.id)
            .order_by(desc(SubjectProfile.created_at), desc(SubjectProfile.id))
        )
    )
    mark_private(response)
    return AdminUserResponse(
        id=user.id,
        status=user.status,
        created_at=user.created_at,
        identities=[
            AdminUserIdentityResponse(
                id=item.id,
                provider=item.provider,
                masked_destination=item.masked_destination,
                destination=_identity_destination(item, identity_cipher),
                status=item.status,
                verified_at=item.verified_at,
                created_at=item.created_at,
            )
            for item in identities
        ],
        consents=[
            AdminUserConsentResponse(
                id=item.id,
                policy_key=item.policy_key,
                policy_version=item.policy_version,
                context=item.context,
                accepted_at=item.accepted_at,
            )
            for item in consents
        ],
        sessions=[
            AdminUserSessionResponse(
                id=item.id,
                status=_session_status(item, now),
                expires_at=item.expires_at,
                last_seen_at=item.last_seen_at,
                revoked_at=item.revoked_at,
                created_at=item.created_at,
            )
            for item in sessions
        ],
        subjects=[await _subject_summary(session, item) for item in subjects],
    )


@router.get(
    "/subjects",
    operation_id="listAdminSubjects",
    response_model=AdminSubjectsResponse,
)
async def list_admin_subjects(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminSubjectsResponse:
    _require_identity_reader(principal[1])
    subjects = list(
        await session.scalars(
            select(SubjectProfile)
            .order_by(desc(SubjectProfile.created_at), desc(SubjectProfile.id))
            .limit(limit)
        )
    )
    mark_private(response)
    return AdminSubjectsResponse(
        subjects=[await _subject_summary_for_list(session, item) for item in subjects]
    )


@router.get(
    "/subjects/{subject_id}",
    operation_id="getAdminSubject",
    response_model=AdminSubjectResponse,
)
async def get_admin_subject(
    subject_id: UUID,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminSubjectResponse:
    _require_identity_reader(principal[1])
    subject = await session.get(SubjectProfile, subject_id)
    if subject is None:
        raise ApiProblem(status=404, title="Subject not found")
    rows = (
        await session.execute(
            select(ProfileVersion, ProfileVersionAuthorization)
            .outerjoin(
                ProfileVersionAuthorization,
                ProfileVersionAuthorization.profile_version_id == ProfileVersion.id,
            )
            .where(ProfileVersion.profile_id == subject.id)
            .order_by(ProfileVersion.version)
        )
    ).all()
    profile_repository = ProfileRepository(
        session,
        EnvelopeCipher.from_settings(request.app.state.settings),
    )
    profiles: dict[UUID, AdminSubjectProfileResponse] = {}
    for version, _authorization in rows:
        try:
            profiles[version.id] = AdminSubjectProfileResponse.model_validate(
                await profile_repository.load_version_payload(version.id)
            )
        except (LookupError, EnvelopeDecryptionError, ValidationError) as error:
            raise ApiProblem(
                status=503,
                title="Subject profile data unavailable",
            ) from error
    mark_private(response)
    return AdminSubjectResponse(
        id=subject.id,
        owner_user_id=subject.owner_user_id,
        label=subject.label,
        status=subject.status,
        created_at=subject.created_at,
        versions=[
            AdminSubjectVersionResponse(
                id=version.id,
                version=version.version,
                created_at=version.created_at,
                authorization=(
                    AdminSubjectAuthorizationResponse(
                        subject_type=authorization.subject_type,
                        is_minor=authorization.is_minor,
                        authorization_confirmed=authorization.authorization_confirmed,
                        photo_authorization_confirmed=authorization.photo_authorization_confirmed,
                        minor_guardian_confirmed=authorization.minor_guardian_confirmed,
                        difference_acknowledged=authorization.difference_acknowledged,
                )
                if authorization is not None
                else None
            ),
                profile=profiles[version.id],
            )
            for version, authorization in rows
        ],
    )
