import asyncio
import fcntl
import hashlib
import json
import os
import re
import secrets
import signal
import stat
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Protocol, runtime_checkable

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
    RuntimeFailure,
    Stopped,
    TimeLayerEntitlementResolution,
    resolve_time_layer_entitlement_resolution,
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
EXPECTED_RELEASE_FILE_COUNT = 218
EXPECTED_RELEASE_PHYSICAL_FILE_COUNT = EXPECTED_RELEASE_FILE_COUNT + 1
V53_TIME_CHECK_RELEASE_FILE_COUNT = 227
V53_TIME_CHECK_RELEASE_PHYSICAL_FILE_COUNT = 228
EXPECTED_REFERENCE_PACK_COUNT = 55
EXPECTED_EVIDENCE_RECORD_COUNT = 1328
FROZEN_RELEASE_MANIFEST_SHA256 = (
    "93433f7fa9a9bef1115216240767c2c8e12e4ad9f0807124d05a47ddd0701f5d"
)
FROZEN_RELEASE_NAME = "mingli-master-portable-core"
FROZEN_SOURCE_COMMIT = "adfd7b6bf1c6a5e6df184bdd792bbf4956b009e1"
_FORBIDDEN_V51_LISTINGS = frozenset(
    {
        "251ecf42ea12a64c7d38618a794442007beea7432835e414251006809c2d3611",
        "e8d4111342d2334868bfa570d31c4105126301e44766a9f5482236db19f2bf68",
        "d1b49d5842feb5d4143330d1d250af625f42644a930f7d9d9c344c5d0363b090",
        "f1deb17a9b4f39b09b2478c8942dcf0761d90bcba95dcbc44a15b8c84f79190b",
        "9700fe96e2c440dc8b14c41aed576264d893c7a23d638708eafe40388771db71",
    }
)
_FORBIDDEN_V51_SOURCES = frozenset(
    {
        "494ce0bba174a77800daf9b9c38ce9c9166d9a94",
        "9c615a70f08d5609af09ead100d2b5d90e558fe8",
        "6db9dd37d8e62cd425798be2c64ad1121c1c1649",
    }
)
_FORBIDDEN_V51_WORKERS = frozenset(
    {
        "3512987322ef18bb91c4798e77d7ef982d2e7e31ae9e2ddd321d78aa90261b50",
        "e89df2c08df29e65ffc91c05e8e4e5be99f72f67e26b79c5b23a4eb2222ddc9c",
    }
)
RUNTIME_PROCESS_PATH = "/opt/node/bin:/usr/local/bin:/usr/bin:/bin"
ONE_SHOT_SHELL_NAME = "run_reading_transaction.sh"
ONE_SHOT_SHELL_INTERPRETER = Path("/bin/sh")
WORKER_PROTOCOL = "mingli-runtime-worker-v2"
WORKER_TURN_TERMINAL = "result-idle-v1"
WORKER_TURN_TERMINAL_TYPE = "idle"
WORKER_RELATIVE = "scripts/reading_engine/runtime_worker.py"
WORKER_FRAME_HEADER_BYTES = 4
WORKER_MAX_FRAME_BYTES = 4 * 1024 * 1024
WORKER_DEFAULT_READY_TIMEOUT_SECONDS = 15.0
WORKER_REQUEST_TIMEOUT_SECONDS = 2.0
WORKER_AUDIT_TIMEOUT_SECONDS = 0.25
WORKER_MAX_PENDING_AUDIT_APPENDS = 2
WORKER_STOPPED_COPY = "本次处理未完成，请稍后重试。"
RUNTIME_TURN_AUDIT_NAME = "runtime-turn-audit.jsonl"
_COMMAND_DIGEST_REDACTED_KEYS = frozenset({"facts", "query", "public_copy"})
_RESULT_FRAME_KEYS = frozenset(
    {
        "type",
        "protocol",
        "identity_sha256",
        "request_id",
        "sequence",
        "result",
        "worker_action",
    }
)
_IDLE_FRAME_KEYS = frozenset({"type", "protocol", "identity_sha256", "request_id", "sequence"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class RuntimeStartupError(RuntimeError):
    """The configured Runtime Release is not safe to admit."""


@dataclass(frozen=True, slots=True)
class RuntimeReleaseInventory:
    release_manifest_sha256: str
    release_file_count: int
    physical_file_count: int
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
    expected_physical_file_count: int = EXPECTED_RELEASE_PHYSICAL_FILE_COUNT

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

        physical_file_count = self._verify_filesystem_inventory(manifest_paths)
        if physical_file_count != self.expected_physical_file_count:
            raise RuntimeStartupError(
                "Runtime release has an unexpected physical file count"
            )
        closure_count = self._verify_closure(manifest_paths)
        provider_ids, ready_provider_ids = self._verify_providers(manifest_paths)
        pack_ids, local_ids = self._verify_reference_packs(manifest_paths)
        evidence_count = self._verify_evidence(manifest_paths, pack_ids, local_ids)
        return RuntimeReleaseInventory(
            release_manifest_sha256=manifest_sha256,
            release_file_count=len(manifest_paths),
            physical_file_count=physical_file_count,
            provider_ids=provider_ids,
            ready_provider_ids=ready_provider_ids,
            reference_pack_count=len(pack_ids),
            evidence_record_count=evidence_count,
            runtime_closure_file_count=closure_count,
        )

    def _verify_filesystem_inventory(self, manifest_paths: set[str]) -> int:
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
        return len(actual_paths)

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
    expected_physical_file_count: int = EXPECTED_RELEASE_PHYSICAL_FILE_COUNT
    _ready: bool = field(default=False, init=False)

    async def _close_runtime(self) -> None:
        close = getattr(self.runtime, "close", None)
        if callable(close):
            with suppress(Exception):
                await close()

    async def startup(self) -> Described:
        self._ready = False
        try:
            adapter_kind = getattr(self.runtime, "adapter_kind", None)
            if adapter_kind not in {"one-shot-process", "runtime-worker-v2"}:
                raise RuntimeStartupError("Fake Runtime is forbidden by the startup gate")
            inventory = self.release_inspector.inspect()
            start = getattr(self.runtime, "start", None)
            if callable(start):
                await start()
            result = await self.runtime.execute(Describe())
            if not isinstance(result, Described):
                raise RuntimeStartupError("Runtime describe did not return Described")
            self._validate(result, inventory)
        except RuntimeStartupError:
            await self._close_runtime()
            raise
        except Exception as error:
            await self._close_runtime()
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
        if inventory.physical_file_count != self.expected_physical_file_count:
            raise RuntimeStartupError("Runtime release physical inventory is incomplete")
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


def _python_shebang_interpreter(launcher_path: Path) -> Path | None:
    try:
        with launcher_path.open("rb") as handle:
            first = handle.readline(256)
    except OSError:
        return None
    if not first.startswith(b"#!"):
        return None
    try:
        line = first[2:].decode("ascii").strip()
    except UnicodeDecodeError:
        return None
    if not line:
        return None
    interpreter = Path(line.split()[0])
    if not interpreter.is_absolute() or not interpreter.name.lower().startswith("python"):
        return None
    return interpreter


def one_shot_spawn_argv(
    launcher_path: Path,
    runtime_python_path: Path | None = None,
) -> tuple[str, ...]:
    """Fixed argv for the one-shot rollback launcher.

    ``run_reading_transaction.sh`` is invoked through ``/bin/sh`` and the
    absolute launcher path.  Python launchers use the worker-v2 isolated
    interpreter form ``python -I -S -B <launcher>`` so the first Describe
    does not pay kernel shebang plus site import against
    ``PYTHONPYCACHEPREFIX=/dev/null`` — that combination hangs a cold
    interpreter past the 2s budget.  The Git mode may be ``100644``; this
    path never chmod's the file and never interpolates user input.
    """

    if not launcher_path.is_absolute():
        raise ValueError("Runtime launcher path must be absolute")
    if launcher_path.name == ONE_SHOT_SHELL_NAME:
        return (str(ONE_SHOT_SHELL_INTERPRETER), str(launcher_path))
    interpreter = _python_shebang_interpreter(launcher_path)
    if interpreter is None and runtime_python_path is not None:
        if not runtime_python_path.is_absolute():
            raise ValueError("Runtime Python path must be absolute")
        interpreter = runtime_python_path
    if interpreter is None:
        return (str(launcher_path),)
    return (str(interpreter), "-I", "-S", "-B", str(launcher_path))


@dataclass(frozen=True, slots=True)
class RuntimeTurnAudit:
    """Host-side, non-PII record of one Runtime turn."""

    command_digest: str
    command_kind: str
    worker_pid: int | None
    worker_boot_nonce: str | None
    sequence: int | None
    result_kind: str
    failure: Mapping[str, object] | None
    transport_fault: str | None
    isolated: bool
    store_root: str

    def to_dict(self) -> dict[str, object]:
        return {
            "command_digest": self.command_digest,
            "command_kind": self.command_kind,
            "worker_pid": self.worker_pid,
            "worker_boot_nonce": self.worker_boot_nonce,
            "sequence": self.sequence,
            "result_kind": self.result_kind,
            "failure": None if self.failure is None else dict(self.failure),
            "transport_fault": self.transport_fault,
            "isolated": self.isolated,
            "store_root": self.store_root,
        }


def runtime_command_digest(command: MingliCommand) -> str:
    """Digest a Command without retaining facts, query text, or public copy."""

    payload = command.to_dict()
    redacted: dict[str, object] = {}
    for key, value in payload.items():
        if key in _COMMAND_DIGEST_REDACTED_KEYS:
            redacted[key] = {
                "digest": hashlib.sha256(_canonical_json_bytes(value)).hexdigest()
            }
        else:
            redacted[key] = value
    return hashlib.sha256(_canonical_json_bytes(redacted)).hexdigest()


def failure_for_transport_fault(fault: str) -> RuntimeFailure:
    if fault == "timeout":
        return RuntimeFailure(
            code="transient.timeout",
            category="transient",
            retryable=True,
        )
    if (
        fault in {"already-isolated", "pipe-unavailable", "process-exited", "encode"}
        or fault.startswith("transport:")
    ):
        return RuntimeFailure(
            code="transient.resource_unavailable",
            category="transient",
            retryable=True,
        )
    return RuntimeFailure.internal_error()


def time_layer_entitlement_resolution_for_transport_fault(
    fault: str,
) -> TimeLayerEntitlementResolution:
    """Host transport faults lock paid layers only; they are not capability signals."""

    del fault
    return resolve_time_layer_entitlement_resolution(
        owner_kind=None,
        request_failed=True,
    )


def time_layer_entitlement_resolution_for_session(
    *,
    owner_kind: Literal["user", "guest"] | None,
    paid_grant: bool | None = None,
) -> TimeLayerEntitlementResolution:
    """Session/grant mapping stays off time_layers[].available/unavailable_reason."""

    return resolve_time_layer_entitlement_resolution(
        owner_kind=owner_kind,
        paid_grant=paid_grant,
    )


def generic_runtime_stopped(*, failure: RuntimeFailure | None = None) -> Stopped:
    return Stopped(
        reason="error",
        public_copy=WORKER_STOPPED_COPY,
        state_token=None,
        input_request=None,
        failure=failure or RuntimeFailure.internal_error(),
    )


def append_runtime_turn_audit(path: Path, record: Mapping[str, object]) -> None:
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    rendered = json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n"
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        os.write(descriptor, rendered.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _audit_safe_transport_fault(fault: str | None) -> str | None:
    """Keep worker-controlled bytes out of the durable audit."""

    if fault is None:
        return None
    for dynamic_prefix in (
        "stderr-before-write:",
        "unbound-result:",
        "unbound-idle:",
    ):
        if fault.startswith(dynamic_prefix):
            return dynamic_prefix.removesuffix(":")
    return fault


def _consume_task_exception(task: asyncio.Task[None]) -> None:
    """Retrieve a detached audit-tail failure to avoid loop-level warnings."""

    if task.cancelled():
        return
    with suppress(Exception):
        task.result()


def _reject_non_finite_json(value: str) -> object:
    raise ValueError(f"non-finite JSON number: {value}")


def _object_without_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_json_bytes(payload: object) -> bytes:
    try:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as error:
        raise RuntimeTransportError("runtime_invalid_output") from error
    return rendered.encode("utf-8")


def encode_worker_frame(
    payload: object,
    *,
    max_bytes: int = WORKER_MAX_FRAME_BYTES,
) -> bytes:
    body = _canonical_json_bytes(payload)
    if not body or len(body) > max_bytes:
        raise RuntimeTransportError("runtime_invalid_output")
    return len(body).to_bytes(WORKER_FRAME_HEADER_BYTES, "big") + body


def _stream_has_pending(reader: asyncio.StreamReader) -> bool:
    buffer = getattr(reader, "_buffer", b"")
    return bool(buffer)


async def _read_worker_frame(
    reader: asyncio.StreamReader,
    *,
    max_bytes: int = WORKER_MAX_FRAME_BYTES,
) -> dict[str, Any]:
    try:
        header = await reader.readexactly(WORKER_FRAME_HEADER_BYTES)
    except asyncio.IncompleteReadError as error:
        raise RuntimeTransportError("runtime_invalid_output") from error
    length = int.from_bytes(header, "big")
    if length < 1 or length > max_bytes:
        raise RuntimeTransportError("runtime_invalid_output")
    try:
        body = await reader.readexactly(length)
    except asyncio.IncompleteReadError as error:
        raise RuntimeTransportError("runtime_invalid_output") from error
    try:
        decoded: object = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_finite_json,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as error:
        raise RuntimeTransportError("runtime_invalid_output") from error
    if not isinstance(decoded, dict):
        raise RuntimeTransportError("runtime_invalid_output")
    return decoded


def _require_absolute_regular_file(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise ValueError(f"{label} path must be absolute")
    try:
        metadata = path.lstat()
    except OSError as error:
        raise RuntimeStartupError(f"{label} is missing") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeStartupError(f"{label} must be a regular file")
    return path


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
                *one_shot_spawn_argv(self._launcher_path, self._runtime_python_path),
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


class WorkerV2MingliRuntimeAdapter:
    """Identity-bound, single-flight Runtime worker v2 client.

    Turns are `Result → idle` with no silent window.  The one-shot launcher
    remains an explicit rollback path and is never used as a silent fallback.
    A fully written command is never replayed.  Late post-terminal bytes do
    not rewrite a returned Result; the next Command write isolates instead.
    """

    adapter_kind = "runtime-worker-v2"
    production_ready = False

    def __init__(
        self,
        *,
        release_root: Path,
        runtime_python_path: Path,
        state_root: Path,
        expected_listing_sha256: str,
        expected_runtime_integrity_sha256: str,
        ready_timeout_seconds: float = WORKER_DEFAULT_READY_TIMEOUT_SECONDS,
        request_timeout_seconds: float = WORKER_REQUEST_TIMEOUT_SECONDS,
        audit_timeout_seconds: float = WORKER_AUDIT_TIMEOUT_SECONDS,
        max_stderr_bytes: int = 64 * 1024,
    ) -> None:
        if _SHA256_RE.fullmatch(expected_listing_sha256) is None:
            raise ValueError("Runtime expected listing SHA-256 is invalid")
        if _SHA256_RE.fullmatch(expected_runtime_integrity_sha256) is None:
            raise ValueError("Runtime expected integrity SHA-256 is invalid")
        if not (0 < ready_timeout_seconds <= 120.0):
            raise ValueError("Runtime worker READY timeout is outside the explicit bound")
        if not (0 < request_timeout_seconds <= WORKER_REQUEST_TIMEOUT_SECONDS):
            raise ValueError("Runtime worker request timeout must be positive and at most 2s")
        if not (0 < audit_timeout_seconds <= WORKER_REQUEST_TIMEOUT_SECONDS):
            raise ValueError("Runtime audit timeout must be positive and at most 2s")
        if max_stderr_bytes < 1:
            raise ValueError("Runtime I/O limits must be positive")
        if not runtime_python_path.is_absolute():
            raise ValueError("Runtime Python path must be absolute")
        if not release_root.is_absolute():
            raise ValueError("Runtime release root must be absolute")
        if not state_root.is_absolute():
            raise ValueError("Runtime state root must be absolute")
        _require_private_directory(state_root, "Runtime state root", writable=True)
        self._release_root = release_root.resolve()
        self._worker_path = _require_absolute_regular_file(
            self._release_root / WORKER_RELATIVE,
            "Runtime worker",
        )
        resolved_worker = self._worker_path.resolve(strict=True)
        if resolved_worker != (self._release_root / WORKER_RELATIVE).resolve(strict=True):
            raise RuntimeStartupError("Runtime worker escapes the release root")
        if not runtime_python_path.is_file():
            raise RuntimeStartupError("Runtime Python is missing")
        self._runtime_python_path = runtime_python_path
        self._state_root = state_root
        self._expected_listing_sha256 = expected_listing_sha256
        self._expected_runtime_integrity_sha256 = expected_runtime_integrity_sha256
        self._ready_timeout_seconds = ready_timeout_seconds
        self._request_timeout_seconds = request_timeout_seconds
        self._audit_timeout_seconds = audit_timeout_seconds
        self._max_stderr_bytes = max_stderr_bytes
        self._lock = asyncio.Lock()
        self._process: asyncio.subprocess.Process | None = None
        self._process_group_id: int | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._stderr = bytearray()
        self._stderr_event = asyncio.Event()
        self._ready: dict[str, Any] | None = None
        self._identity_sha256: str | None = None
        self._next_sequence = 1
        self._written_request_ids: set[str] = set()
        self._isolated = False
        self._written_without_result = False
        self._transport_fault: str | None = None
        self._audit_pid: int | None = None
        self._audit_boot_nonce: str | None = None
        self._last_sequence: int | None = None
        self.last_turn: RuntimeTurnAudit | None = None
        self._audit_tail: asyncio.Task[None] | None = None
        self._audit_pending: set[asyncio.Task[None]] = set()

    @property
    def isolated(self) -> bool:
        return self._isolated

    @property
    def process_alive(self) -> bool:
        process = self._process
        return (
            not self._isolated
            and process is not None
            and self._ready is not None
            and process.returncode is None
        )

    @property
    def ready(self) -> Mapping[str, Any] | None:
        return None if self._ready is None else dict(self._ready)

    def spawn_argv(self) -> tuple[str, ...]:
        return (
            str(self._runtime_python_path),
            "-I",
            "-S",
            "-B",
            str(self._worker_path),
            "--expected-listing-sha256",
            self._expected_listing_sha256,
            "--expected-runtime-integrity-sha256",
            self._expected_runtime_integrity_sha256,
            "--ready-timeout-seconds",
            f"{self._ready_timeout_seconds:g}",
        )

    def _environment(self) -> dict[str, str]:
        return {
            "HOME": "/nonexistent",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "MINGLI_STORE_ROOT": str(self._state_root),
            "PATH": RUNTIME_PROCESS_PATH,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": "/dev/null",
            "TZ": "UTC",
        }

    async def start(self) -> Mapping[str, Any]:
        async with self._lock:
            if self._isolated:
                raise RuntimeStartupError("isolated Runtime worker cannot be restarted in place")
            if self._ready is not None:
                return dict(self._ready)
            try:
                process = await asyncio.create_subprocess_exec(
                    *self.spawn_argv(),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=self._environment(),
                    start_new_session=True,
                )
            except OSError as error:
                raise RuntimeStartupError("Runtime worker spawn failed") from error
            self._process = process
            try:
                self._process_group_id = os.getpgid(process.pid)
            except ProcessLookupError:
                self._process_group_id = None
            self._stderr = bytearray()
            self._stderr_event = asyncio.Event()
            self._stderr_task = asyncio.create_task(self._drain_stderr())
            try:
                async with asyncio.timeout(self._ready_timeout_seconds):
                    if process.stdout is None:
                        raise RuntimeStartupError("Runtime worker pipe is unavailable")
                    ready = await _read_worker_frame(process.stdout)
                    if _stream_has_pending(process.stdout) or self._stderr:
                        raise RuntimeStartupError("Runtime worker emitted extra stdio during READY")
            except TimeoutError as error:
                await self._isolate_locked()
                raise RuntimeStartupError("Runtime worker READY timed out") from error
            except RuntimeTransportError as error:
                await self._isolate_locked()
                raise RuntimeStartupError("Runtime worker READY is invalid") from error
            except RuntimeStartupError:
                await self._isolate_locked()
                raise
            except BaseException:
                await self._isolate_locked()
                raise
            try:
                self._bind_ready(ready)
            except RuntimeStartupError:
                await self._isolate_locked()
                raise
            return dict(ready)

    def _bind_ready(self, ready: Mapping[str, Any]) -> None:
        identity = ready.get("identity_sha256")
        listing = ready.get("listing_sha256")
        integrity = ready.get("runtime_integrity_sha256")
        sequence_start = ready.get("sequence_start")
        if (
            ready.get("type") != "ready"
            or ready.get("protocol") != WORKER_PROTOCOL
            or ready.get("turn_terminal") != WORKER_TURN_TERMINAL
            or ready.get("runtime_protocol") != EXPECTED_RUNTIME_PROTOCOL
            or not isinstance(identity, str)
            or _SHA256_RE.fullmatch(identity) is None
            or listing != self._expected_listing_sha256
            or integrity != self._expected_runtime_integrity_sha256
            or ready.get("single_in_flight") is not True
            or ready.get("replay_policy") != "forbidden"
            or ready.get("fallback_policy") != "forbidden"
            or ready.get("max_frame_bytes") != WORKER_MAX_FRAME_BYTES
            or sequence_start != 1
            or not isinstance(ready.get("pid"), int)
            or not isinstance(ready.get("boot_nonce"), str)
            or not ready.get("boot_nonce")
        ):
            raise RuntimeStartupError("Runtime worker READY identity is invalid")
        self._ready = dict(ready)
        self._identity_sha256 = identity
        self._next_sequence = 1
        pid = ready.get("pid")
        boot_nonce = ready.get("boot_nonce")
        self._audit_pid = pid if isinstance(pid, int) else None
        self._audit_boot_nonce = boot_nonce if isinstance(boot_nonce, str) else None

    def _generic_stop(self, fault: str) -> Stopped:
        self._transport_fault = fault
        return generic_runtime_stopped(failure=failure_for_transport_fault(fault))

    def _retryable_transport_fault(self) -> bool:
        return self._transport_fault in {
            "timeout",
            "pipe-unavailable",
            "encode",
            "transport:BrokenPipeError",
            "transport:ConnectionResetError",
            "transport:RuntimeTransportError",
        }

    def _turn_audit(
        self,
        command: MingliCommand,
        result: MingliResult,
    ) -> RuntimeTurnAudit:
        failure = None
        if isinstance(result, Stopped) and result.failure is not None:
            failure = result.failure.to_audit_dict()
        return RuntimeTurnAudit(
            command_digest=runtime_command_digest(command),
            command_kind=command.kind,
            worker_pid=self._audit_pid,
            worker_boot_nonce=self._audit_boot_nonce,
            sequence=self._last_sequence,
            result_kind=result.kind,
            failure=failure,
            transport_fault=_audit_safe_transport_fault(self._transport_fault),
            isolated=self._isolated,
            store_root=str(self._state_root),
        )

    def _publish_turn(self, command: MingliCommand, result: MingliResult) -> None:
        """Synchronously publish a turn for explicit offline/audit callers."""

        record = self._turn_audit(command, result)
        self.last_turn = record
        append_runtime_turn_audit(
            self._state_root / RUNTIME_TURN_AUDIT_NAME,
            record.to_dict(),
        )

    async def _publish_turn_durable(
        self,
        command: MingliCommand,
        result: MingliResult,
    ) -> None:
        """Publish off-loop while retaining turn order and a bounded request wait."""

        record = self._turn_audit(command, result)
        self.last_turn = record
        if len(self._audit_pending) >= WORKER_MAX_PENDING_AUDIT_APPENDS:
            return
        previous = self._audit_tail

        async def append_in_order() -> None:
            if previous is not None:
                with suppress(Exception):
                    await asyncio.shield(previous)
            await asyncio.to_thread(
                append_runtime_turn_audit,
                self._state_root / RUNTIME_TURN_AUDIT_NAME,
                record.to_dict(),
            )

        pending = asyncio.create_task(append_in_order())
        self._audit_pending.add(pending)

        def finish(task: asyncio.Task[None]) -> None:
            self._audit_pending.discard(task)
            if self._audit_tail is task:
                self._audit_tail = None
            _consume_task_exception(task)

        pending.add_done_callback(finish)
        self._audit_tail = pending
        try:
            async with asyncio.timeout(self._audit_timeout_seconds):
                await asyncio.shield(pending)
        except TimeoutError:
            # Keep at most one detached stalled write plus one replacement.
            # Later records must not form an unbounded chain behind this tail.
            if self._audit_tail is pending:
                self._audit_tail = None
            return

    async def execute(self, command: MingliCommand) -> MingliResult:
        async with self._lock:
            try:
                result = await self._execute_locked(command)
            except RuntimeTransportError:
                with suppress(Exception):
                    await self._publish_turn_durable(
                        command,
                        generic_runtime_stopped(
                            failure=failure_for_transport_fault(
                                self._transport_fault or "timeout"
                            )
                        ),
                    )
                raise
            await self._publish_turn_durable(command, result)
            return result

    async def _execute_locked(self, command: MingliCommand) -> MingliResult:
        previous_transport_fault = self._transport_fault
        self._transport_fault = None
        if (
            self._isolated
            or self._process is None
            or self._ready is None
            or self._identity_sha256 is None
            or self._written_without_result
        ):
            self._transport_fault = previous_transport_fault
            if self._retryable_transport_fault():
                raise RuntimeTransportError("runtime_pipe_unavailable")
            return self._generic_stop("already-isolated")
        request_id = secrets.token_hex(16)
        if (
            _REQUEST_ID_RE.fullmatch(request_id) is None
            or request_id in self._written_request_ids
        ):
            await self._isolate_locked()
            return self._generic_stop("request-id")
        sequence = self._next_sequence
        self._last_sequence = sequence
        envelope = {
            "type": "command",
            "protocol": WORKER_PROTOCOL,
            "identity_sha256": self._identity_sha256,
            "request_id": request_id,
            "sequence": sequence,
            "command": command.to_dict(),
        }
        try:
            encoded = encode_worker_frame(envelope)
        except RuntimeTransportError:
            await self._isolate_locked()
            self._transport_fault = "encode"
            raise
        stdin = self._process.stdin
        stdout = self._process.stdout
        if stdin is None or stdout is None:
            await self._isolate_locked()
            self._transport_fault = "pipe-unavailable"
            raise RuntimeTransportError("runtime_pipe_unavailable")
        if _stream_has_pending(stdout) or self._stderr:
            fault = (
                "pending-before-write"
                if _stream_has_pending(stdout)
                else "stderr-before-write"
            )
            await self._isolate_locked()
            return self._generic_stop(fault)
        try:
            async with asyncio.timeout(self._request_timeout_seconds):
                stdin.write(encoded)
                await stdin.drain()
                self._written_request_ids.add(request_id)
                self._next_sequence = sequence + 1
                self._written_without_result = True
                payload = await _read_worker_frame(stdout)
                if not self._is_bound_result(payload, request_id, sequence):
                    await self._isolate_locked()
                    return self._generic_stop(f"unbound-result:{payload.get('type')}")
                if payload.get("worker_action") != "continue":
                    await self._isolate_locked()
                    return self._generic_stop(
                        f"worker-isolate:{payload.get('worker_action')}"
                    )
                result_payload = payload.get("result")
                if not isinstance(result_payload, Mapping):
                    await self._isolate_locked()
                    return self._generic_stop("invalid-result")
                try:
                    result = result_from_dict(result_payload)
                except (KeyError, TypeError, ValueError):
                    await self._isolate_locked()
                    return self._generic_stop("result-decode")
                terminal = await self._read_frame_watching_stderr(stdout)
                if not self._is_bound_idle(terminal, request_id, sequence):
                    await self._isolate_locked()
                    return self._generic_stop(f"unbound-idle:{terminal.get('type')}")
        except TimeoutError as error:
            await self._isolate_locked()
            self._transport_fault = "timeout"
            raise RuntimeTransportError("runtime_timed_out") from error
        except (BrokenPipeError, ConnectionResetError) as error:
            await self._isolate_locked()
            self._transport_fault = f"transport:{type(error).__name__}"
            raise RuntimeTransportError("runtime_pipe_unavailable") from error
        except RuntimeTransportError:
            await self._isolate_locked()
            self._transport_fault = "transport:RuntimeTransportError"
            raise
        except BaseException:
            await self._isolate_locked()
            raise
        self._written_without_result = False
        if self._process is not None and self._process.returncode is not None:
            await self._isolate_locked()
            return self._generic_stop("process-exited")
        return result

    async def close(self) -> None:
        async with self._lock:
            await self._isolate_locked()
            if self._audit_pending:
                with suppress(Exception):
                    await asyncio.wait(
                        tuple(self._audit_pending),
                        timeout=self._audit_timeout_seconds,
                    )

    def _is_bound_result(
        self,
        payload: Mapping[str, Any],
        request_id: str,
        sequence: int,
    ) -> bool:
        return (
            set(payload) == _RESULT_FRAME_KEYS
            and payload.get("type") == "result"
            and payload.get("protocol") == WORKER_PROTOCOL
            and payload.get("identity_sha256") == self._identity_sha256
            and payload.get("request_id") == request_id
            and payload.get("sequence") == sequence
            and payload.get("worker_action") in {"continue", "isolate"}
            and isinstance(payload.get("result"), Mapping)
        )

    def _is_bound_idle(
        self,
        payload: Mapping[str, Any],
        request_id: str,
        sequence: int,
    ) -> bool:
        return (
            set(payload) == _IDLE_FRAME_KEYS
            and payload.get("type") == WORKER_TURN_TERMINAL_TYPE
            and payload.get("protocol") == WORKER_PROTOCOL
            and payload.get("identity_sha256") == self._identity_sha256
            and payload.get("request_id") == request_id
            and payload.get("sequence") == sequence
        )

    async def _read_frame_watching_stderr(
        self,
        stdout: asyncio.StreamReader,
    ) -> dict[str, Any]:
        if self._stderr:
            raise RuntimeTransportError("runtime_invalid_output")
        read_task = asyncio.create_task(_read_worker_frame(stdout))
        stderr_task = asyncio.create_task(self._stderr_event.wait())
        try:
            done, pending = await asyncio.wait(
                {read_task, stderr_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
        except BaseException:
            read_task.cancel()
            stderr_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await read_task
            with suppress(asyncio.CancelledError, Exception):
                await stderr_task
            raise
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await task
        if self._stderr:
            raise RuntimeTransportError("runtime_invalid_output")
        if read_task not in done:
            raise RuntimeTransportError("runtime_invalid_output")
        return read_task.result()

    async def _drain_stderr(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        try:
            while chunk := await process.stderr.read(64 * 1024):
                remaining = self._max_stderr_bytes + 1 - len(self._stderr)
                if remaining <= 0:
                    self._stderr_event.set()
                    return
                self._stderr.extend(chunk[:remaining])
                if self._stderr:
                    self._stderr_event.set()
        except (asyncio.CancelledError, OSError):
            return

    async def _isolate_locked(self) -> None:
        self._isolated = True
        process = self._process
        process_group_id = self._process_group_id
        self._process = None
        self._process_group_id = None
        self._ready = None
        self._identity_sha256 = None
        self._stderr_event.set()
        if process is not None:
            await _kill_process_group(process, process_group_id)
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await self._stderr_task
            self._stderr_task = None


def _runtime_integrity_sha256(runtime_python_path: Path) -> str:
    integrity_path = runtime_python_path.resolve().parents[1] / "runtime-integrity.json"
    try:
        metadata = integrity_path.lstat()
    except OSError as error:
        raise RuntimeStartupError("Runtime integrity manifest is missing") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeStartupError("Runtime integrity manifest must be a regular file")
    return _sha256_file(integrity_path)


def build_runtime_startup_gate(settings: Settings) -> RuntimeStartupGate:
    """Build the real Runtime boundary exclusively from server settings."""

    if settings.runtime_adapter not in {"worker-v2", "one-shot"}:
        raise RuntimeStartupError("a real worker-v2 Runtime adapter is required")
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
    if settings.runtime_release_profile == "v51":
        if profile["release_manifest_sha256"] in _FORBIDDEN_V51_LISTINGS:
            raise RuntimeStartupError("Runtime release listing is a forbidden v51 identity")
        if profile["source_commit"] in _FORBIDDEN_V51_SOURCES:
            raise RuntimeStartupError("Runtime source commit is a forbidden v51 identity")
        worker_digest = profile.get("worker_sha256")
        if worker_digest in _FORBIDDEN_V51_WORKERS:
            raise RuntimeStartupError("Runtime worker digest is a forbidden v51 identity")
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
    expected_release_file_count = profile["signed_file_count"]
    expected_physical_file_count = profile["physical_file_count"]
    if expected_physical_file_count != expected_release_file_count + 1:
        raise RuntimeStartupError(
            "Runtime release profile must distinguish signed and physical files"
        )
    if settings.runtime_adapter == "one-shot":
        runtime: MingliRuntime = OneShotMingliRuntimeAdapter(
            launcher_path=launcher_path,
            runtime_python_path=runtime_python_path,
            state_root=state_root,
            timeout_seconds=settings.runtime_timeout_seconds,
            max_stdin_bytes=settings.runtime_max_stdin_bytes,
            max_stdout_bytes=settings.runtime_max_stdout_bytes,
            max_stderr_bytes=settings.runtime_max_stderr_bytes,
        )
    else:
        expected_worker_sha256 = profile.get("worker_sha256")
        if expected_worker_sha256 is None:
            locked_worker = _RUNTIME_RELEASE_PROFILES["v53-time-check"]
            raise RuntimeStartupError(
                "Runtime worker digest is not admitted for "
                f"{settings.runtime_release_profile}: listing="
                f"{profile['release_manifest_sha256']} source="
                f"{profile['source_commit']} has no worker_sha256/"
                "worker_protocol/worker_turn_terminal; locked worker "
                f"listing={locked_worker['release_manifest_sha256']} "
                f"source={locked_worker['source_commit']} "
                f"worker={locked_worker['worker_sha256']} "
                f"protocol={locked_worker.get('worker_protocol')}/"
                f"{locked_worker.get('worker_turn_terminal')} "
                "cannot form a signed v51 artifact"
            )
        if profile.get("worker_protocol") != WORKER_PROTOCOL:
            raise RuntimeStartupError("Runtime worker protocol is not admitted")
        if profile.get("worker_turn_terminal") != WORKER_TURN_TERMINAL:
            raise RuntimeStartupError("Runtime worker turn terminal is not admitted")
        worker_path = _require_absolute_regular_file(
            release_root / WORKER_RELATIVE,
            "Runtime worker",
        )
        if _sha256_file(worker_path) != expected_worker_sha256:
            raise RuntimeStartupError("Runtime worker digest mismatch")
        runtime = WorkerV2MingliRuntimeAdapter(
            release_root=release_root,
            runtime_python_path=runtime_python_path,
            state_root=state_root,
            expected_listing_sha256=profile["release_manifest_sha256"],
            expected_runtime_integrity_sha256=_runtime_integrity_sha256(
                runtime_python_path
            ),
            request_timeout_seconds=min(
                settings.chart_fast_path_timeout_seconds,
                WORKER_REQUEST_TIMEOUT_SECONDS,
            ),
        )
    inspector = FileSystemRuntimeReleaseInspector(
        release_root=release_root,
        expected_release_manifest_sha256=profile["release_manifest_sha256"],
        expected_release_name=profile["release_name"],
        expected_source_commit=profile["source_commit"],
        expected_capability_ids=expected_capability_ids,
        expected_release_file_count=expected_release_file_count,
        expected_physical_file_count=expected_physical_file_count,
    )
    return RuntimeStartupGate(
        runtime=runtime,
        release_inspector=inspector,
        expected_manifest_digest=settings.runtime_expected_manifest_digest,
        expected_release_manifest_sha256=profile["release_manifest_sha256"],
        expected_capability_shape_sha256=(settings.runtime_expected_capability_shape_sha256),
        expected_capability_ids=expected_capability_ids,
        expected_release_file_count=expected_release_file_count,
        expected_physical_file_count=expected_physical_file_count,
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
