#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT / "infra" / "mingli-runtime"
EXPECTED_COMMIT = "494ce0bba174a77800daf9b9c38ce9c9166d9a94"
EXPECTED_RELEASE_MANIFEST_SHA256 = (
    "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_local_gate() -> ModuleType:
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        importlib.invalidate_caches()
        sys.modules.pop("local_gate", None)
        return importlib.import_module("local_gate")
    finally:
        sys.path.remove(str(RUNTIME_DIR))


def load_local_verifier() -> ModuleType:
    sys.path.insert(0, str(RUNTIME_DIR))
    try:
        importlib.invalidate_caches()
        sys.modules.pop("verify_local_full", None)
        return importlib.import_module("verify_local_full")
    finally:
        sys.path.remove(str(RUNTIME_DIR))


def write_prepared_inputs(tmp_path: Path) -> tuple[Path, str, dict[str, Any]]:
    source_root = tmp_path / "source"
    scripts = source_root / "scripts"
    scripts.mkdir(parents=True)
    runner = scripts / "run_test_suite.py"
    runner.write_text(
        "raise SystemExit('scripted test must not execute')\n", encoding="utf-8"
    )
    lock = source_root / "requirements-runtime.lock"
    lock.write_text("locked\n", encoding="utf-8")
    research_root = tmp_path / "research"
    research_root.mkdir()
    python = Path(sys.executable).resolve(strict=True)
    payload = {
        "schema": "mingli-prepared-inputs-v1",
        "source": {
            "root": str(source_root),
            "commit": EXPECTED_COMMIT,
            "release_manifest_sha256": EXPECTED_RELEASE_MANIFEST_SHA256,
        },
        "research": {
            "root": str(research_root),
            "commit": EXPECTED_COMMIT,
        },
        "native_runtime": {
            "python": str(python),
            "python_sha256": sha256_file(python),
            "requirements_lock": str(lock),
            "requirements_lock_sha256": sha256_file(lock),
        },
        "bindings": [
            {
                "path": str(runner),
                "kind": "file",
                "sha256": sha256_file(runner),
            },
            {
                "path": str(lock),
                "kind": "file",
                "sha256": sha256_file(lock),
            },
        ],
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path = tmp_path / "prepared-inputs.json"
    path.write_bytes(raw)
    return path, sha256_bytes(raw), payload


class ScriptedExecution:
    def __init__(
        self,
        module: ModuleType,
        *,
        stdout: str,
        elapsed_seconds: float,
        returncode: int = 0,
        on_run: Callable[[], None] | None = None,
    ) -> None:
        self.module = module
        self.stdout = stdout
        self.elapsed_seconds = elapsed_seconds
        self.returncode = returncode
        self.on_run = on_run
        self.commands: list[Any] = []

    def run(self, command: Any) -> Any:
        self.commands.append(command)
        if self.on_run is not None:
            self.on_run()
        return self.module.CommandResult(
            stdout=self.stdout.encode(),
            stderr=b"",
            returncode=self.returncode,
            started_monotonic=100.0,
            finished_monotonic=100.0 + self.elapsed_seconds,
        )


def native_request(
    gate_module: ModuleType,
    tmp_path: Path,
    *,
    deadline_seconds: int = 600,
    slots: int = 10,
) -> tuple[Any, dict[str, Any]]:
    manifest_path, manifest_sha256, payload = write_prepared_inputs(tmp_path)
    request = gate_module.LocalFullRequest(
        profile="native-full",
        prepared_inputs=gate_module.PreparedInputsRef(
            path=manifest_path,
            sha256=manifest_sha256,
        ),
        output_parent=tmp_path / "output",
        deadline_seconds=deadline_seconds,
        slots=slots,
    )
    return request, payload


def complete_summary(*, elapsed_seconds: float = 434.62) -> str:
    return (
        "test plan: targets=126 modules=93 workers=10 parallel=100 serial=26\n"
        "summary: targets=126 modules=93 tests=1584 "
        f"failed_modules=0 elapsed={elapsed_seconds:.2f}s\n"
    )


def assert_nothing_published(output_parent: Path) -> None:
    assert not output_parent.exists() or list(output_parent.iterdir()) == []


def test_native_full_accepts_only_complete_suite_under_budget(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    request, payload = native_request(gate_module, tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=434.62,
    )

    result = gate_module.LocalFullGate(execution).run(request)

    assert result.profile == "native-full"
    assert result.elapsed_seconds == 434.62
    assert len(result.timeline) == 1
    assert result.timeline[0].command_id == "native-release-regression"
    assert result.profile_report.name == "native-full-5.1.json"
    assert result.profile_report.is_file()
    assert len(execution.commands) == 1
    command = execution.commands[0]
    source_root = Path(payload["source"]["root"])
    assert command.argv == (
        payload["native_runtime"]["python"],
        "-B",
        str(source_root / "scripts" / "run_test_suite.py"),
        "--jobs",
        "10",
        "--research-root",
        payload["research"]["root"],
    )
    assert command.cwd == source_root
    assert command.shell is False


@pytest.mark.parametrize(
    "summary",
    [
        "no authoritative summary\n",
        "summary: targets=125 modules=93 tests=1584 failed_modules=0 elapsed=1.00s\n",
        "summary: targets=126 modules=92 tests=1584 failed_modules=0 elapsed=1.00s\n",
        "summary: targets=126 modules=93 tests=1583 failed_modules=0 elapsed=1.00s\n",
        "summary: targets=126 modules=93 tests=1584 failed_modules=1 elapsed=1.00s\n",
    ],
)
def test_native_full_rejects_incomplete_or_missing_summary(
    tmp_path: Path,
    summary: str,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=summary,
        elapsed_seconds=1.0,
    )

    with pytest.raises(gate_module.GateRejected):
        gate_module.LocalFullGate(execution).run(request)

    assert_nothing_published(request.output_parent)


@pytest.mark.parametrize(
    ("returncode", "actual_elapsed", "summary_elapsed"),
    [
        (1, 1.0, 1.0),
        (0, 600.001, 1.0),
        (0, 1.0, 600.01),
    ],
)
def test_native_full_rejects_failure_or_timeout(
    tmp_path: Path,
    returncode: int,
    actual_elapsed: float,
    summary_elapsed: float,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(elapsed_seconds=summary_elapsed),
        elapsed_seconds=actual_elapsed,
        returncode=returncode,
    )

    with pytest.raises(gate_module.GateRejected):
        gate_module.LocalFullGate(execution).run(request)

    assert_nothing_published(request.output_parent)


@pytest.mark.parametrize(
    ("deadline_seconds", "slots"),
    [(601, 10), (600, 11), (0, 10), (600, 0)],
)
def test_native_full_cannot_relax_or_disable_resource_limits(
    tmp_path: Path,
    deadline_seconds: int,
    slots: int,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(
        gate_module,
        tmp_path,
        deadline_seconds=deadline_seconds,
        slots=slots,
    )
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=1.0,
    )

    with pytest.raises(gate_module.GateRejected):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []
    assert_nothing_published(request.output_parent)


def test_native_full_rejects_manifest_sha_mismatch(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    request = gate_module.LocalFullRequest(
        profile=request.profile,
        prepared_inputs=gate_module.PreparedInputsRef(
            path=request.prepared_inputs.path,
            sha256="0" * 64,
        ),
        output_parent=request.output_parent,
    )
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=1.0,
    )

    with pytest.raises(gate_module.GateRejected, match="manifest SHA-256 mismatch"):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []
    assert_nothing_published(request.output_parent)


def test_native_full_rejects_input_drift_during_run(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    request, payload = native_request(gate_module, tmp_path)
    lock = Path(payload["native_runtime"]["requirements_lock"])
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=1.0,
        on_run=lambda: lock.write_text("drifted\n", encoding="utf-8"),
    )

    with pytest.raises(gate_module.GateRejected, match="changed during run"):
        gate_module.LocalFullGate(execution).run(request)

    assert_nothing_published(request.output_parent)


def test_subprocess_execution_runs_fixed_argv_without_shell(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    execution = gate_module.SubprocessExecution()
    command = gate_module.GateCommand(
        command_id="fixed-argv-probe",
        argv=(
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr)",
        ),
        cwd=tmp_path,
        timeout_seconds=5,
        slots=1,
        stdout_limit_bytes=1024,
        stderr_limit_bytes=1024,
    )

    result = execution.run(command)

    assert result.returncode == 0
    assert result.stdout == b"out\n"
    assert result.stderr == b"err\n"
    assert result.finished_monotonic >= result.started_monotonic


def test_subprocess_execution_enforces_output_cap_and_kills_process_group(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    child_pid_path = tmp_path / "child.pid"
    program = (
        "import pathlib, subprocess, sys, time; "
        "child = subprocess.Popen([sys.executable, '-c', "
        "'import time; time.sleep(30)']); "
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(child.pid)); "
        "sys.stdout.write('x' * 4096); sys.stdout.flush(); time.sleep(30)"
    )
    command = gate_module.GateCommand(
        command_id="output-cap-probe",
        argv=(sys.executable, "-c", program),
        cwd=tmp_path,
        timeout_seconds=2,
        slots=1,
        stdout_limit_bytes=64,
        stderr_limit_bytes=64,
    )
    started = time.monotonic()

    with pytest.raises(gate_module.ExecutionFailure, match="stdout exceeded"):
        gate_module.SubprocessExecution().run(command)

    assert time.monotonic() - started < 1.0
    child_pid = int(child_pid_path.read_text())
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.02)
    else:
        pytest.fail("output-cap child process survived process-group cleanup")


def test_native_full_wraps_execution_failure_and_removes_staging(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)

    class TimedOutExecution:
        def run(self, command: Any) -> Any:
            raise gate_module.ExecutionFailure(
                f"{command.command_id} exceeded {command.timeout_seconds}s"
            )

    with pytest.raises(gate_module.GateRejected, match="native execution failed"):
        gate_module.LocalFullGate(TimedOutExecution()).run(request)

    assert_nothing_published(request.output_parent)


def test_native_full_cli_is_the_standard_command(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gate_module = load_local_gate()
    manifest_path, manifest_sha256, _ = write_prepared_inputs(tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=434.62,
    )

    exit_code = gate_module.main(
        [
            "native-full",
            "--prepared-inputs",
            str(manifest_path),
            "--prepared-inputs-sha256",
            manifest_sha256,
            "--output-parent",
            str(tmp_path / "output"),
        ],
        execution=execution,
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["profile"] == "native-full"
    assert output["elapsed_seconds"] == 434.62
    assert Path(output["profile_report"]).is_file()


def test_native_reports_are_independently_revalidated(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    request, _ = native_request(gate_module, tmp_path)
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=434.62,
    )
    result = gate_module.LocalFullGate(execution).run(request)
    verifier = load_local_verifier()

    verified = verifier.validate_native_run(
        result.profile_report,
        result.local_summary,
        expected_prepared_inputs_sha256=request.prepared_inputs.sha256,
    )

    assert verified["profile"] == "native-full"
    assert verified["elapsed_seconds"] == 434.62


def test_prepared_inputs_requires_external_research_root(tmp_path: Path) -> None:
    gate_module = load_local_gate()
    manifest_path, _, payload = write_prepared_inputs(tmp_path)
    payload["research"]["root"] = payload["source"]["root"]
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest_path.write_bytes(raw)
    request = gate_module.LocalFullRequest(
        profile="native-full",
        prepared_inputs=gate_module.PreparedInputsRef(
            path=manifest_path,
            sha256=sha256_bytes(raw),
        ),
        output_parent=tmp_path / "output",
    )
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=1.0,
    )

    with pytest.raises(
        gate_module.GateRejected, match="research root must be external"
    ):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []


def test_prepared_inputs_rejects_fulltext_inside_source_projection(
    tmp_path: Path,
) -> None:
    gate_module = load_local_gate()
    request, payload = native_request(gate_module, tmp_path)
    fulltext = Path(payload["source"]["root"]) / "references" / "fulltext"
    fulltext.mkdir(parents=True)
    (fulltext / "book.md").write_text("external research bytes\n", encoding="utf-8")
    execution = ScriptedExecution(
        gate_module,
        stdout=complete_summary(),
        elapsed_seconds=1.0,
    )

    with pytest.raises(
        gate_module.GateRejected, match="source projection contains fulltext"
    ):
        gate_module.LocalFullGate(execution).run(request)

    assert execution.commands == []
