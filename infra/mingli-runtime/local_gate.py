#!/usr/bin/env python3
"""Run fail-closed local Mingli V5.1 test profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import secrets
import selectors
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NoReturn, Protocol

import prepared_inputs
import verify_local_full

LocalProfile = Literal["native-full", "linux-certify"]
NATIVE_SUMMARY_RE = re.compile(
    r"^summary: targets=(\d+) modules=(\d+) tests=(\d+) "
    r"failed_modules=(\d+) elapsed=(\d+(?:\.\d+)?)s$"
)
MAX_DEADLINE_SECONDS = 600
MAX_SLOTS = 10
MAX_STDOUT_BYTES = 8 * 1024 * 1024
MAX_STDERR_BYTES = 8 * 1024 * 1024


class GateRejected(RuntimeError):
    """The local run cannot publish admissible evidence."""


class ExecutionFailure(RuntimeError):
    """A fixed local command could not complete within its boundary."""


def _fail(message: str) -> NoReturn:
    raise GateRejected(message)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class PreparedInputsRef:
    path: Path
    sha256: str


@dataclass(frozen=True)
class LocalFullRequest:
    profile: LocalProfile
    prepared_inputs: PreparedInputsRef
    output_parent: Path
    deadline_seconds: int = MAX_DEADLINE_SECONDS
    slots: int = MAX_SLOTS


@dataclass(frozen=True)
class GateCommand:
    command_id: str
    argv: tuple[str, ...]
    cwd: Path
    timeout_seconds: float
    slots: int
    stdout_limit_bytes: int = MAX_STDOUT_BYTES
    stderr_limit_bytes: int = MAX_STDERR_BYTES
    shell: bool = False


@dataclass(frozen=True)
class CommandResult:
    stdout: bytes
    stderr: bytes
    returncode: int
    started_monotonic: float
    finished_monotonic: float


@dataclass(frozen=True)
class TimelineEntry:
    command_id: str
    slots: int
    started_monotonic: float
    finished_monotonic: float
    exit_code: int


@dataclass(frozen=True)
class LocalFullResult:
    profile: LocalProfile
    profile_report: Path
    local_summary: Path | None
    timeline: tuple[TimelineEntry, ...]
    elapsed_seconds: float


class Execution(Protocol):
    def run(self, command: GateCommand) -> CommandResult: ...


class SubprocessExecution:
    """Execute a fixed argv in a disposable process group."""

    @staticmethod
    def _terminate_group(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if process.poll() is None:
            process.wait(timeout=2)

    def run(self, command: GateCommand) -> CommandResult:
        if command.shell:
            raise ExecutionFailure("shell execution is forbidden")
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                list(command.argv),
                cwd=command.cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                start_new_session=True,
            )
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            raise ExecutionFailure(f"{command.command_id} could not start") from exc
        assert process.stdout is not None
        assert process.stderr is not None
        streams = {
            "stdout": process.stdout,
            "stderr": process.stderr,
        }
        limits = {
            "stdout": command.stdout_limit_bytes,
            "stderr": command.stderr_limit_bytes,
        }
        buffers = {
            "stdout": bytearray(),
            "stderr": bytearray(),
        }
        selector = selectors.DefaultSelector()
        try:
            for name, stream in streams.items():
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, data=name)
            deadline = started + command.timeout_seconds
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ExecutionFailure(
                        f"{command.command_id} exceeded {command.timeout_seconds}s"
                    )
                events = selector.select(timeout=min(remaining, 0.1))
                for key, _ in events:
                    name = key.data
                    chunk = os.read(key.fileobj.fileno(), 64 * 1024)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    buffers[name].extend(chunk)
                    if len(buffers[name]) > limits[name]:
                        raise ExecutionFailure(
                            f"{command.command_id} {name} exceeded its byte limit"
                        )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ExecutionFailure(
                    f"{command.command_id} exceeded {command.timeout_seconds}s"
                )
            process.wait(timeout=remaining)
        except BaseException as exc:
            self._terminate_group(process)
            if isinstance(exc, ExecutionFailure):
                raise
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            if isinstance(exc, subprocess.TimeoutExpired):
                raise ExecutionFailure(
                    f"{command.command_id} exceeded {command.timeout_seconds}s"
                ) from exc
            raise ExecutionFailure(
                f"{command.command_id} execution infrastructure failed"
            ) from exc
        finally:
            selector.close()
            for stream in streams.values():
                if not stream.closed:
                    stream.close()
        finished = time.monotonic()
        return CommandResult(
            stdout=bytes(buffers["stdout"]),
            stderr=bytes(buffers["stderr"]),
            returncode=process.returncode,
            started_monotonic=started,
            finished_monotonic=finished,
        )


@dataclass(frozen=True)
class NativeSummary:
    targets: int
    modules: int
    tests: int
    failed_modules: int
    elapsed_seconds: float


def _parse_native_summary(stdout: bytes) -> NativeSummary:
    try:
        lines = stdout.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise GateRejected("native suite stdout is not UTF-8") from exc
    matches = [match for line in lines if (match := NATIVE_SUMMARY_RE.fullmatch(line))]
    if len(matches) != 1:
        _fail("native suite must emit exactly one authoritative summary")
    match = matches[0]
    summary = NativeSummary(
        targets=int(match.group(1)),
        modules=int(match.group(2)),
        tests=int(match.group(3)),
        failed_modules=int(match.group(4)),
        elapsed_seconds=float(match.group(5)),
    )
    if (
        summary.targets != 126
        or summary.modules != 93
        or summary.tests != 1584
        or summary.failed_modules != 0
    ):
        _fail("native suite summary is not 126/93/1584/0")
    return summary


def _identity_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        _fail(f"Linux identity {label} must be an object")
    return value


def _parse_linux_identity(
    stdout: bytes,
    linux: prepared_inputs.LinuxRuntimeInputs,
) -> dict[str, object]:
    try:
        identity = _identity_object(json.loads(stdout), "payload")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateRejected("Linux identity payload is not valid JSON") from exc
    if identity.get("schema") != "mingli-vz-amd64-identity-v1":
        _fail("Linux identity schema mismatch")
    instance = _identity_object(identity.get("instance"), "instance")
    if instance != {
        "vm_type": "vz",
        "guest_arch": "aarch64",
        "rosetta_enabled": True,
        "rosetta_binfmt": True,
    }:
        _fail("Linux identity is not VZ Rosetta with binfmt")
    docker = _identity_object(identity.get("docker"), "docker")
    if docker != linux.docker:
        _fail("Linux Docker identity mismatch")
    image = _identity_object(identity.get("image"), "image")
    if image != {
        "archive_sha256": linux.oci_archive_sha256,
        "index_digest": linux.index_digest,
        "platform_manifest_digest": linux.platform_manifest_digest,
        "config_digest": linux.config_digest,
        "attestation_manifest_digest": linux.attestation_manifest_digest,
        "layer_digests": list(linux.layer_digests),
        "rootfs_diff_ids": list(linux.rootfs_diff_ids),
        "docker": {
            "id": linux.index_digest,
            "descriptor_digest": linux.index_digest,
            "descriptor_media_type": "application/vnd.oci.image.index.v1+json",
            "immutable_ref": linux.immutable_image_ref,
            "os": "linux",
            "architecture": "amd64",
            "rootfs_diff_ids": list(linux.rootfs_diff_ids),
        },
    }:
        _fail("Linux image is not the exact OCI index/amd64/config closure")
    container = _identity_object(identity.get("container"), "container")
    expected_scalars = {
        "platform_system": "Linux",
        "platform_machine": "x86_64",
        "uname_machine": "x86_64",
        "python_version": [3, 14, 6],
        "node_version": "v26.3.0",
        "git_version": "git version 2.39.5",
        "sxtwl_smoke": [2024, 1, 1],
    }
    for key, expected in expected_scalars.items():
        if container.get(key) != expected:
            _fail(f"Linux container identity mismatch: {key}")
    elf_machine = _identity_object(container.get("elf_machine"), "ELF machine")
    if elf_machine != {
        "python": 62,
        "node": 62,
        "git": 62,
        "sxtwl": 62,
        "yaml": 62,
    }:
        _fail("Linux container ELF targets are not all x86_64")
    node_libraries = container.get("node_ldd_libraries")
    if not isinstance(node_libraries, list) or "libatomic.so.1" not in node_libraries:
        _fail("Linux Node linkage lacks libatomic.so.1")
    sxtwl_libraries = container.get("sxtwl_ldd_libraries")
    if not isinstance(sxtwl_libraries, list) or "libstdc++.so.6" not in sxtwl_libraries:
        _fail("Linux sxtwl linkage lacks libstdc++.so.6")
    return identity


class LocalFullGate:
    def __init__(
        self,
        execution: Execution,
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._execution = execution
        self._monotonic = monotonic

    def _remaining_seconds(self, started: float, deadline_seconds: int) -> float:
        remaining = deadline_seconds - (self._monotonic() - started)
        if not math.isfinite(remaining) or remaining <= 0:
            _fail("profile exceeded its deadline")
        return remaining

    def _profile_elapsed(
        self,
        started: float,
        command_elapsed_seconds: float,
        deadline_seconds: int,
    ) -> float:
        elapsed = max(self._monotonic() - started, command_elapsed_seconds)
        if not math.isfinite(elapsed) or elapsed < 0 or elapsed > deadline_seconds:
            _fail("profile exceeded its deadline")
        return elapsed

    def _run_linux_identity(
        self,
        request: LocalFullRequest,
        inputs: prepared_inputs.PreparedInputs,
        *,
        run_id: str,
        staging: Path,
        published: Path,
        profile_started: float,
    ) -> LocalFullResult:
        try:
            linux = prepared_inputs.require_linux(inputs)
        except prepared_inputs.PreparedInputsError as exc:
            if staging.exists():
                shutil.rmtree(staging)
            raise GateRejected(str(exc)) from exc
        tracer = Path(__file__).with_name("linux_identity.py")
        command = GateCommand(
            command_id="linux-amd64-identity-tracer",
            argv=(
                sys.executable,
                "-B",
                str(tracer),
                "--instance",
                linux.instance,
                "--image-ref",
                linux.image_ref,
                "--immutable-image-ref",
                linux.immutable_image_ref,
                "--oci-archive",
                str(linux.oci_archive),
                "--oci-archive-sha256",
                linux.oci_archive_sha256,
                "--oci-index-digest",
                linux.index_digest,
                "--oci-platform-manifest-digest",
                linux.platform_manifest_digest,
                "--oci-config-digest",
                linux.config_digest,
                "--oci-attestation-manifest-digest",
                linux.attestation_manifest_digest,
                *(
                    item
                    for digest in linux.layer_digests
                    for item in ("--oci-layer-digest", digest)
                ),
                *(
                    item
                    for digest in linux.rootfs_diff_ids
                    for item in ("--oci-rootfs-diff-id", digest)
                ),
                "--effective-config",
                str(linux.effective_config),
                "--effective-config-sha256",
                linux.effective_config_sha256,
            ),
            cwd=Path(__file__).resolve().parent,
            timeout_seconds=self._remaining_seconds(
                profile_started, request.deadline_seconds
            ),
            slots=1,
        )
        try:
            try:
                result = self._execution.run(command)
            except Exception as exc:
                raise GateRejected(f"Linux identity execution failed: {exc}") from exc
            if len(result.stdout) > command.stdout_limit_bytes:
                _fail("Linux identity stdout exceeded its byte limit")
            if len(result.stderr) > command.stderr_limit_bytes:
                _fail("Linux identity stderr exceeded its byte limit")
            if result.returncode != 0:
                _fail("Linux identity tracer exited nonzero")
            elapsed_seconds = result.finished_monotonic - result.started_monotonic
            if (
                not math.isfinite(elapsed_seconds)
                or elapsed_seconds < 0
                or elapsed_seconds > request.deadline_seconds
            ):
                _fail("Linux identity tracer exceeded its deadline")
            profile_elapsed_seconds = self._profile_elapsed(
                profile_started,
                elapsed_seconds,
                request.deadline_seconds,
            )
            identity = _parse_linux_identity(result.stdout, linux)
            try:
                ending_inputs = prepared_inputs.load(
                    request.prepared_inputs.path,
                    request.prepared_inputs.sha256,
                )
                prepared_inputs.require_linux(ending_inputs)
            except prepared_inputs.PreparedInputsError as exc:
                raise GateRejected(
                    f"prepared inputs changed during run: {exc}"
                ) from exc
            timeline = (
                TimelineEntry(
                    command_id=command.command_id,
                    slots=command.slots,
                    started_monotonic=result.started_monotonic,
                    finished_monotonic=result.finished_monotonic,
                    exit_code=result.returncode,
                ),
            )
            report = {
                "schema": "mingli-linux-identity-tracer-report-v1",
                "profile": request.profile,
                "status": "tracer-passed-not-certified",
                "run_id": run_id,
                "prepared_inputs_sha256": inputs.manifest_sha256,
                "prepared_inputs_path": str(inputs.manifest_path),
                "identity": identity,
                "command": {
                    "command_id": command.command_id,
                    "argv": list(command.argv),
                    "cwd": str(command.cwd),
                    "returncode": result.returncode,
                    "elapsed_seconds": elapsed_seconds,
                    "slots": command.slots,
                    "timeout_seconds": command.timeout_seconds,
                    "shell": command.shell,
                    "stdout_sha256": _sha256_bytes(result.stdout),
                    "stderr_sha256": _sha256_bytes(result.stderr),
                },
            }
            local_summary = {
                "schema": "mingli-local-profile-sla-v1",
                "profile": request.profile,
                "stage": "identity-tracer",
                "certified": False,
                "run_id": run_id,
                "limit_seconds": request.deadline_seconds,
                "max_slots": request.slots,
                "elapsed_seconds": profile_elapsed_seconds,
                "command_elapsed_seconds": elapsed_seconds,
                "profile_report_sha256": _sha256_bytes(_json_bytes(report)),
            }
            (staging / "linux-identity-tracer.json").write_bytes(_json_bytes(report))
            (staging / "local-linux-identity-tracer.json").write_bytes(
                _json_bytes(local_summary)
            )
            os.replace(staging, published)
            return LocalFullResult(
                profile=request.profile,
                profile_report=published / "linux-identity-tracer.json",
                local_summary=published / "local-linux-identity-tracer.json",
                timeline=timeline,
                elapsed_seconds=profile_elapsed_seconds,
            )
        except BaseException:
            if staging.exists():
                shutil.rmtree(staging)
            raise

    def run(self, request: LocalFullRequest) -> LocalFullResult:
        profile_started = self._monotonic()
        if request.profile not in {"native-full", "linux-certify"}:
            _fail("unknown profile")
        if not 1 <= request.deadline_seconds <= MAX_DEADLINE_SECONDS:
            _fail("deadline_seconds must be between 1 and 600")
        if not 1 <= request.slots <= MAX_SLOTS:
            _fail("slots must be between 1 and 10")
        try:
            inputs = prepared_inputs.load(
                request.prepared_inputs.path,
                request.prepared_inputs.sha256,
            )
        except prepared_inputs.PreparedInputsError as exc:
            raise GateRejected(str(exc)) from exc

        output_parent = request.output_parent
        if output_parent.is_symlink() or (
            output_parent.exists() and not output_parent.is_dir()
        ):
            _fail("output parent must be a non-symlink directory")
        output_parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if any(output_parent.iterdir()):
            _fail("output parent must be empty")
        run_id = secrets.token_hex(16)
        staging = output_parent / f".{run_id}.tmp"
        published = output_parent / run_id
        staging.mkdir(mode=0o700)

        if request.profile == "linux-certify":
            return self._run_linux_identity(
                request,
                inputs,
                run_id=run_id,
                staging=staging,
                published=published,
                profile_started=profile_started,
            )

        command = GateCommand(
            command_id="native-release-regression",
            argv=(
                str(inputs.native_python),
                "-B",
                str(inputs.runner_path),
                "--jobs",
                str(request.slots),
                "--research-root",
                str(inputs.research_root),
            ),
            cwd=inputs.source_root,
            timeout_seconds=self._remaining_seconds(
                profile_started, request.deadline_seconds
            ),
            slots=request.slots,
        )
        try:
            try:
                result = self._execution.run(command)
            except Exception as exc:
                raise GateRejected(f"native execution failed: {exc}") from exc
            if len(result.stdout) > command.stdout_limit_bytes:
                _fail("native suite stdout exceeded its byte limit")
            if len(result.stderr) > command.stderr_limit_bytes:
                _fail("native suite stderr exceeded its byte limit")
            if result.returncode != 0:
                _fail("native suite exited nonzero")
            elapsed_seconds = result.finished_monotonic - result.started_monotonic
            if (
                not math.isfinite(elapsed_seconds)
                or elapsed_seconds < 0
                or elapsed_seconds > request.deadline_seconds
            ):
                _fail("native suite exceeded its deadline")
            summary = _parse_native_summary(result.stdout)
            if summary.elapsed_seconds > request.deadline_seconds:
                _fail("native suite summary exceeded its deadline")

            try:
                prepared_inputs.load(
                    request.prepared_inputs.path,
                    request.prepared_inputs.sha256,
                )
            except prepared_inputs.PreparedInputsError as exc:
                raise GateRejected(
                    f"prepared inputs changed during run: {exc}"
                ) from exc

            profile_elapsed_seconds = self._profile_elapsed(
                profile_started,
                elapsed_seconds,
                request.deadline_seconds,
            )

            timeline = (
                TimelineEntry(
                    command_id=command.command_id,
                    slots=command.slots,
                    started_monotonic=result.started_monotonic,
                    finished_monotonic=result.finished_monotonic,
                    exit_code=result.returncode,
                ),
            )
            report = {
                "schema": "mingli-native-full-report-v1",
                "profile": request.profile,
                "status": "passed",
                "run_id": run_id,
                "prepared_inputs_sha256": inputs.manifest_sha256,
                "prepared_inputs_path": str(inputs.manifest_path),
                "profile_elapsed_seconds": profile_elapsed_seconds,
                "summary": {
                    "targets": summary.targets,
                    "modules": summary.modules,
                    "tests": summary.tests,
                    "failed_modules": summary.failed_modules,
                    "elapsed_seconds": summary.elapsed_seconds,
                },
                "command": {
                    "command_id": command.command_id,
                    "argv": list(command.argv),
                    "cwd": str(command.cwd),
                    "returncode": result.returncode,
                    "elapsed_seconds": elapsed_seconds,
                    "slots": command.slots,
                    "timeout_seconds": command.timeout_seconds,
                    "shell": command.shell,
                    "stdout_sha256": _sha256_bytes(result.stdout),
                    "stderr_sha256": _sha256_bytes(result.stderr),
                },
                "artifacts": {
                    "stdout": {
                        "path": "native-release-regression.stdout",
                        "sha256": _sha256_bytes(result.stdout),
                        "size_bytes": len(result.stdout),
                    },
                    "stderr": {
                        "path": "native-release-regression.stderr",
                        "sha256": _sha256_bytes(result.stderr),
                        "size_bytes": len(result.stderr),
                    },
                },
            }
            local_summary = {
                "schema": "mingli-local-profile-sla-v1",
                "profile": request.profile,
                "run_id": run_id,
                "limit_seconds": request.deadline_seconds,
                "max_slots": request.slots,
                "elapsed_seconds": profile_elapsed_seconds,
                "command_elapsed_seconds": elapsed_seconds,
                "profile_report_sha256": _sha256_bytes(_json_bytes(report)),
            }
            (staging / "native-release-regression.stdout").write_bytes(result.stdout)
            (staging / "native-release-regression.stderr").write_bytes(result.stderr)
            (staging / "native-full-5.1.json").write_bytes(_json_bytes(report))
            (staging / "local-native-full-5.1.json").write_bytes(
                _json_bytes(local_summary)
            )
            try:
                verify_local_full.validate_native_run(
                    staging / "native-full-5.1.json",
                    staging / "local-native-full-5.1.json",
                    expected_prepared_inputs_sha256=inputs.manifest_sha256,
                )
            except Exception as exc:
                raise GateRejected(
                    f"native independent verification failed: {exc}"
                ) from exc
            self._profile_elapsed(
                profile_started,
                elapsed_seconds,
                request.deadline_seconds,
            )
            os.replace(staging, published)
            try:
                self._profile_elapsed(
                    profile_started,
                    elapsed_seconds,
                    request.deadline_seconds,
                )
            except BaseException:
                shutil.rmtree(published)
                raise
            return LocalFullResult(
                profile=request.profile,
                profile_report=published / "native-full-5.1.json",
                local_summary=published / "local-native-full-5.1.json",
                timeline=timeline,
                elapsed_seconds=profile_elapsed_seconds,
            )
        except BaseException:
            if staging.exists():
                shutil.rmtree(staging)
            raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a prepared-input Mingli V5.1 local test profile"
    )
    profiles = parser.add_subparsers(dest="profile", required=True)
    for profile in ("native-full", "linux-certify"):
        command = profiles.add_parser(profile)
        command.add_argument("--prepared-inputs", type=Path, required=True)
        command.add_argument("--prepared-inputs-sha256", required=True)
        command.add_argument("--output-parent", type=Path, required=True)
        command.add_argument(
            "--deadline-seconds",
            type=int,
            default=MAX_DEADLINE_SECONDS,
        )
        command.add_argument("--slots", type=int, default=MAX_SLOTS)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    execution: Execution | None = None,
) -> int:
    args = _build_parser().parse_args(argv)
    request = LocalFullRequest(
        profile=args.profile,
        prepared_inputs=PreparedInputsRef(
            path=args.prepared_inputs.expanduser().resolve(),
            sha256=args.prepared_inputs_sha256,
        ),
        output_parent=args.output_parent.expanduser().resolve(),
        deadline_seconds=args.deadline_seconds,
        slots=args.slots,
    )
    try:
        result = LocalFullGate(execution or SubprocessExecution()).run(request)
    except GateRejected as exc:
        print(f"local Gate rejected: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "profile": result.profile,
                "profile_report": str(result.profile_report),
                "local_summary": (
                    str(result.local_summary)
                    if result.local_summary is not None
                    else None
                ),
                "elapsed_seconds": result.elapsed_seconds,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
