import importlib
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


def make_app(
    readiness_probe: Callable[[], Awaitable[None]] | None = None,
) -> FastAPI:
    main = importlib.import_module("app.main")
    create_app: Callable[..., FastAPI] = main.create_app
    return create_app(readiness_probe=readiness_probe)


async def test_liveness_is_process_only() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app()),
        base_url="https://testserver",
    ) as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}


async def test_every_response_has_a_request_id() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=make_app()),
        base_url="https://testserver",
    ) as client:
        generated = await client.get("/api/v1/health/live")
        echoed = await client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": "browser-request-42"},
        )

    assert len(generated.headers["x-request-id"]) >= 16
    assert echoed.headers["x-request-id"] == "browser-request-42"


async def test_readiness_succeeds_when_the_database_probe_succeeds() -> None:
    async def database_is_ready() -> None:
        return None

    async with AsyncClient(
        transport=ASGITransport(app=make_app(database_is_ready)),
        base_url="https://testserver",
    ) as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "database"}


async def test_readiness_returns_a_safe_problem_when_database_is_unavailable() -> None:
    async def database_is_down() -> None:
        raise RuntimeError("postgresql://admin:secret@database/private")

    async with AsyncClient(
        transport=ASGITransport(app=make_app(database_is_down)),
        base_url="https://testserver",
    ) as client:
        response = await client.get("/api/v1/health/ready")
    body: dict[str, Any] = response.json()

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert body["title"] == "Service unavailable"
    assert body["request_id"] == response.headers["x-request-id"]
    assert "secret" not in response.text
