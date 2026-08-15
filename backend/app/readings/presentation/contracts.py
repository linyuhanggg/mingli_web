from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.charts.contracts import ViewModel


class PresentationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PresentationSection(PresentationModel):
    section_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    min_claims: int = Field(ge=0)
    max_claims: int = Field(ge=0)
    max_chars_per_claim: int = Field(ge=1)
    allowed_claim_kind_ids: tuple[str, ...] = Field(min_length=1)


class PresentationContract(PresentationModel):
    schema_version: Literal["presentation-contract/v1"] = "presentation-contract/v1"
    contract_version: str = Field(min_length=1)
    product_version: str = Field(min_length=1)
    renderer: str = Field(min_length=1)
    sections: tuple[PresentationSection, ...] = Field(min_length=1)
    fixed_disclosures: tuple[str, ...]


class SubjectSummary(PresentationModel):
    subject_ref: str = Field(min_length=1)
    label: str = Field(min_length=1)


class ThemeNavigationItem(PresentationModel):
    theme_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class VerificationEntry(PresentationModel):
    enabled: bool


class ClaimCard(PresentationModel):
    claim_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1)
    dimension_id: str = Field(min_length=1)
    claim_kind_id: str = Field(min_length=1)
    certainty_id: str = Field(min_length=1)
    fact_refs: tuple[str, ...]
    finding_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    limit_refs: tuple[str, ...]
    verification: VerificationEntry


class EvidenceCard(PresentationModel):
    evidence_ref: str = Field(min_length=1)
    title: str = Field(min_length=1)
    supports_fact_refs: tuple[str, ...]


class Boundary(PresentationModel):
    limit_ref: str = Field(min_length=1)
    text: str = Field(min_length=1)


class ActionAvailability(PresentationModel):
    enabled: bool


class ReadingActions(PresentationModel):
    correction: ActionAvailability
    follow_up: ActionAvailability
    export: ActionAvailability
    share: ActionAvailability


class DocumentVersions(PresentationModel):
    runtime_release: str = Field(min_length=1)
    view_model_schema: str = Field(min_length=1)
    reading_document_schema: Literal["reading-document/v1"] = "reading-document/v1"


class ReadingDocumentV1(PresentationModel):
    schema_version: Literal["reading-document/v1"] = "reading-document/v1"
    document_id: str = Field(min_length=1)
    reading_version_id: str = Field(min_length=1)
    accepted_copy_ref: str = Field(min_length=1)
    product_version: str = Field(min_length=1)
    presentation_contract_version: str = Field(min_length=1)
    view_model: ViewModel
    answer_summary: str = Field(min_length=1)
    subject_summaries: tuple[SubjectSummary, ...] = Field(min_length=1)
    themes: tuple[ThemeNavigationItem, ...]
    claims: tuple[ClaimCard, ...]
    evidence: tuple[EvidenceCard, ...]
    boundaries: tuple[Boundary, ...]
    actions: ReadingActions
    versions: DocumentVersions
