"""PostgreSQL concurrency gates for owner-scoped reading Idempotency-Key mappings."""

from __future__ import annotations

import asyncio
import importlib
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from app.identity.models import User
from app.profiles.schemas import ProfileConfirmRequest
from app.profiles.service import ProfileService
from app.readings.models import (
    ReadingIdempotencyKey,
    ReadingVersion,
)
from app.readings.service import ReadingService
from app.security.envelope import EnvelopeCipher
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from test_readings_api import seed_runtime_release


@pytest.fixture
async def postgres_idempotency_database() -> AsyncIterator[Any]:
    url = os.environ.get("MINGLI_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("MINGLI_TEST_POSTGRES_URL is required for PostgreSQL concurrency tests")
    identity_models = importlib.import_module("app.identity.models")
    importlib.import_module("app.profiles.models")
    importlib.import_module("app.readings.models")
    schema = f"mingli_idem_test_{uuid4().hex}"
    admin_engine = create_async_engine(url, pool_pre_ping=True)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        url,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": schema}},
    )
    async with engine.begin() as connection:
        await connection.run_sync(identity_models.Base.metadata.create_all)
    harness = _PostgresHarness(engine)
    try:
        yield harness
    finally:
        await harness.dispose()
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()


class _PostgresHarness:
    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def dispose(self) -> None:
        await self.engine.dispose()


class _UserOwner:
    kind = "user"

    def __init__(self, user_id: UUID) -> None:
        self.id = user_id


@pytest.fixture
def postgres_settings() -> Any:
    config = importlib.import_module("app.config")
    return config.Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        cookie_secure=True,
        otp_adapter="fake",
    )


async def _seed_user_with_confirmed_profile(
    database: Any,
    settings: Any,
) -> tuple[UUID, UUID]:
    async with database.sessions() as session:
        user = User(id=uuid4())
        session.add(user)
        await session.flush()
        profiles = ProfileService(session, settings)
        owner = _UserOwner(user.id)
        draft_id = await profiles.create_draft(owner, label="本人")
        summary = await profiles.confirm_draft(
            owner,
            draft_id,
            ProfileConfirmRequest(
                birth_datetime="1994-04-30T05:55:00+08:00",
                timezone="Asia/Shanghai",
                location="北京市朝阳区",
                gender="female",
                time_basis_policy="civil",
                zi_hour_policy="midnight",
                longitude=116.4074,
                latitude=39.9042,
                coordinate_source="user_confirmed",
            ),
        )
        await session.commit()
        return user.id, summary.profile_version_id


async def _start_preview_and_commit(
    database: Any,
    settings: Any,
    *,
    user_id: UUID,
    profile_version_id: UUID,
    idempotency_key: str,
) -> UUID:
    async with database.sessions() as session:
        service = ReadingService(session, settings)
        response, _created = await service.start_preview(
            _UserOwner(user_id),
            profile_version_id=profile_version_id,
            query=None,
            dimension_ids=None,
            idempotency_key=idempotency_key,
        )
        await session.commit()
        return response.reading_version_id


async def test_concurrent_same_owner_same_key_maps_to_one_reading_version(
    postgres_idempotency_database: Any,
    postgres_settings: Any,
) -> None:
    database = postgres_idempotency_database
    await seed_runtime_release(database, postgres_settings)
    user_id, profile_version_id = await _seed_user_with_confirmed_profile(
        database,
        postgres_settings,
    )

    first_id, second_id = await asyncio.gather(
        _start_preview_and_commit(
            database,
            postgres_settings,
            user_id=user_id,
            profile_version_id=profile_version_id,
            idempotency_key="concurrent-key",
        ),
        _start_preview_and_commit(
            database,
            postgres_settings,
            user_id=user_id,
            profile_version_id=profile_version_id,
            idempotency_key="concurrent-key",
        ),
    )

    assert first_id == second_id
    async with database.sessions() as session:
        mapping_count = await session.scalar(
            select(func.count()).select_from(ReadingIdempotencyKey)
        )
        version_count = await session.scalar(
            select(func.count()).select_from(ReadingVersion)
        )
    assert mapping_count == 1
    assert version_count == 1


async def test_concurrent_guest_same_key_maps_to_one_reading_version(
    postgres_idempotency_database: Any,
    postgres_settings: Any,
) -> None:
    database = postgres_idempotency_database
    await seed_runtime_release(database, postgres_settings)
    async with database.sessions() as session:
        guest = importlib.import_module("app.identity.models").GuestSession(
            id=uuid4(),
            token_hash=uuid4().hex,
            csrf_token_hash=uuid4().hex,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session.add(guest)
        await session.flush()
        profiles = ProfileService(session, postgres_settings)
        owner = _GuestOwner(guest.id)
        draft_id = await profiles.create_draft(owner, label="访客")
        summary = await profiles.confirm_draft(
            owner,
            draft_id,
            ProfileConfirmRequest(
                birth_datetime="1994-04-30T05:55:00+08:00",
                timezone="Asia/Shanghai",
                location="北京市朝阳区",
                gender="female",
                time_basis_policy="civil",
                zi_hour_policy="midnight",
                longitude=116.4074,
                latitude=39.9042,
                coordinate_source="user_confirmed",
            ),
        )
        await session.commit()
        guest_id = guest.id
        profile_version_id = summary.profile_version_id

    async def run_once() -> UUID:
        async with database.sessions() as session:
            service = ReadingService(session, postgres_settings)
            response, _created = await service.start_preview(
                _GuestOwner(guest_id),
                profile_version_id=profile_version_id,
                query=None,
                dimension_ids=None,
                idempotency_key="guest-concurrent-key",
            )
            await session.commit()
            return response.reading_version_id

    first_id, second_id = await asyncio.gather(run_once(), run_once())

    assert first_id == second_id
    async with database.sessions() as session:
        mapping_count = await session.scalar(
            select(func.count()).select_from(ReadingIdempotencyKey)
        )
        version_count = await session.scalar(
            select(func.count()).select_from(ReadingVersion)
        )
    assert mapping_count == 1
    assert version_count == 1


class _GuestOwner:
    kind = "guest"

    def __init__(self, guest_id: UUID) -> None:
        self.id = guest_id


@pytest.fixture(autouse=True)
def _envelope_cipher_registered(postgres_settings: Any) -> None:
    EnvelopeCipher.from_settings(postgres_settings)
