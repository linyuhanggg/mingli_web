from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.admin.models import StaffUser
from app.identity.models import ConsentRecord, DeviceSession, LoginIdentity, User
from app.profiles.models import ProfileVersion, ProfileVersionAuthorization, SubjectProfile
from app.security.envelope import EnvelopeCipher
from httpx import AsyncClient
from sqlalchemy import select


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    return {"X-CSRF-Token": login.json()["csrf_token"]}


async def test_admin_identity_reads_users_subjects_and_safe_detail_metadata(
    client: AsyncClient,
    database,
    test_settings,
) -> None:  # type: ignore[no-untyped-def]
    await _admin_headers(client)
    now = datetime.now(UTC)
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        identity_id = uuid4()
        identity_destination = EnvelopeCipher.from_settings(test_settings).encrypt_text(
            "user@example.com",
            context=f"login-identity:{identity_id}",
        )
        identity = LoginIdentity(
            id=identity_id,
            user_id=user.id,
            provider="email",
            provider_subject_hash="a" * 64,
            masked_destination="u***@example.com",
            destination_key_id=identity_destination.key_id,
            destination_nonce=identity_destination.nonce,
            destination_ciphertext=identity_destination.ciphertext,
            destination_fingerprint=identity_destination.fingerprint,
            verified_at=now,
        )
        consent = ConsentRecord(
            user_id=user.id,
            policy_key="terms",
            policy_version="2026-08-01",
            context="signup",
            accepted_at=now,
        )
        device = DeviceSession(
            user_id=user.id,
            token_hash="b" * 64,
            csrf_token_hash="c" * 64,
            expires_at=now + timedelta(hours=2),
            last_seen_at=now,
        )
        subject = SubjectProfile(owner_user_id=user.id, label="本人")
        session.add_all([identity, consent, device, subject])
        await session.flush()
        version_id = uuid4()
        encrypted = EnvelopeCipher.from_settings(test_settings).encrypt_json(
            {
                "birth_datetime": "1994-04-30T05:55:00+08:00",
                "timezone": "Asia/Shanghai",
                "location": "北京市朝阳区",
                "gender": "female",
                "time_basis_policy": "civil",
                "zi_hour_policy": "midnight",
                "longitude": 116.4074,
                "latitude": 39.9042,
                "coordinate_source": "user_confirmed",
            },
            context=f"profile-version:{version_id}",
        )
        version = ProfileVersion(
            id=version_id,
            profile_id=subject.id,
            version=1,
            payload_key_id=encrypted.key_id,
            payload_nonce=encrypted.nonce,
            payload_ciphertext=encrypted.ciphertext,
            payload_fingerprint=encrypted.fingerprint,
        )
        session.add(version)
        await session.flush()
        authorization = ProfileVersionAuthorization(
            profile_version_id=version.id,
            subject_type="self",
            is_minor=False,
            authorization_confirmed=False,
            photo_authorization_confirmed=False,
            minor_guardian_confirmed=False,
            difference_acknowledged=True,
        )
        session.add(authorization)
        await session.commit()

    users = await client.get("/api/v1/admin/users")
    assert users.status_code == 200, users.text
    assert users.json()["users"][0]["id"] == str(user.id)
    assert users.json()["users"][0]["identity_count"] == 1
    assert users.json()["users"][0]["consent_count"] == 1
    assert users.json()["users"][0]["subject_count"] == 1
    assert users.json()["users"][0]["active_session_count"] == 1

    user_detail = await client.get(f"/api/v1/admin/users/{user.id}")
    assert user_detail.status_code == 200, user_detail.text
    assert user_detail.json()["identities"][0]["masked_destination"] == "u***@example.com"
    assert user_detail.json()["identities"][0]["destination"] == "user@example.com"
    assert user_detail.json()["consents"][0]["policy_version"] == "2026-08-01"
    assert user_detail.json()["sessions"][0]["status"] == "active"
    assert "password_hash" not in user_detail.text
    assert "token_hash" not in user_detail.text
    assert "payload_ciphertext" not in user_detail.text

    subjects = await client.get("/api/v1/admin/subjects")
    assert subjects.status_code == 200, subjects.text
    assert subjects.json()["subjects"][0]["id"] == str(subject.id)
    assert subjects.json()["subjects"][0]["version_count"] == 1

    subject_detail = await client.get(f"/api/v1/admin/subjects/{subject.id}")
    assert subject_detail.status_code == 200, subject_detail.text
    assert subject_detail.json()["versions"][0]["version"] == 1
    assert subject_detail.json()["versions"][0]["authorization"]["difference_acknowledged"] is True
    assert subject_detail.json()["versions"][0]["profile"] == {
        "birth_datetime": "1994-04-30T05:55:00+08:00",
        "timezone": "Asia/Shanghai",
        "location": "北京市朝阳区",
        "gender": "female",
        "time_basis_policy": "civil",
        "zi_hour_policy": "midnight",
        "longitude": 116.4074,
        "latitude": 39.9042,
        "coordinate_source": "user_confirmed",
    }
    assert "payload_ciphertext" not in subject_detail.text
    assert "payload_nonce" not in subject_detail.text


async def test_admin_identity_read_allows_support_but_never_returns_password_material(
    client: AsyncClient,
    database,
) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin_headers(client)
    async with database.sessions() as session:
        staff = await session.scalar(
            select(StaffUser).where(StaffUser.email == "ops@example.com")
        )
        assert staff is not None
        staff.role = "support"
        user = User()
        session.add(user)
        await session.flush()
        await session.commit()

    response = await client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 200, response.text
    assert response.json()["users"][0]["id"] == str(user.id)
    assert "password_hash" not in response.text
