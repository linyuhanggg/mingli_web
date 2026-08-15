from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClosureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closure_id: UUID
    user_id: UUID
    status: str
    requested_at: datetime
    cancel_until: datetime
    cancelled_at: datetime | None = None
    executed_at: datetime | None = None


class DataExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    user_id: UUID
    payload: dict[str, Any]


class ClosureListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closures: list[ClosureResponse]
