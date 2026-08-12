from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaziChartSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID


class BaziChartSyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    status: Literal["ready"]
    chart_handle: str | None = None
    fact_panel: dict[str, Any]
    input_request: None = None
