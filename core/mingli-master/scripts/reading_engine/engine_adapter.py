"""Minimal internal protocol for version-pinned chart engines.

The public Runtime lifecycle remains ``describe / prepare / complete``.  This
module is a deeper Provider-owned seam: an owned normalized request becomes a
private engine request/output and is projected into one art-specific nominal
Canonical Facts type.  Private engine values and exceptions are intentionally
absent from :class:`EngineAdapterResult`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, runtime_checkable

from fact_contracts.common import EngineProvenance


NormalizedRequestT = TypeVar("NormalizedRequestT")
PrivateEngineRequestT = TypeVar("PrivateEngineRequestT")
PrivateEngineOutputT = TypeVar("PrivateEngineOutputT")
CanonicalFactsT = TypeVar("CanonicalFactsT")


class EngineAdapterError(RuntimeError):
    """A private engine failure normalized at the Provider-internal seam."""

    def __init__(self, art_id: str, code: str) -> None:
        super().__init__(f"{art_id} engine adapter failed ({code})")
        self.art_id = art_id
        self.code = code


@dataclass(frozen=True)
class EngineAdapterResult(Generic[CanonicalFactsT]):
    """The only value allowed to leave an Engine Adapter invocation."""

    canonical_facts: CanonicalFactsT
    provenance: EngineProvenance

    def __post_init__(self) -> None:
        bound = getattr(self.canonical_facts, "provenance", None)
        if bound != self.provenance:
            raise EngineAdapterError("unknown", "provenance_binding_mismatch")


@runtime_checkable
class EngineAdapter(Protocol[NormalizedRequestT, CanonicalFactsT]):
    """Small public face of a Provider-internal chart-engine adapter."""

    art_id: str

    def adapt(
        self,
        request: NormalizedRequestT,
    ) -> EngineAdapterResult[CanonicalFactsT]: ...


class EngineAdapterBase(
    Generic[
        NormalizedRequestT,
        PrivateEngineRequestT,
        PrivateEngineOutputT,
        CanonicalFactsT,
    ]
):
    """Template that keeps private request/output local to one stack frame."""

    art_id = ""

    def adapt(
        self,
        request: NormalizedRequestT,
    ) -> EngineAdapterResult[CanonicalFactsT]:
        # Request and policy/provenance validation are owned by the adapter.
        # Finish both before crossing into the third-party invocation so their
        # actionable deterministic errors cannot be confused with engine
        # failures.
        engine_request = self._build_engine_request(request)
        provenance = self._provenance(request)

        engine_output: PrivateEngineOutputT
        try:
            engine_output = self._invoke_engine(engine_request)
        except Exception:
            engine_failed = True
        else:
            engine_failed = False

        # Raise only after leaving the ``except`` suite.  This deliberately
        # discards exception chaining as well as the original message/type, so
        # private engine payloads cannot remain reachable through __cause__ or
        # __context__.
        if engine_failed:
            raise EngineAdapterError(
                self.art_id or "unknown",
                "engine_execution_failed",
            )

        try:
            canonical_facts = self._project_engine_output(
                request,
                engine_output,
                provenance,
            )
            return EngineAdapterResult(
                canonical_facts=canonical_facts,
                provenance=provenance,
            )
        except EngineAdapterError:
            raise
        except Exception as exc:
            raise EngineAdapterError(
                self.art_id or "unknown",
                "canonical_projection_failed",
            ) from exc

    def _build_engine_request(
        self,
        request: NormalizedRequestT,
    ) -> PrivateEngineRequestT:
        raise NotImplementedError

    def _invoke_engine(
        self,
        request: PrivateEngineRequestT,
    ) -> PrivateEngineOutputT:
        raise NotImplementedError

    def _project_engine_output(
        self,
        request: NormalizedRequestT,
        output: PrivateEngineOutputT,
        provenance: EngineProvenance,
    ) -> CanonicalFactsT:
        raise NotImplementedError

    def _provenance(self, request: NormalizedRequestT) -> EngineProvenance:
        raise NotImplementedError


__all__ = [
    "EngineAdapter",
    "EngineAdapterBase",
    "EngineAdapterError",
    "EngineAdapterResult",
]
