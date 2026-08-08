import argparse
import asyncio
import json
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class WorkItem:
    id: str
    claim_token: str | None = None
    lease_generation: int | None = None


class WorkSource(Protocol):
    async def claim_one(self) -> WorkItem | None: ...


class WorkProcessor(Protocol):
    async def process(self, item: WorkItem) -> None: ...


@dataclass(slots=True)
class EmptyWorkSource:
    claim_count: int = 0

    async def claim_one(self) -> WorkItem | None:
        self.claim_count += 1
        return None


@dataclass(slots=True)
class InMemoryWorkSource:
    items: list[WorkItem]

    async def claim_one(self) -> WorkItem | None:
        if not self.items:
            return None
        return self.items.pop(0)


@dataclass(slots=True)
class RecordingProcessor:
    processed_ids: list[str] = field(default_factory=list)

    async def process(self, item: WorkItem) -> None:
        self.processed_ids.append(item.id)


class NoopProcessor:
    async def process(self, item: WorkItem) -> None:
        del item


@dataclass(slots=True)
class Worker:
    source: WorkSource
    processor: WorkProcessor = field(default_factory=NoopProcessor)

    async def run_once(self) -> bool:
        item = await self.source.claim_one()
        if item is None:
            return False
        await self.processor.process(item)
        return True


def build_worker(*, source: WorkSource, processor: WorkProcessor) -> Worker:
    return Worker(source=source, processor=processor)


async def run_forever(worker: Worker, poll_interval: float = 2.0) -> None:
    while True:
        processed = await worker.run_once()
        if not processed:
            await asyncio.sleep(poll_interval)


def parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FateRadar background worker")
    parser.add_argument("--once", action="store_true", help="Claim at most one task and exit")
    parser.add_argument("--poll-interval", type=float, default=2.0)
    return parser.parse_args(arguments)


ConfiguredWorkerFactory = Callable[[], AbstractAsyncContextManager[Worker]]


async def _run_configured_worker(worker: Worker, args: argparse.Namespace) -> int:
    if args.once:
        processed = await worker.run_once()
        print(json.dumps({"event": "worker_iteration", "processed": processed}))
        return 0
    await run_forever(worker, poll_interval=args.poll_interval)
    return 0


async def async_main(
    arguments: Sequence[str] | None = None,
    *,
    configured_worker_factory: ConfiguredWorkerFactory | None = None,
) -> int:
    args = parse_args(arguments)
    if configured_worker_factory is None:
        from worker.readings import configured_reading_worker

        configured_worker_factory = configured_reading_worker
    async with configured_worker_factory() as worker:
        return await _run_configured_worker(worker, args)


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
