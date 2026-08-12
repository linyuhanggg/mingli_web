from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from app.adapters.runtime import (
    FakeMingliRuntimeAdapter,
    MingliRuntime,
    build_runtime_startup_gate,
)
from app.config import Settings


class ChartRuntimeTopologyError(RuntimeError):
    """The requested chart Runtime topology is not admitted in this environment."""


class ChartRuntimeLease:
    """Own one chart Runtime and, for one-shot mode, its isolated state root."""

    def __init__(
        self,
        runtime: MingliRuntime,
        *,
        state_root: Path | None = None,
        cleanup: Callable[[], None] | None = None,
    ) -> None:
        self.runtime = runtime
        self.state_root = state_root
        self._cleanup = cleanup
        self._closed = False

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._cleanup is not None:
            self._cleanup()


class ChartRuntimeFactory(Protocol):
    async def startup(self) -> None: ...

    async def open(self) -> ChartRuntimeLease: ...

    async def aclose(self) -> None: ...


class StaticChartRuntimeFactory:
    """Inject a scripted Runtime in contract tests without owning its lifecycle."""

    def __init__(self, runtime: MingliRuntime) -> None:
        self._runtime = runtime

    async def startup(self) -> None:
        return None

    async def open(self) -> ChartRuntimeLease:
        return ChartRuntimeLease(self._runtime)

    async def aclose(self) -> None:
        return None


class IsolatedChartRuntimeFactory:
    """Admit 5.1 once, then give each sync chart an isolated state root."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._startup_lock = asyncio.Lock()
        self._ready = False

    async def startup(self) -> None:
        if self._settings.environment == "production":
            raise ChartRuntimeTopologyError(
                "production sync charts require the single-writer Runtime topology"
            )
        if self._ready:
            return
        async with self._startup_lock:
            if self._ready:
                return
            if self._settings.runtime_adapter == "one-shot":
                lease = self._new_one_shot_lease()
                try:
                    isolated = self._settings.model_copy(
                        update={"runtime_state_root": lease.state_root}
                    )
                    await build_runtime_startup_gate(isolated).startup()
                finally:
                    await lease.aclose()
            self._ready = True

    async def open(self) -> ChartRuntimeLease:
        await self.startup()
        if self._settings.runtime_adapter == "one-shot":
            return self._new_one_shot_lease()
        return ChartRuntimeLease(FakeMingliRuntimeAdapter())

    async def aclose(self) -> None:
        return None

    def _new_one_shot_lease(self) -> ChartRuntimeLease:
        temporary = TemporaryDirectory(prefix="mingli-chart-")
        state_root = Path(temporary.name)
        os.chmod(state_root, 0o700)
        isolated = self._settings.model_copy(
            update={"runtime_state_root": state_root}
        )
        try:
            runtime = build_runtime_startup_gate(isolated).runtime
        except BaseException:
            temporary.cleanup()
            raise
        return ChartRuntimeLease(
            runtime,
            state_root=state_root,
            cleanup=temporary.cleanup,
        )
