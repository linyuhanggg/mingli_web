from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.media.models import PhysiognomyMediaRecord
from app.media.physiognomy import (
    MediaNotFoundError,
    MediaNotReadyError,
    MediaStatus,
    ObservationMode,
    OwnerKind,
    PhysiognomyMediaAdapter,
    PhysiognomyMediaAsset,
    PhysiognomyRuntimeInput,
    PrivateMediaStore,
)


class PhysiognomyMediaService:
    """Persist private media metadata and keep Runtime media-blind."""

    def __init__(self, session: AsyncSession, store: PrivateMediaStore) -> None:
        self.session = session
        self.adapter = PhysiognomyMediaAdapter(store=store)

    async def ingest(
        self,
        *,
        owner_kind: OwnerKind,
        owner_id: UUID,
        content_type: str,
        filename: str,
        payload: bytes,
        width: int,
        height: int,
        consent: bool,
        mode: ObservationMode,
        consent_policy_version: str,
        now: datetime,
    ) -> PhysiognomyMediaAsset:
        asset = self.adapter.ingest(
            owner_kind=owner_kind,
            owner_id=owner_id,
            content_type=content_type,
            filename=filename,
            payload=payload,
            width=width,
            height=height,
            consent=consent,
            mode=mode,
            now=now,
        )
        try:
            self.session.add(
                PhysiognomyMediaRecord(
                    id=UUID(asset.asset_id),
                    owner_user_id=owner_id if owner_kind == "user" else None,
                    owner_guest_session_id=owner_id if owner_kind == "guest" else None,
                    object_key=asset.object_key,
                    content_type=asset.content_type,
                    byte_size=asset.byte_size,
                    width=asset.width,
                    height=asset.height,
                    mode=asset.mode,
                    consent_policy_version=consent_policy_version,
                    consented_at=asset.created_at,
                    status=asset.status,
                    expires_at=asset.expires_at,
                )
            )
            await self.session.flush()
        except Exception:
            self.adapter.delete(asset.asset_id, now=now)
            raise
        return asset

    async def get_owned(
        self,
        *,
        owner_kind: OwnerKind,
        owner_id: UUID,
        asset_id: UUID,
    ) -> PhysiognomyMediaAsset:
        record = await self._record_for_owner(owner_kind, owner_id, asset_id)
        return self._asset_from_record(record)

    async def delete(
        self,
        *,
        owner_kind: OwnerKind,
        owner_id: UUID,
        asset_id: UUID,
        now: datetime,
    ) -> PhysiognomyMediaAsset:
        record = await self._record_for_owner(owner_kind, owner_id, asset_id)
        asset = self._asset_from_record(record)
        if asset.status == "ready":
            self.adapter.restore(asset)
            deleted = self.adapter.delete(asset.asset_id, now=now)
            record.status = deleted.status
            record.deleted_at = deleted.deleted_at
            return deleted
        return asset

    async def build_runtime_input(
        self,
        *,
        owner_kind: OwnerKind,
        owner_id: UUID,
        asset_id: UUID,
        subject_ref: str,
        observations: Sequence[Mapping[str, object]],
        dimension_ids: tuple[str, ...],
    ) -> PhysiognomyRuntimeInput:
        record = await self._record_for_owner(owner_kind, owner_id, asset_id)
        asset = self._asset_from_record(record)
        if asset.status != "ready":
            raise MediaNotReadyError("physiognomy media is no longer available")
        self.adapter.restore(asset)
        return self.adapter.build_runtime_input(
            asset_id=asset.asset_id,
            subject_ref=subject_ref,
            observations=observations,
            dimension_ids=dimension_ids,
        )

    async def expire(self, *, now: datetime) -> tuple[str, ...]:
        current = _utc(now)
        records = list(
            await self.session.scalars(
                select(PhysiognomyMediaRecord).where(
                    PhysiognomyMediaRecord.status == "ready",
                    PhysiognomyMediaRecord.expires_at <= current,
                )
            )
        )
        expired: list[str] = []
        for record in records:
            asset = self._asset_from_record(record)
            self.adapter.restore(asset)
            self.adapter.expire(now=current)
            record.status = "expired"
            record.deleted_at = current
            expired.append(str(record.id))
        return tuple(expired)

    async def _record_for_owner(
        self,
        owner_kind: OwnerKind,
        owner_id: UUID,
        asset_id: UUID,
    ) -> PhysiognomyMediaRecord:
        owner_column = (
            PhysiognomyMediaRecord.owner_user_id
            if owner_kind == "user"
            else PhysiognomyMediaRecord.owner_guest_session_id
        )
        record = await self.session.scalar(
            select(PhysiognomyMediaRecord).where(
                PhysiognomyMediaRecord.id == asset_id,
                owner_column == owner_id,
            )
        )
        if record is None:
            raise MediaNotFoundError("physiognomy media asset not found")
        return record

    @staticmethod
    def _asset_from_record(record: PhysiognomyMediaRecord) -> PhysiognomyMediaAsset:
        owner_kind: OwnerKind
        owner_id: UUID
        if record.owner_user_id is not None:
            owner_kind = "user"
            owner_id = record.owner_user_id
        elif record.owner_guest_session_id is not None:
            owner_kind = "guest"
            owner_id = record.owner_guest_session_id
        else:
            raise MediaNotFoundError("physiognomy media owner is invalid")
        return PhysiognomyMediaAsset(
            asset_id=str(record.id),
            owner_kind=owner_kind,
            owner_id=owner_id,
            object_key=record.object_key,
            content_type=record.content_type,
            byte_size=record.byte_size,
            width=record.width,
            height=record.height,
            mode=cast(ObservationMode, record.mode),
            created_at=_utc(record.created_at),
            expires_at=_utc(record.expires_at),
            status=cast(MediaStatus, record.status),
            deleted_at=None if record.deleted_at is None else _utc(record.deleted_at),
        )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
