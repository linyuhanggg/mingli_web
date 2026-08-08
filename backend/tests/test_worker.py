import importlib


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
