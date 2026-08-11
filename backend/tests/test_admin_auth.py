from __future__ import annotations

from app.config import Settings
from httpx import AsyncClient


async def test_admin_bootstrap_login_me_and_logout(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["role"] == "superadmin"
    assert body["csrf_token"]
    assert "mingli_admin_session" in login.cookies
    assert "mingli_admin_csrf" in login.cookies
    assert "password" not in login.text

    me = await client.get("/api/v1/admin/me")
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["email"] == "ops@example.com"
    assert me_body["role"] == "superadmin"
    assert me.headers.get("cache-control", "").startswith("private")

    overview = await client.get("/api/v1/admin/overview")
    assert overview.status_code == 200
    overview_body = overview.json()
    assert overview_body["is_stub"] is True
    assert len(overview_body["kpis"]) == 4
    assert all(item["is_stub"] for item in overview_body["kpis"])

    logout = await client.post(
        "/api/v1/admin/auth/logout",
        headers={"X-CSRF-Token": body["csrf_token"]},
    )
    assert logout.status_code == 204

    me_after = await client.get("/api/v1/admin/me")
    assert me_after.status_code == 401


async def test_admin_login_rejects_wrong_password(client: AsyncClient) -> None:
    # Create bootstrap account first.
    ok = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert ok.status_code == 200
    await client.post(
        "/api/v1/admin/auth/logout",
        headers={"X-CSRF-Token": ok.json()["csrf_token"]},
    )

    bad = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401
    assert "password_hash" not in bad.text


async def test_admin_me_requires_staff_session(client: AsyncClient) -> None:
    response = await client.get("/api/v1/admin/me")
    assert response.status_code == 401


async def test_user_session_cannot_access_admin(client: AsyncClient) -> None:
    guest = await client.post("/api/v1/guest-sessions")
    assert guest.status_code == 201
    csrf = guest.json()["csrf_token"]
    request_otp = await client.post(
        "/api/v1/auth/otp/request",
        headers={"X-CSRF-Token": csrf},
        json={"channel": "email", "destination": "user@example.com"},
    )
    assert request_otp.status_code == 202
    verify = await client.post(
        "/api/v1/auth/otp/verify",
        headers={"X-CSRF-Token": csrf},
        json={
            "challenge_id": request_otp.json()["challenge_id"],
            "code": "246810",
        },
    )
    assert verify.status_code == 200
    # User cookies present, but admin endpoints stay closed.
    me = await client.get("/api/v1/admin/me")
    assert me.status_code == 401
    overview = await client.get("/api/v1/admin/overview")
    assert overview.status_code == 401


async def test_admin_logout_requires_csrf(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ops@example.com", "password": "correct-horse"},
    )
    assert login.status_code == 200
    missing = await client.post("/api/v1/admin/auth/logout")
    assert missing.status_code == 403


def test_production_settings_forbid_admin_bootstrap() -> None:
    # Keep the assertion narrow: bootstrap fields alone must be rejected in production.
    try:
        Settings(
            environment="production",
            cookie_secure=True,
            otp_adapter="disabled",
            identity_hash_key="production-identity-hash-key-value-not-local",
            content_encryption_key_b64="BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=",
            content_encryption_key_id="prod-content-v1",
            runtime_adapter="one-shot",
            runtime_launcher_path="/opt/mingli-master/scripts/run_reading_transaction.sh",
            runtime_python_path="/opt/mingli-runtime/venv/bin/python",
            runtime_release_root="/opt/mingli-master",
            runtime_state_root="/var/lib/mingli",
            runtime_expected_manifest_digest=(
                "7ddbc04a04cad101dc1ab4951982c60b3138ffbb1b09463c64df719c69940342"
            ),
            runtime_expected_capability_shape_sha256=(
                "8ce44f539004405dc174236612e7185547057b241d9e5fef042dffc958517f60"
            ),
            model_adapter="fake",
            admin_bootstrap_email="ops@example.com",
            admin_bootstrap_password="correct-horse",
        )
    except ValueError as error:
        message = str(error).lower()
        assert "bootstrap" in message
    else:
        raise AssertionError("expected production bootstrap rejection")
