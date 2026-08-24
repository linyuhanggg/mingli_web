from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.validators import validate_iana_timezone


class ProfileDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80, pattern=r".*\S.*")

    @field_validator("label", mode="before")
    @classmethod
    def _normalize_label(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


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
    time_basis_policy: Literal["civil", "solar", "lunar"]
    zi_hour_policy: Literal["midnight", "substitute", "solar"]
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    coordinate_source: str | None = Field(default=None, min_length=1, max_length=40)
    subject_type: Literal["self", "other"] = "self"
    is_minor: bool = False
    authorization_confirmed: bool = False
    photo_authorization_confirmed: bool = False
    minor_guardian_confirmed: bool = False

    @field_validator("timezone")
    @classmethod
    def _timezone_must_be_iana(cls, value: str) -> str:
        return validate_iana_timezone(value)


class ProfileVersionRequest(ProfileConfirmRequest):
    model_config = ConfigDict(extra="forbid")

    difference_acknowledged: bool


class ProfileDisplayNameUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(
        min_length=1,
        max_length=80,
        pattern=r".*\S.*",
    )

    @field_validator("display_name", mode="before")
    @classmethod
    def _normalize_display_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProfileSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: UUID
    profile_version_id: UUID
    subject_ref: str
    version: int
    display_name: Annotated[str, Field(min_length=1, max_length=80)] | None
    birth_date: date | None
    created_at: datetime


class ProfileListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profiles: list[ProfileSummary]


class ProfileVersionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    versions: list[ProfileSummary]
