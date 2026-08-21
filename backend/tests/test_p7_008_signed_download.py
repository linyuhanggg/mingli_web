from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from app.identity.models import User
from app.media.physiognomy import (
    InMemoryPrivateMediaStore,
    MediaNotFoundError,
    MediaNotReadyError,
    SignedDownloadExpiredError,
    SignedDownloadInvalidError,
)
from app.media.service import PhysiognomyMediaService

NOW = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)
JPEG = b"\xff\xd8\xff\xe0" + b"mingli-p7-008-jpeg"
SIGNED_TTL = timedelta(minutes=15)


async def _seed_owned_asset(
    session: Any,
    *,
    store: InMemoryPrivateMediaStore | None = None,
    now: datetime = NOW,
) -> tuple[PhysiognomyMediaService, InMemoryPrivateMediaStore, User, UUID]:
    user = User()
    session.add(user)
    await session.flush()
    media_store = InMemoryPrivateMediaStore() if store is None else store
    service = PhysiognomyMediaService(session, media_store)
    asset = await service.ingest(
        owner_kind="user",
        owner_id=user.id,
        content_type="image/jpeg",
        filename="subject-front.jpg",
        payload=JPEG,
        width=1200,
        height=1600,
        consent=True,
        mode="face",
        consent_policy_version="physiognomy-photo-v1",
        now=now,
    )
    return service, media_store, user, UUID(asset.asset_id)


async def test_owner_issues_signed_download_and_reads_private_bytes(
    database: Any,
) -> None:
    async with database.sessions() as session:
        service, store, user, asset_id = await _seed_owned_asset(session)
        ticket = await service.issue_signed_download(
            owner_kind="user",
            owner_id=user.id,
            asset_id=asset_id,
            ttl=SIGNED_TTL,
            now=NOW,
        )
        downloaded = await service.download_owned(
            owner_kind="user",
            owner_id=user.id,
            token=ticket.token,
            now=NOW + timedelta(minutes=1),
        )

        assert ticket.asset_id == str(asset_id)
        assert ticket.content_type == "image/jpeg"
        assert ticket.expires_at == NOW + SIGNED_TTL
        assert ticket.token.startswith(f"v1.{asset_id}.")
        assert downloaded.payload == JPEG
        assert downloaded.content_type == "image/jpeg"
        assert store.read(f"private/physiognomy/{asset_id}") == JPEG


async def test_expired_signed_download_is_rejected(
    database: Any,
) -> None:
    async with database.sessions() as session:
        service, _, user, asset_id = await _seed_owned_asset(session)
        ticket = await service.issue_signed_download(
            owner_kind="user",
            owner_id=user.id,
            asset_id=asset_id,
            ttl=SIGNED_TTL,
            now=NOW,
        )

        with pytest.raises(SignedDownloadExpiredError, match="expired"):
            await service.download_owned(
                owner_kind="user",
                owner_id=user.id,
                token=ticket.token,
                now=ticket.expires_at,
            )
        with pytest.raises(SignedDownloadExpiredError, match="expired"):
            await service.download_owned(
                owner_kind="user",
                owner_id=user.id,
                token=ticket.token,
                now=ticket.expires_at + timedelta(seconds=1),
            )


async def test_tampered_or_foreign_signature_is_rejected(
    database: Any,
) -> None:
    async with database.sessions() as session:
        service, _, user, asset_id = await _seed_owned_asset(session)
        ticket = await service.issue_signed_download(
            owner_kind="user",
            owner_id=user.id,
            asset_id=asset_id,
            ttl=SIGNED_TTL,
            now=NOW,
        )
        prefix, asset, expires, signature = ticket.token.split(".")
        flipped = "0" if signature[-1] != "0" else "1"
        tampered = ".".join((prefix, asset, expires, signature[:-1] + flipped))

        with pytest.raises(SignedDownloadInvalidError, match="invalid"):
            await service.download_owned(
                owner_kind="user",
                owner_id=user.id,
                token=tampered,
                now=NOW + timedelta(minutes=1),
            )
        with pytest.raises(SignedDownloadInvalidError, match="invalid"):
            await service.download_owned(
                owner_kind="user",
                owner_id=user.id,
                token="not-a-signed-token",
                now=NOW + timedelta(minutes=1),
            )

        other_store = InMemoryPrivateMediaStore()
        other_service = PhysiognomyMediaService(
            session,
            other_store,
            signing_key=b"another-local-fake-media-download-key",
        )
        other_user = User()
        session.add(other_user)
        await session.flush()
        other_asset = await other_service.ingest(
            owner_kind="user",
            owner_id=other_user.id,
            content_type="image/jpeg",
            filename="other.jpg",
            payload=JPEG,
            width=1200,
            height=1600,
            consent=True,
            mode="face",
            consent_policy_version="physiognomy-photo-v1",
            now=NOW,
        )
        foreign = await other_service.issue_signed_download(
            owner_kind="user",
            owner_id=other_user.id,
            asset_id=UUID(other_asset.asset_id),
            ttl=SIGNED_TTL,
            now=NOW,
        )
        with pytest.raises(SignedDownloadInvalidError, match="invalid"):
            await service.download_owned(
                owner_kind="user",
                owner_id=other_user.id,
                token=foreign.token,
                now=NOW + timedelta(minutes=1),
            )


async def test_only_owner_can_issue_or_download(
    database: Any,
) -> None:
    async with database.sessions() as session:
        service, _, owner, asset_id = await _seed_owned_asset(session)
        stranger = User()
        session.add(stranger)
        await session.flush()
        ticket = await service.issue_signed_download(
            owner_kind="user",
            owner_id=owner.id,
            asset_id=asset_id,
            ttl=SIGNED_TTL,
            now=NOW,
        )

        with pytest.raises(MediaNotFoundError):
            await service.issue_signed_download(
                owner_kind="user",
                owner_id=stranger.id,
                asset_id=asset_id,
                ttl=SIGNED_TTL,
                now=NOW,
            )
        with pytest.raises(MediaNotFoundError):
            await service.download_owned(
                owner_kind="user",
                owner_id=stranger.id,
                token=ticket.token,
                now=NOW + timedelta(minutes=1),
            )

        downloaded = await service.download_owned(
            owner_kind="user",
            owner_id=owner.id,
            token=ticket.token,
            now=NOW + timedelta(minutes=1),
        )
        assert downloaded.payload == JPEG


async def test_expiry_cleanup_drops_bytes_and_rejects_signed_download(
    database: Any,
) -> None:
    async with database.sessions() as session:
        service, store, user, asset_id = await _seed_owned_asset(session)
        ticket = await service.issue_signed_download(
            owner_kind="user",
            owner_id=user.id,
            asset_id=asset_id,
            ttl=SIGNED_TTL,
            now=NOW,
        )
        purged = await service.purge_expired_signed_downloads(
            now=NOW + SIGNED_TTL + timedelta(seconds=1)
        )
        expired_assets = await service.expire(now=NOW + timedelta(days=8))

        assert ticket.token in purged
        assert str(asset_id) in expired_assets
        assert store.keys() == ()
        with pytest.raises(MediaNotReadyError):
            await service.download_owned(
                owner_kind="user",
                owner_id=user.id,
                token=ticket.token,
                now=NOW + timedelta(minutes=1),
            )
        with pytest.raises(MediaNotReadyError):
            await service.issue_signed_download(
                owner_kind="user",
                owner_id=user.id,
                asset_id=asset_id,
                ttl=SIGNED_TTL,
                now=NOW + timedelta(days=8),
            )
