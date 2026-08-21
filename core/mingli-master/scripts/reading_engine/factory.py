"""Production assembly: catalog-driven provider adapters behind one engine.

Every provider-specific behaviour (input assembly, enrichment, evidence
compilation, public projection) lives inside the adapters resolved from the
bundled manifests.  This module only wires storage, registry and runtime
context together — it names no provider and owns no domain constant.
"""

from __future__ import annotations

from pathlib import Path

from .catalog import CatalogLoader
from .provider_registry import ProviderRegistry
from .runtime_context import RuntimeContext, build_runtime_context
from .storage import AtomicReadingStore
from .turns import TurnEngine


def build_production_engine(
    *,
    skill_dir: str | Path,
    store_root: str | Path,
    runtime_context: RuntimeContext | None = None,
) -> TurnEngine:
    root = Path(skill_dir).resolve()
    context = runtime_context or build_runtime_context()
    catalog = CatalogLoader(root / "resources/runtime").load()
    providers = ProviderRegistry(
        catalog,
        skill_root=root,
        construction={"skill_dir": root},
    ).adapters()
    return TurnEngine(
        store=AtomicReadingStore(store_root),
        providers=providers,
        catalog=catalog,
        runtime_context=context,
    )


__all__ = ["build_production_engine"]
