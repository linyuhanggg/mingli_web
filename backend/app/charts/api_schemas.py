from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaziChartSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID


class BaziChartSupplyInputRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any]


class BaziChartReadyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    status: Literal["ready"]
    chart_handle: str | None = None
    fact_panel: dict[str, Any]
    input_request: None = None


class BaziChartNeedInputResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    status: Literal["need_input"]
    chart_handle: str
    fact_panel: None = None
    input_request: dict[str, Any]


type BaziChartSyncResponse = BaziChartReadyResponse | BaziChartNeedInputResponse
