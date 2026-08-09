from httpx import AsyncClient

PRIVATE_CACHE_CONTROL = "private, no-store, max-age=0"
PRIVATE_ROBOTS_TAG = "noindex, nofollow, noarchive"


async def create_guest(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/guest-sessions")
    assert response.status_code == 201
    return {"X-CSRF-Token": response.json()["csrf_token"]}


async def login_with_phone(client: AsyncClient) -> None:
    headers = await create_guest(client)
    requested = await client.post(
        "/api/v1/auth/otp/request",
        headers=headers,
        json={"channel": "phone", "destination": "13800138000"},
    )
    assert requested.status_code == 202, requested.text
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        headers=headers,
        json={
            "challenge_id": requested.json()["challenge_id"],
            "code": "246810",
        },
    )
    assert verified.status_code == 200, verified.text


async def test_get_account_success_response_is_private_and_non_indexable(
    client: AsyncClient,
) -> None:
    await login_with_phone(client)

    response = await client.get("/api/v1/account")

    assert response.status_code == 200
    assert response.headers["cache-control"] == PRIVATE_CACHE_CONTROL
    assert response.headers["x-robots-tag"] == PRIVATE_ROBOTS_TAG


async def test_unauthenticated_account_request_keeps_private_error_behavior(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/account")

    assert response.status_code == 401
    assert response.json()["title"] == "Authentication required"
    assert "x-robots-tag" not in response.headers
    assert response.headers.get("cache-control") != PRIVATE_CACHE_CONTROL
