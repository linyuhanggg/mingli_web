#!/usr/bin/env python3
"""Generate the V5.1 Linux Gate report from commands run inside the image.

The default mode is the single audit entry point.  Two private child modes
emit canonical machine-readable characterization and runtime-probe outputs so
their stdout bytes can be captured, run twice where required, and rehashed by
``verify_release.py`` outside the container.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

import verify_release

RELEASE_ROOT = Path("/opt/mingli-master")
RUNTIME_PYTHON = Path("/opt/mingli-runtime/venv/bin/python")
NODE = Path("/opt/node/bin/node")
GIT = Path("/opt/git/bin/git")
AUDIT_SCRIPT = Path("/opt/mingli-runtime/audit_runtime.py")
SBOM_SCRIPT = Path("/opt/mingli-runtime/emit_sbom.py")
VERIFIER = Path("/opt/mingli-runtime/verify_release.py")
PROVENANCE = Path("/opt/mingli-runtime/dependency-provenance.json")
STATE_ROOT = Path("/var/lib/mingli")
SOURCE_ROOT = Path("/audit-source")
OUTPUT_ROOT = Path("/audit-output")
PRODUCTION_OUTPUT_ROOT = Path("/production-output")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
PROVIDER_MATRIX_TIMEOUT_SECONDS = 10_800
RELEASE_REGRESSION_TIMEOUT_SECONDS = 10_800
PRODUCTION_COMMAND_IDS = frozenset(
    {
        "characterization-a",
        "characterization-b",
        "git-smoke",
        "p0-trajectories",
        "production-native-linkage",
        "production-tree-identity",
        "provider-matrix-b",
        "release-regression",
        "runtime-inventory",
        "runtime-probe-machine",
        "runtime-probe-unittest",
        "sbom-regeneration",
    }
)
AUDIT_COMMAND_IDS = frozenset(
    {
        "audit-native-linkage",
        "audit-tree-identity",
        "source-binding",
    }
)


class AuditError(RuntimeError):
    """The real Linux audit did not produce admissible evidence."""


def _fail(message: str) -> NoReturn:
    raise AuditError(message)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} is missing or unsafe: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise AuditError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        _fail(f"{label} must be a JSON object")
    return value


def _characterization_payload(source_root: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise AuditError("PyYAML is unavailable in the final runtime") from exc
    matrix_path = source_root / "references/matrices/provider-completeness.yaml"
    if matrix_path.is_symlink() or not matrix_path.is_file():
        _fail("provider completeness matrix is missing or unsafe")
    try:
        matrix = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError, TypeError) as exc:
        raise AuditError("provider completeness matrix is invalid") from exc
    if not isinstance(matrix, dict) or matrix.get("schema_version") != (
        "mingli-provider-completeness-v1"
    ):
        _fail("provider completeness matrix schema mismatch")
    providers = matrix.get("providers")
    if (
        not isinstance(providers, dict)
        or set(providers) != verify_release.EXPECTED_PROVIDERS
    ):
        _fail("provider completeness matrix does not contain the exact 13 Provider set")
    result: dict[str, Any] = {}
    for provider_id, entry in sorted(providers.items()):
        if not isinstance(entry, dict):
            _fail(f"provider completeness record is invalid: {provider_id}")
        live = entry.get("live_contract")
        replay = entry.get("dedicated_runtime_replay")
        source = entry.get("source_applicability")
        fixtures = entry.get("fixtures")
        dedicated = entry.get("dedicated_audit")
        if not all(
            isinstance(value, dict)
            for value in (live, replay, source, fixtures, dedicated)
        ):
            _fail(f"provider completeness sub-record is invalid: {provider_id}")
        deterministic_facts = (
            entry.get("ready") is True
            and live.get("deterministic") is True
            and live.get("runs") == 2
            and live.get("findings") == []
            and replay.get("case_replay_ready") is True
            and replay.get("findings") == []
            and dedicated.get("provider_ready") is True
            and dedicated.get("status") == "pass"
        )
        evidence_mapping = (
            source.get("ready") is True
            and source.get("findings") == []
            and isinstance(source.get("accepted_fixture_replay_count"), int)
            and source["accepted_fixture_replay_count"] > 0
        )
        fixture_bound = (
            fixtures.get("dedicated_hash_matches") is True
            and fixtures.get("route_owned_ids_match_fixture") is True
            and isinstance(fixtures.get("qualifying_cases"), int)
            and isinstance(fixtures.get("minimum_cases"), int)
            and fixtures["qualifying_cases"] >= fixtures["minimum_cases"]
        )
        provider_record = {
            "assertions": {
                "deterministic_facts": deterministic_facts,
                "evidence_mapping": evidence_mapping,
                "fixture_bound": fixture_bound,
            },
            "deterministic_facts_sha256": verify_release.canonical_sha256(
                {
                    "dedicated_audit": dedicated,
                    "dedicated_runtime_replay": replay,
                    "live_contract": live,
                }
            ),
            "evidence_mapping_sha256": verify_release.canonical_sha256(source),
            "fixture_input_sha256": fixtures.get("sha256"),
            "provider_id": provider_id,
            "provider_output_sha256": verify_release.canonical_sha256(entry),
            "ready": all((deterministic_facts, evidence_mapping, fixture_bound)),
        }
        result[provider_id] = provider_record
    return {
        "providers": result,
        "schema_version": "mingli-characterization-v1",
    }


def emit_characterization(source_root: Path) -> int:
    print(
        json.dumps(
            _characterization_payload(source_root),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def _run_runtime(stdin: str, state_root: Path, *, timeout: float) -> dict[str, Any]:
    environment = {
        "HOME": "/nonexistent",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "MINGLI_PYTHON": str(RUNTIME_PYTHON),
        "MINGLI_STORE_ROOT": str(state_root),
        "PATH": os.environ.get("PATH", "/opt/node/bin:/usr/local/bin:/usr/bin:/bin"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "TZ": "UTC",
    }
    completed = subprocess.run(
        [str(RELEASE_ROOT / "scripts/run_reading_transaction.sh")],
        input=stdin,
        check=False,
        capture_output=True,
        text=True,
        cwd=RELEASE_ROOT,
        env=environment,
        timeout=timeout,
    )
    if completed.returncode != 0:
        _fail("portable runtime probe exited non-zero")
    lines = completed.stdout.splitlines()
    if len(lines) != 1:
        _fail("portable runtime probe did not emit one JSON line")
    try:
        value = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise AuditError("portable runtime probe output is invalid JSON") from exc
    if not isinstance(value, dict):
        _fail("portable runtime probe output must be an object")
    return value


def _probe_launcher_timeout(
    state_root: Path,
    *,
    release_root: Path = RELEASE_ROOT,
    runtime_python: Path = RUNTIME_PYTHON,
    timeout_seconds: float = 1.0,
) -> bool:
    """Timeout the signed launcher and prove its whole process group is gone."""

    with tempfile.TemporaryDirectory(prefix="mingli-timeout-probe-") as temporary:
        root = Path(temporary)
        scripts = root / "scripts"
        scripts.mkdir(mode=0o700)
        source_launcher = release_root / "scripts/run_reading_transaction.sh"
        probe_launcher = scripts / "run_reading_transaction.sh"
        if source_launcher.is_symlink() or not source_launcher.is_file():
            return False
        shutil.copyfile(source_launcher, probe_launcher)
        probe_launcher.chmod(0o600)
        if verify_release.sha256_file(source_launcher) != verify_release.sha256_file(
            probe_launcher
        ):
            return False
        hanging_script = scripts / "runtime_launcher.py"
        pid_path = root / "pid"
        hanging_script.write_text(
            "import json, os, signal, subprocess, sys, time\n"
            "child = subprocess.Popen([sys.executable, '-I', '-S', '-B', '-c', "
            "'import time; time.sleep(3600)'])\n"
            "def stop(signum, _frame):\n"
            "    child.terminate()\n"
            "    try:\n"
            "        child.wait(timeout=1)\n"
            "    except subprocess.TimeoutExpired:\n"
            "        child.kill(); child.wait(timeout=1)\n"
            "    raise SystemExit(128 + signum)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "with open(os.environ['MINGLI_HANG_PID'], 'x', encoding='utf-8') as f:\n"
            "    json.dump({'child': child.pid, 'parent': os.getpid()}, f)\n"
            "while True: time.sleep(60)\n",
            encoding="utf-8",
        )
        hanging_script.chmod(0o600)
        environment = {
            "HOME": "/nonexistent",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "MINGLI_HANG_PID": str(pid_path),
            "MINGLI_PYTHON": str(runtime_python),
            "MINGLI_STORE_ROOT": str(state_root),
            "PATH": "/opt/node/bin:/usr/local/bin:/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TZ": "UTC",
        }
        command = ["/bin/sh", str(probe_launcher)]
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=root,
            env=environment,
            start_new_session=True,
        )
        timed_out = False
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=2)
        if not timed_out or process.returncode is None:
            return False
        try:
            pid_record = json.loads(pid_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        if (
            not isinstance(pid_record, dict)
            or pid_record.get("parent") != process.pid
            or not isinstance(pid_record.get("child"), int)
            or pid_record["child"] == process.pid
        ):
            return False
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                return True
            except PermissionError:
                return False
            time.sleep(0.02)
        return False


def emit_runtime_probes(state_root: Path) -> int:
    started = time.monotonic()
    first = _run_runtime('{"kind":"describe"}\n', state_root, timeout=60)
    elapsed = time.monotonic() - started
    second = _run_runtime('{"kind":"describe"}\n', state_root, timeout=60)
    malformed = _run_runtime("{", state_root, timeout=60)
    launcher_timeout_killed = _probe_launcher_timeout(state_root)
    tampered_release_rejected = False
    with tempfile.TemporaryDirectory(prefix="mingli-tamper-probe-") as temporary:
        target = Path(temporary) / "release"
        shutil.copytree(RELEASE_ROOT, target, symlinks=True)
        skill = target / "SKILL.md"
        skill.chmod(0o644)
        with skill.open("ab") as stream:
            stream.write(b"\ntamper-probe\n")
        try:
            verify_release.inspect_runtime(release_root=target, release_only=True)
        except verify_release.ReleaseVerificationError:
            tampered_release_rejected = True
    assertions = {
        "describe_repeatable": first == second,
        "describe_within_60_seconds": elapsed < 60 and first.get("kind") == "described",
        "launcher_timeout_killed_without_residual_process": launcher_timeout_killed,
        "malformed_input_stopped": (
            malformed.get("kind") == "stopped"
            and malformed.get("reason") == "error"
            and bool(str(malformed.get("public_copy") or "").strip())
        ),
        "tampered_release_rejected": tampered_release_rejected,
    }
    if not all(assertions.values()):
        _fail(f"runtime machine probe failed: {assertions}")
    print(
        json.dumps(
            {
                "assertions": assertions,
                "schema_version": "mingli-runtime-probes-v1",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def _tree_digest(root: Path) -> dict[str, Any]:
    return verify_release.runtime_tree_digest(root)


def emit_tree_identity() -> int:
    payload = {
        "schema_version": "mingli-runtime-tree-identity-v1",
        "trees": {
            "git": _tree_digest(Path("/opt/git")),
            "node": _tree_digest(Path("/opt/node")),
            "release": _tree_digest(RELEASE_ROOT),
            "runtime_venv": _tree_digest(RUNTIME_PYTHON.parent.parent),
        },
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


def emit_native_linkage() -> int:
    payload = verify_release.inspect_native_linkage(RUNTIME_PYTHON, NODE, GIT)
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


def emit_git_smoke() -> int:
    fixture_bytes = b"Mingli V5.1 Git runtime smoke fixture.\n"
    fixed_date = "2000-01-01T00:00:00Z"
    environment = {
        "GIT_AUTHOR_DATE": fixed_date,
        "GIT_AUTHOR_EMAIL": "gate@mingli.invalid",
        "GIT_AUTHOR_NAME": "Mingli Linux Gate",
        "GIT_COMMITTER_DATE": fixed_date,
        "GIT_COMMITTER_EMAIL": "gate@mingli.invalid",
        "GIT_COMMITTER_NAME": "Mingli Linux Gate",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "HOME": "/nonexistent",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/opt/git/bin:/usr/bin:/bin",
        "TZ": "UTC",
    }
    operations: list[str] = []

    def run(
        operation: str,
        arguments: Sequence[str],
        *,
        cwd: Path | None = None,
        binary: bool = False,
    ) -> bytes | str:
        completed = subprocess.run(
            [str(GIT), *arguments],
            check=False,
            capture_output=True,
            cwd=cwd,
            env=environment,
            text=not binary,
            timeout=30,
        )
        stderr = (
            completed.stderr
            if isinstance(completed.stderr, str)
            else bytes(completed.stderr).decode("utf-8", errors="replace")
        )
        if completed.returncode != 0 or stderr:
            _fail(f"Git smoke operation failed: {operation}")
        operations.append(operation)
        return completed.stdout

    version = str(run("version", ("--version",))).strip()
    with tempfile.TemporaryDirectory(prefix="mingli-git-smoke-") as temporary:
        repository = Path(temporary) / "repository"
        run("init", ("init", "--quiet", "--initial-branch=main", str(repository)))
        run(
            "config-user-name",
            ("config", "user.name", "Mingli Linux Gate"),
            cwd=repository,
        )
        run(
            "config-user-email",
            ("config", "user.email", "gate@mingli.invalid"),
            cwd=repository,
        )
        run("config-gc-auto", ("config", "gc.auto", "0"), cwd=repository)
        run(
            "config-maintenance-auto",
            ("config", "maintenance.auto", "false"),
            cwd=repository,
        )
        (repository / "tracked.txt").write_bytes(fixture_bytes)
        run("add", ("add", "--", "tracked.txt"), cwd=repository)
        run(
            "commit",
            ("commit", "--quiet", "-m", "Mingli V5.1 Git smoke fixture"),
            cwd=repository,
        )
        status = str(
            run(
                "status",
                ("status", "--porcelain=v1", "--untracked-files=all"),
                cwd=repository,
            )
        ).rstrip("\n")
        ls_files = str(run("ls-files", ("ls-files", "--stage"), cwd=repository)).rstrip(
            "\n"
        )
        ls_tree = str(
            run("ls-tree", ("ls-tree", "HEAD", "--", "tracked.txt"), cwd=repository)
        ).rstrip("\n")
        commit = str(
            run("rev-parse-commit", ("rev-parse", "--verify", "HEAD"), cwd=repository)
        ).strip()
        tree = str(
            run(
                "rev-parse-tree",
                ("rev-parse", "--verify", "HEAD^{tree}"),
                cwd=repository,
            )
        ).strip()
        archive = run(
            "archive",
            ("archive", "--format=tar", "HEAD"),
            cwd=repository,
            binary=True,
        )
        if not isinstance(archive, bytes):
            _fail("Git smoke archive output was not binary")
        exec_path = str(run("exec-path", ("--exec-path",))).strip()
    payload = {
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "commit_sha1": commit,
        "exec_path": exec_path,
        "fixture": {
            "author_date": fixed_date,
            "author_email": "gate@mingli.invalid",
            "author_name": "Mingli Linux Gate",
            "commit_message": "Mingli V5.1 Git smoke fixture",
            "content_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
            "filename": "tracked.txt",
        },
        "ls_files_row": ls_files,
        "ls_tree_row": ls_tree,
        "operations": operations,
        "schema_version": "mingli-git-smoke-v1",
        "status_porcelain": status,
        "templates_exists": Path("/opt/git/share/git-core/templates").is_dir(),
        "templates_path": "/opt/git/share/git-core/templates",
        "tree_sha1": tree,
        "version": version,
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


def _state_root_identity(state_root: Path) -> dict[str, Any]:
    if not state_root.is_absolute() or state_root.is_symlink():
        _fail("state root identity path is relative or unsafe")
    try:
        resolved = state_root.resolve(strict=True)
        info = state_root.stat()
    except OSError as exc:
        raise AuditError("state root identity path is missing") from exc
    if not resolved.is_dir():
        _fail("state root identity path is not a directory")
    return {
        "gid": info.st_gid,
        "mode": stat.S_IMODE(info.st_mode),
        "path": str(resolved),
        "schema_version": "mingli-state-root-identity-v1",
        "st_dev": info.st_dev,
        "st_ino": info.st_ino,
        "uid": info.st_uid,
    }


def emit_state_root_identity(state_root: Path) -> int:
    print(
        json.dumps(
            _state_root_identity(state_root),
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


def emit_token_record(state_root: Path) -> int:
    try:
        request = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, TypeError) as exc:
        raise AuditError("token record request is invalid JSON") from exc
    fingerprint = (
        request.get("token_fingerprint") if isinstance(request, dict) else None
    )
    verify_release._require_sha256(fingerprint, "token record fingerprint")
    logs = sorted(state_root.rglob("state-tokens/token-log.jsonl"))
    if len(logs) != 1 or logs[0].is_symlink() or not logs[0].is_file():
        _fail("token record audit did not find one safe authoritative log")
    selected: dict[str, Any] | None = None
    for raw_line in logs[0].read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(raw_line)
        except (json.JSONDecodeError, TypeError) as exc:
            raise AuditError("authoritative token log contains invalid JSON") from exc
        if isinstance(item, dict) and item.get("token_hash") == fingerprint:
            selected = item
    if selected is None:
        _fail("requested token fingerprint is absent from the authoritative log")
    version = selected.get("version")
    phase = selected.get("phase")
    if (
        not isinstance(version, int)
        or version <= 0
        or phase
        not in {
            "pending_input",
            "prepared",
            "accepted",
        }
    ):
        _fail("authoritative token record is invalid")
    reading_id = selected.get("reading_id")
    if not isinstance(reading_id, str) or not reading_id:
        _fail("authoritative token record has no reading identity")
    parent = selected.get("parent_token_hash")
    if parent is not None:
        verify_release._require_sha256(parent, "parent token fingerprint")
    payload = {
        "parent_token_fingerprint": parent,
        "phase": phase,
        "reading_id_sha256": hashlib.sha256(reading_id.encode("utf-8")).hexdigest(),
        "schema_version": "mingli-token-record-audit-v1",
        "token_fingerprint": fingerprint,
        "version": version,
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


def _audit_environment(source_root: Path) -> dict[str, str]:
    home = Path("/tmp/mingli-linux-audit-home")
    home.mkdir(mode=0o700, exist_ok=True)
    home.chmod(0o700)
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": str(home),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "MINGLI_PYTHON": str(RUNTIME_PYTHON),
            "MINGLI_RESEARCH_ROOT": str(source_root),
            "MINGLI_STORE_ROOT": str(STATE_ROOT),
            "PATH": "/opt/git/bin:/opt/node/bin:/opt/mingli-runtime/venv/bin:/usr/local/bin:/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(source_root / "scripts"),
            "TZ": "UTC",
        }
    )
    return environment


class CommandRecorder:
    def __init__(self, output_root: Path, image_id: str) -> None:
        self.output_root = output_root
        self.image_id = image_id
        self.records: list[dict[str, Any]] = []

    def run(
        self,
        command_id: str,
        argv: Sequence[str],
        *,
        cwd: Path,
        environment: Mapping[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        if any(record["id"] == command_id for record in self.records):
            _fail(f"duplicate audit command id: {command_id}")
        logs = self.output_root / "evidence/commands"
        logs.mkdir(parents=True, exist_ok=True)
        stdout_path = logs / f"{command_id}.stdout"
        stderr_path = logs / f"{command_id}.stderr"
        started = time.monotonic()
        print(f"audit: start {command_id}", flush=True)
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            try:
                completed = subprocess.run(
                    list(argv),
                    check=False,
                    cwd=cwd,
                    env=dict(environment),
                    stdout=stdout,
                    stderr=stderr,
                    timeout=timeout,
                )
                exit_code = completed.returncode
            except subprocess.TimeoutExpired as exc:
                raise AuditError(f"audit command timed out: {command_id}") from exc
        record = {
            "argv": list(argv),
            "cwd": str(cwd),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "executed_in_image_id": self.image_id,
            "exit_code": exit_code,
            "id": command_id,
            "stderr_path": stderr_path.relative_to(self.output_root).as_posix(),
            "stderr_sha256": verify_release.sha256_file(stderr_path),
            "stdout_path": stdout_path.relative_to(self.output_root).as_posix(),
            "stdout_sha256": verify_release.sha256_file(stdout_path),
            "timeout_seconds": timeout,
        }
        self.records.append(record)
        print(
            f"audit: finish {command_id} exit={exit_code} elapsed={record['elapsed_seconds']}s",
            flush=True,
        )
        if exit_code != 0:
            _fail(f"audit command failed: {command_id}")
        return record


def _copy_file(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        _fail(f"audit input is missing or unsafe: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination, follow_symlinks=False)
    destination.chmod(0o444)


def _collect_backup_paths(evidence: Mapping[str, Any]) -> set[str]:
    paths: set[str] = set()
    snapshots = evidence.get("snapshots")
    token_records = evidence.get("token_records")
    transcripts = evidence.get("transcripts")
    commands = evidence.get("commands")
    if (
        not isinstance(snapshots, dict)
        or not isinstance(token_records, dict)
        or not isinstance(transcripts, dict)
    ):
        _fail("backup evidence file inventory is invalid")
    if not isinstance(commands, list):
        _fail("backup evidence command inventory is invalid")
    for snapshot in snapshots.values():
        if not isinstance(snapshot, dict):
            _fail("backup snapshot evidence record is invalid")
        paths.add(
            verify_release._safe_relative(snapshot.get("ciphertext_path"), "backup")
        )
    for transcript in transcripts.values():
        if not isinstance(transcript, dict):
            _fail("backup transcript evidence record is invalid")
        paths.add(verify_release._safe_relative(transcript.get("path"), "backup"))
    for token_record in token_records.values():
        if not isinstance(token_record, dict):
            _fail("backup token record evidence is invalid")
        paths.add(verify_release._safe_relative(token_record.get("path"), "backup"))
    for command in commands:
        if not isinstance(command, dict):
            _fail("backup command evidence record is invalid")
        paths.add(verify_release._safe_relative(command.get("stdout_path"), "backup"))
        paths.add(verify_release._safe_relative(command.get("stderr_path"), "backup"))
    return paths


def _copy_backup_evidence(source: Path, output_root: Path) -> Path:
    evidence = _read_json(source, "backup/restore input evidence")
    input_root = source.parents[2]
    relative_evidence = source.relative_to(input_root).as_posix()
    if relative_evidence != "evidence/backup/backup-restore.json":
        _fail("backup/restore evidence must use the frozen audit-input path")
    for relative in _collect_backup_paths(evidence):
        _copy_file(input_root / relative, output_root / relative)
    destination = output_root / relative_evidence
    _copy_file(source, destination)
    return destination


def _assert_platform() -> None:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        _fail("audit must run on real Linux x86_64")
    if platform.python_version() != "3.14.6":
        _fail("audit must run under the final CPython 3.14.6 runtime")
    if os.getuid() != 10001 or os.getgid() != 10001:
        _fail("audit must run as the fixed non-root runtime UID/GID")


def _prepare_output_root(output_root: Path, expected: Path) -> None:
    if output_root != expected:
        _fail(f"audit output root must be {expected}")
    if output_root.is_symlink() or not output_root.is_dir():
        _fail("audit output root is missing or unsafe")
    if any(output_root.iterdir()):
        _fail("audit output root must start empty")
    (output_root / "evidence/commands").mkdir(parents=True)


def _parse_regression(record: Mapping[str, Any], output_root: Path) -> dict[str, int]:
    stdout_path = output_root / str(record["stdout_path"])
    output = stdout_path.read_text(encoding="utf-8")
    matches = list(verify_release.SUMMARY_RE.finditer(output))
    if len(matches) != 1:
        _fail("authoritative regression emitted no unique summary")
    match = matches[0]
    result = {
        "failed": int(match.group("failed")),
        "modules": int(match.group("modules")),
        "targets": int(match.group("targets")),
        "tests": int(match.group("tests")),
    }
    if result != {
        "failed": 0,
        "modules": verify_release.EXPECTED_TEST_MODULES,
        "targets": verify_release.EXPECTED_TEST_TARGETS,
        "tests": verify_release.EXPECTED_TEST_COUNT,
    }:
        _fail(f"authoritative regression summary mismatch: {result}")
    return result


def _combined_output(record: Mapping[str, Any], output_root: Path) -> str:
    return (output_root / str(record["stdout_path"])).read_text(encoding="utf-8") + (
        output_root / str(record["stderr_path"])
    ).read_text(encoding="utf-8")


def _output_file_inventory(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            _fail(f"audit evidence contains a symlink: {relative}")
        if path.is_file():
            files[verify_release._safe_relative(relative, "audit evidence")] = (
                verify_release.sha256_file(path)
            )
        elif not path.is_dir():
            _fail(f"audit evidence contains an unsupported object: {relative}")
    return files


def _expected_command_files(records: Sequence[Mapping[str, Any]]) -> set[str]:
    paths: set[str] = set()
    for record in records:
        paths.add(verify_release._safe_relative(record.get("stdout_path"), "command"))
        paths.add(verify_release._safe_relative(record.get("stderr_path"), "command"))
    return paths


def _source_root_is_safe(source_root: Path) -> None:
    if (
        source_root != SOURCE_ROOT
        or source_root.is_symlink()
        or not source_root.is_dir()
    ):
        _fail("authoritative source must be mounted read-only at /audit-source")


def _characterization_report(
    providers: Mapping[str, Any],
    first: Mapping[str, Any],
    second: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        provider_id: {
            "assertions": item["assertions"],
            "command_ids": [
                "release-regression",
                "provider-matrix-b",
                "characterization-a",
                "characterization-b",
            ],
            "deterministic_facts_sha256": item["deterministic_facts_sha256"],
            "evidence_mapping_sha256": item["evidence_mapping_sha256"],
            "fixture_input_sha256": item["fixture_input_sha256"],
            "output_path": first["stdout_path"],
            "output_sha256": first["stdout_sha256"],
            "provider_output_sha256": item["provider_output_sha256"],
            "repeat_output_path": second["stdout_path"],
            "repeat_output_sha256": second["stdout_sha256"],
            "status": "passed",
        }
        for provider_id, item in sorted(providers.items())
    }


def _target_record() -> dict[str, Any]:
    return {
        "architecture": platform.machine(),
        "base_image_digest": verify_release.EXPECTED_BASE_IMAGE[
            "linux_amd64_manifest_digest"
        ],
        "git_version": verify_release.EXPECTED_GIT["version"],
        "node_version": verify_release.EXPECTED_NODE["version"],
        "os": platform.system().lower(),
        "python_path": str(RUNTIME_PYTHON),
        "python_version": platform.python_version(),
        "release_root": str(RELEASE_ROOT),
        "state_root": str(STATE_ROOT),
        "uid": os.getuid(),
    }


def run_production_audit(
    *,
    source_root: Path,
    output_root: Path,
    image_id: str,
) -> int:
    _assert_platform()
    _prepare_output_root(output_root, PRODUCTION_OUTPUT_ROOT)
    verify_release._require_image_digest(image_id, "production image ID")
    _source_root_is_safe(source_root)
    environment = _audit_environment(source_root)
    environment["MINGLI_PRODUCTION_IMAGE_ID"] = image_id
    recorder = CommandRecorder(output_root, image_id)

    sbom_regeneration = recorder.run(
        "sbom-regeneration",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(SBOM_SCRIPT),
        ),
        cwd=RELEASE_ROOT,
        environment=environment,
        timeout=300,
    )
    _copy_file(
        output_root / str(sbom_regeneration["stdout_path"]),
        output_root / "sbom.cdx.json",
    )

    inventory_path = output_root / "evidence/runtime-inventory.json"
    recorder.run(
        "runtime-inventory",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(VERIFIER),
            "--release-root",
            str(RELEASE_ROOT),
            "--runtime-python",
            str(RUNTIME_PYTHON),
            "--node",
            str(NODE),
            "--git",
            str(GIT),
            "--state-root",
            str(STATE_ROOT),
            "--inventory-output",
            str(inventory_path),
        ),
        cwd=RELEASE_ROOT,
        environment=environment,
        timeout=900,
    )
    regression = recorder.run(
        "release-regression",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(source_root / "scripts/run_test_suite.py"),
            "--jobs",
            "10",
            "--research-root",
            str(source_root),
        ),
        cwd=source_root,
        environment=environment,
        timeout=RELEASE_REGRESSION_TIMEOUT_SECONDS,
    )
    _parse_regression(regression, output_root)
    matrix_argv = (
        str(RUNTIME_PYTHON),
        "-B",
        str(source_root / "scripts/audit_provider_completeness.py"),
        "--check",
        "--matrix",
        str(source_root / "references/matrices/provider-completeness.yaml"),
    )
    matrix_b = recorder.run(
        "provider-matrix-b",
        matrix_argv,
        cwd=source_root,
        environment=environment,
        timeout=PROVIDER_MATRIX_TIMEOUT_SECONDS,
    )
    characterization_argv = (
        str(RUNTIME_PYTHON),
        "-B",
        str(AUDIT_SCRIPT),
        "--emit-characterization",
        "--source-root",
        str(source_root),
    )
    characterization_a = recorder.run(
        "characterization-a",
        characterization_argv,
        cwd=source_root,
        environment=environment,
        timeout=60,
    )
    characterization_b = recorder.run(
        "characterization-b",
        characterization_argv,
        cwd=source_root,
        environment=environment,
        timeout=60,
    )
    p0 = recorder.run(
        "p0-trajectories",
        (
            str(RUNTIME_PYTHON),
            "-B",
            "-m",
            "unittest",
            "-v",
            "test_v51_bazi_fortune_completion",
            "test_v51_liuyao_completion",
            "test_v51_portable_interface",
        ),
        cwd=source_root / "scripts",
        environment=environment,
        timeout=3600,
    )
    machine_probe = recorder.run(
        "runtime-probe-machine",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(AUDIT_SCRIPT),
            "--emit-runtime-probes",
            "--state-root",
            str(STATE_ROOT),
        ),
        cwd=RELEASE_ROOT,
        environment=environment,
        timeout=300,
    )
    unittest_probe = recorder.run(
        "runtime-probe-unittest",
        (
            str(RUNTIME_PYTHON),
            "-B",
            "-m",
            "unittest",
            "-v",
            "test_v51_pending_atomicity",
            "test_v51_state_token",
            "test_runtime_launcher",
        ),
        cwd=source_root / "scripts",
        environment=environment,
        timeout=3600,
    )
    git_smoke = recorder.run(
        "git-smoke",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(AUDIT_SCRIPT),
            "--emit-git-smoke",
        ),
        cwd=RELEASE_ROOT,
        environment=environment,
        timeout=300,
    )
    recorder.run(
        "production-native-linkage",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(AUDIT_SCRIPT),
            "--emit-native-linkage",
        ),
        cwd=RELEASE_ROOT,
        environment=environment,
        timeout=300,
    )
    recorder.run(
        "production-tree-identity",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(AUDIT_SCRIPT),
            "--emit-tree-identity",
        ),
        cwd=RELEASE_ROOT,
        environment=environment,
        timeout=900,
    )

    if characterization_a["stdout_sha256"] != characterization_b["stdout_sha256"]:
        _fail("characterization child output changed across two runs")
    machine_characterization = _read_json(
        output_root / str(characterization_a["stdout_path"]),
        "characterization machine output",
    )
    providers = machine_characterization.get("providers")
    if not isinstance(providers, dict) or not all(
        isinstance(item, dict) and item.get("ready") is True
        for item in providers.values()
    ):
        _fail("characterization machine output is not 13/13 ready")
    p0_sentinels = {
        "bazi": "test_full_structured_chart_prepares_with_clean_brief",
        "fortune_day": "test_fortune_is_one_day_view_over_the_same_natal_fact_identity",
        "fortune_week": "test_broad_weekly_question_prepares_with_default_dimensions",
        "liuyao_digital": "test_seeded_digital_cast_is_reproducible_and_records_coin_faces",
        "liuyao_manual": "test_provider_calculates_supplied_cast_and_binds_shared_calendar",
    }
    p0_output = _combined_output(p0, output_root)
    p0_assertions = {
        name: sentinel in p0_output for name, sentinel in p0_sentinels.items()
    }
    if not all(p0_assertions.values()):
        _fail(f"P0 trajectory sentinel missing: {p0_assertions}")
    probe_machine_output = _read_json(
        output_root / str(machine_probe["stdout_path"]),
        "runtime probe machine output",
    )
    probe_output = _combined_output(unittest_probe, output_root)
    probe_assertions = dict(probe_machine_output.get("assertions") or {})
    probe_assertions.update(
        {
            "concurrency_fenced": (
                "test_concurrent_children_yield_exactly_one_winner" in probe_output
            ),
            "token_replay_byte_stable": all(
                sentinel in probe_output
                for sentinel in (
                    "test_one_prepared_token_completes_and_replay_is_idempotent",
                    "test_accept_commit_is_first_write_wins_and_byte_stable",
                )
            ),
        }
    )
    if not all(probe_assertions.values()):
        _fail(f"runtime probe sentinel missing: {probe_assertions}")
    git_smoke_payload = _read_json(
        output_root / str(git_smoke["stdout_path"]),
        "Git smoke machine output",
    )
    verify_release.validate_git_smoke_payload(git_smoke_payload)

    _copy_file(
        RUNTIME_PYTHON.parent.parent / "runtime-integrity.json",
        output_root / "evidence/runtime-integrity.json",
    )
    _copy_file(
        RELEASE_ROOT / verify_release.MANIFEST_NAME,
        output_root / "evidence/release-manifest.json",
    )
    _copy_file(PROVENANCE, output_root / "evidence/dependency-provenance.json")

    inventory = _read_json(inventory_path, "runtime inventory")
    production_evidence: dict[str, Any] = {
        "characterization": _characterization_report(
            providers,
            characterization_a,
            characterization_b,
        ),
        "commands": recorder.records,
        "generated_by": str(AUDIT_SCRIPT),
        "image_id": image_id,
        "git_smoke": {
            "command_id": "git-smoke",
            "output_sha256": git_smoke["stdout_sha256"],
            "status": "passed",
        },
        "inventory": {
            "evidence_index_count": inventory["evidence_index_count"],
            "evidence_rule_ids_unique": inventory["evidence_rule_ids_unique"],
            "provider_count": inventory["provider_count"],
            "provider_ids": inventory["provider_ids"],
            "readiness": inventory["readiness"],
            "reference_pack_count": inventory["reference_pack_count"],
            "runtime_closure_verified": inventory["runtime_closure_verified"],
        },
        "p0_trajectories": {
            "assertions": p0_assertions,
            "command_ids": ["p0-trajectories"],
            "status": "passed",
        },
        "probes": {
            "assertions": probe_assertions,
            "command_ids": ["runtime-probe-machine", "runtime-probe-unittest"],
            "status": "passed",
        },
        "provider_matrix": {
            "runs": [
                {
                    "command_id": command["id"],
                    "elapsed_seconds": command["elapsed_seconds"],
                    "timeout_seconds": command["timeout_seconds"],
                }
                for command in (regression, matrix_b)
            ],
            "status": "passed",
        },
        "schema_version": "mingli-production-evidence-v1",
        "target": _target_record(),
    }
    observed_ids = {record["id"] for record in recorder.records}
    if observed_ids != PRODUCTION_COMMAND_IDS:
        _fail("production command inventory is incomplete")
    expected_files = {
        "evidence/dependency-provenance.json",
        "evidence/release-manifest.json",
        "evidence/runtime-integrity.json",
        "evidence/runtime-inventory.json",
        "sbom.cdx.json",
        *_expected_command_files(recorder.records),
    }
    files = _output_file_inventory(output_root)
    if set(files) != expected_files:
        _fail("production evidence file inventory is not exact")
    production_evidence["files"] = files
    path = output_root / "production-evidence.json"
    _write_json(path, production_evidence)
    print(path)
    return 0


def _copy_production_evidence(
    source: Path,
    output_root: Path,
    image_id: str,
) -> dict[str, Any]:
    evidence = _read_json(source, "production evidence")
    if evidence.get("schema_version") != "mingli-production-evidence-v1":
        _fail("production evidence schema mismatch")
    if evidence.get("image_id") != image_id:
        _fail("production evidence image identity mismatch")
    commands = evidence.get("commands")
    if (
        not isinstance(commands, list)
        or {item.get("id") for item in commands if isinstance(item, dict)}
        != PRODUCTION_COMMAND_IDS
    ):
        _fail("production evidence command inventory mismatch")
    if any(
        not isinstance(item, dict) or item.get("executed_in_image_id") != image_id
        for item in commands
    ):
        _fail("production evidence contains a command from another image")
    files = evidence.get("files")
    if not isinstance(files, dict):
        _fail("production evidence file inventory is missing")
    expected_files = {
        "evidence/dependency-provenance.json",
        "evidence/release-manifest.json",
        "evidence/runtime-integrity.json",
        "evidence/runtime-inventory.json",
        "sbom.cdx.json",
        *_expected_command_files(commands),
    }
    if set(files) != expected_files:
        _fail("production evidence file inventory differs from its command evidence")
    source_root = source.parent
    observed = _output_file_inventory(source_root)
    if set(observed) != expected_files | {"production-evidence.json"}:
        _fail("production evidence bundle contains extras or omissions")
    for relative, expected_digest in files.items():
        verify_release._require_sha256(
            expected_digest, f"production evidence {relative}"
        )
        if observed.get(relative) != expected_digest:
            _fail(f"production evidence digest mismatch: {relative}")
        _copy_file(source_root / relative, output_root / relative)
    _copy_file(source, output_root / "evidence/production-evidence.json")
    return evidence


def finalize_audit(
    *,
    source_root: Path,
    output_root: Path,
    production_evidence_path: Path,
    backup_evidence: Path,
    image_id: str,
    image_digest: str,
    audit_image_id: str,
) -> int:
    _assert_platform()
    _prepare_output_root(output_root, OUTPUT_ROOT)
    for label, value in (
        ("production image ID", image_id),
        ("production image digest", image_digest),
        ("audit image ID", audit_image_id),
    ):
        verify_release._require_image_digest(value, label)
    if image_id != image_digest:
        _fail("local production image ID and OCI config digest must be identical")
    if audit_image_id != image_id:
        _fail("audit image must be an alias of the exact production OCI config")
    _source_root_is_safe(source_root)
    production = _copy_production_evidence(
        production_evidence_path,
        output_root,
        image_id,
    )
    environment = _audit_environment(source_root)
    environment["MINGLI_PRODUCTION_IMAGE_ID"] = image_id
    recorder = CommandRecorder(output_root, audit_image_id)

    source_binding_path = output_root / "evidence/source-binding.json"
    recorder.run(
        "source-binding",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(VERIFIER),
            "--release-root",
            str(RELEASE_ROOT),
            "--research-source",
            str(source_root),
            "--release-only",
            "--inventory-output",
            str(source_binding_path),
        ),
        cwd=RELEASE_ROOT,
        environment=environment,
        timeout=1800,
    )
    audit_tree = recorder.run(
        "audit-tree-identity",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(AUDIT_SCRIPT),
            "--emit-tree-identity",
        ),
        cwd=RELEASE_ROOT,
        environment=environment,
        timeout=900,
    )
    audit_native_linkage = recorder.run(
        "audit-native-linkage",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(AUDIT_SCRIPT),
            "--emit-native-linkage",
        ),
        cwd=RELEASE_ROOT,
        environment=environment,
        timeout=300,
    )
    if {record["id"] for record in recorder.records} != AUDIT_COMMAND_IDS:
        _fail("derived audit command inventory is incomplete")
    production_commands = {
        str(record["id"]): record for record in production["commands"]
    }
    regression = production_commands["release-regression"]
    production_native_linkage = production_commands["production-native-linkage"]
    if (
        production_native_linkage["stdout_sha256"]
        != audit_native_linkage["stdout_sha256"]
    ):
        _fail("derived audit image changed native runtime linkage")
    production_native_payload = _read_json(
        output_root / str(production_native_linkage["stdout_path"]),
        "production native linkage",
    )
    audit_native_payload = _read_json(
        output_root / str(audit_native_linkage["stdout_path"]),
        "audit native linkage",
    )
    if production_native_payload != audit_native_payload:
        _fail("production and audit native linkage identities differ")
    runtime_inventory = _read_json(
        output_root / "evidence/runtime-inventory.json",
        "runtime inventory",
    )
    if runtime_inventory.get("native_linkage") != production_native_payload:
        _fail("runtime inventory and production native linkage differ")
    production_tree = production_commands["production-tree-identity"]
    if production_tree["stdout_sha256"] != audit_tree["stdout_sha256"]:
        _fail("derived audit image changed an admitted runtime tree")
    production_tree_payload = _read_json(
        output_root / str(production_tree["stdout_path"]),
        "production runtime tree identity",
    )
    audit_tree_payload = _read_json(
        output_root / str(audit_tree["stdout_path"]),
        "audit runtime tree identity",
    )
    if production_tree_payload != audit_tree_payload:
        _fail("production and audit runtime tree identities differ")
    source_binding = _read_json(source_binding_path, "source binding")
    if source_binding.get("authoritative_source") != {
        "clean": True,
        "fulltext_count": 55,
        "signed_release_files_matched": 217,
        "source_commit": verify_release.EXPECTED_RELEASE["source_commit"],
    }:
        _fail("authoritative source binding is incomplete")
    regression_summary = _parse_regression(regression, output_root)
    backup_path = _copy_backup_evidence(backup_evidence, output_root)
    backup = _read_json(backup_path, "backup/restore evidence")
    provenance = _read_json(PROVENANCE, "dependency provenance")
    python_distributions = provenance["python_distributions"]
    all_commands = [*production["commands"], *recorder.records]
    report = {
        "artifact": {
            "base_image_digest": verify_release.EXPECTED_BASE_IMAGE[
                "linux_amd64_manifest_digest"
            ],
            "image_digest": image_digest,
            "image_digest_kind": "oci_config",
            "runtime_integrity_sha256": verify_release.sha256_file(
                output_root / "evidence/runtime-integrity.json"
            ),
            "sbom_command_id": "sbom-regeneration",
            "sbom_path": "sbom.cdx.json",
            "sbom_sha256": verify_release.sha256_file(output_root / "sbom.cdx.json"),
        },
        "audit": {
            "audit_image_id": audit_image_id,
            "commands": all_commands,
            "completed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generator": str(AUDIT_SCRIPT),
            "image_id": image_id,
        },
        "backup_restore": {
            **{
                field: backup.get(field)
                for field in verify_release.EXPECTED_BACKUP_FLAGS
            },
            "command_ids": sorted(
                record["id"] for record in backup.get("commands", [])
            ),
            "status": "passed",
        },
        "characterization": production["characterization"],
        "git_smoke": production["git_smoke"],
        "dependencies": {
            "astronomy-engine": python_distributions["astronomy-engine"],
            "cnlunar": python_distributions["cnlunar"],
            "git": provenance["git"],
            "iztro": provenance["vendored"]["iztro"],
            "libatomic1": provenance["system_runtime"]["libatomic1"],
            "node": provenance["node"],
            "pyyaml": python_distributions["PyYAML"],
            "sxtwl": python_distributions["sxtwl"],
        },
        "evidence": {
            "backup_restore_path": backup_path.relative_to(output_root).as_posix(),
            "backup_restore_sha256": verify_release.sha256_file(backup_path),
            "dependency_provenance_path": "evidence/dependency-provenance.json",
            "dependency_provenance_sha256": verify_release.sha256_file(
                output_root / "evidence/dependency-provenance.json"
            ),
            "production_evidence_path": "evidence/production-evidence.json",
            "production_evidence_sha256": verify_release.sha256_file(
                output_root / "evidence/production-evidence.json"
            ),
            "release_manifest_path": "evidence/release-manifest.json",
            "runtime_integrity_path": "evidence/runtime-integrity.json",
            "runtime_inventory_path": "evidence/runtime-inventory.json",
            "runtime_inventory_sha256": verify_release.sha256_file(
                output_root / "evidence/runtime-inventory.json"
            ),
            "source_binding_path": "evidence/source-binding.json",
            "source_binding_sha256": verify_release.sha256_file(source_binding_path),
        },
        "inventory": production["inventory"],
        "p0_trajectories": production["p0_trajectories"],
        "probes": production["probes"],
        "provider_matrix": production["provider_matrix"],
        "product_policy": {
            "p0_provider_ids": sorted(verify_release.EXPECTED_P0_PROVIDERS)
        },
        "release": dict(verify_release.EXPECTED_RELEASE),
        "release_regression": {
            "command_id": "release-regression",
            "elapsed_seconds": regression["elapsed_seconds"],
            "executed_in_image_id": image_id,
            "module_count": regression_summary["modules"],
            "status": "passed",
            "target_count": regression_summary["targets"],
            "test_count": regression_summary["tests"],
            "timeout_seconds": regression["timeout_seconds"],
        },
        "runtime_tree_identity": {
            "audit_command_id": "audit-tree-identity",
            "production_command_id": "production-tree-identity",
            "sha256": production_tree["stdout_sha256"],
            "status": "passed",
        },
        "runtime_native_linkage_identity": {
            "audit_command_id": "audit-native-linkage",
            "payload_sha256": verify_release.canonical_sha256(
                production_native_payload
            ),
            "production_command_id": "production-native-linkage",
            "sha256": production_native_linkage["stdout_sha256"],
            "status": "passed",
            "targets": ["git", "node", "python", "sxtwl", "yaml_c_extension"],
        },
        "schema_version": "mingli-linux-runtime-audit-v1",
        "source_binding": {"command_id": "source-binding", "status": "passed"},
        "target": production["target"],
    }
    verify_release.validate_audit_report(report, artifacts_root=output_root)
    _write_json(output_root / "release-5.1.json", report)
    print(output_root / "release-5.1.json")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--emit-characterization", action="store_true")
    mode.add_argument("--emit-runtime-probes", action="store_true")
    mode.add_argument("--emit-token-record", action="store_true")
    mode.add_argument("--emit-tree-identity", action="store_true")
    mode.add_argument("--emit-native-linkage", action="store_true")
    mode.add_argument("--emit-git-smoke", action="store_true")
    mode.add_argument("--emit-state-root-identity", action="store_true")
    mode.add_argument("--production-audit", action="store_true")
    mode.add_argument("--finalize-audit", action="store_true")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--state-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--backup-evidence", type=Path)
    parser.add_argument("--production-evidence", type=Path)
    parser.add_argument("--image-id")
    parser.add_argument("--image-digest")
    parser.add_argument("--audit-image-id")
    args = parser.parse_args(argv)
    try:
        if args.emit_characterization:
            if args.source_root is None:
                parser.error("--emit-characterization requires --source-root")
            return emit_characterization(args.source_root)
        if args.emit_runtime_probes:
            if args.state_root is None:
                parser.error("--emit-runtime-probes requires --state-root")
            return emit_runtime_probes(args.state_root)
        if args.emit_token_record:
            if args.state_root is None:
                parser.error("--emit-token-record requires --state-root")
            return emit_token_record(args.state_root)
        if args.emit_tree_identity:
            return emit_tree_identity()
        if args.emit_native_linkage:
            return emit_native_linkage()
        if args.emit_git_smoke:
            return emit_git_smoke()
        if args.emit_state_root_identity:
            if args.state_root is None:
                parser.error("--emit-state-root-identity requires --state-root")
            return emit_state_root_identity(args.state_root)
        if args.production_audit:
            required = {
                "image_id": args.image_id,
                "output_root": args.output_root,
                "source_root": args.source_root,
            }
            missing = sorted(name for name, value in required.items() if value is None)
            if missing:
                parser.error("production audit is missing: " + ", ".join(missing))
            return run_production_audit(
                source_root=args.source_root,
                output_root=args.output_root,
                image_id=args.image_id,
            )
        required = {
            "audit_image_id": args.audit_image_id,
            "backup_evidence": args.backup_evidence,
            "image_digest": args.image_digest,
            "image_id": args.image_id,
            "output_root": args.output_root,
            "production_evidence": args.production_evidence,
            "source_root": args.source_root,
        }
        missing = sorted(name for name, value in required.items() if value is None)
        if missing:
            parser.error("audit finalization is missing: " + ", ".join(missing))
        return finalize_audit(
            source_root=args.source_root,
            output_root=args.output_root,
            production_evidence_path=args.production_evidence,
            backup_evidence=args.backup_evidence,
            image_id=args.image_id,
            image_digest=args.image_digest,
            audit_image_id=args.audit_image_id,
        )
    except (AuditError, verify_release.ReleaseVerificationError) as exc:
        print(f"runtime audit failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
