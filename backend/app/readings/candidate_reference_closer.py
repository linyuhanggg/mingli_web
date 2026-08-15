"""Deterministically close NarrativeCandidate reference sets before Guard.

Real models often cite findings/evidence without also listing the finding's
required fact_refs (or an evidence's supports_fact_refs). That is a reference
hygiene problem, not a content judgment. Closing those dependencies keeps the
Guard's closed-world checks honest without inventing new prose or new claims.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from app.readings.narrative_contracts import (
    NarrativeBlock,
    NarrativeCandidate,
    merge_claim_scopes,
)
from app.readings.runtime_contracts import ReadingBrief


def close_candidate_references(
    candidate: NarrativeCandidate,
    brief: ReadingBrief | Mapping[str, object],
) -> NarrativeCandidate:
    payload = brief.to_dict() if isinstance(brief, ReadingBrief) else dict(brief)
    facts = {
        str(item["ref"]): cast(Mapping[str, object], item)
        for item in cast(list[object], payload.get("facts") or [])
        if isinstance(item, Mapping) and item.get("ref")
    }
    evidence = {
        str(item["ref"]): cast(Mapping[str, object], item)
        for item in cast(list[object], payload.get("evidence") or [])
        if isinstance(item, Mapping) and item.get("ref")
    }
    findings = {
        str(item["ref"]): cast(Mapping[str, object], item)
        for item in cast(list[object], payload.get("findings") or [])
        if isinstance(item, Mapping) and item.get("ref")
    }
    limits = {
        str(item["kind_id"]): cast(Mapping[str, object], item)
        for item in cast(list[object], payload.get("limits") or [])
        if isinstance(item, Mapping) and item.get("kind_id")
    }
    scopes = merge_claim_scopes(payload)

    closed_blocks: list[NarrativeBlock] = []
    for block in candidate.blocks:
        closed_blocks.append(
            _close_block(
                block,
                facts=facts,
                evidence=evidence,
                findings=findings,
                limits=limits,
                scopes=scopes,
            )
        )
    return NarrativeCandidate(blocks=tuple(closed_blocks))


def _as_str_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if item is not None and str(item))


def _unique(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _limit_applies(
    limit: Mapping[str, object],
    *,
    subject_ref: str,
    dimension_id: str,
) -> bool:
    scope_refs = _as_str_tuple(limit.get("scope_refs"))
    return not scope_refs or subject_ref in scope_refs or dimension_id in scope_refs


def _close_block(
    block: NarrativeBlock,
    *,
    facts: Mapping[str, Mapping[str, object]],
    evidence: Mapping[str, Mapping[str, object]],
    findings: Mapping[str, Mapping[str, object]],
    limits: Mapping[str, Mapping[str, object]],
    scopes: Mapping[tuple[str, str], Mapping[str, object]],
) -> NarrativeBlock:
    scope = scopes.get((block.subject_ref, block.dimension_id))
    allowed_facts = set(_as_str_tuple(scope.get("fact_refs"))) if scope else set(facts)
    allowed_evidence = (
        set(_as_str_tuple(scope.get("evidence_refs"))) if scope else set(evidence)
    )

    fact_refs = [ref for ref in block.fact_refs if ref in facts and ref in allowed_facts]
    finding_refs = [
        ref
        for ref in block.finding_refs
        if ref in findings
        and str(findings[ref].get("subject_ref")) == block.subject_ref
        and block.dimension_id in _as_str_tuple(findings[ref].get("dimension_ids"))
    ]
    evidence_refs = [
        ref
        for ref in block.evidence_refs
        if ref in evidence and ref in allowed_evidence
    ]
    limit_kind_ids = [
        ref
        for ref in block.limit_kind_ids
        if ref in limits
        and _limit_applies(
            limits[ref],
            subject_ref=block.subject_ref,
            dimension_id=block.dimension_id,
        )
    ]

    # Pull closed-world dependencies required by cited findings.
    for finding_ref in list(finding_refs):
        finding = findings[finding_ref]
        for fact_ref in _as_str_tuple(finding.get("fact_refs")):
            if fact_ref in facts and fact_ref in allowed_facts:
                fact_refs.append(fact_ref)
        for evidence_ref in _as_str_tuple(finding.get("evidence_refs")):
            if evidence_ref in evidence and evidence_ref in allowed_evidence:
                evidence_refs.append(evidence_ref)
        for limit_id in _as_str_tuple(finding.get("limit_kind_ids")):
            if limit_id in limits and _limit_applies(
                limits[limit_id],
                subject_ref=block.subject_ref,
                dimension_id=block.dimension_id,
            ):
                limit_kind_ids.append(limit_id)

    # Ensure each cited evidence intersects the block's fact set.
    for evidence_ref in list(evidence_refs):
        item = evidence[evidence_ref]
        supports = [
            ref
            for ref in _as_str_tuple(item.get("supports_fact_refs"))
            if ref in facts and ref in allowed_facts
        ]
        if not supports:
            # Evidence cannot be grounded in this brief/scope; drop it.
            evidence_refs = [ref for ref in evidence_refs if ref != evidence_ref]
            continue
        if set(supports).isdisjoint(fact_refs):
            fact_refs.append(supports[0])

    # Drop findings that still cannot close after dependency pull.
    kept_findings: list[str] = []
    fact_set = set(fact_refs)
    evidence_set = set(evidence_refs)
    limit_set = set(limit_kind_ids)
    for finding_ref in finding_refs:
        finding = findings[finding_ref]
        if not set(_as_str_tuple(finding.get("fact_refs"))).issubset(fact_set):
            continue
        if not set(_as_str_tuple(finding.get("evidence_refs"))).issubset(evidence_set):
            continue
        if not set(_as_str_tuple(finding.get("limit_kind_ids"))).issubset(limit_set):
            continue
        kept_findings.append(finding_ref)

    return NarrativeBlock(
        block_id=block.block_id,
        block_type=block.block_type,
        text=block.text,
        subject_ref=block.subject_ref,
        dimension_id=block.dimension_id,
        claim_kind_id=block.claim_kind_id,
        certainty_id=block.certainty_id,
        fact_refs=_unique(fact_refs),
        finding_refs=_unique(kept_findings),
        evidence_refs=_unique(evidence_refs),
        limit_kind_ids=_unique(limit_kind_ids),
    )
