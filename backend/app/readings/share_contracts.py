from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.readings.presentation.contracts import PresentationModel, ReadingDocumentV1


class SharedReadingTheme(PresentationModel):
    theme_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class SharedReadingClaim(PresentationModel):
    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class SharedReadingEvidence(PresentationModel):
    evidence_ref: str = Field(min_length=1)
    title: str = Field(min_length=1)


class SharedReadingBoundary(PresentationModel):
    limit_ref: str = Field(min_length=1)
    text: str = Field(min_length=1)


class SharedReadingVersions(PresentationModel):
    runtime_release: str = Field(min_length=1)
    view_model_schema: str = Field(min_length=1)
    reading_document_schema: Literal["reading-document/v1"]


class SharedReadingDocumentV1(PresentationModel):
    """The only document shape allowed through a bearer share token."""

    schema_version: Literal["shared-reading-document/v1"]
    document_id: str = Field(min_length=1)
    reading_version_id: str = Field(min_length=1)
    accepted_copy_ref: str = Field(min_length=1)
    product_version: str = Field(min_length=1)
    presentation_contract_version: str = Field(min_length=1)
    answer_summary: str = Field(min_length=1)
    themes: tuple[SharedReadingTheme, ...]
    claims: tuple[SharedReadingClaim, ...]
    evidence: tuple[SharedReadingEvidence, ...]
    boundaries: tuple[SharedReadingBoundary, ...]
    versions: SharedReadingVersions

    @classmethod
    def from_document(cls, document: ReadingDocumentV1) -> SharedReadingDocumentV1:
        return cls(
            schema_version="shared-reading-document/v1",
            document_id=document.document_id,
            reading_version_id=document.reading_version_id,
            accepted_copy_ref=document.accepted_copy_ref,
            product_version=document.product_version,
            presentation_contract_version=document.presentation_contract_version,
            answer_summary=document.answer_summary,
            themes=tuple(
                SharedReadingTheme(theme_id=theme.theme_id, label=theme.label)
                for theme in document.themes
            ),
            claims=tuple(
                SharedReadingClaim(claim_id=claim.claim_id, text=claim.text)
                for claim in document.claims
            ),
            evidence=tuple(
                SharedReadingEvidence(
                    evidence_ref=evidence.evidence_ref,
                    title=evidence.title,
                )
                for evidence in document.evidence
            ),
            boundaries=tuple(
                SharedReadingBoundary(
                    limit_ref=boundary.limit_ref,
                    text=boundary.text,
                )
                for boundary in document.boundaries
            ),
            versions=SharedReadingVersions(
                runtime_release=document.versions.runtime_release,
                view_model_schema=document.versions.view_model_schema,
                reading_document_schema="reading-document/v1",
            ),
        )


__all__ = [
    "SharedReadingBoundary",
    "SharedReadingClaim",
    "SharedReadingDocumentV1",
    "SharedReadingEvidence",
    "SharedReadingTheme",
    "SharedReadingVersions",
]
