from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.media.physiognomy import PhysiognomyMediaAdapter, PrivateMediaStore
from app.media.service import PhysiognomyMediaService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class MediaPurgeClock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class SystemMediaPurgeClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class MediaPurgeResult:
    purged_tokens: tuple[str, ...]
    expired_asset_ids: tuple[str, ...]


@dataclass(slots=True)
class MediaPurgeWorker:
    """Sweep expired signed-download tickets and retained private media bytes.

    Issue and download stay on PhysiognomyMediaService. This worker only calls
    the existing purge/expire methods with an injected clock and store.
    """

    sessions: async_sessionmaker[AsyncSession]
    store: PrivateMediaStore
    clock: MediaPurgeClock = field(default_factory=SystemMediaPurgeClock)
    adapter: PhysiognomyMediaAdapter | None = None
    signing_key: bytes | None = None

    async def run_once(self) -> MediaPurgeResult:
        current = self.clock.now()
        async with self.sessions() as session:
            service = PhysiognomyMediaService(
                session,
                self.store,
                signing_key=self.signing_key,
            )
            if self.adapter is not None:
                service.adapter = self.adapter
            purged_tokens = await service.purge_expired_signed_downloads(now=current)
            expired_asset_ids = await service.expire(now=current)
            await session.commit()
        return MediaPurgeResult(
            purged_tokens=purged_tokens,
            expired_asset_ids=expired_asset_ids,
        )
