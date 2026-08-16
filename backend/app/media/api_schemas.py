from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ObservationMode = Literal["face", "palm", "posture", "combined"]
PhysiognomyDimension = Literal["state", "source_comparison"]


def _default_physiognomy_dimensions() -> list[PhysiognomyDimension]:
    return ["state"]


class PhysiognomyMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: UUID
    content_type: str
    byte_size: int
    width: int
    height: int
    mode: ObservationMode
    status: Literal["ready", "deleted", "expired"]
    created_at: str
    expires_at: str


class PhysiognomyObservationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region: str = Field(min_length=1, max_length=64)
    feature_kind: str = Field(min_length=1, max_length=64)
    descriptor: str = Field(min_length=1, max_length=96)
    visibility: Literal["full", "partial"]
    uncertainty: float = Field(default=0, ge=0, le=1)
    occlusion: float = Field(default=0, ge=0, le=1)


class PhysiognomyStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: UUID
    subject_ref: str = Field(min_length=1, max_length=120)
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[PhysiognomyDimension] = Field(
        default_factory=_default_physiognomy_dimensions,
        min_length=1,
        max_length=2,
    )
    observations: list[PhysiognomyObservationInput] = Field(
        min_length=1,
        max_length=64,
    )
