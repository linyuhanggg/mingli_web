"""Portable reading interface contracts: three commands, four results.

This module is the only external protocol surface of the reading core. It
must stay free of provider imports, domain vocabulary, transaction state and
host-specific concepts. Every terminal result carries non-empty public text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping

PROTOCOL_VERSION = "mingli-portable-interface-v2"

STOPPED_REASONS = ("need_input", "unsupported", "conflict", "error")

RUNTIME_FAILURE_SCHEMA_VERSION = "mingli-runtime-failure/v1"

_RUNTIME_FAILURE_SPECS = {
    "bootstrap.unexpected_arguments": ("bootstrap", False),
    "bootstrap.guard_load_failed": ("bootstrap", False),
    "bootstrap.runtime_lock_failed": ("bootstrap", False),
    "bootstrap.runtime_identity_invalid": ("bootstrap", False),
    "bootstrap.state_root_invalid": ("bootstrap", False),
    "input_contract.malformed_json": ("input_contract", False),
    "input_contract.invalid_command": ("input_contract", False),
    "input_contract.invalid_payload": ("input_contract", False),
    "input_contract.invalid_state_token": ("input_contract", False),
    "runtime.internal_error": ("runtime_internal", False),
    "transient.timeout": ("transient", True),
    "transient.resource_unavailable": ("transient", True),
}

TRANSITIONS = ("correct", "restart")


def _require_non_empty_text(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty text")


def _str_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        items = tuple(value)
        if all(isinstance(item, str) for item in items):
            return tuple(items)
    raise ValueError(f"{field_name} must be a sequence of strings")


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a JSON object")
    return value


@dataclass(frozen=True)
class RuntimeFailure:
    """Bounded, PII-free diagnostics for ``Stopped(reason="error")``.

    ``code`` is deliberately closed over a static registry.  No exception
    text, paths, command values, state tokens or caller identifiers can be
    serialized through this object.
    """

    code: str
    category: Literal[
        "bootstrap", "input_contract", "runtime_internal", "transient"
    ]
    retryable: bool
    schema_version: Literal["mingli-runtime-failure/v1"] = (
        RUNTIME_FAILURE_SCHEMA_VERSION
    )

    def __post_init__(self) -> None:
        expected = _RUNTIME_FAILURE_SPECS.get(self.code)
        if expected is None:
            raise ValueError(f"unknown Runtime failure code: {self.code!r}")
        if (self.category, self.retryable) != expected:
            raise ValueError("Runtime failure metadata does not match its code")
        if self.schema_version != RUNTIME_FAILURE_SCHEMA_VERSION:
            raise ValueError("unsupported Runtime failure schema version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "code": self.code,
            "category": self.category,
            "retryable": self.retryable,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RuntimeFailure":
        payload = _mapping(payload, "RuntimeFailure")
        expected_keys = {"schema_version", "code", "category", "retryable"}
        if set(payload) != expected_keys:
            raise ValueError("RuntimeFailure must contain only the v1 fields")
        retryable = payload["retryable"]
        if not isinstance(retryable, bool):
            raise ValueError("RuntimeFailure.retryable must be boolean")
        return cls(
            schema_version=str(payload["schema_version"]),  # type: ignore[arg-type]
            code=str(payload["code"]),
            category=str(payload["category"]),  # type: ignore[arg-type]
            retryable=retryable,
        )


def runtime_failure(code: str) -> RuntimeFailure:
    try:
        category, retryable = _RUNTIME_FAILURE_SPECS[code]
    except KeyError as exc:
        raise ValueError(f"unknown Runtime failure code: {code!r}") from exc
    return RuntimeFailure(
        code=code,
        category=category,  # type: ignore[arg-type]
        retryable=retryable,
    )


# ---------------------------------------------------------------------------
# Shared public value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PublicTerm:
    id: str
    label: str
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PublicTerm":
        return cls(
            id=str(payload["id"]),
            label=str(payload["label"]),
            description=(
                None
                if payload.get("description") is None
                else str(payload["description"])
            ),
        )


@dataclass(frozen=True)
class InputFieldView:
    id: str
    label: str
    type_id: str
    description: str | None = None
    choices: tuple[PublicTerm, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type_id": self.type_id,
            "description": self.description,
            "choices": [choice.to_dict() for choice in self.choices],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "InputFieldView":
        return cls(
            id=str(payload["id"]),
            label=str(payload["label"]),
            type_id=str(payload["type_id"]),
            description=(
                None
                if payload.get("description") is None
                else str(payload["description"])
            ),
            choices=tuple(
                PublicTerm.from_dict(_mapping(item, "InputFieldView.choices"))
                for item in payload.get("choices", [])
            ),
        )


@dataclass(frozen=True)
class InputRequirement:
    """One missing input group; any one declared field may satisfy it.

    The group deliberately carries public field views instead of private
    intake identifiers.  Hosts can render it or collect structured values
    without parsing ``Stopped.public_copy``.
    """

    any_of: tuple[InputFieldView, ...]

    def __post_init__(self) -> None:
        if not self.any_of:
            raise ValueError("InputRequirement.any_of must not be empty")
        ids = tuple(field.id for field in self.any_of)
        if any(not field_id for field_id in ids) or len(set(ids)) != len(ids):
            raise ValueError("InputRequirement field ids must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {"any_of": [field.to_dict() for field in self.any_of]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "InputRequirement":
        payload = _mapping(payload, "input requirement")
        raw_fields = payload.get("any_of", [])
        if not isinstance(raw_fields, (list, tuple)):
            raise ValueError("InputRequirement.any_of must be a list")
        return cls(
            any_of=tuple(InputFieldView.from_dict(_mapping(
                item, "InputRequirement.any_of"
            )) for item in raw_fields)
        )


@dataclass(frozen=True)
class InputRequest:
    """All blocking groups for a pending prepare token."""

    requirements: tuple[InputRequirement, ...]

    def __post_init__(self) -> None:
        if not self.requirements:
            raise ValueError("InputRequest.requirements must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirements": [
                requirement.to_dict() for requirement in self.requirements
            ]
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "InputRequest":
        payload = _mapping(payload, "input_request")
        raw_requirements = payload.get("requirements", [])
        if not isinstance(raw_requirements, (list, tuple)):
            raise ValueError("InputRequest.requirements must be a list")
        return cls(
            requirements=tuple(
                InputRequirement.from_dict(_mapping(
                    item, "InputRequest.requirements"
                ))
                for item in raw_requirements
            )
        )


@dataclass(frozen=True)
class TimeSemanticsView:
    """Provider-declared time semantics, exposed only as opaque IDs.

    A host can read this to know which time-basis policies a capability
    supports, which require coordinates, and what happens on an unsupported
    policy, without the generic core naming any domain concept.
    """

    role_id: str
    supported_policy_ids: tuple[str, ...]
    default_policy_id: str
    coordinate_required_policy_ids: tuple[str, ...]
    unsupported_behavior_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "supported_policy_ids": list(self.supported_policy_ids),
            "default_policy_id": self.default_policy_id,
            "coordinate_required_policy_ids": list(
                self.coordinate_required_policy_ids
            ),
            "unsupported_behavior_id": self.unsupported_behavior_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TimeSemanticsView":
        return cls(
            role_id=str(payload["role_id"]),
            supported_policy_ids=_str_tuple(
                payload.get("supported_policy_ids", []), "supported_policy_ids"
            ),
            default_policy_id=str(payload["default_policy_id"]),
            coordinate_required_policy_ids=_str_tuple(
                payload.get("coordinate_required_policy_ids", []),
                "coordinate_required_policy_ids",
            ),
            unsupported_behavior_id=str(payload["unsupported_behavior_id"]),
        )


@dataclass(frozen=True)
class CapabilityView:
    id: str
    label: str
    description: str
    objects: tuple[PublicTerm, ...]
    horizons: tuple[PublicTerm, ...]
    dimensions: tuple[PublicTerm, ...]
    default_dimension_ids: tuple[str, ...]
    input_fields: tuple[InputFieldView, ...]
    required_input_groups: tuple[tuple[str, ...], ...]
    time_semantics: TimeSemanticsView | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "objects": [term.to_dict() for term in self.objects],
            "horizons": [term.to_dict() for term in self.horizons],
            "dimensions": [term.to_dict() for term in self.dimensions],
            "default_dimension_ids": list(self.default_dimension_ids),
            "input_fields": [view.to_dict() for view in self.input_fields],
            "required_input_groups": [
                list(group) for group in self.required_input_groups
            ],
        }
        if self.time_semantics is not None:
            payload["time_semantics"] = self.time_semantics.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CapabilityView":
        raw_time = payload.get("time_semantics")
        return cls(
            id=str(payload["id"]),
            label=str(payload["label"]),
            description=str(payload["description"]),
            objects=tuple(
                PublicTerm.from_dict(item) for item in payload.get("objects", [])
            ),
            horizons=tuple(
                PublicTerm.from_dict(item) for item in payload.get("horizons", [])
            ),
            dimensions=tuple(
                PublicTerm.from_dict(item) for item in payload.get("dimensions", [])
            ),
            default_dimension_ids=_str_tuple(
                payload.get("default_dimension_ids", []),
                "default_dimension_ids",
            ),
            input_fields=tuple(
                InputFieldView.from_dict(item)
                for item in payload.get("input_fields", [])
            ),
            required_input_groups=tuple(
                _str_tuple(group, "required_input_groups")
                for group in payload.get("required_input_groups", [])
            ),
            time_semantics=(
                None
                if raw_time is None
                else TimeSemanticsView.from_dict(_mapping(raw_time, "time_semantics"))
            ),
        )


@dataclass(frozen=True)
class PublicFact:
    ref: str
    subject_ref: str
    kind_id: str
    value: object
    display_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "subject_ref": self.subject_ref,
            "kind_id": self.kind_id,
            "value": self.value,
            "display_text": self.display_text,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PublicFact":
        return cls(
            ref=str(payload["ref"]),
            subject_ref=str(payload["subject_ref"]),
            kind_id=str(payload["kind_id"]),
            value=payload.get("value"),
            display_text=str(payload["display_text"]),
        )


@dataclass(frozen=True)
class PublicEvidence:
    """One public exact citation projected from a verified source binding.

    ``excerpt`` is retained for the v2 transport shape.  Production
    projections populate it with the same verified original text as the
    first ``verbatim_citations`` entry; they never populate it from a rule
    assertion or a summary.  The additive fields stay optional so old
    synthetic briefs can still be decoded and re-encoded byte-for-byte while
    the production seam remains fail-closed for new evidence.
    """

    ref: str
    source_title: str
    locator: str | None
    excerpt: str | None
    supports_fact_refs: tuple[str, ...]
    verification_status: str | None = None
    verbatim_excerpt: str | None = None
    rule_id: str | None = None
    verbatim_citations: tuple[dict[str, str], ...] = ()

    @property
    def evidence_ref(self) -> str:
        """Stable public evidence identity (the legacy ``ref`` alias)."""

        return self.ref

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ref": self.ref,
            "source_title": self.source_title,
            "locator": self.locator,
            "excerpt": self.excerpt,
            "supports_fact_refs": list(self.supports_fact_refs),
        }
        if any(
            value is not None
            for value in (
                self.verification_status,
                self.verbatim_excerpt,
                self.rule_id,
            )
        ) or self.verbatim_citations:
            payload.update(
                {
                    "evidence_ref": self.ref,
                    "verification_status": self.verification_status,
                    "verbatim_excerpt": self.verbatim_excerpt,
                    "rule_id": self.rule_id,
                    "verbatim_citations": [
                        dict(citation) for citation in self.verbatim_citations
                    ],
                }
            )
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PublicEvidence":
        ref = payload.get("ref") or payload.get("evidence_ref")
        if ref is None:
            raise ValueError("public evidence is missing ref/evidence_ref")
        return cls(
            ref=str(ref),
            source_title=str(payload["source_title"]),
            locator=(
                None if payload.get("locator") is None else str(payload["locator"])
            ),
            excerpt=(
                None if payload.get("excerpt") is None else str(payload["excerpt"])
            ),
            supports_fact_refs=_str_tuple(
                payload.get("supports_fact_refs", []),
                "supports_fact_refs",
            ),
            verification_status=(
                None
                if payload.get("verification_status") is None
                else str(payload["verification_status"])
            ),
            verbatim_excerpt=(
                None
                if payload.get("verbatim_excerpt") is None
                else str(payload["verbatim_excerpt"])
            ),
            rule_id=(
                None
                if payload.get("rule_id") is None
                else str(payload["rule_id"])
            ),
            verbatim_citations=tuple(
                dict(citation)
                for citation in payload.get("verbatim_citations") or ()
                if isinstance(citation, Mapping)
            ),
        )


@dataclass(frozen=True)
class ClaimScope:
    subject_ref: str
    dimension_id: str
    allowed_kind_ids: tuple[str, ...]
    certainty_ceiling_id: str
    fact_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_ref": self.subject_ref,
            "dimension_id": self.dimension_id,
            "allowed_kind_ids": list(self.allowed_kind_ids),
            "certainty_ceiling_id": self.certainty_ceiling_id,
            "fact_refs": list(self.fact_refs),
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ClaimScope":
        return cls(
            subject_ref=str(payload["subject_ref"]),
            dimension_id=str(payload["dimension_id"]),
            allowed_kind_ids=_str_tuple(
                payload.get("allowed_kind_ids", []), "allowed_kind_ids"
            ),
            certainty_ceiling_id=str(payload["certainty_ceiling_id"]),
            fact_refs=_str_tuple(payload.get("fact_refs", []), "fact_refs"),
            evidence_refs=_str_tuple(
                payload.get("evidence_refs", []), "evidence_refs"
            ),
        )


@dataclass(frozen=True)
class PublicLimit:
    kind_id: str
    public_text: str
    scope_refs: tuple[str, ...] = ()
    detail_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind_id": self.kind_id,
            "public_text": self.public_text,
            "scope_refs": list(self.scope_refs),
            "detail_ids": list(self.detail_ids),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PublicLimit":
        return cls(
            kind_id=str(payload["kind_id"]),
            public_text=str(payload["public_text"]),
            scope_refs=_str_tuple(payload.get("scope_refs", []), "scope_refs"),
            detail_ids=_str_tuple(payload.get("detail_ids", []), "detail_ids"),
        )


@dataclass(frozen=True)
class PublicFinding:
    """Provider-owned, structured drafting material in the closed brief.

    ``data`` is intentionally opaque to the generic core.  The provider
    manifest owns its identifiers and projection; this contract only keeps
    its public references inside the one prepared turn.
    """

    ref: str
    subject_ref: str
    dimension_ids: tuple[str, ...]
    kind_id: str
    data: object
    fact_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    limit_kind_ids: tuple[str, ...] = ()
    support_mode: Literal["exact", "shared_turn"] = "shared_turn"
    public_text: str | None = None

    def __post_init__(self) -> None:
        if self.support_mode not in {"exact", "shared_turn"}:
            raise ValueError("PublicFinding.support_mode is invalid")
        if self.public_text is not None and not self.public_text.strip():
            raise ValueError("PublicFinding.public_text must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "ref": self.ref,
            "subject_ref": self.subject_ref,
            "dimension_ids": list(self.dimension_ids),
            "kind_id": self.kind_id,
            "data": self.data,
            "fact_refs": list(self.fact_refs),
            "evidence_refs": list(self.evidence_refs),
            "limit_kind_ids": list(self.limit_kind_ids),
            "support_mode": self.support_mode,
        }
        if self.public_text is not None:
            payload["public_text"] = self.public_text
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PublicFinding":
        return cls(
            ref=str(payload["ref"]),
            subject_ref=str(payload["subject_ref"]),
            dimension_ids=_str_tuple(
                payload.get("dimension_ids", []), "dimension_ids"
            ),
            kind_id=str(payload["kind_id"]),
            data=payload.get("data"),
            fact_refs=_str_tuple(payload.get("fact_refs", []), "fact_refs"),
            evidence_refs=_str_tuple(
                payload.get("evidence_refs", []), "evidence_refs"
            ),
            limit_kind_ids=_str_tuple(
                payload.get("limit_kind_ids", []), "limit_kind_ids"
            ),
            support_mode=str(payload.get("support_mode", "shared_turn")),
            public_text=(
                None
                if payload.get("public_text") is None
                else str(payload["public_text"])
            ),
        )


@dataclass(frozen=True)
class ReadingBrief:
    question: str
    vocabulary: tuple[PublicTerm, ...]
    facts: tuple[PublicFact, ...]
    evidence: tuple[PublicEvidence, ...]
    claim_scopes: tuple[ClaimScope, ...]
    limits: tuple[PublicLimit, ...]
    prior_answer: str | None = None
    request_view: RequestView | None = None
    findings: tuple[PublicFinding, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "vocabulary": [term.to_dict() for term in self.vocabulary],
            "facts": [fact.to_dict() for fact in self.facts],
            "evidence": [item.to_dict() for item in self.evidence],
            "findings": [finding.to_dict() for finding in self.findings],
            "claim_scopes": [scope.to_dict() for scope in self.claim_scopes],
            "limits": [limit.to_dict() for limit in self.limits],
            "prior_answer": self.prior_answer,
            "request_view": (
                None
                if self.request_view is None
                else self.request_view.to_dict()
            ),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReadingBrief":
        return cls(
            question=str(payload["question"]),
            vocabulary=tuple(
                PublicTerm.from_dict(item) for item in payload.get("vocabulary", [])
            ),
            facts=tuple(
                PublicFact.from_dict(item) for item in payload.get("facts", [])
            ),
            evidence=tuple(
                PublicEvidence.from_dict(item)
                for item in payload.get("evidence", [])
            ),
            findings=tuple(
                PublicFinding.from_dict(item)
                for item in payload.get("findings", [])
            ),
            claim_scopes=tuple(
                ClaimScope.from_dict(item)
                for item in payload.get("claim_scopes", [])
            ),
            limits=tuple(
                PublicLimit.from_dict(item) for item in payload.get("limits", [])
            ),
            prior_answer=(
                None
                if payload.get("prior_answer") is None
                else str(payload["prior_answer"])
            ),
            request_view=(
                None
                if payload.get("request_view") is None
                else RequestView.from_dict(
                    _mapping(payload["request_view"], "request_view")
                )
            ),
        )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HorizonSelection:
    kind_id: str
    start: str | None = None
    end: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"kind_id": self.kind_id, "start": self.start, "end": self.end}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HorizonSelection":
        return cls(
            kind_id=str(payload["kind_id"]),
            start=(None if payload.get("start") is None else str(payload["start"])),
            end=(None if payload.get("end") is None else str(payload["end"])),
        )


@dataclass(frozen=True)
class RequestView:
    """Public, structured scope for the current prepared turn only."""

    subject_refs: tuple[str, ...]
    capability_ids: tuple[str, ...]
    object_id: str
    dimension_ids: tuple[str, ...]
    horizon: HorizonSelection

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_refs": list(self.subject_refs),
            "capability_ids": list(self.capability_ids),
            "object_id": self.object_id,
            "dimension_ids": list(self.dimension_ids),
            "horizon": self.horizon.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RequestView":
        return cls(
            subject_refs=_str_tuple(payload.get("subject_refs", []), "subject_refs"),
            capability_ids=_str_tuple(
                payload.get("capability_ids", []), "capability_ids"
            ),
            object_id=str(payload["object_id"]),
            dimension_ids=_str_tuple(
                payload.get("dimension_ids", []), "dimension_ids"
            ),
            horizon=HorizonSelection.from_dict(
                _mapping(payload["horizon"], "horizon")
            ),
        )


COMPARISON_REQUIREMENTS = ("required", "optional")


@dataclass(frozen=True)
class ComparisonSelection:
    """One requested comparison capability with explicit provenance.

    ``requirement`` distinguishes a comparison the user asked for
    (``required``) from one the host model proposes to enrich the
    answer (``optional``).  The core uses this single field as the
    authoritative source of comparison intent; no parallel list of ids
    exists in the protocol.
    """

    capability_id: str
    requirement: str = "required"

    def __post_init__(self) -> None:
        if not isinstance(self.capability_id, str) or not self.capability_id.strip():
            raise ValueError("ComparisonSelection.capability_id must be non-empty text")
        if self.requirement not in COMPARISON_REQUIREMENTS:
            raise ValueError(
                "ComparisonSelection.requirement must be one of "
                f"{COMPARISON_REQUIREMENTS!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "requirement": self.requirement,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ComparisonSelection":
        return cls(
            capability_id=str(payload["capability_id"]),
            requirement=str(payload.get("requirement") or "required"),
        )


@dataclass(frozen=True)
class IntentSelection:
    subject_refs: tuple[str, ...]
    object_id: str
    dimension_ids: tuple[str, ...]
    horizon: HorizonSelection
    capability_id: str | None = None
    comparisons: tuple[ComparisonSelection, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_refs": list(self.subject_refs),
            "object_id": self.object_id,
            "dimension_ids": list(self.dimension_ids),
            "horizon": self.horizon.to_dict(),
            "capability_id": self.capability_id,
            "comparisons": [item.to_dict() for item in self.comparisons],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "IntentSelection":
        if "comparisons" in payload:
            comparisons = tuple(
                ComparisonSelection.from_dict(_mapping(item, "comparisons"))
                for item in payload.get("comparisons") or ()
            )
        else:
            # Legacy transport: a flat list of comparison capability ids
            # is treated as a set of required comparisons.  The single
            # source of truth is still ``comparisons``; the legacy field
            # is read here only for migration.
            comparisons = tuple(
                ComparisonSelection(
                    capability_id=str(item), requirement="required"
                )
                for item in payload.get("comparison_capability_ids", ())
            )
        return cls(
            subject_refs=_str_tuple(payload.get("subject_refs", []), "subject_refs"),
            object_id=str(payload["object_id"]),
            dimension_ids=_str_tuple(
                payload.get("dimension_ids", []), "dimension_ids"
            ),
            horizon=HorizonSelection.from_dict(
                _mapping(payload["horizon"], "horizon")
            ),
            capability_id=(
                None
                if payload.get("capability_id") is None
                else str(payload["capability_id"])
            ),
            comparisons=comparisons,
        )


@dataclass(frozen=True)
class Describe:
    kind: Literal["describe"] = "describe"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "describe"}


@dataclass(frozen=True)
class Prepare:
    query: str
    intent: IntentSelection
    facts: Mapping[str, Mapping[str, object]]
    state_token: str | None = None
    transition: Literal["correct", "restart"] | None = None
    kind: Literal["prepare"] = "prepare"

    def __post_init__(self) -> None:
        if self.transition is not None and self.transition not in TRANSITIONS:
            raise ValueError("transition must be one of correct/restart")
        facts = _mapping(self.facts, "facts")
        for subject_ref, fields in facts.items():
            if not isinstance(subject_ref, str) or not subject_ref:
                raise ValueError("facts keys must be subject_ref strings")
            _mapping(fields, f"facts[{subject_ref}]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "prepare",
            "query": self.query,
            "intent": self.intent.to_dict(),
            "facts": {
                subject_ref: dict(fields)
                for subject_ref, fields in self.facts.items()
            },
            "state_token": self.state_token,
            "transition": self.transition,
        }


@dataclass(frozen=True)
class Complete:
    state_token: str
    public_copy: str
    kind: Literal["complete"] = "complete"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "complete",
            "state_token": self.state_token,
            "public_copy": self.public_copy,
        }


Command = Describe | Prepare | Complete


def command_from_dict(payload: Mapping[str, Any]) -> Command:
    payload = _mapping(payload, "command")
    kind = payload.get("kind")
    if kind == "describe":
        return Describe()
    if kind == "prepare":
        return Prepare(
            query=str(payload["query"]),
            intent=IntentSelection.from_dict(
                _mapping(payload["intent"], "intent")
            ),
            facts={
                str(subject_ref): dict(_mapping(fields, "facts"))
                for subject_ref, fields in _mapping(
                    payload.get("facts", {}), "facts"
                ).items()
            },
            state_token=(
                None
                if payload.get("state_token") is None
                else str(payload["state_token"])
            ),
            transition=(
                None
                if payload.get("transition") is None
                else str(payload["transition"])  # type: ignore[arg-type]
            ),
        )
    if kind == "complete":
        return Complete(
            state_token=str(payload["state_token"]),
            public_copy=str(payload["public_copy"]),
        )
    raise ValueError(f"unknown command kind: {kind!r}")


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Described:
    protocol_version: str
    manifest_digest: str
    capabilities: tuple[CapabilityView, ...]
    transition_ids: tuple[str, ...] = TRANSITIONS
    kind: Literal["described"] = "described"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "described",
            "protocol_version": self.protocol_version,
            "manifest_digest": self.manifest_digest,
            "capabilities": [view.to_dict() for view in self.capabilities],
            "transition_ids": list(self.transition_ids),
        }


@dataclass(frozen=True)
class Prepared:
    state_token: str
    brief: ReadingBrief
    kind: Literal["prepared"] = "prepared"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "prepared",
            "state_token": self.state_token,
            "brief": self.brief.to_dict(),
        }


@dataclass(frozen=True)
class Accepted:
    state_token: str
    public_copy: str
    kind: Literal["accepted"] = "accepted"

    def __post_init__(self) -> None:
        _require_non_empty_text(self.public_copy, "Accepted.public_copy")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "accepted",
            "state_token": self.state_token,
            "public_copy": self.public_copy,
            "terminal": True,
            "completion_committed": True,
        }


@dataclass(frozen=True)
class Stopped:
    reason: Literal["need_input", "unsupported", "conflict", "error"]
    public_copy: str
    state_token: str | None = None
    input_request: InputRequest | None = None
    failure: RuntimeFailure | None = None
    kind: Literal["stopped"] = "stopped"

    def __post_init__(self) -> None:
        if self.reason not in STOPPED_REASONS:
            raise ValueError(f"unknown stopped reason: {self.reason!r}")
        _require_non_empty_text(self.public_copy, "Stopped.public_copy")
        if self.input_request is not None and self.reason != "need_input":
            raise ValueError("input_request is only valid for need_input")
        if self.reason == "error" and self.failure is None:
            object.__setattr__(
                self,
                "failure",
                runtime_failure("runtime.internal_error"),
            )
        if self.reason != "error" and self.failure is not None:
            raise ValueError("failure is only valid for Stopped.error")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "stopped",
            "reason": self.reason,
            "public_copy": self.public_copy,
            "state_token": self.state_token,
            "input_request": (
                None
                if self.input_request is None
                else self.input_request.to_dict()
            ),
            "failure": None if self.failure is None else self.failure.to_dict(),
            "continuation_allowed": self.reason == "need_input",
            "terminal": self.reason != "need_input",
            "completion_committed": False,
        }


Result = Described | Prepared | Accepted | Stopped


def result_from_dict(payload: Mapping[str, Any]) -> Result:
    payload = _mapping(payload, "result")
    kind = payload.get("kind")
    if kind == "described":
        return Described(
            protocol_version=str(payload["protocol_version"]),
            manifest_digest=str(payload["manifest_digest"]),
            capabilities=tuple(
                CapabilityView.from_dict(item)
                for item in payload.get("capabilities", [])
            ),
        )
    if kind == "prepared":
        return Prepared(
            state_token=str(payload["state_token"]),
            brief=ReadingBrief.from_dict(_mapping(payload["brief"], "brief")),
        )
    if kind == "accepted":
        return Accepted(
            state_token=str(payload["state_token"]),
            public_copy=str(payload["public_copy"]),
        )
    if kind == "stopped":
        return Stopped(
            reason=str(payload["reason"]),  # type: ignore[arg-type]
            public_copy=str(payload["public_copy"]),
            state_token=(
                None
                if payload.get("state_token") is None
                else str(payload["state_token"])
            ),
            input_request=(
                None
                if payload.get("input_request") is None
                else InputRequest.from_dict(
                    _mapping(payload["input_request"], "input_request")
                )
            ),
            failure=(
                None
                if payload.get("failure") is None
                else RuntimeFailure.from_dict(
                    _mapping(payload["failure"], "failure")
                )
            ),
        )
    raise ValueError(f"unknown result kind: {kind!r}")
