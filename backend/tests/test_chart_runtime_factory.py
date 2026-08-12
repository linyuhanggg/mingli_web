import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


@pytest.mark.asyncio
async def test_one_shot_chart_runtime_uses_private_ephemeral_roots(
    monkeypatch: pytest.MonkeyPatch,
    test_settings: Any,
    tmp_path: Path,
) -> None:
    from app.charts import runtime as chart_runtime

    persistent_worker_root = tmp_path / "worker-state"
    persistent_worker_root.mkdir(mode=0o700)
    settings = test_settings.model_copy(
        update={
            "runtime_adapter": "one-shot",
            "runtime_launcher_path": Path("/opt/runtime/launcher"),
            "runtime_python_path": Path("/opt/runtime/python"),
            "runtime_release_root": Path("/opt/runtime/release"),
            "runtime_state_root": persistent_worker_root,
            "runtime_expected_manifest_digest": "a" * 64,
            "runtime_expected_capability_shape_sha256": "b" * 64,
        }
    )
    opened_roots: list[Path] = []

    class RecordingGate:
        def __init__(self, state_root: Path) -> None:
            self.runtime = SimpleNamespace(state_root=state_root)

        async def startup(self) -> None:
            state_root = self.runtime.state_root
            assert state_root.exists()
            assert stat.S_IMODE(state_root.stat().st_mode) == 0o700

    def recording_gate_factory(isolated_settings: Any) -> RecordingGate:
        state_root = isolated_settings.runtime_state_root
        assert isinstance(state_root, Path)
        assert state_root != persistent_worker_root
        opened_roots.append(state_root)
        return RecordingGate(state_root)

    monkeypatch.setattr(
        chart_runtime,
        "build_runtime_startup_gate",
        recording_gate_factory,
    )

    factory = chart_runtime.IsolatedChartRuntimeFactory(settings)
    await factory.startup()

    admission_root = opened_roots[0]
    assert not admission_root.exists()

    lease = await factory.open()
    request_root = lease.state_root
    assert request_root is not None
    assert request_root != admission_root
    assert request_root.exists()
    assert persistent_worker_root.exists()

    await lease.aclose()

    assert not request_root.exists()
    assert persistent_worker_root.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["staging", "production"])
async def test_deployed_environments_refuse_disposable_api_runtime_roots(
    test_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    from app.charts import runtime as chart_runtime

    gate_calls = 0

    def unexpected_gate(_settings: Any) -> object:
        nonlocal gate_calls
        gate_calls += 1
        raise AssertionError("deployed environments must reject this topology first")

    monkeypatch.setattr(chart_runtime, "build_runtime_startup_gate", unexpected_gate)
    factory = chart_runtime.IsolatedChartRuntimeFactory(
        test_settings.model_copy(
            update={"environment": environment, "runtime_adapter": "one-shot"}
        )
    )

    with pytest.raises(
        chart_runtime.ChartRuntimeTopologyError,
        match="single-writer",
    ):
        await factory.startup()

    assert gate_calls == 0
