#!/usr/bin/env python3
"""Build and audit Mingli V5.1 through a mountless Lima Docker boundary.

The macOS host never assumes that its filesystem is visible in the guest.
Build contexts and clean research source are streamed over ``limactl shell``;
audit inputs and outputs cross the boundary only through uniquely named Docker
volumes and tar streams. Raw runtime tokens, snapshot plaintext and one-time
pads stay in process memory and are never written to the evidence directory.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

import build_context

EXPECTED_COMMIT = "494ce0bba174a77800daf9b9c38ce9c9166d9a94"
EXPECTED_FULLTEXT_COUNT = 54
RUNTIME_UID = 10001
RUNTIME_GID = 10001
IMAGE_ID_RE = re.compile(r"sha256:[0-9a-f]{64}")
VOLUME_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{0,127}")
RUNTIME_TMPFS = "/tmp:rw,noexec,nosuid,nodev,size=128m,mode=1777"
PUBLIC_COPY = "Linux 恢复演练固定正文。"
FOLLOWUP_PUBLIC_COPY = "Linux 恢复演练追问固定正文。"


class GateError(RuntimeError):
    """The real Linux Gate cannot produce admissible evidence."""


def _fail(message: str) -> NoReturn:
    raise GateError(message)


def sha256_bytes(value: bytes | bytearray) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _safe_relative(raw: str) -> str:
    if not raw or "\\" in raw:
        _fail(f"unsafe evidence path: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        _fail(f"unsafe evidence path: {raw!r}")
    return path.as_posix()


def _run_local(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        input=input_bytes,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-4000:]
        _fail(f"host command failed ({' '.join(argv)}): {stderr}")
    return completed


def _tar_tree(root: Path) -> bytes:
    root = root.resolve(strict=True)
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for path in sorted(
            root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
        ):
            relative = path.relative_to(root).as_posix()
            _safe_relative(relative)
            if path.is_symlink():
                _fail(f"tar source contains a symlink: {relative}")
            info = archive.gettarinfo(str(path), arcname=relative)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            if path.is_dir():
                archive.addfile(info)
            elif path.is_file():
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
            else:
                _fail(f"tar source contains an unsupported object: {relative}")
    return output.getvalue()


def _extract_safe_tar(payload: bytes, destination: Path) -> None:
    if (
        destination.is_symlink()
        or not destination.is_dir()
        or any(destination.iterdir())
    ):
        _fail("audit output destination must exist and start empty")
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
        members = archive.getmembers()
        for member in members:
            if member.name in {".", "./"}:
                if not member.isdir():
                    _fail("audit output tar root member is not a directory")
                continue
            raw_relative = member.name.removeprefix("./")
            relative = _safe_relative(raw_relative)
            if member.issym() or member.islnk() or member.isdev():
                _fail(f"audit output contains an unsafe tar member: {relative}")
            target = destination / relative
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                target.chmod(0o700)
                continue
            if not member.isfile():
                _fail(f"audit output contains an unsupported tar member: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                _fail(f"audit output file cannot be extracted: {relative}")
            with target.open("wb") as stream:
                shutil.copyfileobj(source, stream)
            target.chmod(0o600)


class LimaDocker:
    def __init__(self, instance: str) -> None:
        self.instance = instance

    def run(
        self,
        argv: Sequence[str],
        *,
        input_bytes: bytes | bytearray | None = None,
        capture: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        command = ["limactl", "shell", self.instance, "--", *argv]
        completed = subprocess.run(
            command,
            input=input_bytes,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            check=False,
            timeout=timeout,
        )
        if completed.returncode != 0:
            stderr = (
                completed.stderr.decode("utf-8", errors="replace")[-4000:]
                if completed.stderr is not None
                else "see streamed Linux Gate output"
            )
            _fail(f"Lima command failed ({' '.join(argv)}): {stderr}")
        return completed

    def docker(
        self,
        argv: Sequence[str],
        *,
        input_bytes: bytes | bytearray | None = None,
        capture: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        return self.run(
            ["docker", *argv],
            input_bytes=input_bytes,
            capture=capture,
            timeout=timeout,
        )

    def create_volume(self, name: str, run_id: str) -> None:
        if VOLUME_RE.fullmatch(name) is None:
            _fail(f"unsafe Docker volume name: {name}")
        result = self.docker(
            ["volume", "create", "--label", f"mingli.gate.run={run_id}", name]
        )
        if result.stdout.decode().strip() != name:
            _fail(f"Docker created an unexpected volume: {name}")

    def remove_volume(self, name: str) -> None:
        if VOLUME_RE.fullmatch(name) is None:
            return
        self.docker(["volume", "rm", "--force", name], capture=True)


def _prepare_research_source(
    repository: Path,
    installed_release: Path,
    destination: Path,
) -> Path:
    repository = repository.resolve(strict=True)
    installed_release = installed_release.resolve(strict=True)
    if destination.exists():
        _fail("research checkout destination already exists")
    _run_local(
        [
            "git",
            "clone",
            "--no-local",
            "--no-checkout",
            str(repository),
            str(destination),
        ],
        timeout=900,
    )
    _run_local(
        ["git", "-C", str(destination), "checkout", "--detach", EXPECTED_COMMIT],
        timeout=300,
    )
    alternates = destination / ".git/objects/info/alternates"
    if alternates.exists() and alternates.read_text(encoding="utf-8").strip():
        _fail("research checkout depends on an external Git object alternate")

    source_fulltexts = installed_release / "references/fulltext"
    fulltexts = sorted(source_fulltexts.glob("*/*/fulltext.md"))
    if len(fulltexts) != EXPECTED_FULLTEXT_COUNT:
        _fail("installed research source does not contain exactly 54 fulltexts")
    copied: list[str] = []
    for source in fulltexts:
        if source.is_symlink() or not source.is_file():
            _fail(f"research fulltext is missing or unsafe: {source}")
        relative = source.relative_to(installed_release)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target, follow_symlinks=False)
        target.chmod(0o644)
        copied.append(relative.as_posix())
    ignored = (
        _run_local(
            ["git", "-C", str(destination), "check-ignore", "--stdin"],
            input_bytes=("\n".join(copied) + "\n").encode("utf-8"),
        )
        .stdout.decode("utf-8")
        .splitlines()
    )
    if set(ignored) != set(copied):
        _fail("research fulltexts are not all covered by the source ignore policy")
    head = (
        _run_local(["git", "-C", str(destination), "rev-parse", "HEAD"])
        .stdout.decode()
        .strip()
    )
    status = _run_local(
        [
            "git",
            "-C",
            str(destination),
            "status",
            "--porcelain",
            "--untracked-files=all",
        ]
    ).stdout.decode()
    if head != EXPECTED_COMMIT or status.strip():
        _fail("research source is not a clean exact-commit checkout")
    _run_local(["git", "-C", str(destination), "fsck", "--no-dangling"], timeout=900)
    return destination


def _validate_image_id(value: str, label: str) -> str:
    if IMAGE_ID_RE.fullmatch(value) is None:
        _fail(f"{label} is not an OCI config digest: {value!r}")
    return value


def _docker_image_id(vm: LimaDocker, image: str) -> str:
    result = vm.docker(["image", "inspect", "--format", "{{.Id}}", image])
    return _validate_image_id(result.stdout.decode().strip(), "Docker image ID")


def _initialize_volume(
    vm: LimaDocker,
    image_id: str,
    volume: str,
    target: str,
    *,
    mode: str,
) -> None:
    mount = f"source={volume},target={target}"
    vm.docker(
        [
            "run",
            "--rm",
            "--network=none",
            "--user",
            "0:0",
            "--mount",
            mount,
            "--entrypoint",
            "/bin/chown",
            image_id,
            f"{RUNTIME_UID}:{RUNTIME_GID}",
            target,
        ]
    )
    vm.docker(
        [
            "run",
            "--rm",
            "--network=none",
            "--user",
            "0:0",
            "--mount",
            mount,
            "--entrypoint",
            "/bin/chmod",
            image_id,
            mode,
            target,
        ]
    )


def _populate_volume(
    vm: LimaDocker,
    image_id: str,
    volume: str,
    target: str,
    payload: bytes,
) -> None:
    vm.docker(
        [
            "run",
            "--rm",
            "-i",
            "--network=none",
            "--user",
            "0:0",
            "--mount",
            f"source={volume},target={target}",
            "--entrypoint",
            "/bin/tar",
            image_id,
            "-C",
            target,
            "-xf",
            "-",
        ],
        input_bytes=payload,
        timeout=1800,
    )
    vm.docker(
        [
            "run",
            "--rm",
            "--network=none",
            "--user",
            "0:0",
            "--mount",
            f"source={volume},target={target}",
            "--entrypoint",
            "/bin/chown",
            image_id,
            "-R",
            f"{RUNTIME_UID}:{RUNTIME_GID}",
            target,
        ],
        timeout=1800,
    )


class EvidenceWriter:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.commands: list[dict[str, Any]] = []

    def record(
        self,
        command_id: str,
        argv: Sequence[str],
        stdout: bytes,
        stderr: bytes = b"",
        *,
        stdout_capture: str,
    ) -> dict[str, Any]:
        if any(record["id"] == command_id for record in self.commands):
            _fail(f"duplicate backup evidence command: {command_id}")
        stdout_relative = f"evidence/backup/commands/{command_id}.stdout"
        stderr_relative = f"evidence/backup/commands/{command_id}.stderr"
        for relative, payload in (
            (stdout_relative, stdout),
            (stderr_relative, stderr),
        ):
            path = self.root / _safe_relative(relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            path.chmod(0o600)
        record = {
            "argv": list(argv),
            "exit_code": 0,
            "id": command_id,
            "stderr_path": stderr_relative,
            "stderr_sha256": sha256_bytes(stderr),
            "stdout_capture": stdout_capture,
            "stdout_path": stdout_relative,
            "stdout_sha256": sha256_bytes(stdout),
        }
        self.commands.append(record)
        return record


class BackupRestoreDrill:
    def __init__(
        self,
        vm: LimaDocker,
        image_id: str,
        volumes: Mapping[str, str],
        evidence_root: Path,
    ) -> None:
        self.vm = vm
        self.image_id = image_id
        self.volumes = volumes
        self.writer = EvidenceWriter(evidence_root)
        self.evidence_root = evidence_root

    def _runtime_argv(self, volume: str) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network=none",
            "--read-only",
            "--tmpfs",
            RUNTIME_TMPFS,
            "--mount",
            f"source={volume},target=/var/lib/mingli",
            self.image_id,
        ]

    def runtime(
        self,
        command_id: str,
        volume: str,
        command: Mapping[str, Any],
        *,
        expected_kind: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        command_payload = json_bytes(command)
        argv = self._runtime_argv(volume)
        started = time.monotonic()
        completed = self.vm.docker(argv[1:], input_bytes=command_payload, timeout=900)
        if completed.stderr:
            _fail(f"runtime backup command emitted stderr: {command_id}")
        lines = completed.stdout.splitlines()
        if len(lines) != 1:
            _fail(f"runtime backup command emitted non-single output: {command_id}")
        try:
            result = json.loads(lines[0])
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
            raise GateError(f"runtime result is invalid JSON: {command_id}") from exc
        if not isinstance(result, dict) or result.get("kind") != expected_kind:
            _fail(f"runtime result kind mismatch: {command_id}")
        token = result.get("state_token")
        if not isinstance(token, str) or not token:
            _fail(f"runtime result contains no state capability: {command_id}")
        input_token = command.get("state_token")
        sanitized: dict[str, Any] = {
            "command_sha256": sha256_bytes(command_payload),
            "input_token_fingerprint": (
                None
                if input_token is None
                else sha256_bytes(str(input_token).encode("utf-8"))
            ),
            "kind": expected_kind,
            "redaction": "state-token-sha256-fingerprint",
            "result_bytes_sha256": sha256_bytes(completed.stdout),
            "schema_version": "mingli-sanitized-runtime-result-v1",
            "token_fingerprint": sha256_bytes(token.encode("utf-8")),
        }
        if expected_kind == "prepared":
            brief = result.get("brief")
            if not isinstance(brief, dict):
                _fail(f"Prepared result has no ReadingBrief: {command_id}")
            question = brief.get("question")
            prior_answer = brief.get("prior_answer")
            if not isinstance(question, str) or not question:
                _fail(f"Prepared ReadingBrief has no question: {command_id}")
            if prior_answer is not None and not isinstance(prior_answer, str):
                _fail(f"Prepared ReadingBrief prior answer is invalid: {command_id}")
            sanitized.update(
                {
                    "brief_sha256": sha256_bytes(
                        json.dumps(
                            brief,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ),
                    "prior_answer_sha256": (
                        None
                        if prior_answer is None
                        else sha256_bytes(prior_answer.encode("utf-8"))
                    ),
                    "question_sha256": sha256_bytes(question.encode("utf-8")),
                }
            )
        if expected_kind == "accepted":
            public_copy = result.get("public_copy")
            if not isinstance(public_copy, str) or not public_copy:
                _fail(f"Accepted result has no public copy: {command_id}")
            sanitized["public_copy_sha256"] = sha256_bytes(public_copy.encode("utf-8"))
        sanitized_payload = json_bytes(sanitized)
        record = self.writer.record(
            command_id,
            argv,
            sanitized_payload,
            stdout_capture="sanitized-runtime-result-v1",
        )
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        return result, sanitized

    def token_record(
        self,
        command_id: str,
        volume: str,
        token: str,
    ) -> dict[str, Any]:
        fingerprint = sha256_bytes(token.encode("utf-8"))
        argv = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network=none",
            "--read-only",
            "--tmpfs",
            RUNTIME_TMPFS,
            "--mount",
            f"source={volume},target=/var/lib/mingli,readonly",
            "--entrypoint",
            "/opt/mingli-runtime/venv/bin/python",
            self.image_id,
            "-B",
            "/opt/mingli-runtime/audit_runtime.py",
            "--emit-token-record",
            "--state-root",
            "/var/lib/mingli",
        ]
        completed = self.vm.docker(
            argv[1:],
            input_bytes=json_bytes({"token_fingerprint": fingerprint}),
            timeout=60,
        )
        if completed.stderr or len(completed.stdout.splitlines()) != 1:
            _fail(f"token record audit failed: {command_id}")
        try:
            value = json.loads(completed.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
            raise GateError(
                f"token record audit is invalid JSON: {command_id}"
            ) from exc
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != "mingli-token-record-audit-v1"
            or value.get("token_fingerprint") != fingerprint
        ):
            _fail(f"token record audit result mismatch: {command_id}")
        self.writer.record(
            command_id,
            argv,
            completed.stdout,
            completed.stderr,
            stdout_capture="token-record-audit-v1",
        )
        return value

    def check_empty(self, command_id: str, volume: str) -> None:
        argv = [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--read-only",
            "--mount",
            f"source={volume},target=/var/lib/mingli,readonly",
            "--entrypoint",
            "/usr/bin/find",
            self.image_id,
            "/var/lib/mingli",
            "-mindepth",
            "1",
            "-print",
            "-quit",
        ]
        completed = self.vm.docker(argv[1:], timeout=60)
        if completed.stderr or completed.stdout:
            _fail(f"restore volume did not start empty: {volume}")
        self.writer.record(
            command_id,
            argv,
            completed.stdout,
            completed.stderr,
            stdout_capture="raw",
        )

    def capture_snapshot(
        self,
        command_id: str,
        volume: str,
    ) -> bytearray:
        argv = [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--read-only",
            "--mount",
            f"source={volume},target=/var/lib/mingli,readonly",
            "--entrypoint",
            "/bin/tar",
            self.image_id,
            "-C",
            "/var/lib/mingli",
            "-cf",
            "-",
            ".",
        ]
        completed = self.vm.docker(argv[1:], timeout=900)
        if completed.stderr or not completed.stdout:
            _fail(f"state snapshot capture failed: {command_id}")
        snapshot = bytearray(completed.stdout)
        receipt = json_bytes(
            {
                "byte_count": len(snapshot),
                "plaintext_sha256": sha256_bytes(snapshot),
                "schema_version": "mingli-snapshot-capture-v1",
            }
        )
        self.writer.record(
            command_id,
            argv,
            receipt,
            stdout_capture="sha256-receipt-v1",
        )
        return snapshot

    def seal_snapshot(
        self,
        name: str,
        snapshot: bytearray,
    ) -> tuple[dict[str, Any], bytearray, bytes]:
        command_id = f"{name}-snapshot-seal"
        pad = bytearray(os.urandom(len(snapshot)))
        ciphertext = bytes(
            left ^ right for left, right in zip(snapshot, pad, strict=True)
        )
        relative = f"evidence/backup/snapshots/{name}.tar.otp"
        path = self.evidence_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(ciphertext)
        path.chmod(0o600)
        receipt = json_bytes(
            {
                "byte_count": len(ciphertext),
                "ciphertext_sha256": sha256_bytes(ciphertext),
                "plaintext_sha256": sha256_bytes(snapshot),
                "schema_version": "mingli-snapshot-seal-v1",
            }
        )
        self.writer.record(
            command_id,
            ["in-process:xor-one-time-pad", name, relative],
            receipt,
            stdout_capture="cryptographic-receipt-v1",
        )
        record = {
            "byte_count": len(ciphertext),
            "capture_command_id": f"{name}-snapshot-capture",
            "ciphertext_path": relative,
            "ciphertext_sha256": sha256_bytes(ciphertext),
            "encryption": "xor-one-time-pad-key-destroyed",
            "plaintext_sha256": sha256_bytes(snapshot),
            "seal_command_id": command_id,
        }
        return record, pad, ciphertext

    def restore_snapshot(
        self,
        command_id: str,
        volume: str,
        snapshot: bytearray,
        pad: bytearray,
        ciphertext: bytes,
    ) -> None:
        plaintext = bytearray(
            left ^ right for left, right in zip(ciphertext, pad, strict=True)
        )
        if plaintext != snapshot:
            _fail(f"snapshot one-time-pad round trip failed: {command_id}")
        argv = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network=none",
            "--read-only",
            "--mount",
            f"source={volume},target=/var/lib/mingli",
            "--entrypoint",
            "/bin/tar",
            self.image_id,
            "-C",
            "/var/lib/mingli",
            "-xf",
            "-",
        ]
        completed = self.vm.docker(argv[1:], input_bytes=plaintext, timeout=900)
        if completed.stderr:
            _fail(f"snapshot restore emitted stderr: {command_id}")
        for buffer in (plaintext, pad, snapshot):
            for index in range(len(buffer)):
                buffer[index] = 0
        receipt = json_bytes(
            {
                "key_destroyed": True,
                "plaintext_buffer_destroyed": True,
                "schema_version": "mingli-snapshot-restore-v1",
            }
        )
        self.writer.record(
            command_id,
            argv,
            receipt,
            stdout_capture="restore-receipt-v1",
        )

    def run(self) -> Path:
        source_volume = self.volumes["source"]
        prepared_volume = self.volumes["prepared_restore_blank"]
        accepted_volume = self.volumes["accepted_restore_blank"]
        self.check_empty("prepared-restore-volume-empty", prepared_volume)
        self.check_empty("accepted-restore-volume-empty", accepted_volume)

        base_prepare: dict[str, Any] = {
            "facts": {
                "subject:restore": {
                    "birth_datetime_or_four_pillars": "1994-04-30T05:55:00",
                    "gender": "female",
                    "location": "福建省福州市",
                    "timezone": "Asia/Shanghai",
                }
            },
            "intent": {
                "capability_id": "bazi",
                "dimension_ids": [],
                "horizon": {"kind_id": "year"},
                "object_id": "natal",
                "subject_refs": ["subject:restore"],
            },
            "kind": "prepare",
            "query": "Linux 状态恢复演练",
        }
        source_prepared_raw, source_prepared = self.runtime(
            "source-prepare",
            source_volume,
            base_prepare,
            expected_kind="prepared",
        )
        source_token = str(source_prepared_raw["state_token"])
        source_token_record = self.token_record(
            "source-prepared-token-record",
            source_volume,
            source_token,
        )
        prepared_snapshot = self.capture_snapshot(
            "prepared-snapshot-capture", source_volume
        )
        prepared_record, prepared_pad, prepared_ciphertext = self.seal_snapshot(
            "prepared", prepared_snapshot
        )
        self.restore_snapshot(
            "prepared-restore",
            prepared_volume,
            prepared_snapshot,
            prepared_pad,
            prepared_ciphertext,
        )

        replay_command = {**base_prepare, "state_token": source_token}
        prepared_replay_raw, prepared_replay = self.runtime(
            "prepared-token-replay",
            prepared_volume,
            replay_command,
            expected_kind="prepared",
        )
        source_complete = {
            "kind": "complete",
            "public_copy": PUBLIC_COPY,
            "state_token": source_token,
        }
        prepared_restored_accepted_raw, prepared_restored_accepted = self.runtime(
            "prepared-restored-complete",
            prepared_volume,
            source_complete,
            expected_kind="accepted",
        )
        restored_parent_token = str(prepared_restored_accepted_raw["state_token"])
        followup_query = "Linux 状态恢复演练：请继续说明后续重点"
        accepted_followup_command = {
            **base_prepare,
            "query": followup_query,
            "state_token": restored_parent_token,
        }
        accepted_followup_raw, accepted_followup = self.runtime(
            "accepted-followup-prepare",
            prepared_volume,
            accepted_followup_command,
            expected_kind="prepared",
        )
        child_token = str(accepted_followup_raw["state_token"])
        child_token_record = self.token_record(
            "accepted-followup-token-record",
            prepared_volume,
            child_token,
        )
        child_complete = {
            "kind": "complete",
            "public_copy": FOLLOWUP_PUBLIC_COPY,
            "state_token": child_token,
        }
        _, accepted_followup_accepted = self.runtime(
            "accepted-followup-complete",
            prepared_volume,
            child_complete,
            expected_kind="accepted",
        )

        source_accepted_raw, source_accepted = self.runtime(
            "source-complete",
            source_volume,
            source_complete,
            expected_kind="accepted",
        )
        accepted_snapshot = self.capture_snapshot(
            "accepted-snapshot-capture", source_volume
        )
        accepted_record, accepted_pad, accepted_ciphertext = self.seal_snapshot(
            "accepted", accepted_snapshot
        )
        self.restore_snapshot(
            "accepted-restore",
            accepted_volume,
            accepted_snapshot,
            accepted_pad,
            accepted_ciphertext,
        )
        accepted_replay_raw, accepted_replay = self.runtime(
            "accepted-complete-replay",
            accepted_volume,
            source_complete,
            expected_kind="accepted",
        )

        transcript_map = {
            "accepted-replay": ("accepted-complete-replay", accepted_replay),
            "accepted-followup-accepted": (
                "accepted-followup-complete",
                accepted_followup_accepted,
            ),
            "accepted-followup-prepared": (
                "accepted-followup-prepare",
                accepted_followup,
            ),
            "prepared-replay": ("prepared-token-replay", prepared_replay),
            "prepared-restored-accepted": (
                "prepared-restored-complete",
                prepared_restored_accepted,
            ),
            "source-accepted": ("source-complete", source_accepted),
            "source-prepared": ("source-prepare", source_prepared),
        }
        indexed_commands = {record["id"]: record for record in self.writer.commands}
        transcripts = {
            transcript_id: {
                "command_id": command_id,
                "path": indexed_commands[command_id]["stdout_path"],
                "sha256": indexed_commands[command_id]["stdout_sha256"],
            }
            for transcript_id, (command_id, _value) in transcript_map.items()
        }
        token_record_map = {
            "accepted-followup": (
                "accepted-followup-token-record",
                child_token_record,
            ),
            "source-prepared": (
                "source-prepared-token-record",
                source_token_record,
            ),
        }
        token_records = {
            record_id: {
                "command_id": command_id,
                "path": indexed_commands[command_id]["stdout_path"],
                "sha256": indexed_commands[command_id]["stdout_sha256"],
            }
            for record_id, (command_id, _value) in token_record_map.items()
        }
        original_copies = {
            source_accepted["public_copy_sha256"],
            prepared_restored_accepted["public_copy_sha256"],
            accepted_replay["public_copy_sha256"],
        }
        original_complete_commands = {
            source_accepted["command_sha256"],
            prepared_restored_accepted["command_sha256"],
            accepted_replay["command_sha256"],
        }
        source_fingerprint = source_prepared["token_fingerprint"]
        child_fingerprint = accepted_followup["token_fingerprint"]
        evidence = {
            "accepted_followup_created": (
                accepted_followup["input_token_fingerprint"] == source_fingerprint
                and child_fingerprint != source_fingerprint
                and accepted_followup["prior_answer_sha256"]
                == sha256_bytes(PUBLIC_COPY.encode("utf-8"))
                and accepted_followup["question_sha256"]
                == sha256_bytes(followup_query.encode("utf-8"))
                and accepted_followup_accepted["input_token_fingerprint"]
                == child_fingerprint
            ),
            "accepted_token_replayed": (
                accepted_replay["token_fingerprint"]
                == source_accepted["token_fingerprint"]
            ),
            "blank_volume_checks": {
                "accepted_restore_blank": True,
                "prepared_restore_blank": True,
            },
            "commands": sorted(self.writer.commands, key=lambda item: item["id"]),
            "complete_public_copy_byte_identical": (
                len(original_copies) == 1 and len(original_complete_commands) == 1
            ),
            "followup_version_advanced": (
                source_token_record.get("version") == 1
                and source_token_record.get("phase") == "prepared"
                and child_token_record.get("version") == 2
                and child_token_record.get("phase") == "prepared"
                and child_token_record.get("parent_token_fingerprint")
                == source_fingerprint
            ),
            "image_digest": self.image_id,
            "prepared_token_restored": (
                prepared_replay["input_token_fingerprint"] == source_fingerprint
                and prepared_replay["token_fingerprint"] == source_fingerprint
            ),
            "prepared_replay_byte_identical": (
                prepared_replay["result_bytes_sha256"]
                == source_prepared["result_bytes_sha256"]
                and prepared_replay_raw == source_prepared_raw
            ),
            "prepared_restored_completed": (
                prepared_restored_accepted["input_token_fingerprint"]
                == source_fingerprint
                and prepared_restored_accepted["token_fingerprint"]
                == source_fingerprint
            ),
            "schema_version": "mingli-backup-restore-v1",
            "snapshots": {
                "accepted": accepted_record,
                "prepared": prepared_record,
            },
            "token_records": token_records,
            "transcripts": transcripts,
            "volume_ids": dict(self.volumes),
        }
        if not all(
            (
                evidence["accepted_token_replayed"],
                evidence["accepted_followup_created"],
                evidence["complete_public_copy_byte_identical"],
                evidence["followup_version_advanced"],
                evidence["prepared_replay_byte_identical"],
                evidence["prepared_restored_completed"],
                evidence["prepared_token_restored"],
                source_accepted_raw.get("public_copy")
                == accepted_replay_raw.get("public_copy"),
                source_accepted_raw.get("public_copy")
                == prepared_restored_accepted_raw.get("public_copy"),
            )
        ):
            _fail("backup/restore drill did not converge byte-identically")
        rendered = json_bytes(evidence)
        if b"state_token" in rendered:
            _fail("backup/restore evidence contains a forbidden raw-token field")
        evidence_path = self.evidence_root / "evidence/backup/backup-restore.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_bytes(rendered)
        evidence_path.chmod(0o600)
        del source_token, restored_parent_token, child_token, source_prepared_raw
        del prepared_replay_raw, prepared_restored_accepted_raw, accepted_followup_raw
        del source_accepted_raw, accepted_replay_raw
        return evidence_path


def _build_images(
    vm: LimaDocker,
    context: Path,
    run_id: str,
) -> tuple[str, str, str, str]:
    context_tar = _tar_tree(context)
    production_tag = f"mingli-v51-production:{run_id}"
    audit_tag = f"mingli-v51-audit:{run_id}"
    print("gate: building production image", flush=True)
    vm.docker(
        [
            "build",
            "--platform",
            "linux/amd64",
            "--progress=plain",
            "--target",
            "final",
            "--tag",
            production_tag,
            "-",
        ],
        input_bytes=context_tar,
        capture=False,
    )
    print("gate: building audit image", flush=True)
    vm.docker(
        [
            "build",
            "--platform",
            "linux/amd64",
            "--progress=plain",
            "--target",
            "audit",
            "--tag",
            audit_tag,
            "-",
        ],
        input_bytes=context_tar,
        capture=False,
    )
    return (
        production_tag,
        _docker_image_id(vm, production_tag),
        audit_tag,
        _docker_image_id(vm, audit_tag),
    )


def _extract_volume(
    vm: LimaDocker,
    image_id: str,
    volume: str,
    source: str,
) -> bytes:
    completed = vm.docker(
        [
            "run",
            "--rm",
            "--network=none",
            "--read-only",
            "--mount",
            f"source={volume},target={source},readonly",
            "--entrypoint",
            "/bin/tar",
            image_id,
            "-C",
            source,
            "-cf",
            "-",
            ".",
        ],
        timeout=1800,
    )
    if completed.stderr or not completed.stdout:
        _fail("audit output volume could not be extracted")
    return completed.stdout


def run_gate(args: argparse.Namespace) -> Path:
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        _fail("Gate output destination must not already exist")
    output.parent.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d%H%M%S", time.gmtime()) + secrets.token_hex(4)
    prefix = f"mingli-gate-{run_id.lower()}"
    volumes = {
        "source": f"{prefix}-backup-source",
        "prepared_restore_blank": f"{prefix}-prepared-restore",
        "accepted_restore_blank": f"{prefix}-accepted-restore",
        "audit_source": f"{prefix}-audit-source",
        "audit_input": f"{prefix}-audit-input",
        "audit_output": f"{prefix}-audit-output",
        "audit_state": f"{prefix}-audit-state",
        "production_output": f"{prefix}-production-output",
        "production_state": f"{prefix}-production-state",
    }
    vm = LimaDocker(args.instance)
    created_volumes: list[str] = []
    final_temporary: Path | None = None
    with tempfile.TemporaryDirectory(prefix="mingli-v51-gate-") as temporary_text:
        temporary = Path(temporary_text)
        try:
            vm.run(["uname", "-m"])
            context = build_context.build_context(
                args.release_source,
                temporary / "context",
            )
            research_source = _prepare_research_source(
                args.research_repository,
                args.release_source,
                temporary / "research-source",
            )
            production_tag, image_id, audit_tag, audit_image_id = _build_images(
                vm, context, run_id
            )
            _validate_image_id(image_id, "production image ID")
            _validate_image_id(audit_image_id, "audit image ID")
            print(
                f"gate: production={image_id} audit={audit_image_id}",
                flush=True,
            )

            for volume in volumes.values():
                vm.create_volume(volume, run_id)
                created_volumes.append(volume)
            for role in (
                "source",
                "prepared_restore_blank",
                "accepted_restore_blank",
                "audit_state",
                "production_state",
            ):
                _initialize_volume(
                    vm,
                    image_id,
                    volumes[role],
                    "/var/lib/mingli",
                    mode="0700",
                )
            _initialize_volume(
                vm,
                image_id,
                volumes["audit_source"],
                "/audit-source",
                mode="0700",
            )
            _initialize_volume(
                vm,
                image_id,
                volumes["audit_input"],
                "/audit-input",
                mode="0700",
            )
            _initialize_volume(
                vm,
                image_id,
                volumes["production_output"],
                "/production-output",
                mode="0700",
            )
            _initialize_volume(
                vm,
                image_id,
                volumes["audit_output"],
                "/audit-output",
                mode="0700",
            )
            _populate_volume(
                vm,
                image_id,
                volumes["audit_source"],
                "/audit-source",
                _tar_tree(research_source),
            )
            source_check = vm.docker(
                [
                    "run",
                    "--rm",
                    "--network=none",
                    "--read-only",
                    "--mount",
                    f"source={volumes['audit_source']},target=/audit-source,readonly",
                    "--entrypoint",
                    "/usr/bin/git",
                    audit_image_id,
                    "-C",
                    "/audit-source",
                    "status",
                    "--porcelain",
                    "--untracked-files=all",
                ],
                timeout=300,
            )
            if source_check.stderr or source_check.stdout:
                _fail("source volume is not a clean independent checkout")

            audit_input = temporary / "audit-input"
            audit_input.mkdir(mode=0o700)
            backup_volumes = {
                "source": volumes["source"],
                "prepared_restore_blank": volumes["prepared_restore_blank"],
                "accepted_restore_blank": volumes["accepted_restore_blank"],
            }
            drill = BackupRestoreDrill(
                vm,
                image_id,
                backup_volumes,
                audit_input,
            )
            drill.run()

            production_argv = [
                "run",
                "--rm",
                "--network=none",
                "--read-only",
                "--tmpfs",
                RUNTIME_TMPFS,
                "--mount",
                f"source={volumes['audit_source']},target=/audit-source,readonly",
                "--mount",
                (f"source={volumes['production_output']},target=/production-output"),
                "--mount",
                f"source={volumes['production_state']},target=/var/lib/mingli",
                "--entrypoint",
                "/opt/mingli-runtime/venv/bin/python",
                image_id,
                "-B",
                "/opt/mingli-runtime/audit_runtime.py",
                "--production-audit",
                "--source-root",
                "/audit-source",
                "--output-root",
                "/production-output",
                "--image-id",
                image_id,
            ]
            print("gate: running core Gate directly in production", flush=True)
            vm.docker(production_argv, capture=False, timeout=10800)
            production_tar = _extract_volume(
                vm,
                image_id,
                volumes["production_output"],
                "/production-output",
            )
            production_evidence_root = audit_input / "production-evidence"
            production_evidence_root.mkdir(mode=0o700)
            _extract_safe_tar(production_tar, production_evidence_root)
            if not (production_evidence_root / "production-evidence.json").is_file():
                _fail("production image did not emit its evidence bundle")
            _populate_volume(
                vm,
                image_id,
                volumes["audit_input"],
                "/audit-input",
                _tar_tree(audit_input),
            )

            audit_argv = [
                "run",
                "--rm",
                "--network=none",
                "--read-only",
                "--tmpfs",
                RUNTIME_TMPFS,
                "--mount",
                f"source={volumes['audit_source']},target=/audit-source,readonly",
                "--mount",
                f"source={volumes['audit_input']},target=/audit-input,readonly",
                "--mount",
                f"source={volumes['audit_output']},target=/audit-output",
                "--mount",
                f"source={volumes['audit_state']},target=/var/lib/mingli",
                "--entrypoint",
                "/opt/mingli-runtime/venv/bin/python",
                audit_image_id,
                "-B",
                "/opt/mingli-runtime/audit_runtime.py",
                "--finalize-audit",
                "--source-root",
                "/audit-source",
                "--output-root",
                "/audit-output",
                "--production-evidence",
                "/audit-input/production-evidence/production-evidence.json",
                "--backup-evidence",
                "/audit-input/evidence/backup/backup-restore.json",
                "--image-id",
                image_id,
                "--image-digest",
                image_id,
                "--audit-image-id",
                audit_image_id,
            ]
            print("gate: running Git-only audit finalizer", flush=True)
            vm.docker(audit_argv, capture=False, timeout=14400)

            output_tar = _extract_volume(
                vm,
                image_id,
                volumes["audit_output"],
                "/audit-output",
            )
            final_temporary = Path(
                tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent)
            )
            _extract_safe_tar(output_tar, final_temporary)
            report = final_temporary / "release-5.1.json"
            if not report.is_file():
                _fail("Linux audit did not produce release-5.1.json")
            _run_local(
                [
                    sys.executable,
                    str(Path(__file__).with_name("verify_release.py")),
                    "--audit-report",
                    str(report),
                    "--artifacts-root",
                    str(final_temporary),
                ],
                timeout=900,
            )
            (final_temporary / "image-reference.json").write_bytes(
                json_bytes(
                    {
                        "audit_image_id": audit_image_id,
                        "audit_tag": audit_tag,
                        "production_image_id": image_id,
                        "production_tag": production_tag,
                        "schema_version": "mingli-local-image-reference-v1",
                    }
                )
            )
            os.replace(final_temporary, output)
            final_temporary = None
            print(f"gate: admitted evidence written to {output}", flush=True)
            return output
        finally:
            if final_temporary is not None:
                shutil.rmtree(final_temporary, ignore_errors=True)
            for volume in reversed(created_volumes):
                try:
                    vm.remove_volume(volume)
                except GateError as exc:
                    print(f"gate cleanup warning: {exc}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", default="mingli-linux-gate")
    parser.add_argument("--release-source", type=Path, required=True)
    parser.add_argument("--research-repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        run_gate(args)
    except (GateError, build_context.ProjectionError) as exc:
        print(f"Linux Gate failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
