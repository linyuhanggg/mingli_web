from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.api.validators import validate_iana_timezone


class ProfileDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80)


class ProfileDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: UUID
    status: Literal["draft"] = "draft"


class ProfileConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    birth_datetime: str = Field(
        min_length=1,
        max_length=40,
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$",
    )
    timezone: str = Field(min_length=1, max_length=64)
    location: str = Field(min_length=1, max_length=120)
    gender: Literal["male", "female", "other"]
    calendar: Literal["gregorian", "lunar"] = "gregorian"
    lunar_leap_month: bool = False
    birth_time_certainty: Literal["exact", "approximate", "unknown"] = "exact"
    time_basis_policy: Literal["civil", "solar", "lunar"]
    zi_hour_policy: Literal["midnight", "substitute", "solar"]
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    coordinate_source: str | None = Field(default=None, min_length=1, max_length=40)
    coordinate_precision: Literal["exact", "city"] | None = None

    @field_validator("timezone")
    @classmethod
    def _timezone_must_be_iana(cls, value: str) -> str:
        return validate_iana_timezone(value)

    @model_validator(mode="after")
    def _birth_facts_must_be_explicit(self) -> ProfileConfirmRequest:
        has_longitude = self.longitude is not None
        has_latitude = self.latitude is not None
        if has_longitude != has_latitude:
            raise ValueError("longitude and latitude must be provided together")
        if has_longitude:
            if self.coordinate_source is None:
                raise ValueError(
                    "coordinate_source is required when coordinates are provided"
                )
            if self.coordinate_precision is None:
                raise ValueError(
                    "coordinate_precision is required when coordinates are provided"
                )
        if self.time_basis_policy == "solar" and not has_longitude:
            raise ValueError(
                "solar time basis requires explicit user-confirmed coordinates; "
                "the service never estimates them silently"
            )
        if self.calendar == "gregorian" and self.lunar_leap_month:
            raise ValueError("lunar_leap_month requires the lunar calendar")
        return self


class ProfileSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: UUID
    profile_version_id: UUID
    subject_ref: str
    version: int
    created_at: datetime


class ProfileListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profiles: list[ProfileSummary]
