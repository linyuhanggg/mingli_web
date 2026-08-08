from httpx import AsyncClient


async def test_otp_request_requires_a_guest_session(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/otp/request",
        headers={"X-CSRF-Token": "a" * 40},
        json={"channel": "phone", "destination": "13800138000"},
    )

    assert response.status_code == 403
    assert response.json()["title"] == "CSRF validation failed"


async def test_otp_request_rejects_a_mismatched_csrf_header(client: AsyncClient) -> None:
    guest = await client.post("/api/v1/guest-sessions")
    assert guest.status_code == 201

    response = await client.post(
        "/api/v1/auth/otp/request",
        headers={"X-CSRF-Token": "wrong-token" * 4},
        json={"channel": "email", "destination": "user@example.com"},
    )

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")


async def test_logout_rejects_csrf_from_the_old_guest_session(
    client: AsyncClient,
) -> None:
    guest = await client.post("/api/v1/guest-sessions")
    guest_csrf = guest.json()["csrf_token"]
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers={"X-CSRF-Token": guest_csrf},
        json={"channel": "email", "destination": "user@example.com"},
    )
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers={"X-CSRF-Token": guest_csrf},
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": "246810",
        },
    )
    assert verified.status_code == 200

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": guest_csrf},
    )

    assert response.status_code == 403
