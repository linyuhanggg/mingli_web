#!/usr/bin/env python3
"""Identity-bound, single-flight Runtime worker transport.

The existing ``runtime_launcher.py`` remains the one-shot compatibility
entrypoint.  This module is a separate v1 transport candidate: it verifies a
complete signed release and the pinned Python Runtime before emitting READY,
then accepts one length-prefixed Command at a time and emits exactly one
length-prefixed Result for every accepted command.

There is deliberately no retry, replay, batch, fallback, or caller-selected
entrypoint.  A framing violation, sequence violation, identity drift, or
internal transport failure isolates the process and makes the host decide the
next safe action.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import secrets
import select
import signal
import stat
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, Iterator, Mapping, TextIO


sys.dont_write_bytecode = True
sys.pycache_prefix = "/dev/null"


WORKER_PROTOCOL = "mingli-runtime-worker-v1"
RUNTIME_PROTOCOL = "mingli-portable-interface-v2"
WORKER_RELATIVE = "scripts/reading_engine/runtime_worker.py"
ONE_SHOT_RELATIVES = frozenset(
    {
        "scripts/runtime_launcher.py",
        "scripts/run_reading_transaction.sh",
    }
)
RELEASE_MANIFEST = ".mingli-release-manifest.json"
RUNTIME_CLOSURE = "release/runtime-closure-v1.json"
RUNTIME_CLOSURE_SCHEMA = "mingli-runtime-closure-v1"
MAX_FRAME_BYTES = 4 * 1024 * 1024
FRAME_HEADER_BYTES = 4
MAX_SEQUENCE = (1 << 63) - 1
DEFAULT_READY_TIMEOUT_SECONDS = 15.0
MAX_READY_TIMEOUT_SECONDS = 120.0
EXPECTED_REFERENCE_PACK_COUNT = 55
EXPECTED_EVIDENCE_RECORD_COUNT = 1328
EXPECTED_CAPABILITY_COUNT = 14
FALLBACK_ERROR_TEXT = "本次处理未完成，请稍后重试。"
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

EXIT_OK = 0
EXIT_PROTOCOL = 70
EXIT_STARTUP = 78
EXIT_TRANSPORT = 74


class WorkerError(RuntimeError):
    """Base class for fail-closed worker errors."""


class FrameError(WorkerError):
    """The physical frame is ambiguous, malformed, or outside its bound."""


class IdentityError(WorkerError):
    """A signed release, Runtime, or store identity is invalid or drifted."""


class ReadyTimeout(WorkerError):
    """The independent worker readiness deadline expired."""


class DuplicateJsonKey(ValueError):
    """JSON objects with duplicate keys are ambiguous and forbidden."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    try:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise FrameError("frame payload is not bounded JSON") from exc
    return rendered.encode("utf-8")


def _object_without_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _decode_json_object(payload: bytes) -> dict[str, object]:
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        DuplicateJsonKey,
        ValueError,
        RecursionError,
    ) as exc:
        raise FrameError("frame is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise FrameError("frame JSON must be an object")
    return value


def encode_frame(payload: object, *, max_bytes: int = MAX_FRAME_BYTES) -> bytes:
    """Encode one bounded, four-byte big-endian length-prefixed JSON frame."""

    body = _canonical_json_bytes(payload)
    if not body or len(body) > max_bytes:
        raise FrameError("frame length is outside the explicit bound")
    return len(body).to_bytes(FRAME_HEADER_BYTES, "big") + body


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise FrameError("truncated frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(
    stream: BinaryIO,
    *,
    max_bytes: int = MAX_FRAME_BYTES,
) -> dict[str, object] | None:
    """Read one frame, returning ``None`` only for clean boundary EOF."""

    header = stream.read(FRAME_HEADER_BYTES)
    if header == b"":
        return None
    if len(header) != FRAME_HEADER_BYTES:
        raise FrameError("truncated frame header")
    length = int.from_bytes(header, "big")
    if length < 1 or length > max_bytes:
        raise FrameError("declared frame length is outside the explicit bound")
    return _decode_json_object(_read_exact(stream, length))


def write_frame(
    stream: BinaryIO,
    payload: object,
    *,
    max_bytes: int = MAX_FRAME_BYTES,
) -> None:
    encoded = encode_frame(payload, max_bytes=max_bytes)
    offset = 0
    while offset < len(encoded):
        written = stream.write(encoded[offset:])
        if not isinstance(written, int) or written <= 0:
            raise OSError("worker frame write made no progress")
        offset += written
    stream.flush()


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise IdentityError(f"{label} path is invalid")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or value != relative.as_posix()
    ):
        raise IdentityError(f"{label} path is unsafe")
    return value


def _secure_directory(path: Path, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise IdentityError(f"{label} is missing") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise IdentityError(f"{label} must be a real directory")
    if stat.S_IMODE(metadata.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
        raise IdentityError(f"{label} must not be group/world writable")


def _secure_parents(root: Path, relative: str) -> None:
    current = root
    for part in PurePosixPath(relative).parts[:-1]:
        current /= part
        _secure_directory(current, "release directory")


def _read_regular_bytes(root: Path, relative: str, label: str) -> bytes:
    safe = _safe_relative(relative, label)
    _secure_parents(root, safe)
    path = root / safe
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise IdentityError(f"{label} is missing or unsafe") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise IdentityError(f"{label} must be a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        payload = b"".join(chunks)
        ending = os.fstat(descriptor)
        if (info.st_dev, info.st_ino, info.st_size) != (
            ending.st_dev,
            ending.st_ino,
            ending.st_size,
        ):
            raise IdentityError(f"{label} changed while being read")
        return payload
    finally:
        os.close(descriptor)


def _load_json_bytes(payload: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        DuplicateJsonKey,
        RecursionError,
    ) as exc:
        raise IdentityError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise IdentityError(f"{label} must be a JSON object")
    return value


def _safe_release_pattern(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise IdentityError("Runtime closure pattern is invalid")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or not any(token in value for token in ("*", "?", "["))
    ):
        raise IdentityError("Runtime closure pattern is unsafe")
    return path.as_posix()


@dataclass(frozen=True)
class ReleaseIdentity:
    root: str
    listing_sha256: str
    release_name: str
    source_commit: str
    file_count: int
    signed_paths_sha256: str


def verify_release(
    release_root: Path,
    expected_listing_sha256: str,
    *,
    verify_semantics: bool,
) -> ReleaseIdentity:
    """Verify every signed byte/mode and reject every unsigned entry."""

    if SHA256_RE.fullmatch(expected_listing_sha256) is None:
        raise IdentityError("expected release listing SHA-256 is invalid")
    root = release_root.resolve(strict=True)
    _secure_directory(root, "Runtime release root")
    manifest_payload = _read_regular_bytes(
        root,
        RELEASE_MANIFEST,
        "Runtime release manifest",
    )
    listing_sha256 = _sha256_bytes(manifest_payload)
    if listing_sha256 != expected_listing_sha256:
        raise IdentityError("Runtime release manifest digest mismatch")
    manifest = _load_json_bytes(manifest_payload, "Runtime release manifest")
    if (
        set(manifest) != {
            "schema_version",
            "release",
            "source_commit",
            "files",
            "modes",
        }
        or manifest.get("schema_version") != 3
        or not isinstance(manifest.get("release"), str)
        or not manifest.get("release")
        or not isinstance(manifest.get("source_commit"), str)
        or SOURCE_COMMIT_RE.fullmatch(str(manifest.get("source_commit"))) is None
    ):
        raise IdentityError("Runtime release identity is invalid")
    files = manifest.get("files")
    modes = manifest.get("modes")
    if (
        not isinstance(files, dict)
        or not files
        or not isinstance(modes, dict)
        or set(files) != set(modes)
    ):
        raise IdentityError("Runtime release inventory is invalid")

    signed_paths: set[str] = set()
    for raw_relative, expected_digest in files.items():
        relative = _safe_relative(raw_relative, "signed file")
        if (
            not isinstance(expected_digest, str)
            or SHA256_RE.fullmatch(expected_digest) is None
        ):
            raise IdentityError("signed file digest is invalid")
        payload = _read_regular_bytes(root, relative, "signed file")
        if _sha256_bytes(payload) != expected_digest:
            raise IdentityError(f"signed file digest mismatch: {relative}")
        expected_mode = modes.get(relative)
        actual_mode = stat.S_IMODE((root / relative).stat().st_mode)
        if expected_mode not in {0o600, 0o644, 0o700, 0o755}:
            raise IdentityError(f"signed file mode is invalid: {relative}")
        if actual_mode != expected_mode:
            raise IdentityError(f"signed file mode mismatch: {relative}")
        signed_paths.add(relative)

    required = {WORKER_RELATIVE, RUNTIME_CLOSURE, *ONE_SHOT_RELATIVES}
    if not required <= signed_paths:
        raise IdentityError("Runtime release omits a required transport file")

    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    for path in root.rglob("*"):
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise IdentityError("Runtime release inventory is unreadable") from exc
        relative = path.relative_to(root).as_posix()
        if stat.S_ISLNK(metadata.st_mode):
            raise IdentityError("Runtime release contains an unsigned symlink")
        if stat.S_ISDIR(metadata.st_mode):
            _secure_directory(path, "Runtime release directory")
            actual_directories.add(relative)
        elif stat.S_ISREG(metadata.st_mode):
            actual_files.add(relative)
        else:
            raise IdentityError("Runtime release contains an unsigned entry")
    expected_files = signed_paths | {RELEASE_MANIFEST}
    expected_directories: set[str] = set()
    for relative in expected_files:
        parent = PurePosixPath(relative).parent
        while parent != PurePosixPath("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    if actual_files != expected_files or actual_directories != expected_directories:
        raise IdentityError("Runtime release contains an unsigned filesystem entry")

    closure_payload = _load_json_bytes(
        _read_regular_bytes(root, RUNTIME_CLOSURE, "Runtime closure"),
        "Runtime closure",
    )
    if (
        set(closure_payload) != {"schema_version", "files", "patterns"}
        or closure_payload.get("schema_version") != RUNTIME_CLOSURE_SCHEMA
        or not isinstance(closure_payload.get("files"), list)
        or not isinstance(closure_payload.get("patterns"), list)
    ):
        raise IdentityError("Runtime closure contract is invalid")
    selected = {
        _safe_relative(item, "Runtime closure")
        for item in closure_payload["files"]
    }
    for raw_pattern in closure_payload["patterns"]:
        pattern = _safe_release_pattern(raw_pattern)
        matches = {
            relative
            for relative in signed_paths
            if PurePosixPath(relative).match(pattern)
        }
        if not matches:
            raise IdentityError("Runtime closure pattern matched no signed files")
        selected.update(matches)
    # The worker lives under the existing reading_engine release pattern, so
    # the signed manifest and closure must describe exactly the same files.
    # Tests remain outside the release.
    if selected != signed_paths:
        raise IdentityError("Runtime closure does not match the signed release")

    if verify_semantics:
        _verify_reference_catalog(root, signed_paths)

    signed_paths_sha256 = _sha256_bytes(
        "\n".join(sorted(signed_paths)).encode("utf-8")
    )
    return ReleaseIdentity(
        root=str(root),
        listing_sha256=listing_sha256,
        release_name=str(manifest["release"]),
        source_commit=str(manifest["source_commit"]),
        file_count=len(signed_paths),
        signed_paths_sha256=signed_paths_sha256,
    )


def _verify_reference_catalog(root: Path, signed_paths: set[str]) -> None:
    relative = "references/catalog/catalog.json"
    if relative not in signed_paths:
        raise IdentityError("reference catalog is not signed")
    catalog = _load_json_bytes(
        _read_regular_bytes(root, relative, "reference catalog"),
        "reference catalog",
    )
    packs = catalog.get("ready_reference_packs")
    validation = catalog.get("validation")
    if (
        catalog.get("ready_count") != EXPECTED_REFERENCE_PACK_COUNT
        or not isinstance(packs, list)
        or len(packs) != EXPECTED_REFERENCE_PACK_COUNT
        or not isinstance(validation, dict)
        or set(validation.values()) != {"PASS 55/55"}
    ):
        raise IdentityError("reference catalog is not 55/55 ready")
    pack_ids: set[str] = set()
    for item in packs:
        if not isinstance(item, dict):
            raise IdentityError("reference pack record is invalid")
        system = item.get("system")
        slug = item.get("slug")
        if not isinstance(system, str) or not isinstance(slug, str):
            raise IdentityError("reference pack identity is invalid")
        pack_id = f"{system}/{slug}"
        if pack_id in pack_ids or item.get("d2_status") != "ready":
            raise IdentityError("reference pack readiness is invalid")
        pack_ids.add(pack_id)
        for suffix in ("rules.md", "quote-index.md"):
            if f"references/books/{pack_id}/{suffix}" not in signed_paths:
                raise IdentityError("reference pack file is not signed")


def _load_guard(scripts_root: Path):
    helper = scripts_root / "runtime_python.py"
    spec = importlib.util.spec_from_file_location("_mingli_runtime_guard", helper)
    if spec is None or spec.loader is None:
        raise IdentityError("runtime guard could not be loaded")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    return guard


def _runtime_manifest_digest(guard, executable: str) -> str:
    runtime_root = guard.runtime_root_for_executable(executable)
    path = runtime_root / guard.RUNTIME_MANIFEST
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise IdentityError("runtime-integrity manifest is unavailable") from exc
    return _sha256_bytes(payload)


def _validate_runtime(
    guard,
    executable: str,
    expected_runtime_integrity_sha256: str,
) -> tuple[tuple[Path, ...], dict[str, object]]:
    if SHA256_RE.fullmatch(expected_runtime_integrity_sha256) is None:
        raise IdentityError("expected runtime-integrity SHA-256 is invalid")
    before = _runtime_manifest_digest(guard, executable)
    if before != expected_runtime_integrity_sha256:
        raise IdentityError("runtime-integrity manifest digest mismatch")
    try:
        site_roots = tuple(guard.validate_installed_runtime(executable))
        for site_root in site_roots:
            if str(site_root) not in sys.path:
                sys.path.append(str(site_root))
        identity = guard.current_runtime_identity()
        guard.validate_runtime_identity(identity)
    except (OSError, RuntimeError, ValueError) as exc:
        raise IdentityError("pinned Python Runtime validation failed") from exc
    after = _runtime_manifest_digest(guard, executable)
    if after != before:
        raise IdentityError("runtime-integrity identity drifted during validation")
    return site_roots, identity


@dataclass(frozen=True)
class StoreIdentity:
    path: str
    device: int
    inode: int
    mode: int

    def bound_payload(self) -> dict[str, object]:
        return {
            "path": self.path,
            "device": self.device,
            "inode": self.inode,
            "mode": self.mode,
        }


def _store_identity(path: Path) -> StoreIdentity:
    metadata = path.stat()
    return StoreIdentity(
        path=str(path),
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=stat.S_IMODE(metadata.st_mode),
    )


def _prepare_store_namespace(store_root: Path) -> StoreIdentity:
    store = store_root.resolve(strict=False)
    store.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path in (store.parent, store):
        if path.is_symlink() or not path.is_dir():
            raise IdentityError("store namespace must be a real directory")
        os.chmod(path, 0o700)
        _secure_directory(path, "store namespace")
    probe = store / f".runtime-worker-ready-{os.getpid()}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(probe, flags, 0o600)
        try:
            os.write(descriptor, b"ready\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        probe.unlink()
        directory = os.open(store, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError as exc:
        try:
            probe.unlink(missing_ok=True)
        finally:
            raise IdentityError("store namespace is not safely writable") from exc
    return _store_identity(store.resolve(strict=True))


def _verify_store_namespace(store_root: Path, expected: StoreIdentity) -> None:
    try:
        actual = store_root.resolve(strict=True)
    except OSError as exc:
        raise IdentityError("store namespace is unavailable") from exc
    if str(actual) != expected.path:
        raise IdentityError("store namespace identity drifted")
    _secure_directory(actual, "store namespace")
    if _store_identity(actual) != expected:
        raise IdentityError("store namespace identity drifted")


@contextmanager
def _ready_deadline(seconds: float) -> Iterator[None]:
    if not (0 < seconds <= MAX_READY_TIMEOUT_SECONDS):
        raise ValueError("ready timeout is outside the explicit bound")
    started = time.monotonic()
    can_alarm = (
        hasattr(signal, "setitimer")
        and hasattr(signal, "ITIMER_REAL")
        and hasattr(signal, "SIGALRM")
    )
    previous_handler: Any = None
    previous_timer: tuple[float, float] | None = None
    if can_alarm:
        def timeout_handler(_signum: int, _frame: object) -> None:
            raise ReadyTimeout("worker READY deadline expired")

        previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, timeout_handler)
        previous_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
        if time.monotonic() - started > seconds:
            raise ReadyTimeout("worker READY deadline expired")
    finally:
        if can_alarm:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
            if previous_timer is not None and previous_timer[0] > 0:
                signal.setitimer(
                    signal.ITIMER_REAL,
                    previous_timer[0],
                    previous_timer[1],
                )


@dataclass(frozen=True)
class WorkerIdentity:
    protocol: str
    runtime_protocol: str
    release_path: str
    listing_sha256: str
    release_name: str
    source_commit: str
    release_file_count: int
    signed_paths_sha256: str
    runtime_integrity_sha256: str
    python_identity: Mapping[str, object]
    store_namespace: str
    store_namespace_identity: Mapping[str, object]
    pid: int
    boot_nonce: str
    describe_manifest_digest: str
    capability_ids: tuple[str, ...]

    def bound_payload(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "runtime_protocol": self.runtime_protocol,
            "release_path": self.release_path,
            "listing_sha256": self.listing_sha256,
            "release_name": self.release_name,
            "source_commit": self.source_commit,
            "release_file_count": self.release_file_count,
            "signed_paths_sha256": self.signed_paths_sha256,
            "runtime_integrity_sha256": self.runtime_integrity_sha256,
            "python_identity": dict(self.python_identity),
            "store_namespace": self.store_namespace,
            "store_namespace_identity": dict(self.store_namespace_identity),
            "pid": self.pid,
            "boot_nonce": self.boot_nonce,
            "describe_manifest_digest": self.describe_manifest_digest,
            "capability_ids": list(self.capability_ids),
        }

    @property
    def identity_sha256(self) -> str:
        return _sha256_bytes(_canonical_json_bytes(self.bound_payload()))

    def ready_payload(
        self,
        *,
        ready_timeout_seconds: float,
        boot_ms: float,
    ) -> dict[str, object]:
        if not 0 <= boot_ms <= ready_timeout_seconds * 1000:
            raise ReadyTimeout("worker READY deadline expired")
        return {
            "type": "ready",
            **self.bound_payload(),
            "identity_sha256": self.identity_sha256,
            "sequence_start": 1,
            "single_in_flight": True,
            "max_frame_bytes": MAX_FRAME_BYTES,
            "ready_timeout_seconds": ready_timeout_seconds,
            "boot_ms": round(boot_ms, 3),
            "replay_policy": "forbidden",
            "fallback_policy": "forbidden",
        }


def _stopped_result() -> dict[str, object]:
    return {
        "kind": "stopped",
        "reason": "error",
        "public_copy": FALLBACK_ERROR_TEXT,
        "state_token": None,
    }


@dataclass(frozen=True)
class ProtocolFault:
    reason: str
    request_id: str | None = None
    sequence: int | None = None


class WorkerSession:
    """Strict monotonic Command/Result state machine for one worker boot."""

    def __init__(
        self,
        *,
        identity_sha256: str,
        execute_command: Callable[[Mapping[str, object]], dict[str, object]],
        verify_identity: Callable[[], None],
    ) -> None:
        self.identity_sha256 = identity_sha256
        self.execute_command = execute_command
        self.verify_identity = verify_identity
        self.next_sequence = 1
        self.request_ids: set[str] = set()

    def _fault(self, payload: Mapping[str, object]) -> ProtocolFault | None:
        request_id = payload.get("request_id")
        sequence = payload.get("sequence")
        safe_request_id = (
            request_id
            if isinstance(request_id, str)
            and REQUEST_ID_RE.fullmatch(request_id) is not None
            else None
        )
        safe_sequence = (
            sequence
            if isinstance(sequence, int)
            and not isinstance(sequence, bool)
            and 1 <= sequence <= MAX_SEQUENCE
            else None
        )
        if set(payload) != {
            "type",
            "protocol",
            "identity_sha256",
            "request_id",
            "sequence",
            "command",
        }:
            return ProtocolFault("command envelope fields are invalid")
        if safe_request_id is None or safe_sequence is None:
            return ProtocolFault("command request identity is invalid")
        if payload.get("type") != "command" or payload.get("protocol") != WORKER_PROTOCOL:
            return ProtocolFault("command protocol is invalid", safe_request_id, safe_sequence)
        if payload.get("identity_sha256") != self.identity_sha256:
            return ProtocolFault("worker identity mismatch", safe_request_id, safe_sequence)
        if safe_sequence != self.next_sequence:
            return ProtocolFault("command sequence is out of order", safe_request_id, safe_sequence)
        if safe_request_id in self.request_ids:
            return ProtocolFault("request id is duplicated", safe_request_id, safe_sequence)
        if not isinstance(payload.get("command"), Mapping):
            return ProtocolFault("command payload is invalid", safe_request_id, safe_sequence)
        return None

    def _result_envelope(
        self,
        *,
        request_id: str,
        sequence: int,
        result: Mapping[str, object],
        isolate: bool,
    ) -> dict[str, object]:
        return {
            "type": "result",
            "protocol": WORKER_PROTOCOL,
            "identity_sha256": self.identity_sha256,
            "request_id": request_id,
            "sequence": sequence,
            "result": dict(result),
            "worker_action": "isolate" if isolate else "continue",
        }

    def reject_pipelined(
        self,
        payload: Mapping[str, object],
    ) -> dict[str, object] | None:
        fault = self._fault(payload)
        request_id = fault.request_id if fault is not None else payload.get("request_id")
        sequence = fault.sequence if fault is not None else payload.get("sequence")
        if not isinstance(request_id, str) or not isinstance(sequence, int):
            return None
        return self._result_envelope(
            request_id=request_id,
            sequence=sequence,
            result=_stopped_result(),
            isolate=True,
        )

    def process(
        self,
        payload: Mapping[str, object],
    ) -> tuple[dict[str, object] | None, bool]:
        fault = self._fault(payload)
        if fault is not None:
            if fault.request_id is None or fault.sequence is None:
                return None, True
            return (
                self._result_envelope(
                    request_id=fault.request_id,
                    sequence=fault.sequence,
                    result=_stopped_result(),
                    isolate=True,
                ),
                True,
            )

        request_id = str(payload["request_id"])
        sequence = int(payload["sequence"])
        self.request_ids.add(request_id)
        self.next_sequence += 1
        isolate = False
        try:
            self.verify_identity()
            result = self.execute_command(payload["command"])  # type: ignore[arg-type]
            if (
                not isinstance(result, dict)
                or result.get("kind")
                not in {"described", "prepared", "accepted", "stopped"}
            ):
                raise WorkerError("Runtime returned an invalid Result union")
            self.verify_identity()
        except Exception:  # noqa: BLE001 - isolate without leaking internals
            result = _stopped_result()
            isolate = True
        return (
            self._result_envelope(
                request_id=request_id,
                sequence=sequence,
                result=result,
                isolate=isolate,
            ),
            isolate,
        )


def _input_has_buffered_data(stream: BinaryIO) -> bool:
    if hasattr(stream, "getbuffer") and hasattr(stream, "tell"):
        try:
            return stream.tell() < len(stream.getbuffer())  # type: ignore[attr-defined]
        except (OSError, ValueError):
            return False
    try:
        descriptor = stream.fileno()
    except (AttributeError, OSError):
        return False
    readable, _, _ = select.select([descriptor], [], [], 0)
    if not readable:
        return False
    try:
        peek = getattr(stream, "peek", None)
        if callable(peek):
            return bool(peek(1))
    except (OSError, ValueError):
        return False
    return True


def serve(
    session: WorkerSession,
    stdin: BinaryIO,
    stdout: BinaryIO,
    stderr: TextIO,
) -> int:
    """Serve frames synchronously; no second command can execute in flight."""

    while True:
        try:
            payload = read_frame(stdin)
        except FrameError:
            print("runtime_worker: invalid input frame; isolating", file=stderr)
            return EXIT_PROTOCOL
        if payload is None:
            return EXIT_OK

        if _input_has_buffered_data(stdin):
            response = session.reject_pipelined(payload)
            if response is not None:
                try:
                    write_frame(stdout, response)
                except (BrokenPipeError, OSError, FrameError):
                    return EXIT_TRANSPORT
            print("runtime_worker: multiple in-flight commands; isolating", file=stderr)
            return EXIT_PROTOCOL

        response, isolate = session.process(payload)
        pipelined_during_execution = _input_has_buffered_data(stdin)
        if response is not None:
            if pipelined_during_execution:
                response["worker_action"] = "isolate"
            try:
                write_frame(stdout, response)
            except FrameError:
                fallback = session._result_envelope(
                    request_id=str(response.get("request_id") or "transport"),
                    sequence=int(response.get("sequence") or 1),
                    result=_stopped_result(),
                    isolate=True,
                )
                try:
                    write_frame(stdout, fallback)
                except (BrokenPipeError, OSError, FrameError):
                    return EXIT_TRANSPORT
                return EXIT_PROTOCOL
            except (BrokenPipeError, OSError):
                return EXIT_TRANSPORT
        if isolate or pipelined_during_execution:
            if pipelined_during_execution:
                print("runtime_worker: multiple in-flight commands; isolating", file=stderr)
            return EXIT_PROTOCOL


@dataclass(frozen=True)
class Bootstrap:
    identity: WorkerIdentity
    interface: object
    verify_identity: Callable[[], None]


def bootstrap(
    *,
    expected_listing_sha256: str,
    expected_runtime_integrity_sha256: str,
    ready_timeout_seconds: float,
) -> Bootstrap:
    script_path = Path(__file__).absolute()
    resolved_script = script_path.resolve(strict=True)
    if script_path != resolved_script:
        raise IdentityError("worker entrypoint must not be a symlink")
    scripts_root = resolved_script.parent.parent
    release_root = scripts_root.parent.resolve(strict=True)
    guard = _load_guard(scripts_root)
    runtime_root = guard.runtime_root_for_executable(sys.executable)

    with _ready_deadline(ready_timeout_seconds):
        release = verify_release(
            release_root,
            expected_listing_sha256,
            verify_semantics=True,
        )
        site_roots, python_runtime_identity = _validate_runtime(
            guard,
            sys.executable,
            expected_runtime_integrity_sha256,
        )
        for site_root in site_roots:
            if str(site_root) not in sys.path:
                sys.path.append(str(site_root))
        if str(scripts_root) not in sys.path:
            sys.path.insert(0, str(scripts_root))

        from adapters.json_cli import resolve_store_root
        from reading_engine.evidence_rules import production_evidence_rules
        from reading_engine.interface import ReadingInterface
        from reading_engine.interface_contracts import Describe, Described

        # READY owns the expensive complete evidence validation.  Provider
        # turns retain their scoped validation and therefore cannot bypass it.
        evidence_rules = production_evidence_rules()
        if len(evidence_rules) != EXPECTED_EVIDENCE_RECORD_COUNT:
            raise IdentityError("evidence index is not 1328/1328 ready")

        store_identity = _prepare_store_namespace(resolve_store_root(release_root))
        store_root = Path(store_identity.path)
        interface = ReadingInterface(
            skill_root=release_root,
            store_root=store_root,
        )
        described = interface.execute(Describe())
        if not isinstance(described, Described):
            raise IdentityError("Runtime describe did not return Described")
        if described.protocol_version != RUNTIME_PROTOCOL:
            raise IdentityError("Runtime protocol identity mismatch")
        capability_ids = tuple(sorted(item.id for item in described.capabilities))
        if (
            len(capability_ids) != EXPECTED_CAPABILITY_COUNT
            or len(set(capability_ids)) != EXPECTED_CAPABILITY_COUNT
        ):
            raise IdentityError("Runtime capability inventory is incomplete")
        # Build the production engine now so request latency does not include
        # store/catalog/provider factory construction.
        interface.engine

        python_identity = {
            "implementation": platform.python_implementation(),
            "executable": str(Path(sys.executable).resolve(strict=True)),
            "version": list(sys.version_info[:3]),
            "runtime": python_runtime_identity,
        }
        identity = WorkerIdentity(
            protocol=WORKER_PROTOCOL,
            runtime_protocol=described.protocol_version,
            release_path=release.root,
            listing_sha256=release.listing_sha256,
            release_name=release.release_name,
            source_commit=release.source_commit,
            release_file_count=release.file_count,
            signed_paths_sha256=release.signed_paths_sha256,
            runtime_integrity_sha256=expected_runtime_integrity_sha256,
            python_identity=python_identity,
            store_namespace=str(store_root),
            store_namespace_identity=store_identity.bound_payload(),
            pid=os.getpid(),
            boot_nonce=secrets.token_hex(32),
            describe_manifest_digest=described.manifest_digest,
            capability_ids=capability_ids,
        )

    def verify_bound_identity() -> None:
        current_release = verify_release(
            release_root,
            expected_listing_sha256,
            verify_semantics=False,
        )
        if current_release != release:
            raise IdentityError("Runtime release identity drifted")
        _, current_runtime_identity = _validate_runtime(
            guard,
            sys.executable,
            expected_runtime_integrity_sha256,
        )
        if current_runtime_identity != python_runtime_identity:
            raise IdentityError("Python Runtime identity drifted")
        _verify_store_namespace(store_root, store_identity)
        if os.getpid() != identity.pid:
            raise IdentityError("worker PID identity drifted")

    return Bootstrap(
        identity=identity,
        interface=interface,
        verify_identity=verify_bound_identity,
    )


@contextmanager
def _reject_internal_stdio() -> Iterator[None]:
    """Keep Runtime writes from ever corrupting the framed transport."""

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (AttributeError, OSError, ValueError):
            pass
    saved_stdout = os.dup(sys.stdout.fileno())
    saved_stderr = os.dup(sys.stderr.fileno())
    with tempfile.TemporaryFile(mode="w+b") as captured_stdout, tempfile.TemporaryFile(
        mode="w+b"
    ) as captured_stderr:
        try:
            os.dup2(captured_stdout.fileno(), sys.stdout.fileno())
            os.dup2(captured_stderr.fileno(), sys.stderr.fileno())
            yield
        finally:
            for stream in (sys.stdout, sys.stderr):
                try:
                    stream.flush()
                except (AttributeError, OSError, ValueError):
                    pass
            os.dup2(saved_stdout, sys.stdout.fileno())
            os.dup2(saved_stderr, sys.stderr.fileno())
            os.close(saved_stdout)
            os.close(saved_stderr)
        captured_stdout.seek(0)
        captured_stderr.seek(0)
        if captured_stdout.read(1) or captured_stderr.read(1):
            raise WorkerError("Runtime wrote outside the Result transport")


def _execute_with_interface(interface: object) -> Callable[[Mapping[str, object]], dict[str, object]]:
    def execute(payload: Mapping[str, object]) -> dict[str, object]:
        with _reject_internal_stdio():
            from reading_engine.interface_contracts import command_from_dict

            command = command_from_dict(payload)
            result = interface.execute(command)  # type: ignore[attr-defined]
        rendered = result.to_dict()
        if not isinstance(rendered, dict):
            raise WorkerError("Runtime Result is not a JSON object")
        return rendered

    return execute


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-listing-sha256", required=True)
    parser.add_argument("--expected-runtime-integrity-sha256", required=True)
    parser.add_argument(
        "--ready-timeout-seconds",
        type=float,
        default=DEFAULT_READY_TIMEOUT_SECONDS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    started = time.perf_counter()
    arguments = _parser().parse_args(argv)
    try:
        # BufferedReader may prefetch a second frame while reading the first,
        # hiding pipelining from the file descriptor readiness check.  Use the
        # raw pipe for the physical protocol so queued commands remain visible
        # and single-in-flight is enforceable.
        stdin = getattr(sys.stdin.buffer, "raw", sys.stdin.buffer)
        stdout = getattr(sys.stdout.buffer, "raw", sys.stdout.buffer)
        guard = _load_guard(Path(__file__).resolve(strict=True).parent.parent)
        runtime_root = guard.runtime_root_for_executable(sys.executable)
        with guard.runtime_lock(runtime_root, exclusive=False):
            built = bootstrap(
                expected_listing_sha256=arguments.expected_listing_sha256,
                expected_runtime_integrity_sha256=(
                    arguments.expected_runtime_integrity_sha256
                ),
                ready_timeout_seconds=arguments.ready_timeout_seconds,
            )
            write_frame(
                stdout,
                built.identity.ready_payload(
                    ready_timeout_seconds=arguments.ready_timeout_seconds,
                    boot_ms=(time.perf_counter() - started) * 1000,
                ),
            )
            session = WorkerSession(
                identity_sha256=built.identity.identity_sha256,
                execute_command=_execute_with_interface(built.interface),
                verify_identity=built.verify_identity,
            )
            return serve(
                session,
                stdin,
                stdout,
                sys.stderr,
            )
    except (OSError, RuntimeError, ValueError, FrameError) as exc:
        print(
            f"runtime_worker: startup failed ({type(exc).__name__}: {exc})",
            file=sys.stderr,
        )
        return EXIT_STARTUP


if __name__ == "__main__":
    raise SystemExit(main())
