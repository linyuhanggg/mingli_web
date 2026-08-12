from datetime import date
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaziChartSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID


class BaziChartSupplyInputRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, Any] = Field(min_length=1)


class RuntimeInputChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str | None


class RuntimeInputField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    type_id: Literal["integer", "text", "textarea", "choice"]
    description: str | None
    choices: list[RuntimeInputChoice]


class RuntimeInputRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    any_of: list[RuntimeInputField] = Field(min_length=1)


class RuntimeInputRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirements: list[RuntimeInputRequirement] = Field(min_length=1)


class PublicTerm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    description: str | None


class ReadingFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str
    subject_ref: str
    kind_id: str
    value: Any
    display_text: str


class ReadingEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str
    source_title: str
    locator: str | None = None
    excerpt: str | None = None
    supports_fact_refs: list[str]


class ReadingFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str
    subject_ref: str
    dimension_ids: list[str]
    kind_id: str
    data: dict[str, Any]
    fact_refs: list[str]
    evidence_refs: list[str]
    limit_kind_ids: list[str]
    support_mode: Literal["exact", "shared_turn"]


class ReadingClaimScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_ref: str
    dimension_id: str
    allowed_kind_ids: list[str]
    certainty_ceiling_id: str
    fact_refs: list[str]
    evidence_refs: list[str]


class ReadingLimit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind_id: str
    public_text: str
    scope_refs: list[str]
    detail_ids: list[str]


class ReadingHorizon(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind_id: str
    start: date | None
    end: date | None


class ReadingRequestView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_refs: list[str]
    capability_ids: list[str]
    object_id: str
    dimension_ids: list[str]
    horizon: ReadingHorizon


class ReadingFactPanel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    vocabulary: list[PublicTerm]
    facts: list[ReadingFact]
    evidence: list[ReadingEvidence]
    findings: list[ReadingFinding]
    claim_scopes: list[ReadingClaimScope]
    limits: list[ReadingLimit]
    prior_answer: str | None
    request_view: ReadingRequestView | None


class BaziChartReadyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    status: Literal["ready"]
    chart_handle: None
    fact_panel: ReadingFactPanel
    input_request: None


class BaziChartNeedInputResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version_id: UUID
    status: Literal["need_input"]
    chart_handle: str
    fact_panel: None
    input_request: RuntimeInputRequest


type BaziChartSyncResponse = Annotated[
    BaziChartReadyResponse | BaziChartNeedInputResponse,
    Field(discriminator="status"),
]
