"""Typed, digest-bound contracts for one Mingli reading transaction."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal


def canonical_digest(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReadingRequest:
    query: str
    action: Literal["new", "continue", "recast", "correct", "resume"] | None = None
    system: str | None = None
    intent: dict[str, Any] = field(default_factory=dict)
    reading_id: str | None = None
    transaction_version: int = 1
    intake_id: str | None = None
    reference_datetime: str | None = None
    timezone: str | None = None
    location: str | None = None
    birth_data: dict[str, Any] = field(default_factory=dict)
    chart_data: dict[str, Any] = field(default_factory=dict)
    event_datetime: str | None = None
    goal: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    image_supplied: bool = False
    transcribed_chart: str | None = None
    # Transitional v3 decode field. The v4 CLI never accepts or emits this
    # option; it exists only while immutable v3 records can still be imported.
    system_hint: str | None = field(default=None, repr=False)

    def with_reading_id(self, reading_id: str) -> "ReadingRequest":
        return replace(self, reading_id=reading_id)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if not self.intent:
            payload.pop("intent")
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReadingRequest":
        return cls(**payload)


@dataclass(frozen=True)
class ProviderOutputBinding:
    """Bind one declared provider output to concrete calculation JSON pointers."""

    name: str
    json_pointers: tuple[str, ...]
    horizons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "json_pointers": list(self.json_pointers),
        }
        if self.horizons:
            payload["horizons"] = list(self.horizons)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProviderOutputBinding":
        return cls(
            name=str(payload["name"]),
            json_pointers=tuple(payload.get("json_pointers") or ()),
            horizons=tuple(payload.get("horizons") or ()),
        )


@dataclass(frozen=True)
class ProviderAlgorithmDependency:
    """One version-pinned algorithm dependency declared by a live provider."""

    id: str
    version: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("provider algorithm dependency requires id")
        if not self.version.strip():
            raise ValueError("provider algorithm dependency requires version")

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "version": self.version}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProviderAlgorithmDependency":
        return cls(id=str(payload["id"]), version=str(payload["version"]))


@dataclass(frozen=True)
class ProviderCapability:
    """Executable fact-layer declaration used by the semantic resolver."""

    system: str
    mode: str
    objects: tuple[str, ...]
    horizons: tuple[str, ...]
    dimensions: tuple[str, ...]
    required_inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    independent_lineage: str
    algorithm_dependencies: tuple[ProviderAlgorithmDependency, ...] = ()
    extension_outputs: tuple[str, ...] = ()
    output_bindings: tuple[ProviderOutputBinding, ...] = ()
    extension_output_bindings: tuple[ProviderOutputBinding, ...] = ()
    exact_horizons: tuple[str, ...] = ()
    assumption_cost: int = 0
    default_priority: int = 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "mode": self.mode,
            "objects": list(self.objects),
            "horizons": list(self.horizons),
            "dimensions": list(self.dimensions),
            "required_inputs": list(self.required_inputs),
            "outputs": list(self.outputs),
            "algorithm_dependencies": [
                item.to_dict() for item in self.algorithm_dependencies
            ],
            "extension_outputs": list(self.extension_outputs),
            "output_bindings": [item.to_dict() for item in self.output_bindings],
            "extension_output_bindings": [
                item.to_dict() for item in self.extension_output_bindings
            ],
            "exact_horizons": list(self.exact_horizons),
            "independent_lineage": self.independent_lineage,
            "assumption_cost": self.assumption_cost,
            "default_priority": self.default_priority,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProviderCapability":
        normalized = dict(payload)
        for name in (
            "objects",
            "horizons",
            "dimensions",
            "required_inputs",
            "outputs",
            "extension_outputs",
            "exact_horizons",
        ):
            normalized[name] = tuple(normalized.get(name) or ())
        normalized["output_bindings"] = tuple(
            ProviderOutputBinding.from_dict(item)
            for item in normalized.get("output_bindings") or ()
        )
        normalized["extension_output_bindings"] = tuple(
            ProviderOutputBinding.from_dict(item)
            for item in normalized.get("extension_output_bindings") or ()
        )
        normalized["algorithm_dependencies"] = tuple(
            ProviderAlgorithmDependency.from_dict(item)
            for item in normalized.get("algorithm_dependencies") or ()
        )
        normalized["default_priority"] = int(normalized.get("default_priority", 100))
        normalized["assumption_cost"] = int(normalized.get("assumption_cost", 0))
        return cls(**normalized)



@dataclass(frozen=True)
class FactExtensionResult:
    system: str
    base_calculation_digest: str
    requested_dimensions: tuple[str, ...]
    horizon: dict[str, Any]
    status: Literal["complete", "partial", "unsupported"]
    facts: dict[str, Any]
    unsupported_dimensions: tuple[str, ...]
    rule_traces: tuple[dict[str, Any], ...]
    extension_digest: str

    @classmethod
    def create(
        cls,
        *,
        system: str,
        base_calculation_digest: str,
        requested_dimensions: tuple[str, ...],
        horizon: dict[str, Any],
        status: Literal["complete", "partial", "unsupported"],
        facts: dict[str, Any],
        unsupported_dimensions: tuple[str, ...] = (),
        rule_traces: tuple[dict[str, Any], ...] = (),
    ) -> "FactExtensionResult":
        dimensions = tuple(dict.fromkeys(requested_dimensions))
        unsupported = tuple(dict.fromkeys(unsupported_dimensions))
        if status not in {"complete", "partial", "unsupported"}:
            raise ValueError("invalid fact extension status")
        if not dimensions:
            raise ValueError("fact extension requires requested dimensions")
        if status == "complete" and unsupported:
            raise ValueError("complete fact extension cannot have unsupported dimensions")
        if status == "unsupported" and facts:
            raise ValueError("unsupported fact extension cannot contain calculated facts")
        if status == "unsupported" and not unsupported:
            raise ValueError("unsupported fact extension requires unsupported dimensions")
        if status == "partial" and (not facts or not unsupported):
            raise ValueError(
                "partial fact extension requires facts and unsupported dimensions"
            )
        payload = {
            "system": system,
            "base_calculation_digest": base_calculation_digest,
            "requested_dimensions": list(dimensions),
            "horizon": horizon,
            "status": status,
            "facts": facts,
            "unsupported_dimensions": list(unsupported),
            "rule_traces": list(rule_traces),
        }
        return cls(
            system=system,
            base_calculation_digest=base_calculation_digest,
            requested_dimensions=dimensions,
            horizon=dict(horizon),
            status=status,
            facts=facts,
            unsupported_dimensions=unsupported,
            rule_traces=rule_traces,
            extension_digest=canonical_digest(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "base_calculation_digest": self.base_calculation_digest,
            "requested_dimensions": list(self.requested_dimensions),
            "horizon": self.horizon,
            "status": self.status,
            "facts": self.facts,
            "unsupported_dimensions": list(self.unsupported_dimensions),
            "rule_traces": list(self.rule_traces),
            "extension_digest": self.extension_digest,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FactExtensionResult":
        record = cls.create(
            system=str(payload["system"]),
            base_calculation_digest=str(payload["base_calculation_digest"]),
            requested_dimensions=tuple(payload.get("requested_dimensions") or ()),
            horizon=dict(payload.get("horizon") or {}),
            status=payload["status"],
            facts=dict(payload.get("facts") or {}),
            unsupported_dimensions=tuple(
                payload.get("unsupported_dimensions") or ()
            ),
            rule_traces=tuple(payload.get("rule_traces") or ()),
        )
        if record.extension_digest != payload.get("extension_digest"):
            raise ValueError("fact extension digest mismatch")
        return record


@dataclass(frozen=True)
class CalculationResult:
    system: str
    provider_id: str
    provider_version: str
    input_hash: str
    result_hash: str
    facts: dict[str, Any]
    diagnostics: tuple[str, ...] = ()
    fact_extension: FactExtensionResult | None = None

    @classmethod
    def create(
        cls,
        *,
        system: str,
        provider_id: str,
        provider_version: str,
        input_payload: dict[str, Any],
        facts: dict[str, Any],
        diagnostics: tuple[str, ...] = (),
    ) -> "CalculationResult":
        input_hash = canonical_digest(input_payload)
        result_hash = canonical_digest(
            {
                "system": system,
                "provider_id": provider_id,
                "provider_version": provider_version,
                "input_hash": input_hash,
                "facts": facts,
                "diagnostics": list(diagnostics),
            }
        )
        return cls(
            system=system,
            provider_id=provider_id,
            provider_version=provider_version,
            input_hash=input_hash,
            result_hash=result_hash,
            facts=facts,
            diagnostics=diagnostics,
            fact_extension=None,
        )

    def base(self) -> "CalculationResult":
        return replace(self, fact_extension=None)

    def with_fact_extension(
        self,
        extension: FactExtensionResult,
    ) -> "CalculationResult":
        if extension.system != self.system:
            raise ValueError("fact extension system mismatch")
        if extension.base_calculation_digest != self.result_hash:
            raise ValueError("fact extension belongs to another base calculation")
        return replace(self, fact_extension=extension)

    def indexed_facts(self) -> dict[str, Any]:
        if self.fact_extension is None:
            return self.facts
        return {
            **self.facts,
            "fact_extensions": self.fact_extension.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["diagnostics"] = list(self.diagnostics)
        if self.fact_extension is None:
            payload.pop("fact_extension")
        else:
            payload["fact_extension"] = self.fact_extension.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CalculationResult":
        normalized = dict(payload)
        normalized["diagnostics"] = tuple(normalized.get("diagnostics") or ())
        raw_extension = normalized.get("fact_extension")
        normalized["fact_extension"] = (
            FactExtensionResult.from_dict(raw_extension)
            if isinstance(raw_extension, dict)
            else None
        )
        record = cls(**normalized)
        expected = canonical_digest(
            {
                "system": record.system,
                "provider_id": record.provider_id,
                "provider_version": record.provider_version,
                "input_hash": record.input_hash,
                "facts": record.facts,
                "diagnostics": list(record.diagnostics),
            }
        )
        if record.result_hash != expected:
            raise ValueError("calculation result digest mismatch")
        if record.fact_extension is not None:
            if record.fact_extension.system != record.system:
                raise ValueError("fact extension system mismatch")
            if (
                record.fact_extension.base_calculation_digest
                != record.result_hash
            ):
                raise ValueError(
                    "fact extension belongs to another base calculation"
                )
        return record


@dataclass(frozen=True)
class FactRef:
    fact_id: str
    path: str
    value: Any
    provider_id: str
    provider_version: str
    reading_id: str
    version: int


@dataclass(frozen=True)
class EvidenceNode:
    rule_id: str
    source: str
    anchor: str
    applicability: str
    assertion: str
    lineage: str
    quote_hash: str
    fact_refs: tuple[str, ...] = ()
    source_path: str = ""
    source_sha256: str = ""
    reading_id: str = ""
    version: int = 0
    # Exact classical citations are copied from the verified rule binding at
    # evidence compilation time.  Keeping them on the node prevents the
    # public projection from having to reconstruct an original quote from the
    # rule assertion (which may be a summary or a model-facing rewrite).
    exact_citations: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class SourceRelationship:
    left_rule_id: str
    right_rule_id: str
    relation: Literal["independent", "derived", "parallel", "conflict"]


@dataclass(frozen=True)
class EvidenceGap:
    reason: Literal[
        "zero_applicable_evidence",
        "no_applicable_counter_evidence",
    ]
    questions: tuple[str, ...] = ()
    source_packs: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceBundle:
    system: str
    evidence: tuple[EvidenceNode, ...]
    counter_evidence: tuple[EvidenceNode, ...]
    source_relationships: tuple[SourceRelationship, ...]
    bundle_digest: str
    source_gaps: tuple[EvidenceGap, ...] = ()
    intent_digest: str = ""

    @classmethod
    def create(
        cls,
        *,
        system: str,
        evidence: tuple[EvidenceNode, ...],
        counter_evidence: tuple[EvidenceNode, ...] = (),
        source_relationships: tuple[SourceRelationship, ...] = (),
        source_gaps: tuple[EvidenceGap, ...] = (),
        intent_digest: str = "",
    ) -> "EvidenceBundle":
        rule_ids = [item.rule_id for item in (*evidence, *counter_evidence)]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError(
                "evidence rule_id must be unique across support and counter lanes"
            )
        payload = {
            "system": system,
            "evidence": [asdict(item) for item in evidence],
            "counter_evidence": [asdict(item) for item in counter_evidence],
            "source_relationships": [asdict(item) for item in source_relationships],
        }
        if source_gaps:
            payload["source_gaps"] = [asdict(item) for item in source_gaps]
        if intent_digest:
            payload["intent_digest"] = intent_digest
        return cls(
            system=system,
            evidence=evidence,
            counter_evidence=counter_evidence,
            source_relationships=source_relationships,
            bundle_digest=canonical_digest(payload),
            source_gaps=source_gaps,
            intent_digest=intent_digest,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "system": self.system,
            "evidence": [asdict(item) for item in self.evidence],
            "counter_evidence": [asdict(item) for item in self.counter_evidence],
            "source_relationships": [
                asdict(item) for item in self.source_relationships
            ],
            "bundle_digest": self.bundle_digest,
        }
        if self.source_gaps:
            payload["source_gaps"] = [asdict(item) for item in self.source_gaps]
        if self.intent_digest:
            payload["intent_digest"] = self.intent_digest
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceBundle":
        def node(item: dict[str, Any]) -> EvidenceNode:
            normalized = dict(item)
            normalized["fact_refs"] = tuple(normalized.get("fact_refs") or ())
            normalized["exact_citations"] = tuple(
                dict(citation)
                for citation in normalized.get("exact_citations") or ()
                if isinstance(citation, dict)
            )
            return EvidenceNode(**normalized)

        record = cls(
            system=payload["system"],
            evidence=tuple(node(item) for item in payload.get("evidence") or ()),
            counter_evidence=tuple(
                node(item) for item in payload.get("counter_evidence") or ()
            ),
            source_relationships=tuple(
                SourceRelationship(**item)
                for item in payload.get("source_relationships") or ()
            ),
            bundle_digest=payload["bundle_digest"],
            source_gaps=tuple(
                EvidenceGap(
                    reason=item["reason"],
                    questions=tuple(item.get("questions") or ()),
                    source_packs=tuple(item.get("source_packs") or ()),
                )
                for item in payload.get("source_gaps") or ()
            ),
            intent_digest=str(payload.get("intent_digest") or ""),
        )
        expected = cls.create(
            system=record.system,
            evidence=record.evidence,
            counter_evidence=record.counter_evidence,
            source_relationships=record.source_relationships,
            source_gaps=record.source_gaps,
            intent_digest=record.intent_digest,
        ).bundle_digest
        if record.bundle_digest != expected:
            raise ValueError("evidence bundle digest mismatch")
        return record


@dataclass(frozen=True)
class JudgmentDimension:
    dimension: str
    verdict: str
    confidence: str
    conclusion: str
    evidence_ids: tuple[str, ...] = ()
    counter_evidence_ids: tuple[str, ...] = ()
    timing_window: str | None = None
    uncertainty: str | None = None


def judgment_dimension_digest(dimension: JudgmentDimension) -> str:
    """Bind public prose to one immutable judgment dimension."""

    return canonical_digest(asdict(dimension))


@dataclass(frozen=True)
class Judgment:
    system: str
    calculation_digest: str
    evidence_digest: str
    basis_label: str
    basis_text: str
    dimensions: tuple[JudgmentDimension, ...]
    judgment_digest: str
    intent_digest: str = ""

    @classmethod
    def create(
        cls,
        *,
        system: str,
        calculation_digest: str,
        evidence_digest: str,
        basis_label: str,
        basis_text: str,
        dimensions: tuple[JudgmentDimension, ...],
        intent_digest: str = "",
    ) -> "Judgment":
        payload = {
            "system": system,
            "calculation_digest": calculation_digest,
            "evidence_digest": evidence_digest,
            "basis_label": basis_label,
            "basis_text": basis_text,
            "dimensions": [asdict(item) for item in dimensions],
        }
        if intent_digest:
            payload["intent_digest"] = intent_digest
        return cls(
            system=system,
            calculation_digest=calculation_digest,
            evidence_digest=evidence_digest,
            basis_label=basis_label,
            basis_text=basis_text,
            dimensions=dimensions,
            judgment_digest=canonical_digest(payload),
            intent_digest=intent_digest,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "system": self.system,
            "calculation_digest": self.calculation_digest,
            "evidence_digest": self.evidence_digest,
            "basis_label": self.basis_label,
            "basis_text": self.basis_text,
            "dimensions": [asdict(item) for item in self.dimensions],
            "judgment_digest": self.judgment_digest,
        }
        if self.intent_digest:
            payload["intent_digest"] = self.intent_digest
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Judgment":
        dimensions = []
        for item in payload.get("dimensions") or ():
            normalized = dict(item)
            normalized["evidence_ids"] = tuple(normalized.get("evidence_ids") or ())
            normalized["counter_evidence_ids"] = tuple(
                normalized.get("counter_evidence_ids") or ()
            )
            dimensions.append(JudgmentDimension(**normalized))
        record = cls(
            system=payload["system"],
            calculation_digest=payload["calculation_digest"],
            evidence_digest=payload["evidence_digest"],
            basis_label=payload["basis_label"],
            basis_text=payload["basis_text"],
            dimensions=tuple(dimensions),
            judgment_digest=payload["judgment_digest"],
            intent_digest=str(payload.get("intent_digest") or ""),
        )
        expected = cls.create(
            system=record.system,
            calculation_digest=record.calculation_digest,
            evidence_digest=record.evidence_digest,
            basis_label=record.basis_label,
            basis_text=record.basis_text,
            dimensions=record.dimensions,
            intent_digest=record.intent_digest,
        ).judgment_digest
        if record.judgment_digest != expected:
            raise ValueError("judgment digest mismatch")
        return record



def _validate_artifact_bindings(
    calculation: CalculationResult,
    evidence: EvidenceBundle,
    judgment: Judgment,
) -> None:
    if len({calculation.system, evidence.system, judgment.system}) != 1:
        raise ValueError("reading artifact system mismatch")
    if judgment.calculation_digest != calculation.result_hash:
        raise ValueError("judgment calculation digest mismatch")
    if judgment.evidence_digest != evidence.bundle_digest:
        raise ValueError("judgment evidence digest mismatch")
    evidence_ids = {item.rule_id for item in evidence.evidence}
    counter_ids = {item.rule_id for item in evidence.counter_evidence}
    all_source_ids = evidence_ids | counter_ids
    for relationship in evidence.source_relationships:
        if relationship.left_rule_id not in all_source_ids:
            raise ValueError("source relationship contains an unknown left rule")
        if relationship.right_rule_id not in all_source_ids:
            raise ValueError("source relationship contains an unknown right rule")
        if relationship.left_rule_id == relationship.right_rule_id:
            raise ValueError("source relationship cannot point to itself")
    for dimension in judgment.dimensions:
        if not set(dimension.evidence_ids) <= evidence_ids:
            raise ValueError("judgment contains an unknown evidence id")
        if not set(dimension.counter_evidence_ids) <= counter_ids:
            raise ValueError("judgment contains an unknown counter-evidence id")


@dataclass(frozen=True)
class DraftClaim:
    dimension: str
    polarity: str
    confidence: str
    text: str
    claim_digest: str = ""
    frozen_conclusion: str = ""


@dataclass(frozen=True)
class PublicDraft:
    basis_text: str
    claims: tuple[DraftClaim, ...]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "basis_text": self.basis_text,
            "claims": [asdict(item) for item in self.claims],
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PublicDraft":
        return cls(
            basis_text=str(payload["basis_text"]),
            claims=tuple(DraftClaim(**item) for item in payload.get("claims") or ()),
            explanation=str(payload["explanation"]),
        )


@dataclass(frozen=True)
class ClaimTrace:
    role: Literal["main", "support", "qualification"]
    text: str
    fact_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    counter_evidence_refs: tuple[str, ...]
    dimension: str = ""
    visible_span: tuple[int, int] = ()


@dataclass(frozen=True)
class AnswerDraft:
    visible_basis: str
    main_answer: str
    public_copy: str
    visible_basis_span: tuple[int, int]
    main_answer_span: tuple[int, int]
    claim_traces: tuple[ClaimTrace, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "visible_basis": self.visible_basis,
            "main_answer": self.main_answer,
            "public_copy": self.public_copy,
            "visible_basis_span": list(self.visible_basis_span),
            "main_answer_span": list(self.main_answer_span),
            "claim_traces": [asdict(item) for item in self.claim_traces],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnswerDraft":
        traces = []
        for item in payload.get("claim_traces") or ():
            normalized = dict(item)
            for name in (
                "fact_refs",
                "evidence_refs",
                "counter_evidence_refs",
                "visible_span",
            ):
                normalized[name] = tuple(normalized.get(name) or ())
            traces.append(ClaimTrace(**normalized))
        return cls(
            visible_basis=str(payload.get("visible_basis") or ""),
            main_answer=str(payload.get("main_answer") or ""),
            public_copy=str(payload.get("public_copy") or ""),
            visible_basis_span=tuple(payload.get("visible_basis_span") or ()),
            main_answer_span=tuple(payload.get("main_answer_span") or ()),
            claim_traces=tuple(traces),
        )


@dataclass(frozen=True)
class PreparedReading:
    reading_id: str
    version: int
    system: str
    prepared_digest: str = ""
    request_digest: str = ""
    intent_digest: str = ""
    calculation_digest: str = ""
    fact_extension_digest: str = ""
    evidence_digest: str = ""
    judgment_digest: str = ""
    basis_label: str = ""
    basis_text: str = ""
    requested_dimensions: tuple[str, ...] = ()
    dimensions: tuple[JudgmentDimension, ...] = ()
    evidence: tuple[EvidenceNode, ...] = ()
    counter_evidence: tuple[EvidenceNode, ...] = ()
    active_query: str = ""
    root_query: str = ""
    is_followup: bool = False
    calculation: CalculationResult | None = None
    fact_index: tuple[FactRef, ...] = ()
    source_relationships: tuple[SourceRelationship, ...] = ()
    parent_reading_id: str | None = None
    root_reading_id: str = ""
    action: str = "new"
    supersedes_version: int | None = None
    prior_claims: tuple[str, ...] = ()
    source_gaps: tuple[EvidenceGap, ...] = ()
    status: str = "prepared"

    def to_dict(self) -> dict[str, Any]:
        calculation_facts: dict[str, Any] = {}
        if self.calculation is not None:
            if self.calculation.system in {"physiognomy", "selection"}:
                # The complete deterministic candidate board remains in
                # ``calculation``.  The transport convenience view must use
                # the same bounded evidence projection as the fact index or
                # a 32-day window duplicates every exact-time record.
                from .fact_index import indexed_fact_payload

                calculation_facts = indexed_fact_payload(self.calculation)
            else:
                calculation_facts = self.calculation.indexed_facts()
        dimensions = []
        for item in self.dimensions:
            payload = asdict(item)
            payload["claim_digest"] = judgment_dimension_digest(item)
            dimensions.append(payload)
        return {
            "reading_id": self.reading_id,
            "version": self.version,
            "system": self.system,
            "prepared_digest": self.prepared_digest,
            "request_digest": self.request_digest,
            "intent_digest": self.intent_digest,
            "calculation_digest": self.calculation_digest,
            "fact_extension_digest": self.fact_extension_digest,
            "evidence_digest": self.evidence_digest,
            "judgment_digest": self.judgment_digest,
            "basis_label": self.basis_label,
            "basis_text": self.basis_text,
            "requested_dimensions": list(self.requested_dimensions),
            "dimensions": dimensions,
            "calculation": (
                self.calculation.to_dict()
                if self.calculation is not None
                and self.calculation.system != "physiognomy"
                else None
            ),
            "calculation_facts": calculation_facts,
            "fact_index": [asdict(item) for item in self.fact_index],
            "evidence": [asdict(item) for item in self.evidence],
            "counter_evidence": [asdict(item) for item in self.counter_evidence],
            "source_relationships": [
                asdict(item) for item in self.source_relationships
            ],
            "active_query": self.active_query,
            "root_query": self.root_query,
            "is_followup": self.is_followup,
            "parent_reading_id": self.parent_reading_id,
            "root_reading_id": self.root_reading_id,
            "action": self.action,
            "supersedes_version": self.supersedes_version,
            "prior_claims": list(self.prior_claims),
            "source_gaps": [asdict(item) for item in self.source_gaps],
            "status": self.status,
        }


@dataclass(frozen=True)
class AcceptedClaim:
    role: Literal["main", "support", "qualification"]
    text: str
    visible_span: tuple[int, int]
    dimension: str
    fact_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    counter_evidence_refs: tuple[str, ...]
    claim_digest: str

    @classmethod
    def create(
        cls,
        *,
        role: str,
        text: str,
        visible_span: tuple[int, int],
        dimension: str,
        fact_refs: tuple[str, ...],
        evidence_refs: tuple[str, ...],
        counter_evidence_refs: tuple[str, ...],
    ) -> "AcceptedClaim":
        if role not in {"main", "support", "qualification"}:
            raise ValueError("accepted claim role is invalid")
        if not text.strip() or len(visible_span) != 2:
            raise ValueError("accepted claim text/span is invalid")
        if not dimension.strip():
            raise ValueError("accepted claim dimension is empty")
        fact_refs = tuple(sorted(set(fact_refs)))
        evidence_refs = tuple(sorted(set(evidence_refs)))
        counter_evidence_refs = tuple(sorted(set(counter_evidence_refs)))
        core = {
            "role": role,
            "text": text,
            "visible_span": list(visible_span),
            "dimension": dimension,
            "fact_refs": list(fact_refs),
            "evidence_refs": list(evidence_refs),
            "counter_evidence_refs": list(counter_evidence_refs),
        }
        return cls(
            role=role,
            text=text,
            visible_span=visible_span,
            dimension=dimension,
            fact_refs=fact_refs,
            evidence_refs=evidence_refs,
            counter_evidence_refs=counter_evidence_refs,
            claim_digest=canonical_digest(core),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["visible_span"] = list(self.visible_span)
        payload["fact_refs"] = list(self.fact_refs)
        payload["evidence_refs"] = list(self.evidence_refs)
        payload["counter_evidence_refs"] = list(self.counter_evidence_refs)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AcceptedClaim":
        record = cls.create(
            role=str(payload["role"]),
            text=str(payload["text"]),
            visible_span=tuple(payload.get("visible_span") or ()),
            dimension=str(payload["dimension"]),
            fact_refs=tuple(payload.get("fact_refs") or ()),
            evidence_refs=tuple(payload.get("evidence_refs") or ()),
            counter_evidence_refs=tuple(payload.get("counter_evidence_refs") or ()),
        )
        if record.claim_digest != payload.get("claim_digest"):
            raise ValueError("accepted claim digest mismatch")
        return record


@dataclass(frozen=True)
class AcceptedReading:
    reading_id: str
    version: int
    system: str
    public_copy: str
    public_copy_sha256: str
    request_digest: str
    calculation_digest: str
    evidence_digest: str
    judgment_digest: str
    repair_attempts: int
    fallback_used: bool
    draft_validation_findings: tuple[str, ...] = ()
    prepared_digest: str = ""
    parent_reading_id: str | None = None
    root_reading_id: str = ""
    action: str = "new"
    supersedes_version: int | None = None
    prior_claims: tuple[str, ...] = ()
    intent_digest: str = ""
    accepted_claims: tuple[AcceptedClaim, ...] = ()
    status: str = "accepted"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["accepted_claims"] = [item.to_dict() for item in self.accepted_claims]
        if not self.draft_validation_findings:
            payload.pop("draft_validation_findings")
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AcceptedReading":
        normalized = dict(payload)
        normalized["draft_validation_findings"] = tuple(
            normalized.get("draft_validation_findings") or ()
        )
        reading_id = str(normalized.get("reading_id") or "")
        normalized.setdefault("parent_reading_id", None)
        normalized.setdefault("root_reading_id", reading_id)
        normalized.setdefault("action", "v3-import")
        normalized.setdefault("supersedes_version", None)
        normalized["prior_claims"] = tuple(normalized.get("prior_claims") or ())
        normalized.setdefault("intent_digest", "")
        normalized["accepted_claims"] = tuple(
            AcceptedClaim.from_dict(item)
            for item in normalized.get("accepted_claims") or ()
        )
        record = cls(**normalized)
        expected = hashlib.sha256(record.public_copy.encode("utf-8")).hexdigest()
        if record.public_copy_sha256 != expected:
            raise ValueError("public copy digest mismatch")
        return record


@dataclass(frozen=True)
class NeedUserFact:
    system: str
    missing_facts: tuple[str, ...]
    known_facts: dict[str, Any]
    intake_id: str | None = None
    request_digest: str | None = None
    status: str = "need_user_fact"


@dataclass(frozen=True)
class UnsupportedDimension:
    system: str
    calculation_digest: str
    extension_digest: str
    unsupported_dimensions: tuple[str, ...]
    horizon: dict[str, Any]
    status: str = "unsupported_dimension"


@dataclass(frozen=True)
class PublishedIntakeQuestion:
    intake_id: str
    question: str
    question_sha256: str
    status: str = "question_published"


@dataclass(frozen=True)
class NotApplicable:
    """Query does not qualify for mingli reading; not an error."""

    question: str
    status: str = "not_applicable"


@dataclass(frozen=True)
class InternalFailure:
    code: str
    safe_message: str
    user_retry_instruction: None = None
    status: str = "internal_failure"


@dataclass(frozen=True)
class AnswerRepairRequired:
    reading_id: str
    prepared_digest: str
    field_errors: tuple[str, ...]
    status: str = "repair_required"


@dataclass(frozen=True)
class IntakeRecord:
    intake_id: str
    request: ReadingRequest
    system: str
    missing_facts: tuple[str, ...]
    question: str | None
    question_sha256: str | None
    intake_digest: str

    @classmethod
    def create(
        cls,
        *,
        intake_id: str,
        request: ReadingRequest,
        system: str,
        missing_facts: tuple[str, ...],
        question: str | None = None,
    ) -> "IntakeRecord":
        question_sha256 = (
            hashlib.sha256(question.encode("utf-8")).hexdigest()
            if question is not None
            else None
        )
        core = {
            "intake_id": intake_id,
            "request": request.to_dict(),
            "system": system,
            "missing_facts": list(missing_facts),
            "question": question,
            "question_sha256": question_sha256,
        }
        return cls(
            intake_id=intake_id,
            request=request,
            system=system,
            missing_facts=missing_facts,
            question=question,
            question_sha256=question_sha256,
            intake_digest=canonical_digest(core),
        )

    def with_question(self, question: str) -> "IntakeRecord":
        return self.create(
            intake_id=self.intake_id,
            request=self.request,
            system=self.system,
            missing_facts=self.missing_facts,
            question=question,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "intake_id": self.intake_id,
            "request": self.request.to_dict(),
            "system": self.system,
            "missing_facts": list(self.missing_facts),
            "question": self.question,
            "question_sha256": self.question_sha256,
            "intake_digest": self.intake_digest,
        }
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "IntakeRecord":
        record = cls.create(
            intake_id=payload["intake_id"],
            request=ReadingRequest.from_dict(payload["request"]),
            system=payload["system"],
            missing_facts=tuple(payload.get("missing_facts") or ()),
            question=payload["question"],
        )
        if record.question_sha256 != payload.get("question_sha256"):
            raise ValueError("intake question digest mismatch")
        if record.intake_digest != payload.get("intake_digest"):
            raise ValueError("intake digest mismatch")
        return record


@dataclass(frozen=True)
class PreparedArtifact:
    """One subject/capability fact-and-evidence member of a prepared reading."""

    subject_ref: str
    capability_id: str
    independent_lineage_id: str
    calculation: CalculationResult
    evidence: EvidenceBundle
    judgment: Judgment
    artifact_digest: str

    @classmethod
    def create(
        cls,
        *,
        subject_ref: str,
        capability_id: str,
        independent_lineage_id: str,
        calculation: CalculationResult,
        evidence: EvidenceBundle,
        judgment: Judgment,
    ) -> "PreparedArtifact":
        if not subject_ref or not capability_id or not independent_lineage_id:
            raise ValueError("prepared artifact identity must be non-empty")
        _validate_artifact_bindings(calculation, evidence, judgment)
        if calculation.system != capability_id or judgment.system != capability_id:
            raise ValueError("prepared artifact capability mismatch")
        core = {
            "subject_ref": subject_ref,
            "capability_id": capability_id,
            "independent_lineage_id": independent_lineage_id,
            "calculation": calculation.to_dict(),
            "evidence": evidence.to_dict(),
            "judgment": judgment.to_dict(),
        }
        return cls(
            subject_ref=subject_ref,
            capability_id=capability_id,
            independent_lineage_id=independent_lineage_id,
            calculation=calculation,
            evidence=evidence,
            judgment=judgment,
            artifact_digest=canonical_digest(core),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_ref": self.subject_ref,
            "capability_id": self.capability_id,
            "independent_lineage_id": self.independent_lineage_id,
            "calculation": self.calculation.to_dict(),
            "evidence": self.evidence.to_dict(),
            "judgment": self.judgment.to_dict(),
            "artifact_digest": self.artifact_digest,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PreparedArtifact":
        record = cls.create(
            subject_ref=str(payload["subject_ref"]),
            capability_id=str(payload["capability_id"]),
            independent_lineage_id=str(payload["independent_lineage_id"]),
            calculation=CalculationResult.from_dict(payload["calculation"]),
            evidence=EvidenceBundle.from_dict(payload["evidence"]),
            judgment=Judgment.from_dict(payload["judgment"]),
        )
        if record.artifact_digest != payload.get("artifact_digest"):
            raise ValueError("prepared artifact digest mismatch")
        return record


@dataclass(frozen=True)
class PreparedReadingRecord:
    reading_id: str
    version: int
    request: ReadingRequest
    calculation: CalculationResult
    evidence: EvidenceBundle
    judgment: Judgment
    prepared_digest: str
    parent_reading_id: str | None = None
    root_reading_id: str = ""
    action: str = "new"
    supersedes_version: int | None = None
    prior_claims: tuple[str, ...] = ()
    artifacts: tuple[PreparedArtifact, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        reading_id: str,
        version: int,
        request: ReadingRequest,
        calculation: CalculationResult,
        evidence: EvidenceBundle,
        judgment: Judgment,
        parent_reading_id: str | None = None,
        root_reading_id: str | None = None,
        action: str | None = None,
        supersedes_version: int | None = None,
        prior_claims: tuple[str, ...] = (),
        artifacts: tuple[PreparedArtifact, ...] = (),
    ) -> "PreparedReadingRecord":
        _validate_artifact_bindings(calculation, evidence, judgment)
        if request.reading_id != reading_id:
            raise ValueError("prepared request reading_id mismatch")
        intent_digest = canonical_digest(request.intent)
        if evidence.intent_digest and evidence.intent_digest != intent_digest:
            raise ValueError("prepared evidence intent digest mismatch")
        if judgment.intent_digest and judgment.intent_digest != intent_digest:
            raise ValueError("prepared judgment intent digest mismatch")
        resolved_root = root_reading_id or reading_id
        resolved_action = action or request.action or "v3-import"
        from .fact_index import build_fact_index

        indexed_fact_ids = {
            item.fact_id
            for item in build_fact_index(
                calculation,
                reading_id=reading_id,
                version=version,
            )
        }
        allowed_evidence_owners = {reading_id}
        if (
            resolved_action == "continue"
            and version == 1
            and parent_reading_id is not None
            and parent_reading_id != reading_id
        ):
            allowed_evidence_owners.add(parent_reading_id)
        for node in (*evidence.evidence, *evidence.counter_evidence):
            if node.reading_id and node.reading_id not in allowed_evidence_owners:
                raise ValueError("evidence belongs to another reading")
            if node.version and node.version > version:
                raise ValueError("evidence belongs to a future reading version")
            if not set(node.fact_refs) <= indexed_fact_ids:
                raise ValueError("evidence contains an unknown fact reference")
        if resolved_action not in {
            "new",
            "continue",
            "recast",
            "correct",
            "resume",
            "v3-import",
        }:
            raise ValueError("invalid reading lineage action")
        if supersedes_version is not None and supersedes_version < 1:
            raise ValueError("supersedes_version must be positive")
        core = {
            "reading_id": reading_id,
            "version": version,
            "request": request.to_dict(),
            "calculation": calculation.to_dict(),
            "evidence": evidence.to_dict(),
            "judgment": judgment.to_dict(),
            "parent_reading_id": parent_reading_id,
            "root_reading_id": resolved_root,
            "action": resolved_action,
            "supersedes_version": supersedes_version,
            "prior_claims": list(prior_claims),
        }
        if artifacts:
            identities = {
                (item.subject_ref, item.capability_id) for item in artifacts
            }
            if len(identities) != len(artifacts):
                raise ValueError("prepared artifact identity is duplicated")
            primary_artifact = artifacts[0]
            if (
                primary_artifact.calculation != calculation
                or primary_artifact.evidence != evidence
                or primary_artifact.judgment != judgment
            ):
                raise ValueError("first prepared artifact must bind primary artifacts")
            for artifact in artifacts:
                for node in (
                    *artifact.evidence.evidence,
                    *artifact.evidence.counter_evidence,
                ):
                    if node.reading_id and node.reading_id != reading_id:
                        raise ValueError("prepared artifact evidence belongs to another reading")
                    if node.version and node.version != version:
                        raise ValueError("prepared artifact evidence version mismatch")
            core["artifacts"] = [item.to_dict() for item in artifacts]
        return cls(
            reading_id=reading_id,
            version=version,
            request=request,
            calculation=calculation,
            evidence=evidence,
            judgment=judgment,
            prepared_digest=canonical_digest(core),
            parent_reading_id=parent_reading_id,
            root_reading_id=resolved_root,
            action=resolved_action,
            supersedes_version=supersedes_version,
            prior_claims=tuple(prior_claims),
            artifacts=tuple(artifacts),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "reading_id": self.reading_id,
            "version": self.version,
            "request": self.request.to_dict(),
            "calculation": self.calculation.to_dict(),
            "evidence": self.evidence.to_dict(),
            "judgment": self.judgment.to_dict(),
            "parent_reading_id": self.parent_reading_id,
            "root_reading_id": self.root_reading_id,
            "action": self.action,
            "supersedes_version": self.supersedes_version,
            "prior_claims": list(self.prior_claims),
            "prepared_digest": self.prepared_digest,
            "artifact_digests": {
                "calculation_digest": self.calculation.result_hash,
                "intent_digest": canonical_digest(self.request.intent),
                "evidence_digest": self.evidence.bundle_digest,
                "judgment_digest": self.judgment.judgment_digest,
            },
        }
        if self.artifacts:
            payload["artifacts"] = [item.to_dict() for item in self.artifacts]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PreparedReadingRecord":
        reading_id = payload["reading_id"]
        version = int(payload["version"])
        request = ReadingRequest.from_dict(payload["request"])
        calculation = CalculationResult.from_dict(payload["calculation"])
        evidence = EvidenceBundle.from_dict(payload["evidence"])
        judgment = Judgment.from_dict(payload["judgment"])
        lineage_fields = {
            "parent_reading_id",
            "root_reading_id",
            "action",
            "supersedes_version",
            "prior_claims",
        }
        if lineage_fields <= set(payload):
            record = cls.create(
                reading_id=reading_id,
                version=version,
                request=request,
                calculation=calculation,
                evidence=evidence,
                judgment=judgment,
                parent_reading_id=payload.get("parent_reading_id"),
                root_reading_id=payload.get("root_reading_id"),
                action=payload.get("action"),
                supersedes_version=payload.get("supersedes_version"),
                prior_claims=tuple(payload.get("prior_claims") or ()),
                artifacts=tuple(
                    PreparedArtifact.from_dict(item)
                    for item in payload.get("artifacts") or ()
                ),
            )
            if record.prepared_digest != payload.get("prepared_digest"):
                raise ValueError("prepared reading digest mismatch")
            expected_digests = {
                "calculation_digest": record.calculation.result_hash,
                "intent_digest": canonical_digest(record.request.intent),
                "evidence_digest": record.evidence.bundle_digest,
                "judgment_digest": record.judgment.judgment_digest,
            }
            supplied_digests = payload.get("artifact_digests")
            if supplied_digests is not None and supplied_digests != expected_digests:
                raise ValueError("prepared artifact digest mismatch")
            return record

        _validate_artifact_bindings(calculation, evidence, judgment)
        if request.reading_id != reading_id:
            raise ValueError("prepared request reading_id mismatch")
        legacy_core = {
            "reading_id": reading_id,
            "version": version,
            "request": request.to_dict(),
            "calculation": calculation.to_dict(),
            "evidence": evidence.to_dict(),
            "judgment": judgment.to_dict(),
        }
        legacy_digest = canonical_digest(legacy_core)
        if legacy_digest != payload.get("prepared_digest"):
            raise ValueError("prepared reading digest mismatch")
        return cls(
            reading_id=reading_id,
            version=version,
            request=request,
            calculation=calculation,
            evidence=evidence,
            judgment=judgment,
            prepared_digest=legacy_digest,
            parent_reading_id=None,
            root_reading_id=reading_id,
            action=request.action or "v3-import",
            supersedes_version=None,
            prior_claims=(),
        )

    def public_contract(self) -> PreparedReading:
        from .fact_index import build_fact_index

        root_query = str(self.request.metadata.get("root_query") or self.request.query)
        v4 = self.request.action is not None
        return PreparedReading(
            reading_id=self.reading_id,
            version=self.version,
            system=self.judgment.system,
            prepared_digest=self.prepared_digest,
            request_digest=canonical_digest(self.request.to_dict()),
            intent_digest=canonical_digest(self.request.intent),
            calculation_digest=self.calculation.result_hash,
            fact_extension_digest=(
                self.calculation.fact_extension.extension_digest
                if self.calculation.fact_extension is not None
                else ""
            ),
            evidence_digest=self.evidence.bundle_digest,
            judgment_digest=self.judgment.judgment_digest,
            basis_label=self.judgment.basis_label,
            basis_text=self.judgment.basis_text,
            requested_dimensions=tuple(
                str(item)
                for item in self.request.intent.get("question_dimensions") or ()
            ),
            dimensions=() if v4 else self.judgment.dimensions,
            evidence=self.evidence.evidence,
            counter_evidence=self.evidence.counter_evidence,
            calculation=(
                None
                if self.calculation.system in {"physiognomy", "liuyao"}
                else self.calculation
            ),
            fact_index=build_fact_index(
                self.calculation,
                reading_id=self.reading_id,
                version=self.version,
            ),
            source_relationships=self.evidence.source_relationships,
            active_query=self.request.query,
            root_query=root_query,
            is_followup=self.version > 1 or self.parent_reading_id is not None,
            parent_reading_id=self.parent_reading_id,
            root_reading_id=self.root_reading_id,
            action=self.action,
            supersedes_version=self.supersedes_version,
            prior_claims=self.prior_claims,
            source_gaps=self.evidence.source_gaps,
        )


@dataclass(frozen=True)
class ReadingRecord:
    request: ReadingRequest
    calculation: CalculationResult
    evidence: EvidenceBundle
    judgment: Judgment
    accepted: AcceptedReading
    artifacts: tuple[PreparedArtifact, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "request": self.request.to_dict(),
            "calculation": self.calculation.to_dict(),
            "evidence": self.evidence.to_dict(),
            "judgment": self.judgment.to_dict(),
            "accepted": self.accepted.to_dict(),
        }
        if self.artifacts:
            payload["artifacts"] = [item.to_dict() for item in self.artifacts]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReadingRecord":
        record = cls(
            request=ReadingRequest.from_dict(payload["request"]),
            calculation=CalculationResult.from_dict(payload["calculation"]),
            evidence=EvidenceBundle.from_dict(payload["evidence"]),
            judgment=Judgment.from_dict(payload["judgment"]),
            accepted=AcceptedReading.from_dict(payload["accepted"]),
            artifacts=tuple(
                PreparedArtifact.from_dict(item)
                for item in payload.get("artifacts") or ()
            ),
        )
        _validate_artifact_bindings(
            record.calculation,
            record.evidence,
            record.judgment,
        )
        accepted = record.accepted
        if record.request.reading_id != accepted.reading_id:
            raise ValueError("accepted request reading_id mismatch")
        if accepted.system != record.judgment.system:
            raise ValueError("accepted reading system mismatch")
        if accepted.request_digest != canonical_digest(record.request.to_dict()):
            raise ValueError("accepted request digest mismatch")
        if accepted.intent_digest and accepted.intent_digest != canonical_digest(
            record.request.intent
        ):
            raise ValueError("accepted intent digest mismatch")
        if accepted.calculation_digest != record.calculation.result_hash:
            raise ValueError("accepted calculation digest mismatch")
        if accepted.evidence_digest != record.evidence.bundle_digest:
            raise ValueError("accepted evidence digest mismatch")
        if accepted.judgment_digest != record.judgment.judgment_digest:
            raise ValueError("accepted judgment digest mismatch")
        if accepted.accepted_claims:
            from .fact_index import build_fact_index

            fact_ids = {
                item.fact_id
                for item in build_fact_index(
                    record.calculation,
                    reading_id=accepted.reading_id,
                    version=accepted.version,
                )
            }
            evidence_ids = {item.rule_id for item in record.evidence.evidence}
            counter_ids = {item.rule_id for item in record.evidence.counter_evidence}
            dimensions = {item.dimension for item in record.judgment.dimensions}
            claim_identities: set[tuple[tuple[int, int], str]] = set()
            for claim in accepted.accepted_claims:
                identity = (claim.visible_span, claim.dimension)
                if identity in claim_identities:
                    raise ValueError("accepted claim semantic identity is duplicated")
                claim_identities.add(identity)
                start, end = claim.visible_span
                if accepted.public_copy[start:end] != claim.text:
                    raise ValueError("accepted claim public span mismatch")
                if claim.dimension not in dimensions:
                    raise ValueError("accepted claim dimension mismatch")
                if not set(claim.fact_refs) <= fact_ids:
                    raise ValueError("accepted claim fact reference mismatch")
                if not set(claim.evidence_refs) <= evidence_ids:
                    raise ValueError("accepted claim evidence reference mismatch")
                if not set(claim.counter_evidence_refs) <= counter_ids:
                    raise ValueError("accepted claim counter-evidence reference mismatch")
        accepted_payload = payload["accepted"]
        lineage_fields = {
            "parent_reading_id",
            "root_reading_id",
            "action",
            "supersedes_version",
            "prior_claims",
        }
        if lineage_fields <= set(accepted_payload):
            prepared_digest = PreparedReadingRecord.create(
                reading_id=accepted.reading_id,
                version=accepted.version,
                request=record.request,
                calculation=record.calculation,
                evidence=record.evidence,
                judgment=record.judgment,
                parent_reading_id=accepted.parent_reading_id,
                root_reading_id=accepted.root_reading_id,
                action=accepted.action,
                supersedes_version=accepted.supersedes_version,
                prior_claims=accepted.prior_claims,
                artifacts=record.artifacts,
            ).prepared_digest
        else:
            prepared_digest = canonical_digest(
                {
                    "reading_id": accepted.reading_id,
                    "version": accepted.version,
                    "request": record.request.to_dict(),
                    "calculation": record.calculation.to_dict(),
                    "evidence": record.evidence.to_dict(),
                    "judgment": record.judgment.to_dict(),
                }
            )
        if accepted.prepared_digest != prepared_digest:
            raise ValueError("accepted prepared digest mismatch")
        return record
