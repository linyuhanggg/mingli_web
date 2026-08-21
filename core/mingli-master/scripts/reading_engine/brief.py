"""Compile the closed-world ReadingBrief from one provider preparation.

The brief is the entire drafting surface: bounded public facts, applicable
evidence, claim scopes, limits and a minimal vocabulary projection for every
opaque identifier it references. It only consumes the public projection a
provider adapter published — never the private calculation, never a fact
index, never any generic domain constant.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .interface_contracts import (
    ClaimScope,
    PublicEvidence,
    PublicFact,
    PublicFinding,
    PublicLimit,
    PublicTerm,
    ReadingBrief,
    RequestView,
)


def _verified_public_evidence(item: Mapping[str, Any]) -> PublicEvidence | None:
    """Decode only a complete exact citation at the public boundary.

    Provider adapters normally perform this projection themselves.  Keeping
    the same gate here protects the transport seam from a hand-built or stale
    preparation that tries to publish a rule assertion as an original quote.
    """

    verification_status = item.get("verification_status")
    verbatim_excerpt = item.get("verbatim_excerpt")
    source_title = item.get("source_title")
    locator = item.get("locator")
    rule_id = item.get("rule_id")
    raw_ref = item.get("ref")
    raw_evidence_ref = item.get("evidence_ref")
    if (
        raw_ref is not None
        and raw_evidence_ref is not None
        and raw_ref != raw_evidence_ref
    ):
        return None
    evidence_ref = raw_evidence_ref or raw_ref
    if (
        verification_status != "verified_exact"
        or not isinstance(rule_id, str)
        or not rule_id.strip()
        or not isinstance(evidence_ref, str)
        or not evidence_ref.strip()
    ):
        return None
    raw_citations = item.get("verbatim_citations")
    citations: list[dict[str, str]] = []
    if raw_citations is not None:
        if not isinstance(raw_citations, (list, tuple)) or not raw_citations:
            return None
        for raw_citation in raw_citations:
            if not isinstance(raw_citation, Mapping):
                return None
            citation_title = raw_citation.get("source_title")
            citation_locator = raw_citation.get("locator")
            citation_excerpt = raw_citation.get("verbatim_excerpt")
            citation_status = raw_citation.get(
                "verification_status", verification_status
            )
            if (
                citation_status != "verified_exact"
                or not isinstance(citation_title, str)
                or not citation_title.strip()
                or not isinstance(citation_locator, str)
                or not citation_locator.strip()
                or not isinstance(citation_excerpt, str)
                or not citation_excerpt.strip()
            ):
                return None
            citations.append(
                {
                    "source_title": citation_title,
                    "locator": citation_locator,
                    "verbatim_excerpt": citation_excerpt,
                    "verification_status": "verified_exact",
                }
            )
        first = citations[0]
        # The singular fields are a compatibility view of the first exact
        # citation.  If a caller supplies conflicting summaries, reject the
        # whole item instead of guessing which text to expose.
        if any(
            value is not None
            and value != expected
            for value, expected in (
                (source_title, first["source_title"]),
                (locator, first["locator"]),
                (verbatim_excerpt, first["verbatim_excerpt"]),
            )
        ):
            return None
        source_title = first["source_title"]
        locator = first["locator"]
        verbatim_excerpt = first["verbatim_excerpt"]
    else:
        if (
            not isinstance(verbatim_excerpt, str)
            or not verbatim_excerpt.strip()
            or not isinstance(source_title, str)
            or not source_title.strip()
            or not isinstance(locator, str)
            or not locator.strip()
        ):
            return None
        citations = [
            {
                "source_title": source_title,
                "locator": locator,
                "verbatim_excerpt": verbatim_excerpt,
                "verification_status": "verified_exact",
            }
        ]
    supports = item.get("supports_fact_refs") or ()
    if not isinstance(supports, (list, tuple)) or not all(
        isinstance(ref, str) for ref in supports
    ):
        return None
    return PublicEvidence(
        ref=evidence_ref,
        source_title=source_title,
        locator=locator,
        # Keep the legacy field, but only with the verified original.  A
        # caller-provided summary is never allowed to become ``excerpt``.
        excerpt=verbatim_excerpt,
        supports_fact_refs=tuple(supports),
        verification_status=verification_status,
        verbatim_excerpt=verbatim_excerpt,
        rule_id=rule_id,
        verbatim_citations=tuple(citations),
    )


def compile_brief(
    preparation: Any,
    *,
    question: str,
    term_resolver: Callable[[str], PublicTerm],
    prior_answer: str | None = None,
) -> ReadingBrief:
    """Build the self-contained brief from one provider public projection."""

    facts = tuple(
        PublicFact(
            ref=str(fact["ref"]),
            subject_ref=str(fact["subject_ref"]),
            kind_id=str(fact["kind_id"]),
            value=fact.get("value"),
            display_text=str(fact["display_text"]),
        )
        for fact in preparation.public_facts
        if isinstance(fact, Mapping)
    )
    plan = preparation.evidence_plan or {}
    evidence = tuple(
        item
        for raw_item in plan.get("evidence") or ()
        if isinstance(raw_item, Mapping)
        for item in (_verified_public_evidence(raw_item),)
        if item is not None
    )
    claim_scopes = tuple(
        ClaimScope(
            subject_ref=str(scope["subject_ref"]),
            dimension_id=str(scope["dimension_id"]),
            allowed_kind_ids=tuple(
                str(item) for item in scope["allowed_kind_ids"]
            ),
            certainty_ceiling_id=str(scope["certainty_ceiling_id"]),
            fact_refs=tuple(str(item) for item in scope.get("fact_refs") or ()),
            evidence_refs=tuple(
                str(item) for item in scope.get("evidence_refs") or ()
            ),
        )
        for scope in preparation.claim_scopes
        if isinstance(scope, Mapping)
    )
    limits_list: list[PublicLimit] = []
    for limit in preparation.limits:
        if not isinstance(limit, Mapping):
            continue
        kind_id = str(limit["kind_id"])
        public_text = limit.get("public_text")
        if not isinstance(public_text, str) or not public_text.strip():
            public_text = term_resolver(kind_id).label
        limits_list.append(
            PublicLimit(
                kind_id=kind_id,
                public_text=str(public_text),
                scope_refs=tuple(
                    str(item) for item in limit.get("scope_refs") or ()
                ),
                detail_ids=tuple(
                    str(item) for item in limit.get("detail_ids") or ()
                ),
            )
        )
    limits = tuple(limits_list)
    findings = tuple(
        PublicFinding(
            ref=str(finding["ref"]),
            subject_ref=str(finding["subject_ref"]),
            dimension_ids=tuple(
                str(item) for item in finding.get("dimension_ids") or ()
            ),
            kind_id=str(finding["kind_id"]),
            data=finding.get("data"),
            fact_refs=tuple(
                str(item) for item in finding.get("fact_refs") or ()
            ),
            evidence_refs=tuple(
                str(item) for item in finding.get("evidence_refs") or ()
            ),
            limit_kind_ids=tuple(
                str(item) for item in finding.get("limit_kind_ids") or ()
            ),
            support_mode=str(finding.get("support_mode") or "shared_turn"),
            public_text=(
                str(finding["public_text"])
                if isinstance(finding.get("public_text"), str)
                and str(finding["public_text"]).strip()
                else None
            ),
        )
        for finding in preparation.findings
        if isinstance(finding, Mapping)
    )
    request_payload = getattr(preparation, "request_view", None)
    request_view = (
        RequestView.from_dict(request_payload)
        if isinstance(request_payload, Mapping) and request_payload
        else None
    )

    vocabulary: dict[str, PublicTerm] = {}
    for scope in claim_scopes:
        vocabulary.setdefault(
            scope.dimension_id, term_resolver(scope.dimension_id)
        )
        for kind_id in scope.allowed_kind_ids:
            vocabulary.setdefault(kind_id, term_resolver(kind_id))
        vocabulary.setdefault(
            scope.certainty_ceiling_id,
            term_resolver(scope.certainty_ceiling_id),
        )
    for fact in facts:
        vocabulary.setdefault(fact.kind_id, term_resolver(fact.kind_id))
    for limit in limits:
        vocabulary.setdefault(limit.kind_id, term_resolver(limit.kind_id))
    fact_refs = {fact.ref for fact in facts}
    evidence_refs = {item.ref for item in evidence}
    limit_kind_ids = {limit.kind_id for limit in limits}
    for finding in findings:
        if not set(finding.fact_refs) <= fact_refs:
            raise ValueError("public finding references an unavailable fact")
        if not set(finding.evidence_refs) <= evidence_refs:
            raise ValueError("public finding references unavailable evidence")
        if not set(finding.limit_kind_ids) <= limit_kind_ids:
            raise ValueError("public finding references an unavailable limit")
        vocabulary.setdefault(finding.kind_id, term_resolver(finding.kind_id))

    return ReadingBrief(
        question=question,
        vocabulary=tuple(vocabulary.values()),
        facts=facts,
        evidence=evidence,
        claim_scopes=claim_scopes,
        limits=limits,
        prior_answer=prior_answer,
        request_view=request_view,
        findings=findings,
    )


__all__ = ["compile_brief"]
