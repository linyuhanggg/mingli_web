from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.identity.models import User
from app.media.physiognomy import InMemoryPrivateMediaStore
from app.media.service import PhysiognomyMediaService
from worker.media_purge import MediaPurgeWorker

NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)
JPEG = b"\xff\xd8\xff\xe0" + b"mingli-p7-008-purge"
SIGNED_TTL = timedelta(minutes=15)


class FrozenClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def now(self) -> datetime:
        return self.current


async def _ingest(
    service: PhysiognomyMediaService,
    user: User,
    *,
    now: datetime,
    filename: str,
) -> UUID:
    asset = await service.ingest(
        owner_kind="user",
        owner_id=user.id,
        content_type="image/jpeg",
        filename=filename,
        payload=JPEG,
        width=1200,
        height=1600,
        consent=True,
        mode="face",
        consent_policy_version="physiognomy-photo-v1",
        now=now,
    )
    return UUID(asset.asset_id)


def _worker(
    database: Any,
    store: InMemoryPrivateMediaStore,
    *,
    now: datetime,
    adapter: Any | None = None,
) -> MediaPurgeWorker:
    return MediaPurgeWorker(
        sessions=database.sessions,
        store=store,
        clock=FrozenClock(now),
        adapter=adapter,
    )


async def test_purge_worker_clears_expired_tickets_and_expired_bytes(
    database: Any,
) -> None:
    store = InMemoryPrivateMediaStore()

    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = PhysiognomyMediaService(session, store)
        expired_id = await _ingest(
            service,
            user,
            now=NOW - timedelta(days=8),
            filename="expired.jpg",
        )
        expired_ticket = await service.issue_signed_download(
            owner_kind="user",
            owner_id=user.id,
            asset_id=expired_id,
            ttl=SIGNED_TTL,
            now=NOW - timedelta(days=8),
        )
        live_id = await _ingest(service, user, now=NOW, filename="live.jpg")
        live_ticket = await service.issue_signed_download(
            owner_kind="user",
            owner_id=user.id,
            asset_id=live_id,
            ttl=SIGNED_TTL,
            now=NOW,
        )
        await session.commit()
        adapter = service.adapter

    first = await _worker(database, store, now=NOW, adapter=adapter).run_once()
    second = await _worker(database, store, now=NOW, adapter=adapter).run_once()

    assert expired_ticket.token in first.purged_tokens
    assert live_ticket.token not in first.purged_tokens
    assert str(expired_id) in first.expired_asset_ids
    assert str(live_id) not in first.expired_asset_ids
    assert store.keys() == (f"private/physiognomy/{live_id}",)
    assert store.read(f"private/physiognomy/{live_id}") == JPEG
    assert second.purged_tokens == ()
    assert second.expired_asset_ids == ()
    assert store.keys() == (f"private/physiognomy/{live_id}",)

    async with database.sessions() as session:
        download_service = PhysiognomyMediaService(session, store)
        download_service.adapter = adapter
        downloaded = await download_service.download_owned(
            owner_kind="user",
            owner_id=user.id,
            token=live_ticket.token,
            now=NOW + timedelta(minutes=1),
        )
        assert downloaded.payload == JPEG
        assert downloaded.asset_id == str(live_id)


async def test_purge_worker_uses_injected_clock_and_store(database: Any) -> None:
    store = InMemoryPrivateMediaStore()

    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = PhysiognomyMediaService(session, store)
        asset_id = await _ingest(service, user, now=NOW, filename="fresh.jpg")
        ticket = await service.issue_signed_download(
            owner_kind="user",
            owner_id=user.id,
            asset_id=asset_id,
            ttl=SIGNED_TTL,
            now=NOW,
        )
        await session.commit()
        adapter = service.adapter

    object_key = f"private/physiognomy/{asset_id}"
    before_ticket_expiry = await _worker(
        database,
        store,
        now=NOW + timedelta(minutes=14),
        adapter=adapter,
    ).run_once()
    assert before_ticket_expiry.purged_tokens == ()
    assert before_ticket_expiry.expired_asset_ids == ()
    assert store.keys() == (object_key,)

    after_ticket_expiry = await _worker(
        database,
        store,
        now=NOW + SIGNED_TTL + timedelta(seconds=1),
        adapter=adapter,
    ).run_once()
    assert ticket.token in after_ticket_expiry.purged_tokens
    assert after_ticket_expiry.expired_asset_ids == ()
    assert store.keys() == (object_key,)

    after_asset_expiry = await _worker(
        database,
        store,
        now=NOW + timedelta(days=8),
        adapter=adapter,
    ).run_once()
    assert after_asset_expiry.purged_tokens == ()
    assert str(asset_id) in after_asset_expiry.expired_asset_ids
    assert store.keys() == ()

    again = await _worker(
        database,
        store,
        now=NOW + timedelta(days=8),
        adapter=adapter,
    ).run_once()
    assert again.purged_tokens == ()
    assert again.expired_asset_ids == ()
    assert store.keys() == ()


async def test_purge_worker_expires_from_injected_store_without_shared_adapter(
    database: Any,
) -> None:
    store = InMemoryPrivateMediaStore()

    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        service = PhysiognomyMediaService(session, store)
        asset_id = await _ingest(
            service,
            user,
            now=NOW - timedelta(days=8),
            filename="orphan.jpg",
        )
        await session.commit()

    result = await _worker(database, store, now=NOW).run_once()
    repeat = await _worker(database, store, now=NOW).run_once()

    assert str(asset_id) in result.expired_asset_ids
    assert result.purged_tokens == ()
    assert store.keys() == ()
    assert repeat.expired_asset_ids == ()
    assert repeat.purged_tokens == ()
    assert store.keys() == ()
