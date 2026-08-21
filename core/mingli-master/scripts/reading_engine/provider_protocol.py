"""One deep seam for every reading provider adapter.

External code only sees a descriptor plus one ``prepare`` call. Concrete
adapters own their private algorithms, resources, default-profile handling
and privacy projection; nothing here names a concrete provider or domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from .catalog import ProviderDescriptor


class ProviderActionError(ValueError):
    """A provider-owned lifecycle rule maps to one public failure code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ProviderRequest:
    """Structured request already resolved to one capability."""

    query: str
    subject_refs: tuple[str, ...]
    object_id: str
    dimension_ids: tuple[str, ...]
    horizon: Mapping[str, Any]
    facts: Mapping[str, Mapping[str, Any]]
    transition: str | None = None
    reading_id: str | None = None
    version: int = 1
    scope_subject_refs: tuple[str, ...] = ()
    comparisons: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class ResolvedComparison:
    """One per-turn comparison binding without mutating the catalog.

    ``descriptor`` is absent only for an optional comparison that failed
    structural validation.  Required structural failures are returned to the
    caller before the engine is invoked.
    """

    capability_id: str
    requirement: str
    descriptor: ProviderDescriptor | None
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class ProviderContext:
    """Generic dependencies injected when the deep module is constructed."""

    now_iso: str | None = None
    default_timezone: str | None = None
    subject_facts: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    prior_lineage: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ProviderNeedInput:
    missing_input_groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ProviderUnsupported:
    reason_id: str


@dataclass(frozen=True)
class ProviderPreparation:
    calculation: Any
    public_facts: tuple[Any, ...]
    fact_index: tuple[Any, ...]
    evidence_plan: Mapping[str, Any]
    claim_scopes: tuple[Any, ...]
    limits: tuple[Any, ...]
    provider_id: str
    provider_version: str
    subject_ref: str = ""
    capability_id: str = ""
    independent_lineage_id: str = ""
    request_view: Mapping[str, Any] = field(default_factory=dict)
    findings: tuple[Any, ...] = ()
    members: tuple["ProviderPreparation", ...] = ()


@runtime_checkable
class ProviderAdapter(Protocol):
    @property
    def descriptor(self) -> ProviderDescriptor: ...

    def prepare(
        self,
        request: ProviderRequest,
        context: ProviderContext,
    ) -> ProviderPreparation | ProviderNeedInput | ProviderUnsupported: ...
