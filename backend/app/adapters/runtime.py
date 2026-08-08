from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RuntimeDescription:
    protocol_version: str
    capabilities: tuple[str, ...]
    production_ready: bool


class MingliRuntimeAdapter(Protocol):
    async def describe(self) -> RuntimeDescription: ...


class FakeMingliRuntimeAdapter:
    """Contract-test discovery result; it performs no命理 calculation."""

    async def describe(self) -> RuntimeDescription:
        return RuntimeDescription(
            protocol_version="fake-v1",
            capabilities=("bazi", "fortune", "liuyao"),
            production_ready=False,
        )
