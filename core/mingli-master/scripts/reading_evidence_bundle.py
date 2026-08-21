#!/usr/bin/env python3
"""Compile only applicable, source-bound evidence for one V4 transaction."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import reading_source_plan
import search_bm25
from evidence_independence import source_lineage, source_relationships
from reading_engine.contracts import (
    EvidenceBundle,
    EvidenceGap,
    EvidenceNode,
    FactRef,
)
from reading_engine.evidence_rules import (
    EvidenceRule,
    match_rule,
    production_evidence_rules,
)


SCHEMA_VERSION = "mingli-reading-evidence-bundle-v5"
RETRIEVAL_PROFILE = "applicability-first-semantic-bm25-v1"
ROOT = Path(__file__).resolve().parents[1]
MAX_RULES_PER_PACK = 2
SOURCE_CONDITIONED_METHODOLOGY_FALLBACK_RULE_IDS = frozenset(
    {"bazi/ditiansui-chanwei#DR-01-01"}
)


def _transaction_system(plan: dict[str, Any]) -> str:
    return str(
        plan.get("registry_route")
        or plan.get("subsystem")
        or plan.get("system")
        or ""
    )


def _validate_fact_provider_identity(
    plan: dict[str, Any],
    fact_index: tuple[FactRef, ...],
) -> None:
    identity = plan.get("provider_identity")
    if not isinstance(identity, dict):
        raise ValueError("source plan has no provider identity")
    expected = (
        str(identity.get("provider_id") or ""),
        str(identity.get("provider_version") or ""),
    )
    if not all(expected):
        raise ValueError("source plan provider identity is incomplete")
    observed = {(item.provider_id, item.provider_version) for item in fact_index}
    if observed != {expected}:
        raise ValueError(
            "fact index provider identity does not match the selected route provider"
        )


def _validate_plan(
    goal: dict[str, Any],
    facts: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    if plan.get("schema_version") != reading_source_plan.SCHEMA_VERSION:
        raise ValueError("source plan mismatch: invalid schema")
    expected = reading_source_plan.compile_source_plan(
        _transaction_system(plan),
        goal,
        facts,
    )
    if expected != plan:
        raise ValueError("source plan mismatch: regenerate from goal and facts")


def _compatible_rule_systems(plan: dict[str, Any]) -> set[str]:
    declared = plan.get("compatible_rule_systems")
    if isinstance(declared, list) and declared:
        return {str(item) for item in declared}
    return {str(plan.get("system") or "")}


def _lineage(pack: str) -> str:
    """Keep unaudited packs conservative until the provenance task closes."""

    try:
        return source_lineage(pack)
    except ValueError:
        return f"unregistered:{pack}"


def _semantic_terms(
    goal: dict[str, Any],
    plan: dict[str, Any],
    fact_index: tuple[FactRef, ...],
    *,
    counter: bool,
) -> list[str]:
    key = "counter_evidence_questions" if counter else "evidence_questions"
    questions = list(goal.get(key) or ())
    if counter and not questions:
        questions = list(goal.get("evidence_questions") or ())
    terms = [str(item).strip() for item in questions if str(item).strip()]
    terms.extend(
        str(item).strip()
        for item in (
            *(plan.get("question_dimensions") or ()),
            *(plan.get("requested_dimensions") or ()),
        )
        if str(item).strip()
    )
    terms.extend(item.fact_id for item in fact_index)
    terms.extend(
        str(item.value).strip()
        for item in fact_index
        if (
            "/named_patterns/" in item.path
            or "/board_predicates/" in item.path
        )
        and item.path.rsplit("/", 1)[-1] in {"id", "name"}
        and isinstance(item.value, (str, int, float))
        and str(item.value).strip()
    )
    requested_dimensions = {
        str(item)
        for item in (
            *(plan.get("question_dimensions") or ()),
            *(plan.get("requested_dimensions") or ()),
        )
    }
    for projection in plan.get("semantic_term_projections") or ():
        if not isinstance(projection, dict):
            continue
        if projection.get("requires_questions", True) and not questions:
            continue
        required_dimension = projection.get("requires_dimension")
        if required_dimension and str(required_dimension) not in requested_dimensions:
            continue
        path_contains = str(projection.get("path_contains") or "")
        leaves = {str(item) for item in projection.get("leaves") or ()}
        terms.extend(
            str(item.value).strip()
            for item in fact_index
            if path_contains
            and path_contains in item.path
            and item.path.rsplit("/", 1)[-1] in leaves
            and isinstance(item.value, str)
            and item.value.strip()
        )
    return list(dict.fromkeys(terms))


def _rule_text(rule: EvidenceRule) -> str:
    return " ".join(
        item
        for item in (rule.source_title, rule.chapter, *rule.topics, rule.quote)
        if str(item).strip()
    )


def _source_conditioned_rule_ids(
    fact_index: tuple[FactRef, ...],
) -> set[str]:
    """Return rules explicitly emitted by source-conditioned fact patterns."""

    return {
        item.value.strip()
        for item in fact_index
        if "/source_conditioned_patterns/" in item.path
        and item.path.rsplit("/", 1)[-1] == "rule_id"
        and isinstance(item.value, str)
        and item.value.strip()
    }


def _rank_rules(
    rules: list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]],
    terms: list[str],
    *,
    source_conditioned_rule_ids: set[str] | None = None,
) -> list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]]:
    if not rules or not terms:
        return []
    documents = [
        search_bm25.Document(
            path=ROOT / rule.source_path,
            line_no=index,
            text=_rule_text(rule),
            tokens=search_bm25.tokenize(_rule_text(rule)),
        )
        for index, (rule, _, _) in enumerate(rules, start=1)
    ]
    by_index = {
        document.line_no: candidate
        for document, candidate in zip(documents, rules)
    }
    ranked = search_bm25.bm25(
        search_bm25.tokenize(" ".join(terms)),
        documents,
    )
    candidates = [by_index[document.line_no] for _, document in ranked]

    def specificity(
        candidate: tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]],
    ) -> int:
        rule = candidate[0]
        return 0 if any(
            str(predicate.path_suffix or "").endswith(
                ("/named_patterns", "/board_predicates")
            )
            for predicate in rule.required_fact_predicates
        ) else 1

    ranked_candidates = sorted(candidates, key=specificity)
    ranked_rule_ids = {candidate[0].rule_id for candidate in ranked_candidates}
    explicit_ids = source_conditioned_rule_ids or set()
    fallback_methodology = [
        candidate
        for candidate in rules
        if candidate[0].rule_id in explicit_ids
        and candidate[0].rule_id in SOURCE_CONDITIONED_METHODOLOGY_FALLBACK_RULE_IDS
        and candidate[0].rule_id not in ranked_rule_ids
        and candidate[0].evidence_role == "methodology_rule"
        and candidate[0].runtime_active
        and candidate[0].classical_binding_status == "verified"
        and bool(candidate[0].classical_sources)
        and bool(candidate[1])
    ]
    # Applicability predicates matched before ranking.  An explicitly admitted,
    # calculation-emitted methodology rule is therefore direct evidence even
    # when its wording has no lexical overlap with the user's question.
    return fallback_methodology + ranked_candidates


def _eligible_rules(
    plan: dict[str, Any],
    fact_index: tuple[FactRef, ...],
    *,
    rules: tuple[EvidenceRule, ...] | None = None,
) -> dict[str, list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]]]:
    if plan.get("scope_compatible") is False:
        return {}
    selected_packs = {
        str(source["pack"])
        for source in plan.get("sources") or ()
        if isinstance(source, dict) and source.get("pack")
    }
    compatible = _compatible_rule_systems(plan)
    chapter_filters = plan.get("pack_chapter_filters")
    if not isinstance(chapter_filters, dict):
        chapter_filters = {}
    allowed_roles_raw = plan.get("allowed_evidence_roles")
    allowed_roles = (
        {str(item) for item in allowed_roles_raw}
        if isinstance(allowed_roles_raw, list)
        else None
    )
    grouped: dict[
        str,
        list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]],
    ] = {}
    active_rules = production_evidence_rules() if rules is None else rules
    for rule in active_rules:
        if rule.source_pack not in selected_packs or rule.system not in compatible:
            continue
        chapter_filter = chapter_filters.get(rule.source_pack)
        if isinstance(chapter_filter, dict):
            applicable_chapter = chapter_filter.get("applicable_chapter")
            exempt_roles = {
                str(item) for item in chapter_filter.get("exempt_roles") or ()
            }
            if (
                applicable_chapter
                and rule.evidence_role not in exempt_roles
                and rule.chapter != applicable_chapter
            ):
                continue
        if allowed_roles is not None and rule.evidence_role not in allowed_roles:
            continue
        eligible, fact_refs, audit = match_rule(rule, fact_index)
        if not eligible:
            continue
        if not rule.required_fact_predicates:
            continue
        grouped.setdefault(rule.source_pack, []).append((rule, fact_refs, audit))
    return grouped


def _select_ranked(
    eligible: dict[
        str,
        list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]],
    ],
    packs: tuple[str, ...],
    terms: list[str],
    *,
    source_conditioned_rule_ids: set[str],
) -> list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]]:
    selected: list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]] = []
    for pack in packs:
        selected.extend(
            _rank_rules(
                eligible.get(pack, []),
                terms,
                source_conditioned_rule_ids=source_conditioned_rule_ids,
            )[:MAX_RULES_PER_PACK]
        )
    return selected


def _related_rules(
    selected: list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]],
    eligible: dict[
        str,
        list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]],
    ],
    *,
    relation: str,
) -> list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]]:
    available = {
        candidate[0].rule_id: candidate
        for candidates in eligible.values()
        for candidate in candidates
    }
    found: list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]] = []
    for rule, _, _ in selected:
        if relation == "counter":
            ids = (*rule.exception_rule_ids, *rule.conflict_rule_ids)
        else:
            ids = rule.depends_on_rule_ids
        for rule_id in ids:
            candidate = available.get(rule_id)
            if candidate is not None and candidate not in found:
                found.append(candidate)
    return found


def _unique_candidates(
    candidates: list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]],
) -> list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]]:
    """Preserve first-ranked evidence candidates by their stable rule identity."""

    by_rule_id: dict[
        str, tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]
    ] = {}
    unique: list[tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]]] = []
    for candidate in candidates:
        rule_id = candidate[0].rule_id
        first = by_rule_id.get(rule_id)
        if first is None:
            by_rule_id[rule_id] = candidate
            unique.append(candidate)
            continue
        if candidate != first:
            raise ValueError(f"conflicting evidence candidate for rule id: {rule_id}")
    return unique


def _node(
    candidate: tuple[EvidenceRule, tuple[str, ...], tuple[str, ...]],
    *,
    titles: dict[str, str],
    reading_id: str,
    version: int,
) -> EvidenceNode:
    rule, fact_refs, predicate_audit = candidate
    assertion = f"{rule.chapter}：{rule.quote}" if rule.chapter else rule.quote
    # The rule assertion is a distilled, applicability-facing statement.  It
    # is deliberately not the public quotation.  Carry the independently
    # bound classical source passages forward as typed exact citations so the
    # later public seam can fail closed without guessing from ``quote`` or
    # ``assertion``.
    exact_citations = (
        tuple(
            {
                "verification_status": "verified_exact",
                "verbatim_excerpt": source.verbatim_quote,
                "source_title": rule.source_title,
                "locator": source.anchor,
                "rule_id": rule.rule_id,
            }
            for source in rule.classical_sources
        )
        if rule.runtime_active and rule.classical_binding_status == "verified"
        else ()
    )
    return EvidenceNode(
        rule_id=rule.rule_id,
        source=titles[rule.source_pack],
        anchor=rule.source_anchor,
        applicability=";".join(predicate_audit),
        assertion=assertion,
        lineage=_lineage(rule.source_pack),
        quote_hash=hashlib.sha256(assertion.encode("utf-8")).hexdigest(),
        fact_refs=fact_refs,
        source_path=rule.source_path,
        source_sha256=rule.source_sha256,
        reading_id=reading_id,
        version=version,
        exact_citations=exact_citations,
    )


def compile_evidence_bundle(
    goal: dict[str, Any],
    facts: dict[str, Any],
    plan: dict[str, Any],
    *,
    fact_index: tuple[FactRef, ...],
    reading_id: str,
    version: int,
) -> EvidenceBundle:
    """Filter by source identity and fact predicates before semantic ranking."""

    if not isinstance(goal, dict) or not isinstance(facts, dict):
        raise TypeError("goal and facts must be objects")
    _validate_plan(goal, facts, plan)
    fact_ids = {item.fact_id for item in fact_index}
    if any(item.reading_id != reading_id for item in fact_index):
        raise ValueError("fact index belongs to another reading")
    if any(item.version != version for item in fact_index):
        raise ValueError("fact index belongs to another reading version")
    _validate_fact_provider_identity(plan, fact_index)
    if fact_ids != set(plan.get("fact_ids") or ()):
        raise ValueError("source plan fact index does not match current calculation")

    sources = tuple(
        source
        for source in plan.get("sources") or ()
        if isinstance(source, dict)
    )
    titles = {str(source["pack"]): str(source["title"]) for source in sources}
    support_packs = tuple(
        str(source["pack"])
        for source in sources
        if source.get("role") != "counter"
    )
    counter_packs = tuple(
        str(source["pack"])
        for source in sources
        if source.get("role") == "counter"
    )
    eligible = _eligible_rules(plan, fact_index)
    source_conditioned_rule_ids = _source_conditioned_rule_ids(fact_index)
    support = _select_ranked(
        eligible,
        support_packs,
        _semantic_terms(goal, plan, fact_index, counter=False),
        source_conditioned_rule_ids=source_conditioned_rule_ids,
    )
    support.extend(_related_rules(support, eligible, relation="dependency"))
    counters = _select_ranked(
        eligible,
        counter_packs,
        _semantic_terms(goal, plan, fact_index, counter=True),
        source_conditioned_rule_ids=set(),
    )
    counters.extend(_related_rules(support, eligible, relation="counter"))
    support = _unique_candidates(support)
    support_rule_ids = {candidate[0].rule_id for candidate in support}
    counters = [
        candidate
        for candidate in _unique_candidates(counters)
        if candidate[0].rule_id not in support_rule_ids
    ]

    evidence = tuple(
        _node(item, titles=titles, reading_id=reading_id, version=version)
        for item in support
    )
    counter_evidence = tuple(
        _node(item, titles=titles, reading_id=reading_id, version=version)
        for item in counters
    )
    questions = tuple(str(item) for item in goal.get("evidence_questions") or ())
    counter_questions = tuple(
        str(item) for item in goal.get("counter_evidence_questions") or ()
    ) or questions
    gaps: list[EvidenceGap] = []
    if not evidence:
        gaps.append(
            EvidenceGap(
                reason="zero_applicable_evidence",
                questions=questions,
                source_packs=support_packs,
            )
        )
    if not counter_evidence:
        gaps.append(
            EvidenceGap(
                reason="no_applicable_counter_evidence",
                questions=counter_questions,
                source_packs=counter_packs or support_packs,
            )
        )
    return EvidenceBundle.create(
        system=_transaction_system(plan),
        evidence=evidence,
        counter_evidence=counter_evidence,
        source_relationships=source_relationships(evidence, counter_evidence),
        source_gaps=tuple(gaps),
    )


def validate_evidence_bundle(
    goal: dict[str, Any],
    facts: dict[str, Any],
    plan: dict[str, Any],
    bundle: EvidenceBundle | None,
    *,
    fact_index: tuple[FactRef, ...],
    reading_id: str,
    version: int,
) -> bool:
    if not isinstance(bundle, EvidenceBundle):
        return False
    try:
        expected = compile_evidence_bundle(
            goal,
            facts,
            plan,
            fact_index=fact_index,
            reading_id=reading_id,
            version=version,
        )
    except (OSError, KeyError, TypeError, ValueError):
        return False
    return bundle == expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal-file", required=True)
    parser.add_argument("--facts-file", required=True)
    parser.add_argument("--source-plan-file", required=True)
    parser.add_argument("--fact-index-file", required=True)
    parser.add_argument("--reading-id", required=True)
    parser.add_argument("--version", required=True, type=int)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        goal = json.loads(Path(args.goal_file).read_text(encoding="utf-8"))
        facts = json.loads(Path(args.facts_file).read_text(encoding="utf-8"))
        plan = json.loads(Path(args.source_plan_file).read_text(encoding="utf-8"))
        raw_index = json.loads(Path(args.fact_index_file).read_text(encoding="utf-8"))
        fact_index = tuple(FactRef(**item) for item in raw_index)
        bundle = compile_evidence_bundle(
            goal,
            facts,
            plan,
            fact_index=fact_index,
            reading_id=args.reading_id,
            version=args.version,
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rendered = json.dumps(
        bundle.to_dict(), ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
