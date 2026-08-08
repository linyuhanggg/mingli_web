import importlib
from contextlib import asynccontextmanager


async def test_worker_iteration_is_idle_when_no_task_exists() -> None:
    worker_module = importlib.import_module("worker.main")
    source = worker_module.EmptyWorkSource()
    worker = worker_module.Worker(source=source)

    processed = await worker.run_once()

    assert processed is False
    assert source.claim_count == 1


async def test_worker_processes_one_claimed_task() -> None:
    worker_module = importlib.import_module("worker.main")
    source = worker_module.InMemoryWorkSource([worker_module.WorkItem(id="task-1")])
    processor = worker_module.RecordingProcessor()
    worker = worker_module.Worker(source=source, processor=processor)

    processed = await worker.run_once()

    assert processed is True
    assert processor.processed_ids == ["task-1"]


def test_worker_dependency_builder_keeps_domain_wiring_out_of_the_loop() -> None:
    worker_module = importlib.import_module("worker.main")
    source = worker_module.InMemoryWorkSource([])
    processor = worker_module.RecordingProcessor()

    worker = worker_module.build_worker(source=source, processor=processor)

    assert worker.source is source
    assert worker.processor is processor


async def test_async_main_uses_the_configured_worker_context(
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    worker_module = importlib.import_module("worker.main")
    source = worker_module.InMemoryWorkSource([worker_module.WorkItem(id="reading-1")])
    processor = worker_module.RecordingProcessor()
    events: list[str] = []

    @asynccontextmanager
    async def configured_worker():  # type: ignore[no-untyped-def]
        events.append("entered")
        yield worker_module.build_worker(source=source, processor=processor)
        events.append("closed")

    result = await worker_module.async_main(
        ["--once"],
        configured_worker_factory=configured_worker,
    )

    assert result == 0
    assert processor.processed_ids == ["reading-1"]
    assert events == ["entered", "closed"]
    assert '"processed": true' in capsys.readouterr().out
