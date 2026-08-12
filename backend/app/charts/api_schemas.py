from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaziChartSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID


class BaziChartSupplyInputRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any] = Field(min_length=1)


class BaziChartReadyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    status: Literal["ready"]
    chart_handle: None
    fact_panel: dict[str, Any]
    input_request: None


class BaziChartNeedInputResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    status: Literal["need_input"]
    chart_handle: str
    fact_panel: None
    input_request: dict[str, Any]


type BaziChartSyncResponse = Annotated[
    BaziChartReadyResponse | BaziChartNeedInputResponse,
    Field(discriminator="status"),
]
