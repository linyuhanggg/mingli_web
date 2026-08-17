from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.api.validators import validate_iana_timezone
from app.charts.contracts import ViewModel
from app.readings.presentation import ReadingDocumentV1
from app.readings.share_contracts import SharedReadingDocumentV1
from app.readings.status import ReadingStatus

JsonObject = dict[str, Any]
DeliveryState = Literal[
    "not_required",
    "payment_required",
    "queued",
    "processing",
    "waiting_input",
    "delivered",
    "delayed",
    "failed",
]
LiuyaoCast = Annotated[
    list[Annotated[int, Field(ge=6, le=9)]],
    Field(min_length=6, max_length=6),
]
MeihuaTrigram = Literal["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
MeihuaCastingMethod = Literal[
    "time",
    "supplied_number",
    "sound_count",
    "observation",
    "supplied_hexagram",
]
LiuyaoQuestionClass = Literal["finance"]


class PreviewStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )
    target_year: int | None = Field(default=None, ge=1800, le=2199)
    target_month: str | None = Field(
        default=None,
        pattern=r"^\d{4}-(?:0[1-9]|1[0-2])$",
    )
    target_date: date | None = None

    @model_validator(mode="after")
    def _only_one_time_target(self) -> "PreviewStartRequest":
        supplied = sum(
            value is not None
            for value in (self.target_year, self.target_month, self.target_date)
        )
        if supplied > 1:
            raise ValueError("target_year, target_month, and target_date are mutually exclusive")
        return self


class BaziDeepStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    query: str | None = Field(default=None, min_length=1, max_length=300)


class CanwenStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    selected_art_ids: list[Literal["bazi", "ziwei", "qizheng"]] = Field(
        min_length=2,
        max_length=3,
    )
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[
        Literal["career", "health", "location", "outcome", "relationship", "state", "timing"]
    ] | None = Field(default=None, min_length=1, max_length=4)


class HecanStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    selected_art_ids: list[Literal["bazi", "ziwei", "qizheng"]] = Field(
        min_length=2,
        max_length=3,
    )
    dimension_ids: list[
        Literal[
            "career",
            "health",
            "location",
            "outcome",
            "relationship",
            "state",
            "timing",
        ]
    ] | None = Field(default=None, min_length=1, max_length=4)


class RelationshipStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_ids: list[UUID] = Field(min_length=2, max_length=2)
    relationship_type: Literal[
        "romantic",
        "married",
        "parent_child",
        "business",
        "work",
        "friend",
    ]
    dimension_ids: list[Literal["relationship"]] | None = Field(
        default=None,
        min_length=1,
        max_length=1,
    )

    @field_validator("profile_version_ids")
    @classmethod
    def _profile_versions_must_be_distinct(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("relationship profiles must be distinct")
        return value


class ChartSimilarityStartRequest(BaseModel):
    """Start the bounded exact Bazi four-pillar comparison."""

    model_config = ConfigDict(extra="forbid")

    profile_version_ids: list[UUID] = Field(min_length=2, max_length=2)
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[Literal["state"]] | None = Field(
        default=None,
        min_length=1,
        max_length=1,
    )

    @field_validator("profile_version_ids")
    @classmethod
    def _profile_versions_must_be_distinct(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("chart similarity profiles must be distinct")
        return value


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
    question_class: LiuyaoQuestionClass | None = None
    dimension_ids: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )

    @field_validator("timezone")
    @classmethod
    def _timezone_must_be_iana(cls, value: str) -> str:
        return validate_iana_timezone(value)


class LiuyaoDeepStartRequest(LiuyaoStartRequest):
    """Start a paid Liuyao deep read from one preserved six-line cast."""


class WenshiStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cast: LiuyaoCast | Literal["digital_coin"]
    event_datetime: datetime
    timezone: str = Field(min_length=1, max_length=64)
    location: str = Field(min_length=1, max_length=120)
    subject_ref: str | None = Field(default=None, min_length=1, max_length=120)
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[Literal["outcome", "timing"]] | None = Field(
        default=None,
        min_length=1,
        max_length=2,
    )
    time_basis_policy: Literal[
        "civil",
        "solar",
        "longitude_mean_solar-v1",
        "local_apparent_solar-v1",
    ] = "civil"
    zi_hour_policy: Literal["midnight", "substitute", "solar"] = "midnight"
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    coordinate_source: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator("timezone")
    @classmethod
    def _timezone_must_be_iana(cls, value: str) -> str:
        return validate_iana_timezone(value)


class EventArtStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    time_basis_policy: Literal[
        "civil",
        "solar",
        "longitude_mean_solar-v1",
        "local_apparent_solar-v1",
    ] = "civil"
    zi_hour_policy: Literal["midnight", "substitute", "solar"] = "midnight"
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    coordinate_source: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator("timezone")
    @classmethod
    def _timezone_must_be_iana(cls, value: str) -> str:
        return validate_iana_timezone(value)


class DaliurenStartRequest(EventArtStartRequest):
    """Start a Liuren event reading, with an explicit bounded timing window."""

    timing_start: date | None = None
    timing_end: date | None = None

    @model_validator(mode="after")
    def _timing_window_matches_requested_dimension(self) -> "DaliurenStartRequest":
        dimensions = set(self.dimension_ids or ("outcome",))
        timing_requested = "timing" in dimensions
        if timing_requested and (self.timing_start is None or self.timing_end is None):
            raise ValueError(
                "Daliuren timing requires timing_start and timing_end"
            )
        if not timing_requested and (
            self.timing_start is not None or self.timing_end is not None
        ):
            raise ValueError(
                "Daliuren timing bounds require the timing dimension"
            )
        if self.timing_start is not None and self.timing_end is not None:
            if self.timing_end < self.timing_start:
                raise ValueError("Daliuren timing_end must not precede timing_start")
            if self.timing_end - self.timing_start > timedelta(days=30):
                raise ValueError("Daliuren timing horizon may contain at most 31 days")
        return self


class QimenDeepStartRequest(EventArtStartRequest):
    """Start a paid Qimen deep-read job from one frozen event board."""


class LumingNayinStartRequest(PreviewStartRequest):
    """Start the profile-bound Luming/Nayin Runtime product."""


class RhythmStartRequest(BaseModel):
    """Start the facts-only Nayin sound profile tool."""

    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[Literal["state"]] | None = Field(
        default=None,
        min_length=1,
        max_length=1,
    )


class FiveElementsFactsStartRequest(BaseModel):
    """Start the profile-bound, facts-only five-elements product."""

    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[Literal["state"]] | None = Field(
        default=None,
        min_length=1,
        max_length=1,
    )


TimeCheckEventDomain = Literal[
    "career",
    "education",
    "finance",
    "relationship",
    "family",
    "location",
    "health",
]


class TimeCheckKnownEvent(BaseModel):
    """A dated, user-confirmed event used only for bounded time evidence."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=80)
    occurred_at: datetime | date
    domain: TimeCheckEventDomain


class TimeCheckStartRequest(BaseModel):
    """Start the bounded twelve-hour candidate fact tool."""

    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    time_range_start: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    time_range_end: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    known_events: list[str] = Field(default_factory=list, max_length=5)
    known_event_facts: list[TimeCheckKnownEvent] = Field(
        default_factory=list,
        max_length=5,
    )
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[Literal["time_options"]] | None = Field(
        default=None,
        min_length=1,
        max_length=1,
    )


class TaiyiStartRequest(EventArtStartRequest):
    """Start a time-and-location-bound Taiyi annual board."""


class SelectionStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_profile: str = Field(min_length=1, max_length=80)
    requested_actions: list[str] = Field(default_factory=list, max_length=16)
    date_range_start: date
    date_range_end: date
    requested_scopes: list[Literal["directional_judgment"]] = Field(
        default_factory=list,
        max_length=4,
    )
    hard_constraints: JsonObject = Field(default_factory=dict)
    participant_facts: list[JsonObject] = Field(default_factory=list, max_length=16)
    directional_context: dict[str, str] | None = None
    include_folk_comparison: bool = False
    timezone: str = Field(min_length=1, max_length=64)
    location: str = Field(min_length=1, max_length=120)
    subject_ref: str | None = Field(default=None, min_length=1, max_length=120)
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[Literal["location", "state", "timing"]] | None = Field(
        default=None,
        min_length=1,
        max_length=3,
    )
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    coordinate_source: str | None = Field(default=None, min_length=1, max_length=40)

    @field_validator("timezone")
    @classmethod
    def _timezone_must_be_iana(cls, value: str) -> str:
        return validate_iana_timezone(value)


class FengshuiStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fengshui_spec: JsonObject = Field(min_length=1)
    subject_ref: str | None = Field(default=None, min_length=1, max_length=120)
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[Literal["current_state", "direction", "location", "state"]] | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )


class MeihuaStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    casting_method: MeihuaCastingMethod = "time"
    event_datetime: datetime
    timezone: str = Field(min_length=1, max_length=64)
    location: str = Field(min_length=1, max_length=120)
    subject_ref: str | None = Field(default=None, min_length=1, max_length=120)
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[Literal["outcome", "state"]] | None = Field(
        default=None,
        min_length=1,
        max_length=2,
    )
    time_basis_policy: Literal[
        "civil",
        "solar",
        "longitude_mean_solar-v1",
        "local_apparent_solar-v1",
    ] = "civil"
    zi_hour_policy: Literal["midnight", "substitute", "solar"] = "midnight"
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    coordinate_source: str | None = Field(default=None, min_length=1, max_length=40)
    number: int | None = Field(default=None, gt=0)
    count: int | None = Field(default=None, gt=0)
    upper_trigram: MeihuaTrigram | None = None
    lower_trigram: MeihuaTrigram | None = None
    moving_line: int | None = Field(default=None, ge=1, le=6)
    provenance: JsonObject | None = Field(default=None, min_length=1)
    observation_source: JsonObject | None = Field(default=None, min_length=1)

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


class RecastProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["profile_preview", "today", "week"]
    profile_version_id: UUID
    query: str | None = Field(default=None, min_length=1, max_length=300)
    dimension_ids: list[Literal["overview", "career"]] | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )


class RecastLiuyaoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["liuyao_one_question"]
    cast: LiuyaoCast | Literal["digital_coin"]
    event_datetime: datetime
    timezone: str = Field(min_length=1, max_length=64)
    location: str = Field(min_length=1, max_length=120)
    subject_ref: str | None = Field(default=None, min_length=1, max_length=120)
    query: str | None = Field(default=None, min_length=1, max_length=300)
    question_class: LiuyaoQuestionClass | None = None
    dimension_ids: list[Literal["career", "outcome", "timing"]] | None = Field(
        default=None,
        min_length=1,
        max_length=4,
    )

    @field_validator("timezone")
    @classmethod
    def _timezone_must_be_iana(cls, value: str) -> str:
        return validate_iana_timezone(value)


RecastRequest = Annotated[
    RecastProfileRequest | RecastLiuyaoRequest,
    Field(discriminator="action"),
]


class VerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["accepted", "partial", "disagreed", "unknown"]
    note: str | None = Field(default=None, max_length=500)


class ClaimVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["accepted", "partial", "disagreed", "unknown"]
    note: str | None = Field(default=None, max_length=500)


class ReportFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["helpful", "not_helpful", "unknown"]
    note: str | None = Field(default=None, max_length=500)


class CreateShareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ttl_seconds: int = Field(default=86_400, ge=300, le=604_800)


class CreateExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["png", "pdf"]
    ttl_seconds: int = Field(default=86_400, ge=300, le=86_400)


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
    product_id: str | None = None
    runtime_capability_ids: list[str] = Field(default_factory=list)
    version: int = Field(ge=1)
    status: ReadingStatus
    object_id: str
    dimension_ids: list[str]
    horizon: Horizon
    prior_answer: str | None = None
    input_request: JsonObject | None = None
    created_at: datetime
    # Public delivery/payment state is intentionally separate from the
    # internal ReadingStatus state machine.  Free previews do not have a
    # fulfillment gate; paid products expose only this bounded projection.
    delivery_state: DeliveryState = "not_required"


class ReadingStartResponse(ReadingVersionSummary):
    pass


class FulfillmentBindingRequest(BaseModel):
    """Bind one verified payment to an owned Reading Job."""

    model_config = ConfigDict(extra="forbid")

    payment_id: UUID


class FulfillmentBindingResponse(BaseModel):
    """Safe owner-scoped result of the local fulfillment binding step."""

    model_config = ConfigDict(extra="forbid")

    fulfillment_id: UUID
    reading_version_id: UUID
    reading_job_id: UUID
    status: str = Field(min_length=1, max_length=24)
    created: bool


class ReadingListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    readings: list[ReadingVersionSummary]


class AccountHistoryVersionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_version_id: UUID
    reading_root_id: UUID
    capability_id: str
    product_id: str | None = None
    runtime_capability_ids: list[str] = Field(default_factory=list)
    version: int = Field(ge=1)
    status: ReadingStatus
    object_id: str
    dimension_ids: list[str]
    horizon: Horizon
    created_at: datetime


class AccountHistoryRootResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_root_id: UUID
    profile_version_id: UUID | None
    capability_id: str
    product_id: str | None = None
    runtime_capability_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    versions: list[AccountHistoryVersionSummary]


class AccountHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roots: list[AccountHistoryRootResponse]


class ReadingVerificationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification_id: UUID
    reading_version_id: UUID
    outcome: Literal["accepted", "partial", "disagreed", "unknown"]
    note: str | None
    created_at: datetime


class ReadingResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_version_id: UUID
    status: str
    accepted_copy: str | None
    fact_panel: JsonObject | None
    view_model: ViewModel | None
    verification: ReadingVerificationSummary | None
    input_request: JsonObject | None
    document: ReadingDocumentV1 | None


class ClaimVerificationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification_id: UUID
    reading_version_id: UUID
    claim_id: str
    outcome: Literal["accepted", "partial", "disagreed", "unknown"]
    note: str | None
    created_at: datetime


class ReportFeedbackSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_id: UUID
    reading_version_id: UUID
    outcome: Literal["helpful", "not_helpful", "unknown"]
    note: str | None
    created_at: datetime


class ShareResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: UUID
    token: str
    expires_at: datetime


class ExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_id: UUID
    token: str
    format: Literal["png", "pdf"]
    content_type: str
    file_name: str
    expires_at: datetime


class SharedReadingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: SharedReadingDocumentV1
