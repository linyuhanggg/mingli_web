"""Public API for the Mingli single-reading transaction engine.

Heavy runtime modules are resolved lazily so importing the typed contracts does
not initialize provider routing (which itself depends on those contracts).
"""

from .contracts import (
    AcceptedReading,
    CalculationResult,
    FactExtensionResult,
    InternalFailure,
    NeedUserFact,
    NotApplicable,
    PreparedReading,
    ReadingRequest,
    UnsupportedDimension,
)


def __getattr__(name: str):
    if name == "build_production_engine":
        from .factory import build_production_engine

        return build_production_engine
    raise AttributeError(name)

__all__ = [
    "AcceptedReading",
    "CalculationResult",
    "FactExtensionResult",
    "InternalFailure",
    "NeedUserFact",
    "NotApplicable",
    "PreparedReading",
    "ReadingRequest",
    "UnsupportedDimension",
    "build_production_engine",
]
