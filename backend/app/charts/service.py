from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.charts.api_schemas import BaziChartSyncResponse
from app.charts.sessions import ChartSessionManager
from app.config import Settings
from app.profiles.service import OwnerProtocol, ProfileService
from app.readings.request_compiler import (
    ConfirmedProfileVersion,
    compile_bazi_prepare,
)


class ChartServiceError(RuntimeError):
    """A synchronous chart request could not be completed."""


class ChartProfileNotFoundError(ChartServiceError):
    """The requested Profile Version is absent or belongs to another owner."""


class ChartService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        sessions: ChartSessionManager,
    ) -> None:
        self.profiles = ProfileService(session, settings)
        self.sessions = sessions

    async def sync_bazi(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
        idempotency_key: str,
    ) -> BaziChartSyncResponse:
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        command = compile_bazi_prepare(
            action="profile_preview",
            query="查看这个档案的确定性八字盘。",
            profile=profile,
            dimension_ids=("overview",),
        )
        return await self.sessions.start(
            owner_key=f"{owner.kind}:{owner.id}",
            profile_version_id=profile_version_id,
            prepare=command,
            idempotency_key=idempotency_key,
        )

    async def supply_input(
        self,
        owner: OwnerProtocol,
        *,
        chart_handle: str,
        values: dict[str, object],
        idempotency_key: str,
    ) -> BaziChartSyncResponse:
        return await self.sessions.supply_input(
            owner_key=f"{owner.kind}:{owner.id}",
            chart_handle=chart_handle,
            values=values,
            idempotency_key=idempotency_key,
        )

    async def _owned_confirmed_profile(
        self,
        owner: OwnerProtocol,
        profile_version_id: UUID,
    ) -> ConfirmedProfileVersion:
        try:
            _profile, version = await self.profiles.get_owned_profile_version(
                owner,
                profile_version_id,
            )
        except LookupError as error:
            raise ChartProfileNotFoundError("Profile Version not found") from error
        payload = await self.profiles.repository.load_version_payload(version.id)
        return ConfirmedProfileVersion(
            subject_ref=f"profile-version:{version.id}",
            birth_datetime=str(payload["birth_datetime"]),
            birth_datetime_or_four_pillars=str(payload["birth_datetime"]),
            timezone=str(payload["timezone"]),
            location=str(payload["location"]),
            gender=str(payload["gender"]),
            time_basis_policy=str(payload["time_basis_policy"]),
            zi_hour_policy=str(payload["zi_hour_policy"]),
            longitude=cast(float | None, payload.get("longitude")),
            latitude=cast(float | None, payload.get("latitude")),
            coordinate_source=cast(str | None, payload.get("coordinate_source")),
        )
