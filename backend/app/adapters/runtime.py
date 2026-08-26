import asyncio
import hashlib
import json
import os
import re
import signal
import stat
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Protocol, runtime_checkable

from app.config import _RUNTIME_RELEASE_PROFILES, Settings
from app.readings.capability_policy import (
    V51_RELEASE_CAPABILITY_IDS,
    V53_TIME_CHECK_RELEASE_CAPABILITY_IDS,
)
from app.readings.errors import RuntimeTransportError
from app.readings.runtime_contracts import (
    Accepted,
    Complete,
    Describe,
    Described,
    MingliCommand,
    MingliResult,
    Prepare,
    Prepared,
    ReadingBrief,
    Stopped,
    result_from_dict,
)

FAKE_STATE_TOKEN = "fake-opaque-state"
FAKE_MANIFEST_DIGEST = "f" * 64
_FAKE_RELEASE_CAPABILITY_SPECS = (
    ("bazi", "八字 Fake", "natal", ("life", "year", "month", "day")),
    ("fengshui", "风水 Fake", "fixture_object", ("fixture",)),
    ("fortune", "近时 Fake", "near_time_personal", ("day", "week")),
    ("liuren", "大六壬 Fake", "fixture_object", ("fixture",)),
    ("liuyao", "六爻 Fake", "concrete_event", ("instant",)),
    ("luming-nayin", "禄命纳音 Fake", "fixture_object", ("fixture",)),
    ("meihua", "梅花易数 Fake", "fixture_object", ("fixture",)),
    ("physiognomy", "相法 Fake", "fixture_object", ("fixture",)),
    ("qimen", "奇门遁甲 Fake", "fixture_object", ("fixture",)),
    ("selection", "择日 Fake", "fixture_object", ("fixture",)),
    ("taiyi", "太乙 Fake", "fixture_object", ("fixture",)),
    ("xingming", "星命 Fake", "fixture_object", ("fixture",)),
    ("ziwei", "紫微斗数 Fake", "fixture_object", ("fixture",)),
)
_FAKE_RELEASE_CAPABILITY_IDS = frozenset(
    capability_id
    for capability_id, _label, _object_id, _horizons in (_FAKE_RELEASE_CAPABILITY_SPECS)
)


@runtime_checkable
class MingliRuntime(Protocol):
    async def execute(self, command: MingliCommand) -> MingliResult: ...


EXPECTED_RUNTIME_PROTOCOL = "mingli-portable-interface-v2"
EXPECTED_RELEASE_FILE_COUNT = 217
V53_TIME_CHECK_RELEASE_FILE_COUNT = 225
EXPECTED_REFERENCE_PACK_COUNT = 55
EXPECTED_EVIDENCE_RECORD_COUNT = 1328
FROZEN_RELEASE_MANIFEST_SHA256 = "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68"
FROZEN_RELEASE_NAME = "mingli-master-portable-core"
FROZEN_SOURCE_COMMIT = "494ce0bba174a77800daf9b9c38ce9c9166d9a94"
RUNTIME_PROCESS_PATH = "/opt/node/bin:/usr/local/bin:/usr/bin:/bin"


class RuntimeStartupError(RuntimeError):
    """The configured Runtime Release is not safe to admit."""


@dataclass(frozen=True, slots=True)
class RuntimeReleaseInventory:
    release_manifest_sha256: str
    release_file_count: int
    provider_ids: tuple[str, ...]
    ready_provider_ids: tuple[str, ...]
    reference_pack_count: int
    evidence_record_count: int
    runtime_closure_file_count: int


class RuntimeReleaseInspector(Protocol):
    def inspect(self) -> RuntimeReleaseInventory: ...


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeStartupError(f"{label} path is invalid")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or value != relative.as_posix():
        raise RuntimeStartupError(f"{label} path is unsafe")
    return value


def _regular_file(root: Path, relative: object, label: str) -> Path:
    safe_relative = _safe_relative(relative, label)
    candidate = root / safe_relative
    try:
        metadata = candidate.lstat()
    except OSError as error:
        raise RuntimeStartupError(f"{label} is missing") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeStartupError(f"{label} must be a regular file")
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise RuntimeStartupError(f"{label} escapes the release root") from error
    return candidate


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeStartupError(f"{label} is not valid JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeStartupError(f"{label} must be a JSON object")
    return payload


def _require_private_directory(path: Path, label: str, *, writable: bool) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise RuntimeStartupError(f"{label} is missing") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeStartupError(f"{label} must be a real directory")
    if stat.S_IMODE(metadata.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeStartupError(f"{label} must not be group/world writable")
    if writable and not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        raise RuntimeStartupError(f"{label} must be readable and writable")


def _require_secure_release_parents(root: Path, relative: str) -> None:
    current = root
    for part in PurePosixPath(relative).parts[:-1]:
        current /= part
        _require_private_directory(current, "Runtime release directory", writable=False)


def _heading_ids(path: Path) -> set[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise RuntimeStartupError("reference index is unreadable") from error
    local_id_pattern = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~:-]*[-_:][A-Za-z0-9._~:-]*")
    ids: list[str] = []
    for line in lines:
        heading = re.match(r"^#{2,6}\s+(\S+)(?:\s|$)", line)
        index_row = re.match(r"^\|\s*([^|\s]+)\s*\|", line)
        match = heading or index_row
        if match is not None and local_id_pattern.fullmatch(match.group(1)):
            ids.append(match.group(1))
    if len(ids) != len(set(ids)):
        raise RuntimeStartupError("reference index contains duplicate local ids")
    return set(ids)


@dataclass(frozen=True, slots=True)
class FileSystemRuntimeReleaseInspector:
    release_root: Path
    expected_release_manifest_sha256: str
    expected_release_name: str
    expected_source_commit: str
    expected_capability_ids: tuple[str, ...] = V51_RELEASE_CAPABILITY_IDS
    expected_release_file_count: int = EXPECTED_RELEASE_FILE_COUNT

    def inspect(self) -> RuntimeReleaseInventory:
        _require_private_directory(self.release_root, "Runtime release root", writable=False)
        manifest_path = _regular_file(
            self.release_root,
            ".mingli-release-manifest.json",
            "Runtime release manifest",
        )
        manifest_sha256 = _sha256_file(manifest_path)
        if manifest_sha256 != self.expected_release_manifest_sha256:
            raise RuntimeStartupError("Runtime release manifest digest mismatch")
        manifest = _load_json(manifest_path, "Runtime release manifest")
        if (
            set(manifest) != {"schema_version", "release", "source_commit", "files", "modes"}
            or manifest.get("schema_version") != 3
            or manifest.get("release") != self.expected_release_name
            or manifest.get("source_commit") != self.expected_source_commit
        ):
            raise RuntimeStartupError("Runtime release identity mismatch")
        raw_files = manifest.get("files")
        raw_modes = manifest.get("modes")
        if not isinstance(raw_files, dict) or not isinstance(raw_modes, dict):
            raise RuntimeStartupError("Runtime release manifest inventory is invalid")
        if (
            len(raw_files) != self.expected_release_file_count
            or set(raw_files) != set(raw_modes)
        ):
            raise RuntimeStartupError("Runtime release manifest has an unexpected file count")
        manifest_paths: set[str] = set()
        for raw_relative, expected_digest in raw_files.items():
            relative = _safe_relative(raw_relative, "signed file")
            if not isinstance(expected_digest, str) or not re.fullmatch(
                r"[0-9a-f]{64}", expected_digest
            ):
                raise RuntimeStartupError("signed file digest is invalid")
            _require_secure_release_parents(self.release_root, relative)
            path = _regular_file(self.release_root, relative, "signed file")
            if _sha256_file(path) != expected_digest:
                raise RuntimeStartupError("signed file digest mismatch")
            expected_mode = raw_modes[relative]
            if (
                not isinstance(expected_mode, int)
                or stat.S_IMODE(path.stat().st_mode) != expected_mode
            ):
                raise RuntimeStartupError(f"signed file mode mismatch: {relative}")
            manifest_paths.add(relative)

        self._verify_filesystem_inventory(manifest_paths)
        closure_count = self._verify_closure(manifest_paths)
        provider_ids, ready_provider_ids = self._verify_providers(manifest_paths)
        pack_ids, local_ids = self._verify_reference_packs(manifest_paths)
        evidence_count = self._verify_evidence(manifest_paths, pack_ids, local_ids)
        return RuntimeReleaseInventory(
            release_manifest_sha256=manifest_sha256,
            release_file_count=len(manifest_paths),
            provider_ids=provider_ids,
            ready_provider_ids=ready_provider_ids,
            reference_pack_count=len(pack_ids),
            evidence_record_count=evidence_count,
            runtime_closure_file_count=closure_count,
        )

    def _verify_filesystem_inventory(self, manifest_paths: set[str]) -> None:
        actual_paths: set[str] = set()
        actual_directories: set[str] = set()
        for path in self.release_root.rglob("*"):
            try:
                metadata = path.lstat()
            except OSError as error:
                raise RuntimeStartupError("Runtime release inventory is unreadable") from error
            relative = path.relative_to(self.release_root).as_posix()
            if stat.S_ISLNK(metadata.st_mode):
                raise RuntimeStartupError("Runtime release contains an unsigned filesystem entry")
            if stat.S_ISDIR(metadata.st_mode):
                _require_private_directory(path, "Runtime release directory", writable=False)
                actual_directories.add(relative)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise RuntimeStartupError("Runtime release contains an unsigned filesystem entry")
            actual_paths.add(relative)
        expected_paths = manifest_paths | {".mingli-release-manifest.json"}
        expected_directories: set[str] = set()
        for relative in expected_paths:
            parent = PurePosixPath(relative).parent
            while parent != PurePosixPath("."):
                expected_directories.add(parent.as_posix())
                parent = parent.parent
        if actual_paths != expected_paths or actual_directories != expected_directories:
            raise RuntimeStartupError("Runtime release contains an unsigned filesystem entry")

    def _verify_closure(self, manifest_paths: set[str]) -> int:
        closure = _load_json(
            _regular_file(
                self.release_root,
                "release/runtime-closure-v1.json",
                "Runtime closure",
            ),
            "Runtime closure",
        )
        if closure.get("schema_version") != "mingli-runtime-closure-v1":
            raise RuntimeStartupError("Runtime closure schema mismatch")
        explicit = closure.get("files")
        patterns = closure.get("patterns")
        if not isinstance(explicit, list) or not isinstance(patterns, list):
            raise RuntimeStartupError("Runtime closure inventory is invalid")
        selected = {_safe_relative(item, "Runtime closure") for item in explicit}
        for raw_pattern in patterns:
            if not isinstance(raw_pattern, str) or not raw_pattern:
                raise RuntimeStartupError("Runtime closure pattern is invalid")
            matches = {
                relative
                for relative in manifest_paths
                if PurePosixPath(relative).match(raw_pattern)
            }
            if not matches:
                raise RuntimeStartupError("Runtime closure pattern matched no signed files")
            selected.update(matches)
        if selected != manifest_paths:
            raise RuntimeStartupError(
                "Runtime closure does not cover "
                f"all {len(manifest_paths)} signed release files"
            )
        return len(selected)

    def _verify_providers(
        self, manifest_paths: set[str]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        catalog_path = _regular_file(
            self.release_root,
            "resources/runtime/catalog-v1.json",
            "Provider catalog",
        )
        catalog = _load_json(catalog_path, "Provider catalog")
        entries = catalog.get("providers")
        if (
            set(catalog) != {"providers", "schema_version"}
            or catalog.get("schema_version") != "catalog-v1"
            or not isinstance(entries, list)
            or len(entries) != len(self.expected_capability_ids)
        ):
            raise RuntimeStartupError(
                "Runtime Provider catalog is incomplete "
                f"(expected {len(self.expected_capability_ids)} Provider catalog entries)"
            )
        provider_ids: list[str] = []
        for entry in entries:
            relative = _safe_relative(entry, "Provider manifest")
            release_relative = f"resources/runtime/{relative}"
            if release_relative not in manifest_paths:
                raise RuntimeStartupError("Provider manifest is not signed")
            provider = _load_json(
                _regular_file(
                    self.release_root / "resources" / "runtime",
                    relative,
                    "Provider manifest",
                ),
                "Provider manifest",
            )
            provider_id = provider.get("id")
            runtime_capability = provider.get("runtime_capability")
            if (
                provider.get("schema_version") != "provider-manifest-v1"
                or not isinstance(provider_id, str)
                or not isinstance(provider.get("entrypoint"), str)
                or not isinstance(provider.get("capability"), dict)
                or not isinstance(runtime_capability, dict)
                or runtime_capability.get("system") != provider_id
            ):
                raise RuntimeStartupError("Provider manifest is not ready")
            provider_ids.append(provider_id)
        ordered = tuple(sorted(provider_ids))
        if len(set(provider_ids)) != len(provider_ids) or ordered != self.expected_capability_ids:
            raise RuntimeStartupError("Provider inventory does not match the admitted release")
        return ordered, ordered

    def _verify_reference_packs(
        self,
        manifest_paths: set[str],
    ) -> tuple[set[str], dict[str, set[str]]]:
        catalog = _load_json(
            _regular_file(
                self.release_root,
                "references/catalog/catalog.json",
                "reference catalog",
            ),
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
            raise RuntimeStartupError("reference catalog is not 55/55 ready")
        pack_ids: set[str] = set()
        local_ids: dict[str, set[str]] = {}
        for item in packs:
            if not isinstance(item, dict):
                raise RuntimeStartupError("reference pack record is invalid")
            system = item.get("system")
            slug = item.get("slug")
            if not isinstance(system, str) or not isinstance(slug, str):
                raise RuntimeStartupError("reference pack identity is invalid")
            pack_id = f"{system}/{slug}"
            if pack_id in pack_ids or item.get("d2_status") != "ready":
                raise RuntimeStartupError("reference pack readiness is invalid")
            pack_ids.add(pack_id)
            rules_relative = f"references/books/{pack_id}/rules.md"
            quotes_relative = f"references/books/{pack_id}/quote-index.md"
            if rules_relative not in manifest_paths or quotes_relative not in manifest_paths:
                raise RuntimeStartupError("reference pack files are not signed")
            rules = _regular_file(self.release_root, rules_relative, "reference rules")
            quotes = _regular_file(self.release_root, quotes_relative, "reference quote index")
            local_ids[pack_id] = _heading_ids(rules) | _heading_ids(quotes)
            if item.get("local_fulltext_required_for_runtime") not in {True, False}:
                raise RuntimeStartupError("reference pack runtime policy is invalid")
            if item.get("local_fulltext_required_for_runtime") is True:
                fulltext = _safe_relative(item.get("local_fulltext_path"), "reference excerpt")
                if fulltext not in manifest_paths:
                    raise RuntimeStartupError("required reference excerpt is not signed")
                if _sha256_file(
                    _regular_file(self.release_root, fulltext, "reference excerpt")
                ) != item.get("local_fulltext_sha256"):
                    raise RuntimeStartupError("reference excerpt digest mismatch")
        return pack_ids, local_ids

    def _verify_evidence(
        self,
        manifest_paths: set[str],
        pack_ids: set[str],
        local_ids: Mapping[str, set[str]],
    ) -> int:
        relative = "references/index/evidence-rules.jsonl"
        if relative not in manifest_paths:
            raise RuntimeStartupError("evidence index is not signed")
        path = _regular_file(self.release_root, relative, "evidence index")
        try:
            rows = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeStartupError("evidence index is not valid JSONL") from error
        if len(rows) != EXPECTED_EVIDENCE_RECORD_COUNT or any(
            not isinstance(row, dict) for row in rows
        ):
            raise RuntimeStartupError("evidence index must contain 1328 records")
        rule_ids = [row.get("rule_id") for row in rows]
        if any(not isinstance(rule_id, str) or not rule_id for rule_id in rule_ids):
            raise RuntimeStartupError("evidence rule id is invalid")
        rule_id_set = set(rule_ids)
        if len(rule_id_set) != EXPECTED_EVIDENCE_RECORD_COUNT:
            raise RuntimeStartupError("evidence rule ids are not unique")
        source_digests: dict[str, str] = {}
        for row in rows:
            rule_id = str(row["rule_id"])
            source_pack = row.get("source_pack")
            if (
                row.get("schema_version") != "mingli-evidence-rule-v1"
                or row.get("record_kind") != "substantive_rule"
                or source_pack not in pack_ids
            ):
                raise RuntimeStartupError("evidence record identity is invalid")
            source_relative = _safe_relative(row.get("source_path"), "evidence source")
            if source_relative not in manifest_paths:
                raise RuntimeStartupError("evidence source is not signed")
            source_digest = source_digests.setdefault(
                source_relative,
                _sha256_file(_regular_file(self.release_root, source_relative, "evidence source")),
            )
            quote = row.get("quote")
            if source_digest != row.get("source_sha256"):
                raise RuntimeStartupError("evidence source digest mismatch")
            if (
                not isinstance(quote, str)
                or not quote.strip()
                or hashlib.sha256(quote.encode("utf-8")).hexdigest() != row.get("quote_hash")
            ):
                raise RuntimeStartupError("evidence quote digest mismatch")
            for field_name in ("depends_on_rule_ids", "exception_rule_ids"):
                refs = row.get(field_name)
                if not isinstance(refs, list) or any(ref not in rule_id_set for ref in refs):
                    raise RuntimeStartupError("evidence rule dependency is not closed")
            conflicts = row.get("conflict_rule_ids")
            if not isinstance(conflicts, list):
                raise RuntimeStartupError("evidence conflict references are invalid")
            for conflict in conflicts:
                if conflict in rule_id_set:
                    continue
                if not isinstance(conflict, str) or conflict.count("#") != 1:
                    raise RuntimeStartupError("evidence conflict reference is not closed")
                pack_id, local_id = conflict.split("#", 1)
                if local_id not in local_ids.get(pack_id, set()):
                    raise RuntimeStartupError("evidence conflict reference is not closed")
            del rule_id
        return len(rows)


def _json_compatible(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_compatible(item) for item in value]
    return value


def runtime_capability_shape_sha256(capabilities: object) -> str:
    payload = json.dumps(
        _json_compatible(capabilities),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(slots=True)
class RuntimeStartupGate:
    runtime: MingliRuntime
    release_inspector: RuntimeReleaseInspector
    expected_manifest_digest: str
    expected_release_manifest_sha256: str
    expected_capability_shape_sha256: str
    expected_capability_ids: tuple[str, ...] = V51_RELEASE_CAPABILITY_IDS
    expected_release_file_count: int = EXPECTED_RELEASE_FILE_COUNT
    _ready: bool = field(default=False, init=False)

    async def startup(self) -> Described:
        self._ready = False
        try:
            if getattr(self.runtime, "adapter_kind", None) != "one-shot-process":
                raise RuntimeStartupError("Fake Runtime is forbidden by the startup gate")
            inventory = self.release_inspector.inspect()
            result = await self.runtime.execute(Describe())
            if not isinstance(result, Described):
                raise RuntimeStartupError("Runtime describe did not return Described")
            self._validate(result, inventory)
        except RuntimeStartupError:
            raise
        except Exception as error:
            raise RuntimeStartupError("runtime_startup_failed") from error
        self._ready = True
        return result

    async def readiness_probe(self) -> None:
        if not self._ready:
            raise RuntimeStartupError("Runtime startup admission is not ready")

    def _validate(self, description: Described, inventory: RuntimeReleaseInventory) -> None:
        if description.protocol_version != EXPECTED_RUNTIME_PROTOCOL:
            raise RuntimeStartupError("Runtime protocol mismatch")
        if description.manifest_digest != self.expected_manifest_digest:
            raise RuntimeStartupError("Runtime manifest digest mismatch")
        described_ids = tuple(str(item["id"]) for item in description.capabilities)
        if described_ids != self.expected_capability_ids:
            raise RuntimeStartupError(
                "Runtime must describe the exact "
                f"{len(self.expected_capability_ids)} Provider set"
            )
        if (
            runtime_capability_shape_sha256(description.capabilities)
            != self.expected_capability_shape_sha256
        ):
            raise RuntimeStartupError("Runtime capability shape mismatch")
        if inventory.release_manifest_sha256 != self.expected_release_manifest_sha256:
            raise RuntimeStartupError("Runtime release manifest digest mismatch")
        expected_providers = self.expected_capability_ids
        if inventory.provider_ids != expected_providers:
            raise RuntimeStartupError("Runtime release Provider inventory mismatch")
        if inventory.ready_provider_ids != expected_providers:
            count = len(expected_providers)
            raise RuntimeStartupError(
                f"Runtime release is not fully ready ({count}/{count} ready)"
            )
        if inventory.release_file_count != self.expected_release_file_count:
            raise RuntimeStartupError("Runtime release manifest is incomplete")
        if inventory.runtime_closure_file_count != self.expected_release_file_count:
            raise RuntimeStartupError("Runtime closure is incomplete")
        if inventory.reference_pack_count != EXPECTED_REFERENCE_PACK_COUNT:
            raise RuntimeStartupError("Runtime reference inventory is not 55/55")
        if inventory.evidence_record_count != EXPECTED_EVIDENCE_RECORD_COUNT:
            raise RuntimeStartupError("Runtime evidence inventory is not 1328")


async def _read_capped_stream(
    stream: asyncio.StreamReader,
    *,
    limit: int,
    error_code: str,
) -> bytes:
    data = bytearray()
    while chunk := await stream.read(min(64 * 1024, limit + 1 - len(data))):
        data.extend(chunk)
        if len(data) > limit:
            raise RuntimeTransportError(error_code)
    return bytes(data)


async def _exchange(
    process: asyncio.subprocess.Process,
    stdin: bytes,
    *,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> tuple[bytes, bytes]:
    if process.stdin is None or process.stdout is None or process.stderr is None:
        raise RuntimeTransportError("runtime_pipe_unavailable")
    stdout_task = asyncio.create_task(
        _read_capped_stream(
            process.stdout,
            limit=max_stdout_bytes,
            error_code="runtime_stdout_too_large",
        )
    )
    stderr_task = asyncio.create_task(
        _read_capped_stream(
            process.stderr,
            limit=max_stderr_bytes,
            error_code="runtime_stderr_too_large",
        )
    )
    try:
        with suppress(BrokenPipeError, ConnectionResetError):
            process.stdin.write(stdin)
            await process.stdin.drain()
            process.stdin.close()
            await process.stdin.wait_closed()
        stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
        await process.wait()
        return stdout, stderr
    finally:
        for task in (stdout_task, stderr_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)


async def _kill_process_group(
    process: asyncio.subprocess.Process,
    process_group_id: int | None = None,
) -> None:
    if process_group_id is None:
        with suppress(ProcessLookupError):
            process_group_id = os.getpgid(process.pid)
    if process_group_id is not None:
        with suppress(ProcessLookupError, PermissionError):
            os.killpg(process_group_id, signal.SIGKILL)
    await process.wait()


class OneShotMingliRuntimeAdapter:
    """Call the fixed portable JSON Runtime exactly once per command."""

    adapter_kind = "one-shot-process"
    production_ready = False

    def __init__(
        self,
        *,
        launcher_path: Path,
        runtime_python_path: Path,
        state_root: Path,
        timeout_seconds: float,
        max_stdin_bytes: int = 2 * 1024 * 1024,
        max_stdout_bytes: int = 2 * 1024 * 1024,
        max_stderr_bytes: int = 64 * 1024,
    ) -> None:
        if not launcher_path.is_absolute():
            raise ValueError("Runtime launcher path must be absolute")
        if not runtime_python_path.is_absolute():
            raise ValueError("Runtime Python path must be absolute")
        if not state_root.is_absolute():
            raise ValueError("Runtime state root must be absolute")
        if timeout_seconds <= 0:
            raise ValueError("Runtime timeout must be positive")
        if max_stdin_bytes < 1 or max_stdout_bytes < 1 or max_stderr_bytes < 1:
            raise ValueError("Runtime I/O limits must be positive")
        _require_private_directory(state_root, "Runtime state root", writable=True)
        self._launcher_path = launcher_path
        self._runtime_python_path = runtime_python_path
        self._state_root = state_root
        self._timeout_seconds = timeout_seconds
        self._max_stdin_bytes = max_stdin_bytes
        self._max_stdout_bytes = max_stdout_bytes
        self._max_stderr_bytes = max_stderr_bytes

    async def execute(self, command: MingliCommand) -> MingliResult:
        stdin = (
            json.dumps(
                command.to_dict(),
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
        if len(stdin) > self._max_stdin_bytes:
            raise RuntimeTransportError("runtime_stdin_too_large")
        environment = {
            "HOME": "/nonexistent",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "MINGLI_PYTHON": str(self._runtime_python_path),
            "MINGLI_STORE_ROOT": str(self._state_root),
            "PATH": RUNTIME_PROCESS_PATH,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": "/dev/null",
            "TZ": "UTC",
        }
        try:
            process = await asyncio.create_subprocess_exec(
                str(self._launcher_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=environment,
                start_new_session=True,
            )
        except OSError as error:
            raise RuntimeTransportError("runtime_spawn_failed") from error
        try:
            process_group_id: int | None = os.getpgid(process.pid)
        except ProcessLookupError:
            process_group_id = None
        try:
            async with asyncio.timeout(self._timeout_seconds):
                stdout, _stderr = await _exchange(
                    process,
                    stdin,
                    max_stdout_bytes=self._max_stdout_bytes,
                    max_stderr_bytes=self._max_stderr_bytes,
                )
        except TimeoutError as error:
            await _kill_process_group(process, process_group_id)
            raise RuntimeTransportError("runtime_timed_out") from error
        except RuntimeTransportError:
            await _kill_process_group(process, process_group_id)
            raise
        except BaseException:
            await _kill_process_group(process, process_group_id)
            raise
        if process.returncode != 0:
            raise RuntimeTransportError("runtime_nonzero_exit")
        try:
            decoded: object = json.loads(stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            decoded = None
        if not isinstance(decoded, Mapping):
            stdout = b""
            raise RuntimeTransportError("runtime_invalid_output")
        try:
            result: MingliResult | None = result_from_dict(decoded)
        except (KeyError, TypeError, ValueError):
            result = None
        if result is None:
            decoded = None
            stdout = b""
            raise RuntimeTransportError("runtime_invalid_result")
        return result


def build_runtime_startup_gate(settings: Settings) -> RuntimeStartupGate:
    """Build the real Runtime boundary exclusively from server settings."""

    if settings.runtime_adapter != "one-shot":
        raise RuntimeStartupError("a real one-shot Runtime adapter is required")
    required_paths = {
        "launcher": settings.runtime_launcher_path,
        "Python": settings.runtime_python_path,
        "release root": settings.runtime_release_root,
        "state root": settings.runtime_state_root,
    }
    if any(path is None for path in required_paths.values()):
        raise RuntimeStartupError("Runtime process paths are incomplete")
    if settings.runtime_expected_manifest_digest is None:
        raise RuntimeStartupError("Runtime expected manifest digest is missing")
    if settings.runtime_expected_capability_shape_sha256 is None:
        raise RuntimeStartupError("Runtime expected capability shape digest is missing")
    profile = _RUNTIME_RELEASE_PROFILES.get(settings.runtime_release_profile)
    if profile is None:
        raise RuntimeStartupError("Runtime release profile is not admitted")
    if settings.environment == "production" or settings.runtime_release_profile != "v51":
        if settings.runtime_expected_manifest_digest != profile["manifest_digest"]:
            raise RuntimeStartupError(
                "Runtime manifest digest does not match the admitted release"
            )
        if (
            settings.runtime_expected_capability_shape_sha256
            != profile["capability_shape_sha256"]
        ):
            raise RuntimeStartupError(
                "Runtime capability shape does not match the admitted release"
            )
    launcher_path = required_paths["launcher"]
    runtime_python_path = required_paths["Python"]
    release_root = required_paths["release root"]
    state_root = required_paths["state root"]
    assert launcher_path is not None
    assert runtime_python_path is not None
    assert release_root is not None
    assert state_root is not None
    expected_capability_ids = (
        V53_TIME_CHECK_RELEASE_CAPABILITY_IDS
        if settings.runtime_release_profile == "v53-time-check"
        else V51_RELEASE_CAPABILITY_IDS
    )
    expected_release_file_count = (
        V53_TIME_CHECK_RELEASE_FILE_COUNT
        if settings.runtime_release_profile == "v53-time-check"
        else EXPECTED_RELEASE_FILE_COUNT
    )
    runtime = OneShotMingliRuntimeAdapter(
        launcher_path=launcher_path,
        runtime_python_path=runtime_python_path,
        state_root=state_root,
        timeout_seconds=settings.runtime_timeout_seconds,
        max_stdin_bytes=settings.runtime_max_stdin_bytes,
        max_stdout_bytes=settings.runtime_max_stdout_bytes,
        max_stderr_bytes=settings.runtime_max_stderr_bytes,
    )
    inspector = FileSystemRuntimeReleaseInspector(
        release_root=release_root,
        expected_release_manifest_sha256=profile["release_manifest_sha256"],
        expected_release_name=profile["release_name"],
        expected_source_commit=profile["source_commit"],
        expected_capability_ids=expected_capability_ids,
        expected_release_file_count=expected_release_file_count,
    )
    return RuntimeStartupGate(
        runtime=runtime,
        release_inspector=inspector,
        expected_manifest_digest=settings.runtime_expected_manifest_digest,
        expected_release_manifest_sha256=profile["release_manifest_sha256"],
        expected_capability_shape_sha256=(settings.runtime_expected_capability_shape_sha256),
        expected_capability_ids=expected_capability_ids,
        expected_release_file_count=expected_release_file_count,
    )


def _term(term_id: str, label: str) -> dict[str, object]:
    return {"id": term_id, "label": label, "description": None}


def _capability(
    capability_id: str,
    *,
    label: str,
    object_id: str,
    horizons: tuple[str, ...],
) -> dict[str, object]:
    return {
        "id": capability_id,
        "label": label,
        "description": "仅用于网站合同测试的 Fake 能力。",
        "objects": [_term(object_id, object_id)],
        "horizons": [_term(item, item) for item in horizons],
        "dimensions": [_term("overview", "概览"), _term("career", "事业")],
        "default_dimension_ids": ["overview"],
        "input_fields": [
            {
                "id": "fixture_input",
                "label": "合同测试输入",
                "type_id": "text",
                "description": None,
                "choices": [],
            }
        ],
        "required_input_groups": [["fixture_input"]],
    }


class FakeMingliRuntimeAdapter:
    """Deterministic contract Fake; it never performs命理 calculation."""

    adapter_kind = "fake"
    production_ready = False

    def __init__(self) -> None:
        self._accepted_by_token: dict[str, str] = {}

    async def execute(self, command: MingliCommand) -> MingliResult:
        if isinstance(command, Describe):
            return self._describe()
        if isinstance(command, Prepare):
            return self._prepare(command)
        if isinstance(command, Complete):
            first_copy = self._accepted_by_token.setdefault(
                command.state_token,
                command.public_copy,
            )
            return Accepted(
                state_token=command.state_token,
                public_copy=first_copy,
            )
        raise TypeError(f"unsupported command type: {type(command).__name__}")

    def _describe(self) -> Described:
        return Described(
            protocol_version="mingli-portable-interface-v2",
            manifest_digest=FAKE_MANIFEST_DIGEST,
            capabilities=tuple(
                _capability(
                    capability_id,
                    label=label,
                    object_id=object_id,
                    horizons=horizons,
                )
                for capability_id, label, object_id, horizons in (_FAKE_RELEASE_CAPABILITY_SPECS)
            ),
        )

    def _prepare(self, command: Prepare) -> Prepared | Stopped:
        capability_id = command.intent.get("capability_id")
        if capability_id not in _FAKE_RELEASE_CAPABILITY_IDS:
            return Stopped(
                reason="unsupported",
                public_copy="Fake Runtime 未描述该测试能力。",
                state_token=None,
                input_request=None,
            )
        if not command.facts:
            return Stopped(
                reason="need_input",
                public_copy="Fake Runtime 还需要合同测试输入。",
                state_token=FAKE_STATE_TOKEN,
                input_request={
                    "requirements": [
                        {
                            "any_of": [
                                {
                                    "id": "fixture_input",
                                    "label": "合同测试输入",
                                    "type_id": "text",
                                    "description": None,
                                    "choices": [],
                                }
                            ]
                        }
                    ]
                },
            )
        return Prepared(
            state_token=FAKE_STATE_TOKEN,
            brief=self._brief(command, str(capability_id)),
        )

    def _brief(self, command: Prepare, capability_id: str) -> ReadingBrief:
        raw_subjects = command.intent.get("subject_refs")
        subject_refs = raw_subjects if isinstance(raw_subjects, tuple) else ()
        subject_ref = str(subject_refs[0]) if subject_refs else "fixture:subject"
        raw_dimensions = command.intent.get("dimension_ids")
        dimensions = (
            tuple(str(item) for item in raw_dimensions)
            if isinstance(raw_dimensions, tuple)
            else ("overview",)
        )
        raw_horizon = command.intent.get("horizon")
        horizon = raw_horizon if isinstance(raw_horizon, Mapping) else {}

        findings = [
            {
                "ref": f"finding:fake-{index}",
                "subject_ref": subject_ref,
                "dimension_ids": [dimension_id],
                "kind_id": "kind.tendency",
                "data": {"fixture": True},
                "fact_refs": ["fact:fake-1"],
                "evidence_refs": [],
                "limit_kind_ids": ["limit:traditional"],
                "support_mode": "exact",
            }
            for index, dimension_id in enumerate(dimensions, start=1)
        ]
        claim_scopes = [
            {
                "subject_ref": subject_ref,
                "dimension_id": dimension_id,
                "allowed_kind_ids": ["kind.tendency"],
                "certainty_ceiling_id": "certainty.tendency",
                "fact_refs": ["fact:fake-1"],
                "evidence_refs": [],
            }
            for dimension_id in dimensions
        ]

        return ReadingBrief.from_dict(
            {
                "question": command.query,
                "vocabulary": [],
                "facts": [
                    {
                        "ref": "fact:fake-1",
                        "subject_ref": subject_ref,
                        "kind_id": "kind.fixture",
                        "value": {"fixture": True},
                        "display_text": "这是 Fake Runtime 合同事实，不是命理结果。",
                    }
                ],
                "evidence": [],
                "findings": findings,
                "claim_scopes": claim_scopes,
                "limits": [
                    {
                        "kind_id": "limit:traditional",
                        "public_text": "这是 Fake Runtime 合同边界。",
                        "scope_refs": [subject_ref],
                        "detail_ids": [],
                    }
                ],
                "prior_answer": None,
                "request_view": {
                    "subject_refs": list(subject_refs) or [subject_ref],
                    "capability_ids": [capability_id],
                    "object_id": str(command.intent["object_id"]),
                    "dimension_ids": list(dimensions),
                    "horizon": {
                        "kind_id": str(horizon["kind_id"]),
                        "start": horizon.get("start"),
                        "end": horizon.get("end"),
                    },
                },
            }
        )
