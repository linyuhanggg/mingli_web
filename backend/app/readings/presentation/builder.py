from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from app.charts.projectors import project_runtime_view_model
from app.readings.narrative_contracts import NarrativeCandidate, OutputContract
from app.readings.presentation.contracts import (
    ActionAvailability,
    Boundary,
    ClaimCard,
    DocumentVersions,
    EvidenceCard,
    PresentationContract,
    PresentationSection,
    ReadingActions,
    ReadingDocumentV1,
    SubjectSummary,
    ThemeNavigationItem,
    VerificationEntry,
)
from app.readings.presentation.projector import build_reading_document as validate_reading_document
from app.readings.runtime_contracts import Prepared, ReadingBrief


@dataclass(frozen=True, slots=True)
class ReadingDocumentContext:
    """The immutable inputs needed to project one accepted reading document."""

    reading_version_id: UUID
    accepted_copy_ref: str
    product_id: str
    relationship_type: str | None
    runtime_release: str
    prepared: Prepared
    candidate: NarrativeCandidate
    output_contract: OutputContract
    product_version: str | None = None
    presentation_contract_version: str | None = None
    follow_up_count: int = 0
    follow_up_window_seconds: int = 0

    def __post_init__(self) -> None:
        if not self.accepted_copy_ref.strip():
            raise ValueError("accepted_copy_ref must be non-empty")
        if not self.product_id.strip():
            raise ValueError("product_id must be non-empty")
        if not self.runtime_release.strip():
            raise ValueError("runtime_release must be non-empty")


_THEME_LABELS = {
    "career": "事业",
    "health": "健康",
    "location": "迁移与位置",
    "outcome": "结果",
    "relationship": "关系",
    "state": "状态",
    "timing": "时机",
}
_FULLTEXT_LINE_LOCATOR = re.compile(
    r"(?:^|/)fulltext\.md#L(?P<line>\d+)(?:-L(?P<end_line>\d+))?$",
    re.IGNORECASE,
)


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item.strip())


def _public_source_title(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "依据"
    title = value.strip()
    if title.startswith("《") and title.endswith("》"):
        return title
    return f"《{title}》"


def _public_locator(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    locator = value.strip()
    match = _FULLTEXT_LINE_LOCATOR.fullmatch(locator)
    if match is not None:
        end_line = match.group("end_line")
        if end_line is None:
            return f"第 {match.group('line')} 行"
        return f"第 {match.group('line')} 至 {end_line} 行"
    # Paths, file anchors, and rule IDs are runtime locators rather than
    # user-facing source labels. Plain labels such as "卷三" remain useful.
    if "/" in locator or "#" in locator or "." in locator:
        return None
    return locator


def _subject_summaries(
    brief: Mapping[str, object],
    candidate: NarrativeCandidate,
) -> tuple[SubjectSummary, ...]:
    request_view = brief.get("request_view")
    refs = (
        _strings(request_view.get("subject_refs"))
        if isinstance(request_view, Mapping)
        else ()
    )
    if not refs:
        refs = tuple(dict.fromkeys(block.subject_ref for block in candidate.blocks))
    if not refs:
        raise ValueError("ReadingDocument requires at least one subject")
    labels: tuple[str, ...]
    if len(refs) == 1:
        labels = ("本人",)
    elif len(refs) == 2:
        labels = ("甲方", "乙方")
    else:
        labels = tuple(f"对象{index}" for index in range(1, len(refs) + 1))
    return tuple(
        SubjectSummary(subject_ref=ref, label=labels[index])
        for index, ref in enumerate(refs)
    )


def _themes(
    brief: Mapping[str, object],
    candidate: NarrativeCandidate,
) -> tuple[ThemeNavigationItem, ...]:
    request_view = brief.get("request_view")
    raw_dimensions = (
        request_view.get("dimension_ids") if isinstance(request_view, Mapping) else None
    )
    dimensions = _strings(raw_dimensions)
    if not dimensions:
        dimensions = tuple(dict.fromkeys(block.dimension_id for block in candidate.blocks))
    return tuple(
        ThemeNavigationItem(theme_id=dimension, label=_THEME_LABELS.get(dimension, dimension))
        for dimension in dimensions
    )


def _evidence(brief: Mapping[str, object]) -> tuple[EvidenceCard, ...]:
    result: list[EvidenceCard] = []
    raw_evidence = brief.get("evidence")
    if not isinstance(raw_evidence, (list, tuple)):
        return ()
    for raw in raw_evidence:
        if not isinstance(raw, Mapping):
            continue
        evidence_ref = raw.get("ref")
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            continue
        title = _public_source_title(raw.get("source_title") or raw.get("title"))
        locator = _public_locator(raw.get("locator"))
        if locator is not None:
            title = f"{title} · {locator}"
        result.append(
            EvidenceCard(
                evidence_ref=evidence_ref,
                title=title,
                supports_fact_refs=_strings(raw.get("supports_fact_refs")),
            )
        )
    return tuple(result)


def _boundaries(brief: Mapping[str, object], disclosure: str) -> tuple[Boundary, ...]:
    result: list[Boundary] = []
    raw_limits = brief.get("limits")
    if isinstance(raw_limits, (list, tuple)):
        for raw in raw_limits:
            if not isinstance(raw, Mapping):
                continue
            limit_ref = raw.get("kind_id")
            text = raw.get("public_text")
            if (
                isinstance(limit_ref, str)
                and limit_ref.strip()
                and isinstance(text, str)
                and text.strip()
            ):
                result.append(Boundary(limit_ref=limit_ref, text=text))
    result.append(Boundary(limit_ref="contract:disclosure", text=disclosure))
    return tuple(result)


def _presentation_contract(
    product_id: str,
    output_contract: OutputContract,
    candidate: NarrativeCandidate,
    *,
    product_version: str | None = None,
    presentation_contract_version: str | None = None,
) -> PresentationContract:
    allowed_kinds = tuple(
        dict.fromkeys(
            [
                *(block.claim_kind_id for block in candidate.blocks),
                "kind.fact",
                "kind.tendency",
            ]
        )
    )
    max_chars = max((len(block.text) for block in candidate.blocks), default=1)
    return PresentationContract(
        contract_version=(
            presentation_contract_version.strip()
            if isinstance(presentation_contract_version, str)
            and presentation_contract_version.strip()
            else f"{product_id}-presentation/v1"
        ),
        product_version=(
            product_version.strip()
            if isinstance(product_version, str) and product_version.strip()
            else f"{product_id}-reading/v1"
        ),
        renderer="reading-document/v1",
        sections=(
            PresentationSection(
                section_id="overview",
                title="判断",
                min_claims=output_contract.min_blocks,
                max_claims=output_contract.max_blocks,
                max_chars_per_claim=max(max_chars, output_contract.max_output_chars),
                allowed_claim_kind_ids=allowed_kinds,
            ),
        ),
        fixed_disclosures=(output_contract.disclosure_text,),
    )


class ReadingDocumentBuilder:
    """Project a Guard-approved candidate and Runtime brief into ReadingDocumentV1."""

    def build(self, context: ReadingDocumentContext) -> ReadingDocumentV1 | None:
        prepared_brief = context.prepared.brief
        brief = (
            prepared_brief.to_dict()
            if isinstance(prepared_brief, ReadingBrief)
            else dict(prepared_brief)
        )
        view_model = project_runtime_view_model(
            brief,
            product_id=context.product_id,
            relationship_type=context.relationship_type,
        )
        # A capability without a typed public ViewModel is not silently turned
        # into a fake document. It stays accepted while its document is deferred.
        if view_model is None:
            return None

        contract = _presentation_contract(
            context.product_id,
            context.output_contract,
            context.candidate,
            product_version=context.product_version,
            presentation_contract_version=context.presentation_contract_version,
        )
        claims = tuple(
            ClaimCard(
                claim_id=block.block_id,
                section_id="overview",
                text=block.text,
                subject_ref=block.subject_ref,
                dimension_id=block.dimension_id,
                claim_kind_id=block.claim_kind_id,
                certainty_id=block.certainty_id,
                fact_refs=block.fact_refs,
                finding_refs=block.finding_refs,
                evidence_refs=block.evidence_refs,
                limit_refs=block.limit_kind_ids,
                verification=VerificationEntry(enabled=True),
            )
            for block in context.candidate.blocks
        )
        payload = {
            "schema_version": "reading-document/v1",
            "document_id": f"reading-version:{context.reading_version_id}",
            "reading_version_id": str(context.reading_version_id),
            "accepted_copy_ref": context.accepted_copy_ref,
            "product_version": contract.product_version,
            "presentation_contract_version": contract.contract_version,
            "view_model": view_model.model_dump(mode="json"),
            "answer_summary": context.candidate.blocks[0].text,
            "subject_summaries": _subject_summaries(brief, context.candidate),
            "themes": _themes(brief, context.candidate),
            "claims": claims,
            "evidence": _evidence(brief),
            "boundaries": _boundaries(brief, context.output_contract.disclosure_text),
            "actions": ReadingActions(
                correction=ActionAvailability(enabled=True),
                follow_up=ActionAvailability(enabled=context.follow_up_count > 0),
                export=ActionAvailability(enabled=True),
                share=ActionAvailability(enabled=True),
            ),
            "versions": DocumentVersions(
                runtime_release=context.runtime_release,
                view_model_schema=view_model.schema_version,
            ),
        }
        return validate_reading_document(contract, payload)
