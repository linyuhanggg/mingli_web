#!/usr/bin/env python3
"""Externally anchored acceptance and pipeline-creation registry for Mingli."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import stat
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


INDEX_SCHEMA = "mingli-accepted-index-v2"
INDEX_NAME = ".accepted-index-v2.json"
LOCK_NAME = ".accepted-index-v2.lock"
TRUST_DIR_NAME = ".mingli-index-trust-v1"
TRUST_LOCK_NAME = "trust.lock"
KEY_NAME = "key.bin"
CHECKPOINT_SCHEMA = "mingli-index-checkpoint-v1"
CREATION_SCHEMA = "mingli-pipeline-creation-v1"
BINDING_SCHEMA = "mingli-index-root-binding-v1"
EVENT_TYPES = {"initial", "followup"}
SYSTEMS = {"bazi", "liuren"}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _mac(key: bytes, value: Any) -> str:
    return hmac.new(key, _canonical_bytes(value), hashlib.sha256).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_private_directory(path: Path) -> None:
    missing: list[Path] = []
    cursor = path
    while not cursor.exists():
        missing.append(cursor)
        cursor = cursor.parent
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"unsafe trust directory: {path}")
    for created in reversed(missing):
        os.chmod(created, 0o700)
        _fsync_directory(created.parent)
    os.chmod(path, 0o700)


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    _ensure_private_directory(path.parent)
    content = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.chmod(temporary_name, 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        _fsync_directory(path.parent)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def _trust_dir(root: Path) -> Path:
    return root.parent / TRUST_DIR_NAME


@contextmanager
def _trust_lock(root: Path, *, create: bool) -> Iterator[None]:
    trust_dir = _trust_dir(root)
    if not trust_dir.exists():
        if not create:
            yield
            return
        _ensure_private_directory(trust_dir)
    elif trust_dir.is_symlink() or not trust_dir.is_dir():
        raise ValueError("acceptance index trust directory is unsafe")
    descriptor = os.open(
        trust_dir / TRUST_LOCK_NAME,
        os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(descriptor, "r+") as handle:
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
            raise ValueError("acceptance index trust lock is unsafe")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield


def _load_or_create_key(root: Path, *, create: bool) -> bytes:
    trust_dir = _trust_dir(root)
    key_path = trust_dir / KEY_NAME
    if not key_path.exists():
        if not create:
            raise ValueError("acceptance index trust key is missing")
        _ensure_private_directory(trust_dir)
        key = os.urandom(32)
        try:
            descriptor = os.open(
                key_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            key = key_path.read_bytes()
        else:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(key)
                handle.flush()
                os.fsync(handle.fileno())
            _fsync_directory(trust_dir)
    else:
        if key_path.is_symlink():
            raise ValueError("acceptance index trust key must not be a symlink")
        key = key_path.read_bytes()
    if len(key) != 32 or (key_path.stat().st_mode & 0o077):
        raise ValueError("acceptance index trust key is invalid or not private")
    return key


def _accepted_bytes(envelope: dict[str, Any]) -> bytes:
    return (
        json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _validate_envelope(envelope: dict[str, Any]) -> bool:
    try:
        if envelope.get("schema_version") != "mingli-accepted-public-v1":
            return False
        manifest = envelope.get("manifest")
        public_copy = envelope.get("public_copy")
        if not isinstance(manifest, dict) or not isinstance(public_copy, str):
            return False
        manifest_payload = {
            name: value
            for name, value in manifest.items()
            if name != "manifest_digest"
        }
        if manifest.get("manifest_digest") != _canonical_digest(manifest_payload):
            return False
        sections = manifest.get("sections")
        if not isinstance(sections, list) or not sections:
            return False
        rendered = "【玄枢｜MINGLI】\n" + "\n\n".join(
            str(section["text"]).strip() for section in sections
        )
        public_digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        if public_copy != rendered or manifest.get("public_copy_sha256") != public_digest:
            return False
        for name in (
            "reading_id",
            "manifest_digest",
            "public_copy_sha256",
            "inference_digest",
        ):
            if envelope.get(name) != manifest.get(name):
                return False
        envelope_payload = {
            name: value
            for name, value in envelope.items()
            if name != "envelope_digest"
        }
        return envelope.get("envelope_digest") == _canonical_digest(envelope_payload)
    except (KeyError, TypeError, ValueError):
        return False


def _chart_sections(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        section
        for section in manifest.get("sections", [])
        if isinstance(section, dict) and section.get("kind") == "chart"
    ]


def _empty_index() -> dict[str, Any]:
    return {
        "schema_version": INDEX_SCHEMA,
        "index_id": None,
        "events": [],
        "index_digest": None,
        "index_mac": None,
    }


def _seal_index(index: dict[str, Any], key: bytes) -> dict[str, Any]:
    payload = {
        name: value
        for name, value in index.items()
        if name not in {"index_digest", "index_mac"}
    }
    index["index_digest"] = _canonical_digest(payload)
    index["index_mac"] = _mac(
        key,
        {**payload, "index_digest": index["index_digest"]},
    )
    return index


def _validate_index(index: dict[str, Any], key: bytes) -> bool:
    try:
        if index.get("schema_version") != INDEX_SCHEMA:
            return False
        index_id = index.get("index_id")
        if (
            not isinstance(index_id, str)
            or len(index_id) != 32
            or any(character not in "0123456789abcdef" for character in index_id)
        ):
            return False
        events = index.get("events")
        if not isinstance(events, list):
            return False
        prior_event_digest: str | None = None
        initial_sequences: dict[tuple[str, str], int] = {}
        latest_events: dict[tuple[str, str], dict[str, Any]] = {}
        operation_ids: set[str] = set()
        for sequence, event in enumerate(events, start=1):
            if not isinstance(event, dict) or event.get("sequence") != sequence:
                return False
            if event.get("previous_event_digest") != prior_event_digest:
                return False
            if event.get("event_type") not in EVENT_TYPES or event.get("system") not in SYSTEMS:
                return False
            reading_id = event.get("reading_id")
            artifact_relpath = event.get("artifact_relpath")
            pipeline_relpath = event.get("pipeline_manifest_relpath")
            if not isinstance(reading_id, str) or not reading_id:
                return False
            if not isinstance(artifact_relpath, str) or not artifact_relpath:
                return False
            relative = Path(artifact_relpath)
            if relative.is_absolute() or ".." in relative.parts:
                return False
            if not isinstance(pipeline_relpath, str) or not pipeline_relpath:
                return False
            relative_pipeline = Path(pipeline_relpath)
            if (
                relative_pipeline.is_absolute()
                or ".." in relative_pipeline.parts
                or relative_pipeline.parent != relative
            ):
                return False
            for name in (
                "pipeline_manifest_sha256",
                "accepted_file_sha256",
                "envelope_digest",
                "manifest_digest",
                "operation_id",
                "event_digest",
            ):
                if not _valid_digest(event.get(name)):
                    return False
            if event["operation_id"] in operation_ids:
                return False
            operation_ids.add(event["operation_id"])
            envelope = event.get("accepted_envelope")
            if not isinstance(envelope, dict) or not _validate_envelope(envelope):
                return False
            if (
                event["accepted_file_sha256"]
                != hashlib.sha256(_accepted_bytes(envelope)).hexdigest()
                or event["envelope_digest"] != envelope["envelope_digest"]
                or event["manifest_digest"] != envelope["manifest_digest"]
                or event["reading_id"] != envelope["reading_id"]
            ):
                return False
            key_tuple = (event["system"], reading_id)
            if event["event_type"] == "initial":
                if key_tuple in initial_sequences:
                    return False
                if event.get("initial_sequence") != sequence:
                    return False
                if event.get("prior_manifest_digest") is not None:
                    return False
                if event.get("reservation_name") is not None:
                    return False
                if event.get("draft_sha256") is not None:
                    return False
                initial_sequences[key_tuple] = sequence
            else:
                prior = latest_events.get(key_tuple)
                if prior is None:
                    return False
                if event.get("initial_sequence") != initial_sequences[key_tuple]:
                    return False
                initial = events[initial_sequences[key_tuple] - 1]
                if any(
                    event.get(name) != initial.get(name)
                    for name in (
                        "artifact_relpath",
                        "pipeline_manifest_relpath",
                        "pipeline_manifest_sha256",
                    )
                ):
                    return False
                if event.get("prior_manifest_digest") != prior["manifest_digest"]:
                    return False
                if envelope["manifest"].get("followup_of_manifest_digest") != prior["manifest_digest"]:
                    return False
                if envelope["manifest"].get("claims") != prior["accepted_envelope"]["manifest"].get("claims"):
                    return False
                if _chart_sections(envelope["manifest"]) != _chart_sections(
                    prior["accepted_envelope"]["manifest"]
                ):
                    return False
                if not isinstance(event.get("reservation_name"), str) or not event["reservation_name"]:
                    return False
                if not _valid_digest(event.get("draft_sha256")):
                    return False
            event_payload = {
                name: value
                for name, value in event.items()
                if name != "event_digest"
            }
            if event["event_digest"] != _canonical_digest(event_payload):
                return False
            prior_event_digest = event["event_digest"]
            latest_events[key_tuple] = event
        payload = {
            name: value
            for name, value in index.items()
            if name not in {"index_digest", "index_mac"}
        }
        if index.get("index_digest") != _canonical_digest(payload):
            return False
        return hmac.compare_digest(
            str(index.get("index_mac") or ""),
            _mac(key, {**payload, "index_digest": index["index_digest"]}),
        )
    except (KeyError, TypeError, ValueError):
        return False


def _checkpoint_path(root: Path, index_id: str) -> Path:
    return _trust_dir(root) / "checkpoints" / f"{index_id}.json"


def _binding_path(root: Path, index_id: str) -> Path:
    return _trust_dir(root) / "bindings" / f"{index_id}.json"


def _root_path_digest(root: Path) -> str:
    return hashlib.sha256(str(root.resolve(strict=True)).encode("utf-8")).hexdigest()


def _load_binding(
    root: Path,
    index_id: str,
    key: bytes,
) -> dict[str, Any] | None:
    path = _binding_path(root, index_id)
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError("acceptance index root binding is unsafe")
    payload = _read_object(path)
    supplied_mac = payload.get("binding_mac")
    unsigned = {
        name: value for name, value in payload.items() if name != "binding_mac"
    }
    aliases = payload.get("root_path_digests")
    active_root_path = payload.get("active_root_path")
    if (
        payload.get("schema_version") != BINDING_SCHEMA
        or payload.get("index_id") != index_id
        or not isinstance(aliases, list)
        or not aliases
        or any(not _valid_digest(alias) for alias in aliases)
        or len(set(aliases)) != len(aliases)
        or (
            active_root_path is not None
            and (
                not isinstance(active_root_path, str)
                or not Path(active_root_path).is_absolute()
                or len(aliases) != 1
                or hashlib.sha256(active_root_path.encode("utf-8")).hexdigest()
                != aliases[0]
            )
        )
        or not isinstance(supplied_mac, str)
        or not hmac.compare_digest(supplied_mac, _mac(key, unsigned))
    ):
        raise ValueError("acceptance index root binding is invalid")
    return payload


def _ensure_binding(root: Path, index_id: str, key: bytes) -> None:
    current = _root_path_digest(root)
    current_path = str(root.resolve(strict=True))
    existing = _load_binding(root, index_id, key)
    aliases = list(existing["root_path_digests"]) if existing else []
    active_root_path = existing.get("active_root_path") if existing else None
    if aliases == [current] and active_root_path == current_path:
        return
    if existing is not None and current not in aliases:
        if active_root_path is None:
            raise ValueError(
                "legacy root binding must be upgraded at its active path before moving"
            )
        if Path(active_root_path).exists():
            raise ValueError("active pipeline root still exists; refusing copied-root takeover")
    payload: dict[str, Any] = {
        "schema_version": BINDING_SCHEMA,
        "index_id": index_id,
        "root_path_digests": [current],
        "active_root_path": current_path,
    }
    payload["binding_mac"] = _mac(key, payload)
    _atomic_write(_binding_path(root, index_id), payload)


def _binding_matches(root: Path, index_id: str, key: bytes) -> bool:
    binding = _load_binding(root, index_id, key)
    return binding is not None and _root_path_digest(root) in binding["root_path_digests"]


def _checkpoint(index: dict[str, Any], key: bytes) -> dict[str, Any]:
    payload = {
        "schema_version": CHECKPOINT_SCHEMA,
        "index_id": index["index_id"],
        "index": index,
    }
    payload["checkpoint_mac"] = _mac(key, payload)
    return payload


def _load_checkpoint(root: Path, index_id: str, key: bytes) -> dict[str, Any]:
    path = _checkpoint_path(root, index_id)
    if not path.is_file() or path.is_symlink():
        raise ValueError("acceptance index checkpoint is missing")
    payload = _read_object(path)
    supplied_mac = payload.get("checkpoint_mac")
    unsigned = {
        name: value for name, value in payload.items() if name != "checkpoint_mac"
    }
    if (
        payload.get("schema_version") != CHECKPOINT_SCHEMA
        or payload.get("index_id") != index_id
        or not isinstance(supplied_mac, str)
        or not hmac.compare_digest(supplied_mac, _mac(key, unsigned))
        or not isinstance(payload.get("index"), dict)
        or not _validate_index(payload["index"], key)
    ):
        raise ValueError("acceptance index checkpoint is invalid")
    return payload["index"]


def _index_extends(candidate: dict[str, Any], prefix: dict[str, Any]) -> bool:
    candidate_events = candidate.get("events")
    prefix_events = prefix.get("events")
    return bool(
        candidate.get("index_id") == prefix.get("index_id")
        and isinstance(candidate_events, list)
        and isinstance(prefix_events, list)
        and len(candidate_events) >= len(prefix_events)
        and candidate_events[: len(prefix_events)] == prefix_events
    )


def _load_unlocked(root: Path) -> dict[str, Any]:
    path = root / INDEX_NAME
    if not path.exists():
        recovered = _recover_missing_index(root)
        if recovered is None:
            return _empty_index()
        _atomic_write(path, recovered)
        return recovered
    if path.is_symlink():
        raise ValueError("acceptance index must not be a symlink")
    try:
        index = _read_object(path)
        if index.get("schema_version") != INDEX_SCHEMA:
            raise ValueError("legacy or unsupported acceptance index requires migration")
        key = _load_or_create_key(root, create=False)
        if not _validate_index(index, key):
            raise ValueError("acceptance index is invalid")
        checkpoint_index = _load_checkpoint(root, index["index_id"], key)
        if not _binding_matches(root, index["index_id"], key):
            if not _checkpoint_matches_root(checkpoint_index, root):
                raise ValueError("acceptance index belongs to another pipeline root")
            _ensure_binding(root, index["index_id"], key)
        else:
            _ensure_binding(root, index["index_id"], key)
    except (OSError, ValueError, json.JSONDecodeError):
        recovered = _recover_missing_index(root)
        if recovered is None:
            raise ValueError("acceptance index is invalid and cannot be recovered")
        _atomic_write(path, recovered)
        return recovered
    if checkpoint_index["index_digest"] != index["index_digest"]:
        if _index_extends(index, checkpoint_index):
            _atomic_write(
                _checkpoint_path(root, index["index_id"]),
                _checkpoint(index, key),
            )
        elif _index_extends(checkpoint_index, index):
            _atomic_write(path, checkpoint_index)
            index = checkpoint_index
        else:
            raise ValueError("acceptance index and checkpoint histories diverge")
    return index


def _checkpoint_matches_root(index: dict[str, Any], root: Path) -> bool:
    events = index.get("events")
    if not isinstance(events, list) or not events:
        return False
    matched = 0
    visited: set[str] = set()
    for event in events:
        pipeline_relpath = event["pipeline_manifest_relpath"]
        if pipeline_relpath in visited:
            continue
        visited.add(pipeline_relpath)
        artifact = root / event["artifact_relpath"]
        pipeline = root / pipeline_relpath
        try:
            artifact_exists = artifact.exists()
            pipeline_exists = pipeline.exists()
            if not artifact_exists and not pipeline_exists:
                continue
            if (
                not artifact_exists
                or not pipeline_exists
                or artifact.is_symlink()
                or not artifact.resolve(strict=True).is_dir()
                or pipeline.is_symlink()
                or not pipeline.resolve(strict=True).is_file()
                or not pipeline.resolve(strict=True).is_relative_to(
                    artifact.resolve(strict=True)
                )
                or _sha256(pipeline) != event["pipeline_manifest_sha256"]
            ):
                return False
            matched += 1
        except OSError:
            return False
    return matched > 0


def _recover_missing_index(root: Path) -> dict[str, Any] | None:
    trust_dir = _trust_dir(root)
    key_path = trust_dir / KEY_NAME
    checkpoint_dir = trust_dir / "checkpoints"
    if not key_path.is_file() or key_path.is_symlink() or not checkpoint_dir.is_dir():
        return None
    key = _load_or_create_key(root, create=False)
    exact_candidates: dict[str, dict[str, Any]] = {}
    saw_exact_binding = False
    for path in checkpoint_dir.glob("*.json"):
        if path.is_symlink() or len(path.stem) != 32:
            continue
        try:
            index = _load_checkpoint(root, path.stem, key)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        try:
            if _binding_matches(root, index["index_id"], key):
                saw_exact_binding = True
                if _checkpoint_matches_root(index, root):
                    exact_candidates[index["index_digest"]] = index
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    if not exact_candidates:
        if saw_exact_binding:
            raise ValueError(
                "bound acceptance history does not match this pipeline root"
            )
        return None
    longest = max(len(index["events"]) for index in exact_candidates.values())
    finalists = [
        index
        for index in exact_candidates.values()
        if len(index["events"]) == longest
    ]
    if len(finalists) != 1:
        raise ValueError("multiple acceptance checkpoints match the pipeline root")
    selected = finalists[0]
    _ensure_binding(root, selected["index_id"], key)
    return selected


def load_acceptance_index(root: str | Path) -> dict[str, Any]:
    resolved_root = Path(root).expanduser().resolve(strict=True)
    with _trust_lock(resolved_root, create=False):
        return _load_unlocked(resolved_root)


def _commit_index(root: Path, index: dict[str, Any], key: bytes) -> None:
    _ensure_binding(root, index["index_id"], key)
    checkpoint = _checkpoint(index, key)
    _atomic_write(_checkpoint_path(root, index["index_id"]), checkpoint)
    _atomic_write(root / INDEX_NAME, index)


def _contained_file(path: str | Path, *, artifact_dir: Path, label: str) -> Path:
    supplied = Path(path).expanduser()
    if supplied.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    resolved = supplied.resolve(strict=True)
    if not resolved.is_file() or not resolved.is_relative_to(artifact_dir):
        raise ValueError(f"{label} is outside its reading directory")
    return resolved


def record_acceptance(
    root: str | Path,
    *,
    event_type: str,
    system: str,
    reading_id: str,
    artifact_dir: str | Path,
    pipeline_manifest_path: str | Path,
    accepted_path: str | Path | None = None,
    accepted_envelope: dict[str, Any] | None = None,
    prior_manifest_digest: str | None = None,
    operation_id: str | None = None,
    reservation_name: str | None = None,
    draft_sha256: str | None = None,
) -> dict[str, Any]:
    resolved_root = Path(root).expanduser().resolve(strict=True)
    resolved_artifact = Path(artifact_dir).expanduser().resolve(strict=True)
    if not resolved_artifact.is_dir() or not resolved_artifact.is_relative_to(resolved_root):
        raise ValueError("reading directory is outside the pipeline root")
    if event_type not in EVENT_TYPES or system not in SYSTEMS:
        raise ValueError("acceptance event type or system is invalid")
    pipeline_path = _contained_file(
        pipeline_manifest_path,
        artifact_dir=resolved_artifact,
        label="pipeline manifest",
    )
    if accepted_envelope is None:
        if accepted_path is None:
            raise ValueError("acceptance requires an envelope or accepted file")
        accepted_file = _contained_file(
            accepted_path,
            artifact_dir=resolved_artifact,
            label="accepted public",
        )
        accepted_envelope = _read_object(accepted_file)
    if not isinstance(accepted_envelope, dict) or not _validate_envelope(accepted_envelope):
        raise ValueError("accepted public envelope is invalid")
    if accepted_envelope.get("reading_id") != reading_id:
        raise ValueError("accepted public reading ID differs from the index event")
    pipeline_sha256 = _sha256(pipeline_path)
    accepted_sha256 = hashlib.sha256(_accepted_bytes(accepted_envelope)).hexdigest()
    if operation_id is None:
        operation_id = hashlib.sha256(
            f"{event_type}\0{system}\0{reading_id}\0{pipeline_sha256}\0{accepted_envelope['manifest_digest']}".encode()
        ).hexdigest()
    if not _valid_digest(operation_id):
        raise ValueError("acceptance operation ID is invalid")
    lock_descriptor = os.open(
        resolved_root / LOCK_NAME,
        os.O_CREAT | os.O_RDWR,
        0o600,
    )
    with _trust_lock(resolved_root, create=True), os.fdopen(
        lock_descriptor, "r+"
    ) as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        index = _load_unlocked(resolved_root)
        key = _load_or_create_key(resolved_root, create=True)
        if index["index_id"] is None:
            index = {
                "schema_version": INDEX_SCHEMA,
                "index_id": uuid.uuid4().hex,
                "events": [],
                "index_digest": None,
                "index_mac": None,
            }
        events = index["events"]
        prior_events = [
            event
            for event in events
            if event["system"] == system and event["reading_id"] == reading_id
        ]
        existing_operations = [
            event for event in events if event["operation_id"] == operation_id
        ]
        if existing_operations:
            existing = existing_operations[0]
            expected_identity = {
                "event_type": event_type,
                "system": system,
                "reading_id": reading_id,
                "pipeline_manifest_sha256": pipeline_sha256,
                "envelope_digest": accepted_envelope["envelope_digest"],
                "manifest_digest": accepted_envelope["manifest_digest"],
                "prior_manifest_digest": prior_manifest_digest,
                "reservation_name": reservation_name,
                "draft_sha256": draft_sha256,
            }
            if all(existing.get(name) == value for name, value in expected_identity.items()):
                return existing
            raise ValueError("acceptance operation ID is already bound to another operation")
        if event_type == "initial":
            if prior_events:
                raise ValueError("reading is already indexed")
            initial_sequence = len(events) + 1
            prior_manifest_digest = None
            reservation_name = None
            draft_sha256 = None
        else:
            if not prior_events:
                raise ValueError("follow-up acceptance has no indexed initial reading")
            latest = prior_events[-1]
            if latest["manifest_digest"] != prior_manifest_digest:
                raise ValueError(
                    "follow-up prior manifest digest is stale; another operation committed first"
                )
            if pipeline_sha256 != prior_events[0]["pipeline_manifest_sha256"]:
                raise ValueError("pipeline manifest differs from its indexed initial commit")
            if accepted_envelope["manifest"].get("followup_of_manifest_digest") != prior_manifest_digest:
                raise ValueError("follow-up envelope is not bound to the indexed baseline")
            if accepted_envelope["manifest"].get("claims") != latest["accepted_envelope"]["manifest"].get("claims"):
                raise ValueError("follow-up cannot change frozen claims")
            if _chart_sections(accepted_envelope["manifest"]) != _chart_sections(
                latest["accepted_envelope"]["manifest"]
            ):
                raise ValueError("follow-up cannot change frozen chart sections")
            if not isinstance(reservation_name, str) or not reservation_name:
                raise ValueError("follow-up acceptance requires its reservation name")
            if not _valid_digest(draft_sha256):
                raise ValueError("follow-up acceptance requires its draft digest")
            initial_sequence = prior_events[0]["initial_sequence"]
        event: dict[str, Any] = {
            "sequence": len(events) + 1,
            "initial_sequence": initial_sequence,
            "event_type": event_type,
            "system": system,
            "reading_id": reading_id,
            "artifact_relpath": str(resolved_artifact.relative_to(resolved_root)),
            "pipeline_manifest_relpath": str(pipeline_path.relative_to(resolved_root)),
            "pipeline_manifest_sha256": pipeline_sha256,
            "accepted_file_sha256": accepted_sha256,
            "envelope_digest": accepted_envelope["envelope_digest"],
            "manifest_digest": accepted_envelope["manifest_digest"],
            "accepted_envelope": accepted_envelope,
            "prior_manifest_digest": prior_manifest_digest,
            "operation_id": operation_id,
            "reservation_name": reservation_name,
            "draft_sha256": draft_sha256,
            "previous_event_digest": events[-1]["event_digest"] if events else None,
        }
        event["event_digest"] = _canonical_digest(event)
        events.append(event)
        _seal_index(index, key)
        _commit_index(resolved_root, index, key)
        return event


def latest_acceptance_event(
    root: str | Path,
    *,
    system: str,
    reading_id: str,
) -> dict[str, Any] | None:
    index = load_acceptance_index(root)
    matches = [
        event
        for event in index["events"]
        if event["system"] == system and event["reading_id"] == reading_id
    ]
    return matches[-1] if matches else None


def acceptance_event_by_operation(
    root: str | Path,
    *,
    operation_id: str,
) -> dict[str, Any] | None:
    if not _valid_digest(operation_id):
        raise ValueError("acceptance operation ID is invalid")
    index = load_acceptance_index(root)
    matches = [
        event for event in index["events"] if event["operation_id"] == operation_id
    ]
    if len(matches) > 1:
        raise ValueError("acceptance operation ID is not unique")
    return matches[0] if matches else None


def _creation_path(root: Path, pipeline_sha256: str) -> Path:
    return _trust_dir(root) / "creations" / f"{pipeline_sha256}.json"


def _validate_creation_payload(
    payload: dict[str, Any],
    *,
    pipeline_sha256: str,
    key: bytes,
) -> None:
    supplied_mac = payload.get("creation_mac")
    unsigned = {
        name: value for name, value in payload.items() if name != "creation_mac"
    }
    active_root_path = payload.get("active_root_path")
    active_root_digest = payload.get("active_root_path_digest")
    active_pair_valid = (
        active_root_path is None
        and active_root_digest is None
    ) or (
        isinstance(active_root_path, str)
        and Path(active_root_path).is_absolute()
        and _valid_digest(active_root_digest)
        and hashlib.sha256(active_root_path.encode("utf-8")).hexdigest()
        == active_root_digest
    )
    if (
        payload.get("schema_version") != CREATION_SCHEMA
        or payload.get("pipeline_manifest_sha256") != pipeline_sha256
        or payload.get("system") not in SYSTEMS
        or not isinstance(payload.get("reading_id"), str)
        or not payload["reading_id"]
        or not isinstance(payload.get("artifact_relpath"), str)
        or Path(payload["artifact_relpath"]).is_absolute()
        or ".." in Path(payload["artifact_relpath"]).parts
        or not active_pair_valid
        or not isinstance(supplied_mac, str)
        or not hmac.compare_digest(supplied_mac, _mac(key, unsigned))
    ):
        raise ValueError("pipeline creation record is invalid")


def _bind_creation_to_root(
    payload: dict[str, Any],
    *,
    root: Path,
    pipeline: dict[str, Any],
    key: bytes,
    path: Path,
) -> dict[str, Any]:
    current = str(root.resolve(strict=True))
    active = payload.get("active_root_path")
    if active is None:
        declared = pipeline.get("pipeline_root")
        if isinstance(declared, str) and declared:
            declared_path = Path(declared).expanduser()
            if declared_path.exists():
                declared_active = str(declared_path.resolve(strict=True))
                if declared_active != current:
                    raise ValueError(
                        "pipeline creation root still exists; refusing copied-root takeover"
                    )
    elif active != current and Path(active).exists():
        raise ValueError(
            "pipeline creation root still exists; refusing copied-root takeover"
        )
    if active == current:
        return payload
    updated = {
        name: value
        for name, value in payload.items()
        if name
        not in {"creation_mac", "active_root_path", "active_root_path_digest"}
    }
    updated["active_root_path"] = current
    updated["active_root_path_digest"] = hashlib.sha256(
        current.encode("utf-8")
    ).hexdigest()
    updated["creation_mac"] = _mac(key, updated)
    _atomic_write(path, updated)
    return updated


def record_pipeline_creation(
    root: str | Path,
    *,
    system: str,
    reading_id: str,
    artifact_dir: str | Path,
    pipeline_manifest_path: str | Path,
    expected_pipeline_sha256: str,
) -> dict[str, Any]:
    resolved_root = Path(root).expanduser().resolve(strict=True)
    resolved_artifact = Path(artifact_dir).expanduser().resolve(strict=True)
    if system not in SYSTEMS or not resolved_artifact.is_relative_to(resolved_root):
        raise ValueError("pipeline creation identity is invalid")
    pipeline_path = _contained_file(
        pipeline_manifest_path,
        artifact_dir=resolved_artifact,
        label="pipeline manifest",
    )
    if not _valid_digest(expected_pipeline_sha256):
        raise ValueError("expected pipeline manifest digest is invalid")
    with _trust_lock(resolved_root, create=True):
        pipeline_sha256 = _sha256(pipeline_path)
        if pipeline_sha256 != expected_pipeline_sha256:
            raise ValueError("pipeline manifest changed before creation registration")
        key = _load_or_create_key(resolved_root, create=True)
        payload: dict[str, Any] = {
            "schema_version": CREATION_SCHEMA,
            "system": system,
            "reading_id": reading_id,
            "artifact_relpath": str(resolved_artifact.relative_to(resolved_root)),
            "pipeline_manifest_sha256": pipeline_sha256,
            "active_root_path": str(resolved_root),
            "active_root_path_digest": _root_path_digest(resolved_root),
        }
        payload["creation_mac"] = _mac(key, payload)
        path = _creation_path(resolved_root, pipeline_sha256)
        if path.exists():
            existing = _read_object(path)
            _validate_creation_payload(
                existing,
                pipeline_sha256=pipeline_sha256,
                key=key,
            )
            identity_fields = (
                "schema_version",
                "system",
                "reading_id",
                "artifact_relpath",
                "pipeline_manifest_sha256",
            )
            if any(existing.get(name) != payload.get(name) for name in identity_fields):
                raise ValueError(
                    "pipeline creation hash is already registered differently"
                )
            pipeline = _read_object(pipeline_path)
            return _bind_creation_to_root(
                existing,
                root=resolved_root,
                pipeline=pipeline,
                key=key,
                path=path,
            )
        _atomic_write(path, payload)
        return payload


def load_pipeline_creation(
    root: str | Path,
    pipeline_manifest_path: str | Path,
) -> dict[str, Any]:
    resolved_root = Path(root).expanduser().resolve(strict=True)
    pipeline_path = Path(pipeline_manifest_path).expanduser().resolve(strict=True)
    pipeline_sha256 = _sha256(pipeline_path)
    with _trust_lock(resolved_root, create=False):
        key = _load_or_create_key(resolved_root, create=False)
        path = _creation_path(resolved_root, pipeline_sha256)
        if not path.is_file() or path.is_symlink():
            raise ValueError("pipeline manifest has no trusted creation record")
        payload = _read_object(path)
        _validate_creation_payload(
            payload,
            pipeline_sha256=pipeline_sha256,
            key=key,
        )
        pipeline = _read_object(pipeline_path)
        payload = _bind_creation_to_root(
            payload,
            root=resolved_root,
            pipeline=pipeline,
            key=key,
            path=path,
        )
        artifact_dir = (resolved_root / payload["artifact_relpath"]).resolve(
            strict=True
        )
        if artifact_dir != pipeline_path.parent.resolve():
            raise ValueError(
                "pipeline creation record points to another reading directory"
            )
        return payload


__all__ = [
    "INDEX_NAME",
    "INDEX_SCHEMA",
    "acceptance_event_by_operation",
    "latest_acceptance_event",
    "load_acceptance_index",
    "load_pipeline_creation",
    "record_acceptance",
    "record_pipeline_creation",
]
