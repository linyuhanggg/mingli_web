from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.charts.api_schemas import BaziChartSyncResponse
from app.charts.runtime import ChartRuntimeFactory
from app.config import Settings
from app.profiles.service import OwnerProtocol, ProfileService
from app.readings.public_fact_panel import project_public_fact_panel
from app.readings.request_compiler import (
    ConfirmedProfileVersion,
    compile_bazi_prepare,
)
from app.readings.runtime_contracts import Prepared


class ChartServiceError(RuntimeError):
    """A synchronous chart request could not be completed."""


class ChartProfileNotFoundError(ChartServiceError):
    """The requested Profile Version is absent or belongs to another owner."""


class ChartPrepareStoppedError(ChartServiceError):
    """Runtime did not prepare a chart from the confirmed profile."""


class ChartService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        runtime_factory: ChartRuntimeFactory,
    ) -> None:
        self.profiles = ProfileService(session, settings)
        self.runtime_factory = runtime_factory

    async def sync_bazi(
        self,
        owner: OwnerProtocol,
        *,
        profile_version_id: UUID,
    ) -> BaziChartSyncResponse:
        profile = await self._owned_confirmed_profile(owner, profile_version_id)
        command = compile_bazi_prepare(
            action="profile_preview",
            query="查看这个档案的确定性八字盘。",
            profile=profile,
            dimension_ids=("overview",),
        )
        lease = await self.runtime_factory.open()
        try:
            result = await lease.runtime.execute(command)
        finally:
            await lease.aclose()
        if not isinstance(result, Prepared):
            raise ChartPrepareStoppedError("Runtime did not prepare the chart")
        fact_panel = project_public_fact_panel(result.brief)
        if fact_panel is None:
            raise ChartPrepareStoppedError("Runtime prepared no public fact panel")
        return BaziChartSyncResponse(
            profile_version_id=profile_version_id,
            status="ready",
            fact_panel=fact_panel,
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
