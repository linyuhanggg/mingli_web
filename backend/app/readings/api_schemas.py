from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.validators import validate_iana_timezone
from app.readings.status import ReadingStatus

JsonObject = dict[str, Any]
LiuyaoCast = Annotated[
    list[Annotated[int, Field(ge=6, le=9)]],
    Field(min_length=6, max_length=6),
]


class PreviewStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )


class FortuneStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    query: str | None = Field(default=None, min_length=1, max_length=300)


class LiuyaoStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cast: LiuyaoCast | Literal["digital_coin"]
    event_datetime: datetime
    timezone: str = Field(min_length=1, max_length=64)
    location: str = Field(min_length=1, max_length=120)
    subject_ref: str | None = Field(default=None, min_length=1, max_length=120)
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )

    @field_validator("timezone")
    @classmethod
    def _timezone_must_be_iana(cls, value: str) -> str:
        return validate_iana_timezone(value)


class SupplyInputRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any] = Field(min_length=1)


class FollowUpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str | None = Field(default=None, min_length=1, max_length=300)


class VerificationResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_ref: str = Field(min_length=1, max_length=200)
    outcome: Literal["accepted", "partial", "disagreed", "unknown"]


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[VerificationResultItem] = Field(min_length=3, max_length=3)
    note: str | None = Field(default=None, max_length=500)


class Horizon(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind_id: str
    start: date | None = None
    end: date | None = None


class ReadingVersionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_version_id: UUID
    reading_root_id: UUID
    profile_version_id: UUID | None
    capability_id: str
    version: int = Field(ge=1)
    status: ReadingStatus
    object_id: str
    dimension_ids: list[str]
    horizon: Horizon
    prior_answer: str | None = None
    input_request: JsonObject | None = None
    created_at: datetime


class ReadingStartResponse(ReadingVersionSummary):
    pass


class ReadingListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    readings: list[ReadingVersionSummary]


class ReadingVerificationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification_id: UUID
    reading_version_id: UUID
    results: list[VerificationResultItem]
    note: str | None
    created_at: datetime


class ReadingResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_version_id: UUID
    status: str
    accepted_copy: str | None
    fact_panel: JsonObject | None
    verification: ReadingVerificationSummary | None
    input_request: JsonObject | None
