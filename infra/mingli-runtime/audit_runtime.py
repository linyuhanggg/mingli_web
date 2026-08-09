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
AUDIT_SCRIPT = Path("/opt/mingli-runtime/audit_runtime.py")
VERIFIER = Path("/opt/mingli-runtime/verify_release.py")
PROVENANCE = Path("/opt/mingli-runtime/dependency-provenance.json")
STATE_ROOT = Path("/var/lib/mingli")
SOURCE_ROOT = Path("/audit-source")
OUTPUT_ROOT = Path("/audit-output")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


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


def _probe_launcher_timeout(state_root: Path) -> bool:
    """Timeout the real shell launcher and prove its process group is gone."""

    with tempfile.TemporaryDirectory(prefix="mingli-timeout-probe-") as temporary:
        root = Path(temporary)
        hanging_python = root / "python-hang"
        pid_path = root / "pid"
        hanging_python.write_text(
            "#!/usr/local/bin/python3.14\n"
            "import os,time\n"
            "open(os.environ['MINGLI_HANG_PID'], 'w').write(str(os.getpid()))\n"
            "while True: time.sleep(60)\n",
            encoding="utf-8",
        )
        hanging_python.chmod(0o700)
        environment = {
            "HOME": "/nonexistent",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "MINGLI_HANG_PID": str(pid_path),
            "MINGLI_PYTHON": str(hanging_python),
            "MINGLI_STORE_ROOT": str(state_root),
            "PATH": "/opt/node/bin:/usr/local/bin:/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TZ": "UTC",
        }
        process = subprocess.Popen(
            [str(RELEASE_ROOT / "scripts/run_reading_transaction.sh")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=RELEASE_ROOT,
            env=environment,
            start_new_session=True,
            text=True,
        )
        timed_out = False
        try:
            process.communicate('{"kind":"describe"}\n', timeout=0.2)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=2)
        if not timed_out or process.returncode is None:
            return False
        if not pid_path.is_file() or pid_path.read_text(encoding="utf-8") != str(
            process.pid
        ):
            return False
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
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


def _audit_environment(source_root: Path) -> dict[str, str]:
    home = Path("/tmp/mingli-linux-audit-home")
    home.mkdir(mode=0o700, exist_ok=True)
    home.chmod(0o700)
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "MINGLI_PYTHON": str(RUNTIME_PYTHON),
            "MINGLI_RESEARCH_ROOT": str(source_root),
            "MINGLI_STORE_ROOT": str(STATE_ROOT),
            "PATH": "/opt/node/bin:/opt/mingli-runtime/venv/bin:/usr/local/bin:/usr/bin:/bin",
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
    transcripts = evidence.get("transcripts")
    commands = evidence.get("commands")
    if not isinstance(snapshots, dict) or not isinstance(transcripts, dict):
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


def _prepare_output_root(output_root: Path) -> None:
    if output_root != OUTPUT_ROOT:
        _fail("audit output root must be /audit-output")
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


def run_audit(
    *,
    source_root: Path,
    output_root: Path,
    sbom: Path,
    backup_evidence: Path,
    image_id: str,
    image_digest: str,
    audit_image_id: str,
) -> int:
    _assert_platform()
    _prepare_output_root(output_root)
    for label, value in (
        ("production image ID", image_id),
        ("production image digest", image_digest),
        ("audit image ID", audit_image_id),
    ):
        verify_release._require_image_digest(value, label)
    if image_id != image_digest:
        _fail("local production image ID and OCI config digest must be identical")
    if (
        source_root != SOURCE_ROOT
        or source_root.is_symlink()
        or not source_root.is_dir()
    ):
        _fail("authoritative source must be mounted read-only at /audit-source")
    environment = _audit_environment(source_root)
    recorder = CommandRecorder(output_root, audit_image_id)

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
            "--state-root",
            str(STATE_ROOT),
            "--research-source",
            str(source_root),
            "--inventory-output",
            str(inventory_path),
        ),
        cwd=RELEASE_ROOT,
        environment=environment,
        timeout=900,
    )
    matrix_argv = (
        str(RUNTIME_PYTHON),
        "-B",
        str(source_root / "scripts/audit_provider_completeness.py"),
        "--check",
        "--matrix",
        str(source_root / "references/matrices/provider-completeness.yaml"),
    )
    recorder.run(
        "provider-matrix-a",
        matrix_argv,
        cwd=source_root,
        environment=environment,
        timeout=3600,
    )
    recorder.run(
        "provider-matrix-b",
        matrix_argv,
        cwd=source_root,
        environment=environment,
        timeout=3600,
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
    regression = recorder.run(
        "release-regression",
        (
            str(RUNTIME_PYTHON),
            "-B",
            str(source_root / "scripts/run_test_suite.py"),
            "--jobs",
            "5",
            "--research-root",
            str(source_root),
        ),
        cwd=source_root,
        environment=environment,
        timeout=10800,
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
    regression_summary = _parse_regression(regression, output_root)
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

    _copy_file(sbom, output_root / "sbom.cdx.json")
    _copy_file(
        RUNTIME_PYTHON.parent.parent / "runtime-integrity.json",
        output_root / "evidence/runtime-integrity.json",
    )
    _copy_file(
        RELEASE_ROOT / verify_release.MANIFEST_NAME,
        output_root / "evidence/release-manifest.json",
    )
    _copy_file(PROVENANCE, output_root / "evidence/dependency-provenance.json")
    backup_path = _copy_backup_evidence(backup_evidence, output_root)

    inventory = _read_json(inventory_path, "runtime inventory")
    provenance = _read_json(PROVENANCE, "dependency provenance")
    backup = _read_json(backup_path, "backup/restore evidence")
    python_distributions = provenance["python_distributions"]
    characterization_report = {
        provider_id: {
            "assertions": item["assertions"],
            "command_ids": [
                "provider-matrix-a",
                "provider-matrix-b",
                "characterization-a",
                "characterization-b",
            ],
            "deterministic_facts_sha256": item["deterministic_facts_sha256"],
            "evidence_mapping_sha256": item["evidence_mapping_sha256"],
            "fixture_input_sha256": item["fixture_input_sha256"],
            "output_path": characterization_a["stdout_path"],
            "output_sha256": characterization_a["stdout_sha256"],
            "provider_output_sha256": item["provider_output_sha256"],
            "repeat_output_path": characterization_b["stdout_path"],
            "repeat_output_sha256": characterization_b["stdout_sha256"],
            "status": "passed",
        }
        for provider_id, item in sorted(providers.items())
    }
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
            "sbom_path": "sbom.cdx.json",
            "sbom_sha256": verify_release.sha256_file(output_root / "sbom.cdx.json"),
        },
        "audit": {
            "audit_image_id": audit_image_id,
            "commands": recorder.records,
            "completed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generator": str(AUDIT_SCRIPT),
            "image_id": image_id,
        },
        "backup_restore": {
            "accepted_token_replayed": backup.get("accepted_token_replayed"),
            "command_ids": sorted(
                record["id"] for record in backup.get("commands", [])
            ),
            "prepared_token_restored": backup.get("prepared_token_restored"),
            "status": "passed",
        },
        "characterization": characterization_report,
        "dependencies": {
            "astronomy-engine": python_distributions["astronomy-engine"],
            "cnlunar": python_distributions["cnlunar"],
            "iztro": provenance["vendored"]["iztro"],
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
            "release_manifest_path": "evidence/release-manifest.json",
            "runtime_integrity_path": "evidence/runtime-integrity.json",
            "runtime_inventory_path": "evidence/runtime-inventory.json",
            "runtime_inventory_sha256": verify_release.sha256_file(inventory_path),
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
        "product_policy": {
            "p0_provider_ids": sorted(verify_release.EXPECTED_P0_PROVIDERS)
        },
        "release": dict(verify_release.EXPECTED_RELEASE),
        "release_regression": {
            "command_id": "release-regression",
            "module_count": regression_summary["modules"],
            "status": "passed",
            "target_count": regression_summary["targets"],
            "test_count": regression_summary["tests"],
        },
        "schema_version": "mingli-linux-runtime-audit-v1",
        "target": {
            "architecture": platform.machine(),
            "base_image_digest": verify_release.EXPECTED_BASE_IMAGE[
                "linux_amd64_manifest_digest"
            ],
            "node_version": verify_release.EXPECTED_NODE["version"],
            "os": platform.system().lower(),
            "python_path": str(RUNTIME_PYTHON),
            "python_version": platform.python_version(),
            "release_root": str(RELEASE_ROOT),
            "state_root": str(STATE_ROOT),
            "uid": os.getuid(),
        },
    }
    verify_release.validate_audit_report(report, artifacts_root=output_root)
    _write_json(output_root / "release-5.1.json", report)
    print(output_root / "release-5.1.json")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--emit-characterization", action="store_true")
    mode.add_argument("--emit-runtime-probes", action="store_true")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--state-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--sbom", type=Path)
    parser.add_argument("--backup-evidence", type=Path)
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
        required = {
            "audit_image_id": args.audit_image_id,
            "backup_evidence": args.backup_evidence,
            "image_digest": args.image_digest,
            "image_id": args.image_id,
            "output_root": args.output_root,
            "sbom": args.sbom,
            "source_root": args.source_root,
        }
        missing = sorted(name for name, value in required.items() if value is None)
        if missing:
            parser.error("full audit is missing: " + ", ".join(missing))
        return run_audit(
            source_root=args.source_root,
            output_root=args.output_root,
            sbom=args.sbom,
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
