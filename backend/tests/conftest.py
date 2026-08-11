import importlib
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def database() -> AsyncIterator[Any]:
    database_module = importlib.import_module("app.database")
    models = importlib.import_module("app.identity.models")
    # Register every domain model on the shared Base before create_all. API tests
    # intentionally exercise the real repositories against one database.
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
    importlib.import_module("app.admin.models")
    database = database_module.Database("sqlite+aiosqlite:///:memory:")

    async with database.engine.begin() as connection:
        await connection.run_sync(models.Base.metadata.create_all)

    yield database
    await database.dispose()


@pytest.fixture
def test_settings():  # type: ignore[no-untyped-def]
    config = importlib.import_module("app.config")
    return config.Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="fake",
        admin_bootstrap_email="ops@example.com",
        admin_bootstrap_password="correct-horse",
    )


@pytest.fixture
async def client(database: Any, test_settings: Any) -> AsyncIterator[AsyncClient]:
    main = importlib.import_module("app.main")
    application = main.create_app(settings=test_settings, database=database)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="https://testserver",
    ) as http_client:
        yield http_client
