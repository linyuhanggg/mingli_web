"""Typed, source-bound rules for applicability-first evidence retrieval."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .contracts import FactRef


INDEX_PATH = (
    Path(__file__).resolve().parents[2]
    / "references"
    / "index"
    / "evidence-rules.jsonl"
)
SCHEMA_VERSION = "mingli-evidence-rule-v1"
CLASSICAL_EVIDENCE_BINDINGS_SHA256 = (
    "73c5a8a5d2041e7d49f838c70d0ca184fee060fd355a8f29b0fd6f9a0a7abc8d"
)
EVIDENCE_ROLES = frozenset(
    {
        "casting_rule",
        "imagery_correspondence",
        "issue_specific_judgment_rule",
        "methodology_rule",
        "terminology_only",
        "edition_boundary",
        "timing_rule",
        "verdict_prohibited",
    }
)
_PRODUCTION_SYSTEM: ContextVar[str | None] = ContextVar(
    "mingli_production_evidence_system",
    default=None,
)


@dataclass(frozen=True)
class FactPredicate:
    path_suffix: str
    operator: str
    value: Any = None
    values: tuple[Any, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = {"path_suffix": self.path_suffix, "operator": self.operator}
        if self.value is not None:
            payload["value"] = self.value
        if self.values:
            payload["values"] = list(self.values)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FactPredicate":
        return cls(
            path_suffix=str(payload["path_suffix"]),
            operator=str(payload["operator"]),
            value=payload.get("value"),
            values=tuple(payload.get("values") or ()),
        )


@dataclass(frozen=True)
class ClassicalSource:
    path: str
    sha256: str
    anchor: str
    verbatim_quote: str
    verbatim_quote_sha256: str
    location: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "anchor": self.anchor,
            "verbatim_quote": self.verbatim_quote,
            "verbatim_quote_sha256": self.verbatim_quote_sha256,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ClassicalSource":
        return cls(
            path=str(payload["path"]),
            sha256=str(payload["sha256"]),
            anchor=str(payload["anchor"]),
            verbatim_quote=str(payload["verbatim_quote"]),
            verbatim_quote_sha256=str(payload["verbatim_quote_sha256"]),
            location=str(payload["location"]),
        )


@dataclass(frozen=True)
class EvidenceRule:
    rule_id: str
    local_rule_id: str
    system: str
    source_pack: str
    source_title: str
    source_layer: str
    chapter: str
    title: str
    quote: str
    source_anchor: str
    topics: tuple[str, ...]
    required_fact_predicates: tuple[FactPredicate, ...]
    excluded_fact_predicates: tuple[FactPredicate, ...]
    exception_rule_ids: tuple[str, ...]
    conflict_rule_ids: tuple[str, ...]
    depends_on_rule_ids: tuple[str, ...]
    record_kind: str
    source_path: str
    source_sha256: str
    quote_hash: str
    evidence_role: str = "issue_specific_judgment_rule"
    runtime_active: bool = True
    classical_binding_status: str = "synthetic_test_only"
    applicability_signature: str = ""
    rule_record_digest: str = ""
    classical_binding_digest: str = ""
    classical_sources: tuple[ClassicalSource, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "local_rule_id": self.local_rule_id,
            "system": self.system,
            "source_pack": self.source_pack,
            "source_title": self.source_title,
            "source_layer": self.source_layer,
            "chapter": self.chapter,
            "title": self.title,
            "quote": self.quote,
            "source_anchor": self.source_anchor,
            "topics": list(self.topics),
            "required_fact_predicates": [
                item.to_dict() for item in self.required_fact_predicates
            ],
            "excluded_fact_predicates": [
                item.to_dict() for item in self.excluded_fact_predicates
            ],
            "exception_rule_ids": list(self.exception_rule_ids),
            "conflict_rule_ids": list(self.conflict_rule_ids),
            "depends_on_rule_ids": list(self.depends_on_rule_ids),
            "record_kind": self.record_kind,
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "quote_hash": self.quote_hash,
            "evidence_role": self.evidence_role,
            "runtime_active": self.runtime_active,
            "classical_binding_status": self.classical_binding_status,
            "applicability_signature": self.applicability_signature,
            "rule_record_digest": self.rule_record_digest,
            "classical_binding_digest": self.classical_binding_digest,
            "classical_sources": [item.to_dict() for item in self.classical_sources],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceRule":
        return cls(
            rule_id=str(payload["rule_id"]),
            local_rule_id=str(payload.get("local_rule_id") or payload["rule_id"]),
            system=str(payload["system"]),
            source_pack=str(payload["source_pack"]),
            source_title=str(payload.get("source_title") or payload["source_pack"]),
            source_layer=str(payload["source_layer"]),
            chapter=str(payload["chapter"]),
            title=str(payload.get("title") or payload["rule_id"]),
            quote=str(payload["quote"]),
            source_anchor=str(payload["source_anchor"]),
            topics=tuple(payload.get("topics") or ()),
            required_fact_predicates=tuple(
                FactPredicate.from_dict(item)
                for item in payload.get("required_fact_predicates") or ()
            ),
            excluded_fact_predicates=tuple(
                FactPredicate.from_dict(item)
                for item in payload.get("excluded_fact_predicates") or ()
            ),
            exception_rule_ids=tuple(payload.get("exception_rule_ids") or ()),
            conflict_rule_ids=tuple(payload.get("conflict_rule_ids") or ()),
            depends_on_rule_ids=tuple(payload.get("depends_on_rule_ids") or ()),
            record_kind=str(payload["record_kind"]),
            source_path=str(payload["source_path"]),
            source_sha256=str(payload["source_sha256"]),
            quote_hash=str(payload["quote_hash"]),
            evidence_role=str(
                payload.get("evidence_role") or "issue_specific_judgment_rule"
            ),
            runtime_active=payload.get("runtime_active") is True,
            classical_binding_status=str(payload.get("classical_binding_status") or ""),
            applicability_signature=str(payload.get("applicability_signature") or ""),
            rule_record_digest=str(payload.get("rule_record_digest") or ""),
            classical_binding_digest=str(payload.get("classical_binding_digest") or ""),
            classical_sources=tuple(
                ClassicalSource.from_dict(item)
                for item in payload.get("classical_sources") or ()
            ),
        )

    def search_text(self) -> str:
        return " ".join((self.title, self.chapter, self.quote, *self.topics))


def _validated_source(
    rule: EvidenceRule,
    *,
    root: Path,
    cache: dict[str, tuple[Path, str]],
) -> Path:
    """Resolve and hash one immutable release source once per index load."""

    cached = cache.get(rule.source_path)
    if cached is None:
        source = (root / rule.source_path).resolve(strict=True)
        if not source.is_relative_to(root):
            raise ValueError("evidence rule source escapes the skill root")
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        cache[rule.source_path] = (source, actual)
    else:
        source, actual = cached
    if actual != rule.source_sha256:
        raise ValueError(f"evidence rule source hash mismatch: {rule.rule_id}")
    return source


def _validate_rule(
    rule: EvidenceRule,
    *,
    root: Path,
    source_cache: dict[str, tuple[Path, str]],
) -> None:
    if rule.record_kind != "substantive_rule":
        raise ValueError(f"non-substantive evidence record: {rule.rule_id}")
    if not rule.rule_id or not rule.source_pack or not rule.quote.strip():
        raise ValueError("evidence rule has an empty identity or quote")
    if rule.evidence_role not in EVIDENCE_ROLES:
        raise ValueError(f"invalid evidence role: {rule.rule_id}")
    source = _validated_source(rule, root=root, cache=source_cache)
    expected_quote_hash = hashlib.sha256(rule.quote.encode("utf-8")).hexdigest()
    if rule.quote_hash != expected_quote_hash:
        raise ValueError(f"evidence rule quote hash mismatch: {rule.rule_id}")
    # The compiler owns the canonical parsing rules.  Reusing its source-bound
    # validator here prevents a checked JSONL row from rewriting a quote or
    # anchor while retaining the unchanged source-file hash.
    from build_evidence_index import (
        CLASSICAL_EVIDENCE_BINDINGS_SHA256 as BUILD_BINDINGS_SHA256,
        canonical_predicate_signature,
        canonical_rule_record_digest,
        load_classical_evidence_bindings,
        validate_source_bound_record,
    )

    validate_source_bound_record(rule.to_dict(), source_path=source)
    if BUILD_BINDINGS_SHA256 != CLASSICAL_EVIDENCE_BINDINGS_SHA256:
        raise ValueError("build/runtime classical evidence manifest pins differ")
    signature = canonical_predicate_signature(
        [item.to_dict() for item in rule.required_fact_predicates],
        [item.to_dict() for item in rule.excluded_fact_predicates],
    )
    if rule.applicability_signature != signature:
        raise ValueError(f"runtime evidence predicate signature mismatch: {rule.rule_id}")
    if rule.rule_record_digest != canonical_rule_record_digest(rule.to_dict()):
        raise ValueError(f"runtime evidence rule record digest mismatch: {rule.rule_id}")
    manifest = load_classical_evidence_bindings(
        root=root,
        expected_sha256=CLASSICAL_EVIDENCE_BINDINGS_SHA256,
    )
    binding = manifest["bindings"].get(rule.rule_id)
    if rule.required_fact_predicates or rule.excluded_fact_predicates:
        if binding is None:
            raise ValueError(f"runtime evidence rule lacks classical binding: {rule.rule_id}")
        expected_active = binding["verification_status"] == "verified"
        if (
            rule.runtime_active is not expected_active
            or rule.classical_binding_status != binding["verification_status"]
            or rule.classical_binding_digest != binding["binding_digest"]
            or [item.to_dict() for item in rule.classical_sources]
            != binding["classical_sources"]
            or rule.applicability_signature != binding["applicability_signature"]
            or rule.rule_record_digest != binding["rule_record_digest"]
        ):
            raise ValueError(f"runtime evidence/classical binding mismatch: {rule.rule_id}")
    elif (
        rule.runtime_active
        or rule.classical_binding_status != "inactive_unscoped"
        or rule.classical_sources
    ):
        raise ValueError(f"unscoped evidence rule became runtime active: {rule.rule_id}")


def load_evidence_rules(
    path: str | Path = INDEX_PATH,
    *,
    root: str | Path | None = None,
    system: str | None = None,
) -> tuple[EvidenceRule, ...]:
    source = Path(path).resolve(strict=True)
    skill_root = Path(root).resolve() if root is not None else source.parents[2]
    rules: list[EvidenceRule] = []
    seen: set[str] = set()
    source_cache: dict[str, tuple[Path, str]] = {}
    for line_number, line in enumerate(
        source.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"evidence index line {line_number} is not an object")
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported evidence rule schema on line {line_number}"
            )
        if system is not None and payload.get("system") != system:
            continue
        rule = EvidenceRule.from_dict(payload)
        _validate_rule(rule, root=skill_root, source_cache=source_cache)
        if rule.rule_id in seen:
            raise ValueError(f"duplicate evidence rule id: {rule.rule_id}")
        seen.add(rule.rule_id)
        rules.append(rule)
    if not rules:
        raise ValueError("evidence rule index is empty")
    return tuple(rules)


@contextmanager
def production_evidence_scope(system: str):
    """Limit one provider turn to its source-bound evidence partition."""

    if not isinstance(system, str) or not system:
        raise ValueError("production evidence system must be non-empty")
    token = _PRODUCTION_SYSTEM.set(system)
    try:
        yield
    finally:
        _PRODUCTION_SYSTEM.reset(token)


@lru_cache(maxsize=None)
def _production_evidence_rules(system: str | None) -> tuple[EvidenceRule, ...]:
    return load_evidence_rules(INDEX_PATH, system=system)


def production_evidence_rules() -> tuple[EvidenceRule, ...]:
    return _production_evidence_rules(_PRODUCTION_SYSTEM.get())


def _predicate_fact_refs(
    predicate: FactPredicate,
    facts: tuple[FactRef, ...],
) -> tuple[FactRef, ...]:
    if predicate.operator == "present":
        nested = predicate.path_suffix + "/"
        return tuple(
            item
            for item in facts
            if item.path.endswith(predicate.path_suffix) or nested in item.path
        )
    if predicate.operator == "nonempty":
        nested = predicate.path_suffix + "/"
        return tuple(
            item
            for item in facts
            if nested in item.path
            or (
                item.path.endswith(predicate.path_suffix)
                and item.value is not None
                and (
                    not isinstance(
                        item.value,
                        (str, bytes, bytearray, dict, list, tuple, set),
                    )
                    or bool(item.value)
                )
            )
        )
    if predicate.operator == "descendant_eq":
        nested = predicate.path_suffix + "/"
        candidates = tuple(item for item in facts if nested in item.path)
        matching_roots: set[str] = set()
        for item in candidates:
            if item.value != predicate.value:
                continue
            before, _, after = item.path.partition(nested)
            child = after.split("/", 1)[0]
            matching_roots.add(f"{before}{nested}{child}")
        return tuple(
            item
            for item in candidates
            if any(
                item.path == root or item.path.startswith(root + "/")
                for root in matching_roots
            )
        )
    if predicate.operator == "same_record_fields":
        nested = predicate.path_suffix + "/"
        candidates = tuple(item for item in facts if nested in item.path)
        grouped: dict[str, list[FactRef]] = {}
        for item in candidates:
            before, separator, after = item.path.partition(nested)
            if not separator or "/" not in after:
                continue
            child = after.split("/", 1)[0]
            grouped.setdefault(f"{before}{nested}{child}", []).append(item)
        required = predicate.value if isinstance(predicate.value, dict) else {}
        matching_roots = {
            root
            for root, entries in grouped.items()
            if all(
                any(
                    item.path == f"{root}/{field}" and item.value == expected
                    for item in entries
                )
                for field, expected in required.items()
            )
        }
        return tuple(
            item
            for item in candidates
            if any(
                item.path == root or item.path.startswith(root + "/")
                for root in matching_roots
            )
        )
    return tuple(item for item in facts if item.path.endswith(predicate.path_suffix))


def _predicate_matches(predicate: FactPredicate, facts: tuple[FactRef, ...]) -> bool:
    matching = _predicate_fact_refs(predicate, facts)
    if predicate.operator == "present":
        return bool(matching)
    if predicate.operator == "nonempty":
        return bool(matching)
    if predicate.operator == "eq":
        return any(item.value == predicate.value for item in matching)
    if predicate.operator == "in":
        return any(item.value in predicate.values for item in matching)
    if predicate.operator == "contains":
        return any(
            isinstance(item.value, (tuple, list, set, str))
            and predicate.value in item.value
            for item in matching
        )
    if predicate.operator == "descendant_eq":
        return any(item.value == predicate.value for item in matching)
    if predicate.operator == "same_record_fields":
        return bool(matching)
    raise ValueError(
        f"unsupported fact predicate operation: {predicate.operator}"
    )


def match_rule(
    rule: EvidenceRule,
    facts: tuple[FactRef, ...],
) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    """Return eligibility, matched fact IDs, and predicate audit labels."""

    if not rule.runtime_active or not rule.required_fact_predicates:
        return False, (), ()

    matched_refs: list[str] = []
    audit: list[str] = []
    for predicate in rule.required_fact_predicates:
        if not _predicate_matches(predicate, facts):
            return False, (), ()
        matched_refs.extend(
            item.fact_id for item in _predicate_fact_refs(predicate, facts)
        )
        expected = predicate.value if predicate.value is not None else predicate.values
        audit.append(
            f"{predicate.path_suffix}:{predicate.operator}:{expected}"
        )
    for predicate in rule.excluded_fact_predicates:
        if _predicate_matches(predicate, facts):
            return False, (), ()
    return True, tuple(dict.fromkeys(matched_refs)), tuple(audit)


__all__ = [
    "EvidenceRule",
    "ClassicalSource",
    "EVIDENCE_ROLES",
    "FactPredicate",
    "INDEX_PATH",
    "SCHEMA_VERSION",
    "CLASSICAL_EVIDENCE_BINDINGS_SHA256",
    "load_evidence_rules",
    "production_evidence_scope",
    "match_rule",
    "production_evidence_rules",
]
