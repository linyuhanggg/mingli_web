from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

from app.readings.presentation.contracts import PresentationContract, ReadingDocumentV1


def build_reading_document(
    contract: PresentationContract,
    payload: Mapping[str, object],
) -> ReadingDocumentV1:
    document = ReadingDocumentV1.model_validate(payload)
    if document.product_version != contract.product_version:
        raise ValueError("document product_version does not match PresentationContract")
    if document.presentation_contract_version != contract.contract_version:
        raise ValueError("document PresentationContract version does not match")
    if document.versions.view_model_schema != document.view_model.schema_version:
        raise ValueError("document view model version metadata does not match its payload")

    configured_sections = tuple(section.section_id for section in contract.sections)
    if len(configured_sections) != len(set(configured_sections)):
        raise ValueError("PresentationContract section IDs must be unique")
    counts = Counter(claim.section_id for claim in document.claims)
    if not set(counts).issubset(configured_sections):
        raise ValueError("document contains a claim outside PresentationContract sections")
    presented_order = tuple(dict.fromkeys(claim.section_id for claim in document.claims))
    expected_order = tuple(section_id for section_id in configured_sections if counts[section_id])
    if presented_order != expected_order:
        raise ValueError("document claim sections do not follow PresentationContract order")

    for section in contract.sections:
        claim_count = counts[section.section_id]
        if not section.min_claims <= claim_count <= section.max_claims:
            raise ValueError(f"claim slots exceeded for section {section.section_id!r}")
        if any(
            len(claim.text) > section.max_chars_per_claim
            for claim in document.claims
            if claim.section_id == section.section_id
        ):
            raise ValueError(f"claim text exceeds section limit {section.section_id!r}")
        if any(
            claim.claim_kind_id not in section.allowed_claim_kind_ids
            for claim in document.claims
            if claim.section_id == section.section_id
        ):
            raise ValueError(f"claim kind is not allowed in section {section.section_id!r}")

    boundary_texts = {boundary.text for boundary in document.boundaries}
    if not set(contract.fixed_disclosures).issubset(boundary_texts):
        raise ValueError("document is missing a fixed PresentationContract disclosure")
    return document
