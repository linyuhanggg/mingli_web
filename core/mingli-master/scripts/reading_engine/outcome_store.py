"""Immutable, authenticated outcomes for pre-existing structured claims."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Literal, Mapping, Sequence

from .contracts import (
    EvidenceBundle,
    JudgmentDimension,
    ReadingRecord,
    judgment_dimension_digest,
)
from .storage import AtomicReadingStore, _atomic_replace, _ensure_private_directory


DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
OUTCOME_STATUSES = ("hit", "partial", "miss", "unknown")
EVIDENCE_KINDS = ("user_report", "document", "observed_event", "third_party_report")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_copy(value: Any) -> Any:
    return json.loads(_canonical_json(value))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _validate_datetime(value: str, *, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a timezone-aware ISO datetime")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be a timezone-aware ISO datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware ISO datetime")


def _validated_evidence(value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("outcome evidence must be an object")
    allowed = {"kind", "summary", "observed_at"}
    if not set(value) <= allowed or not {"kind", "summary"} <= set(value):
        raise ValueError("outcome evidence fields are not allowed")
    kind = value.get("kind")
    summary = value.get("summary")
    observed_at = value.get("observed_at")
    if kind not in EVIDENCE_KINDS:
        raise ValueError("outcome evidence kind is not allowed")
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 1000:
        raise ValueError("outcome evidence summary must contain 1..1000 characters")
    result = {"kind": kind, "summary": summary}
    if observed_at is not None:
        _validate_datetime(observed_at, field="observed_at")
        result["observed_at"] = observed_at
    if len(_canonical_json(result).encode("utf-8")) > 4096:
        raise ValueError("outcome evidence is too large")
    return result


def _read_private_json(path: Path, *, maximum: int = 1_048_576) -> Any:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RuntimeError(f"unsafe private file: {path.name}") from exc
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise RuntimeError(f"unsafe private file: {path.name}")
        content = os.read(descriptor, maximum + 1)
    finally:
        os.close(descriptor)
    if not content or len(content) > maximum:
        raise ValueError(f"private file size is invalid: {path.name}")
    return json.loads(content)


def _private_directory_identity(path: Path) -> tuple[int, int]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise RuntimeError(f"unsafe private directory: {path.name}") from exc
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise RuntimeError(f"unsafe private directory: {path.name}")
        return info.st_dev, info.st_ino
    finally:
        os.close(descriptor)


@contextmanager
def _secure_lock(path: Path) -> Iterator[int]:
    _ensure_private_directory(path.parent)
    flags = os.O_RDWR | os.O_CREAT
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise RuntimeError(f"unsafe outcome lock: {path.name}") from exc
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            raise RuntimeError(f"unsafe outcome lock: {path.name}")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield descriptor
    finally:
        os.close(descriptor)


def _contributor(
    *,
    role: str,
    system: str,
    provider_id: str,
    provider_version: str,
    evidence: EvidenceBundle,
    judgment_claim_digest: str,
    fact_refs: Sequence[str],
    evidence_refs: Sequence[str],
    counter_evidence_refs: Sequence[str],
) -> dict[str, Any]:
    nodes = tuple(evidence.evidence) + tuple(evidence.counter_evidence)
    node_map = {node.rule_id: node for node in nodes}
    support_ids = sorted(set(evidence_refs))
    counter_ids = sorted(set(counter_evidence_refs))
    if len(nodes) != len(node_map) or set(support_ids) & set(counter_ids):
        raise ValueError("claim support and counter rule identities overlap")
    missing = sorted((set(support_ids) | set(counter_ids)) - set(node_map))
    if missing:
        raise ValueError(f"claim rule identities are missing: {missing}")
    return {
        "role": role,
        "system": system,
        "provider_id": provider_id,
        "provider_version": provider_version,
        "judgment_claim_digest": judgment_claim_digest,
        "fact_refs": sorted(set(fact_refs)),
        "support_rule_ids": support_ids,
        "counter_rule_ids": counter_ids,
        "support_source_lineages": sorted(
            {node_map[item].lineage for item in support_ids}
        ),
        "counter_source_lineages": sorted(
            {node_map[item].lineage for item in counter_ids}
        ),
    }


@dataclass(frozen=True)
class CalibratableClaim:
    claim_id: str
    claim_kind: Literal["judgment_dimension"]
    reading_id: str
    reading_version: int
    prepared_digest: str
    public_copy_sha256: str
    dimension: str
    horizon: dict[str, Any]
    claim_text: str
    contributors: tuple[dict[str, Any], ...]

    @classmethod
    def create(cls, **values: Any) -> "CalibratableClaim":
        payload = {
            "claim_kind": values["claim_kind"],
            "reading_id": values["reading_id"],
            "reading_version": values["reading_version"],
            "prepared_digest": values["prepared_digest"],
            "public_copy_sha256": values["public_copy_sha256"],
            "dimension": values["dimension"],
            "horizon": _canonical_copy(values["horizon"]),
            "claim_text": values["claim_text"],
            "contributors": _canonical_copy(values["contributors"]),
        }
        if payload["claim_kind"] != "judgment_dimension":
            raise ValueError("invalid calibratable claim kind")
        if not isinstance(payload["claim_text"], str) or not payload["claim_text"].strip():
            raise ValueError("calibratable claim text is empty")
        return cls(
            claim_id=_digest(payload),
            **{**payload, "contributors": tuple(payload["contributors"])},
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contributors"] = [dict(item) for item in self.contributors]
        return payload


@dataclass(frozen=True)
class OutcomeRecord:
    schema_version: str
    claim_id: str
    claim_kind: str
    reading_id: str
    reading_version: int
    prepared_digest: str
    public_copy_sha256: str
    dimension: str
    horizon: dict[str, Any]
    claim_text: str
    contributors: tuple[dict[str, Any], ...]
    status: Literal["hit", "partial", "miss", "unknown"]
    evidence: dict[str, str]
    reported_at: str
    record_digest: str
    integrity_mac: str

    @classmethod
    def create(
        cls,
        *,
        claim: CalibratableClaim,
        status: str,
        evidence: Mapping[str, Any],
        reported_at: str,
        integrity_key: bytes,
    ) -> "OutcomeRecord":
        if status not in OUTCOME_STATUSES:
            raise ValueError("outcome status must be hit, partial, miss, or unknown")
        if not isinstance(integrity_key, bytes) or len(integrity_key) < 32:
            raise ValueError("outcome integrity key must contain at least 32 bytes")
        _validate_datetime(reported_at, field="reported_at")
        base = {
            "schema_version": "mingli-outcome-record-v1",
            **claim.to_dict(),
            "status": status,
            "evidence": _validated_evidence(evidence),
            "reported_at": reported_at,
        }
        record_digest = _digest(base)
        authenticated = {**base, "record_digest": record_digest}
        integrity_mac = hmac.new(
            integrity_key,
            _canonical_json(authenticated).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return cls(
            **{
                **authenticated,
                "contributors": tuple(base["contributors"]),
                "integrity_mac": integrity_mac,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contributors"] = [dict(item) for item in self.contributors]
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, integrity_key: bytes) -> "OutcomeRecord":
        normalized = dict(payload)
        integrity_mac = str(normalized.pop("integrity_mac", ""))
        record_digest = str(normalized.get("record_digest") or "")
        base = dict(normalized)
        base.pop("record_digest", None)
        if record_digest != _digest(base):
            raise ValueError("outcome record digest mismatch")
        expected_mac = hmac.new(
            integrity_key,
            _canonical_json(normalized).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(integrity_mac, expected_mac):
            raise ValueError("outcome integrity MAC mismatch")
        claim_payload = {
            key: base[key]
            for key in (
                "claim_kind", "reading_id", "reading_version", "prepared_digest",
                "public_copy_sha256", "dimension", "horizon", "claim_text",
                "contributors",
            )
        }
        if base.get("claim_id") != _digest(claim_payload):
            raise ValueError("outcome claim registry identity mismatch")
        _validated_evidence(base.get("evidence") or {})
        _validate_datetime(str(base.get("reported_at") or ""), field="reported_at")
        if base.get("status") not in OUTCOME_STATUSES:
            raise ValueError("outcome status is invalid")
        return cls(
            **{
                **normalized,
                "contributors": tuple(normalized.get("contributors") or ()),
                "integrity_mac": integrity_mac,
            }
        )


class OutcomeStore:
    def __init__(
        self,
        root: str | Path,
        *,
        reading_store: AtomicReadingStore,
        integrity_key: bytes,
        checkpoint_path: str | Path,
    ) -> None:
        if not isinstance(integrity_key, bytes) or len(integrity_key) < 32:
            raise ValueError("outcome integrity key must contain at least 32 bytes")
        self.root = Path(root).expanduser()
        self.outcomes = self.root / "outcomes"
        self.reading_store = reading_store
        self._integrity_key = integrity_key
        requested_checkpoint = Path(checkpoint_path).expanduser()
        _ensure_private_directory(self.root)
        _ensure_private_directory(self.outcomes)
        checkpoint_parent = requested_checkpoint.parent.resolve()
        self.checkpoint_path = checkpoint_parent / requested_checkpoint.name
        outcome_root = self.root.resolve()
        reading_root = self.reading_store.root.resolve()
        if (
            outcome_root == reading_root
            or outcome_root in reading_root.parents
            or reading_root in outcome_root.parents
        ):
            raise ValueError("reading and outcome stores must be separate")
        if (
            checkpoint_parent == outcome_root
            or outcome_root in checkpoint_parent.parents
            or checkpoint_parent == reading_root
            or reading_root in checkpoint_parent.parents
        ):
            raise ValueError("outcome checkpoint must be outside reading and outcome stores")
        _ensure_private_directory(self.checkpoint_path.parent)
        self._reading_identity_path = reading_root / ".outcome-store-identity.json"
        self._reading_identity_lock = reading_root / ".outcome-store-identity.lock"
        # This probe must stay read-only.  An existing outcome root may reject the
        # supplied reading store, and rejection must not mutate that candidate.
        self._reading_root_identity = _private_directory_identity(reading_root)
        self._reading_store_id = self._load_reading_store_identity()
        self._reading_identity_was_missing = self._reading_store_id is None
        self._root_lock = self.root / ".outcome-root.lock"
        self._checkpoint_binding_path = self.root / ".checkpoint-binding.json"
        guard_key = hashlib.sha256(str(outcome_root).encode("utf-8")).hexdigest()
        self._root_guard_directory = outcome_root.parent / ".mingli-outcome-root-guards"
        self._root_guard_path = self._root_guard_directory / f"{guard_key}.json"
        self._root_guard_lock = self._root_guard_directory / f".{guard_key}.lock"
        lock_name = f".mingli-outcomes-{hashlib.sha256(str(outcome_root).encode()).hexdigest()}.lock"
        self._checkpoint_lock = self.checkpoint_path.parent / lock_name
        with _secure_lock(self._root_guard_lock):
            with _secure_lock(self._root_lock) as root_lock:
                trusted, anchor_damaged, binding_damaged, guard_damaged, reservation = (
                    self._trusted_binding_locked(root_lock)
                )
                with _secure_lock(self._checkpoint_lock):
                    if trusted is not None:
                        bound_id = str(trusted["reading_store_id"])
                        self._assert_reading_root_identity()
                        current_id = self._load_reading_store_identity()
                        if current_id is None:
                            raise ValueError(
                                "reading store identity is missing for outcome checkpoint identity"
                            )
                        if current_id != bound_id:
                            raise ValueError("reading store identity mismatch")
                        # Refresh a stale pre-lock None after a concurrent initializer,
                        # while also closing the probe-to-lock replacement window.
                        self._reading_store_id = current_id
                        entries = self._initial_checkpoint_entries_locked(
                            allow_legacy=True,
                        )
                        self._assert_reading_root_identity()
                        self._repair_binding_copies_locked(root_lock, trusted)
                    else:
                        if (
                            binding_damaged
                            and not self.checkpoint_path.exists()
                        ):
                            raise ValueError(
                                "outcome checkpoint identity binding is damaged"
                            )
                        if (
                            (anchor_damaged or binding_damaged)
                            and self.checkpoint_path.exists()
                        ):
                            raise ValueError(
                                "existing outcome identity cannot be reauthenticated"
                            )
                        if self._reading_store_id is None:
                            self._reading_store_id = secrets.token_hex(32)
                        entries = self._initial_checkpoint_entries_locked(
                            allow_legacy=True,
                        )
                        if reservation is None:
                            self._write_root_reservation()
                        # Only now do we know this is a new store, an authenticated
                        # legacy migration, or a v2 checkpoint whose binding digest
                        # matches the immutable reading-store identity.
                        self._persist_reading_store_identity()
                        self._assert_reading_root_identity()
                        self._validate_checkpoint_records_locked(entries)
                        self._assert_reading_root_identity()
                        self._write_root_guard()
                        self._write_checkpoint_binding()
                        self._write_root_anchor_locked(root_lock)
                    self._write_manifest(entries)

    @staticmethod
    def _parse_reading_store_identity(payload: Any) -> str:
        if not isinstance(payload, dict):
            raise ValueError("reading store identity must be an object")
        core = dict(payload)
        identity_digest = str(core.pop("identity_digest", ""))
        if (
            core.get("schema_version") != "mingli-reading-store-identity-v1"
            or not DIGEST_RE.fullmatch(str(core.get("store_id") or ""))
            or identity_digest != _digest(core)
        ):
            raise ValueError("reading store identity is invalid")
        return str(core["store_id"])

    def _load_reading_store_identity(self) -> str | None:
        if self._reading_identity_path.exists():
            return self._parse_reading_store_identity(
                _read_private_json(self._reading_identity_path)
            )
        return None

    def _assert_reading_root_identity(self) -> None:
        if (
            _private_directory_identity(self.reading_store.root.resolve())
            != self._reading_root_identity
        ):
            raise ValueError("reading store directory identity changed")

    def _persist_reading_store_identity(self) -> None:
        if not DIGEST_RE.fullmatch(str(self._reading_store_id or "")):
            raise ValueError("reading store identity is unavailable")
        self._assert_reading_root_identity()
        with _secure_lock(self._reading_identity_lock):
            self._assert_reading_root_identity()
            if self._reading_identity_path.exists():
                persisted_id = self._parse_reading_store_identity(
                    _read_private_json(self._reading_identity_path)
                )
                # Two otherwise independent outcome roots may both have confirmed
                # a first attachment before either creates the shared identity.
                # The identity lock elects one value; the waiter adopts it before
                # writing its own authenticated binding.
                if (
                    persisted_id != self._reading_store_id
                    and not self._reading_identity_was_missing
                ):
                    raise ValueError("reading store identity mismatch")
                self._reading_store_id = persisted_id
                self._reading_identity_was_missing = False
                self._assert_reading_root_identity()
                return
            core = {
                "schema_version": "mingli-reading-store-identity-v1",
                "store_id": self._reading_store_id,
            }
            _atomic_replace(
                self._reading_identity_path,
                json.dumps(
                    {**core, "identity_digest": _digest(core)},
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ) + "\n",
            )
            self._reading_identity_was_missing = False
            self._assert_reading_root_identity()

    def _assert_reading_store_identity(self) -> None:
        identity = self._load_reading_store_identity()
        if identity is None or identity != self._reading_store_id:
            raise ValueError("reading store identity mismatch")

    def _checkpoint_binding_payload(self) -> dict[str, str]:
        self._assert_reading_root_identity()
        core = {
            "schema_version": "mingli-outcome-checkpoint-binding-v1",
            "outcome_store": str(self.root.resolve()),
            "checkpoint_path": str(self.checkpoint_path),
            "reading_store": str(self.reading_store.root.resolve()),
            "reading_store_id": self._reading_store_id,
        }
        binding_digest = _digest(core)
        authenticated = {**core, "binding_digest": binding_digest}
        return {
            **authenticated,
            "integrity_mac": hmac.new(
                self._integrity_key,
                _canonical_json(authenticated).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest(),
        }

    def _write_checkpoint_binding(self) -> None:
        _atomic_replace(
            self._checkpoint_binding_path,
            json.dumps(
                self._checkpoint_binding_payload(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
        )

    def _write_root_guard(self) -> None:
        _atomic_replace(
            self._root_guard_path,
            json.dumps(
                self._checkpoint_binding_payload(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
        )

    def _root_reservation_payload(self) -> dict[str, str]:
        core = {
            "schema_version": "mingli-outcome-root-reservation-v1",
            "outcome_store": str(self.root.resolve()),
            "checkpoint_path": str(self.checkpoint_path),
            "reading_store": str(self.reading_store.root.resolve()),
            "reading_store_device": str(self._reading_root_identity[0]),
            "reading_store_inode": str(self._reading_root_identity[1]),
        }
        reservation_digest = _digest(core)
        authenticated = {**core, "reservation_digest": reservation_digest}
        return {
            **authenticated,
            "integrity_mac": hmac.new(
                self._integrity_key,
                _canonical_json(authenticated).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest(),
        }

    def _write_root_reservation(self) -> None:
        self._assert_reading_root_identity()
        _atomic_replace(
            self._root_guard_path,
            json.dumps(
                self._root_reservation_payload(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
        )

    def _authenticated_reservation_core(self, payload: Any) -> dict[str, str]:
        if not isinstance(payload, dict):
            raise ValueError("outcome root reservation must be an object")
        integrity_mac = str(payload.get("integrity_mac") or "")
        authenticated = dict(payload)
        authenticated.pop("integrity_mac", None)
        expected_mac = hmac.new(
            self._integrity_key,
            _canonical_json(authenticated).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(integrity_mac, expected_mac):
            raise ValueError("outcome root reservation MAC mismatch")
        core = dict(authenticated)
        reservation_digest = str(core.pop("reservation_digest", ""))
        if (
            core.get("schema_version") != "mingli-outcome-root-reservation-v1"
            or reservation_digest != _digest(core)
            or any(not isinstance(core.get(field), str) for field in (
                "outcome_store", "checkpoint_path", "reading_store",
                "reading_store_device", "reading_store_inode",
            ))
            or not str(core.get("reading_store_device") or "").isdigit()
            or not str(core.get("reading_store_inode") or "").isdigit()
        ):
            raise ValueError("outcome root reservation is invalid")
        return {**core, "reservation_digest": reservation_digest}

    def _assert_reservation_targets_request(
        self,
        core: Mapping[str, str],
    ) -> None:
        if any(
            core.get(field) != expected
            for field, expected in (
                ("outcome_store", str(self.root.resolve())),
                ("checkpoint_path", str(self.checkpoint_path)),
                ("reading_store", str(self.reading_store.root.resolve())),
                ("reading_store_device", str(self._reading_root_identity[0])),
                ("reading_store_inode", str(self._reading_root_identity[1])),
            )
        ):
            raise ValueError("outcome checkpoint identity reservation mismatch")

    def _authenticated_binding_core(self, payload: Any) -> dict[str, str]:
        if not isinstance(payload, dict):
            raise ValueError("outcome checkpoint identity binding must be an object")
        integrity_mac = str(payload.get("integrity_mac") or "")
        authenticated = dict(payload)
        authenticated.pop("integrity_mac", None)
        expected_mac = hmac.new(
            self._integrity_key,
            _canonical_json(authenticated).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(integrity_mac, expected_mac):
            raise ValueError("outcome checkpoint identity binding MAC mismatch")
        core = dict(authenticated)
        binding_digest = str(core.pop("binding_digest", ""))
        if binding_digest != _digest(core):
            raise ValueError("outcome checkpoint identity binding digest mismatch")
        if (
            core.get("schema_version") != "mingli-outcome-checkpoint-binding-v1"
            or not DIGEST_RE.fullmatch(str(core.get("reading_store_id") or ""))
            or any(not isinstance(core.get(field), str) for field in (
                "outcome_store", "checkpoint_path", "reading_store",
            ))
        ):
            raise ValueError("outcome checkpoint identity binding is invalid")
        return {**core, "binding_digest": binding_digest}

    def _assert_binding_targets_request(self, core: Mapping[str, str]) -> None:
        if any(
            core.get(field) != expected
            for field, expected in (
                ("outcome_store", str(self.root.resolve())),
                ("checkpoint_path", str(self.checkpoint_path)),
                ("reading_store", str(self.reading_store.root.resolve())),
            )
        ):
            raise ValueError("outcome checkpoint identity mismatch")

    def _validate_binding_payload(self, payload: Any) -> dict[str, str]:
        core = self._authenticated_binding_core(payload)
        self._assert_binding_targets_request(core)
        if (
            self._reading_store_id is not None
            and core["reading_store_id"] != self._reading_store_id
        ):
            raise ValueError("outcome checkpoint identity mismatch")
        return core

    def _assert_checkpoint_binding(self) -> None:
        self._assert_reading_store_identity()
        self._validate_binding_payload(_read_private_json(self._checkpoint_binding_path))

    def _root_anchor_locked(
        self,
        descriptor: int,
    ) -> tuple[dict[str, Any] | None, bool]:
        os.lseek(descriptor, 0, os.SEEK_SET)
        content = os.read(descriptor, 16_385)
        if not content:
            return None, False
        if len(content) > 16_384:
            return None, True
        try:
            payload = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, True
        if not isinstance(payload, dict):
            return None, True
        return payload, False

    def _write_root_anchor_locked(self, descriptor: int) -> None:
        content = (
            json.dumps(
                self._checkpoint_binding_payload(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n"
        ).encode("utf-8")
        os.lseek(descriptor, 0, os.SEEK_SET)
        written = 0
        while written < len(content):
            count = os.write(descriptor, content[written:])
            if not isinstance(count, int) or count <= 0:
                raise OSError("outcome root identity anchor write made no progress")
            written += count
        os.ftruncate(descriptor, len(content))
        os.fsync(descriptor)

    def _read_binding_file_candidate(
        self,
        path: Path,
    ) -> tuple[dict[str, str] | None, bool]:
        if not path.exists():
            return None, False
        try:
            payload = _read_private_json(path)
            core = self._authenticated_binding_core(payload)
        except ValueError:
            return None, True
        self._assert_binding_targets_request(core)
        return core, False

    def _read_binding_candidate(self) -> tuple[dict[str, str] | None, bool]:
        return self._read_binding_file_candidate(self._checkpoint_binding_path)

    def _read_root_guard_candidate(
        self,
    ) -> tuple[dict[str, str] | None, dict[str, str] | None, bool]:
        if not self._root_guard_path.exists():
            return None, None, False
        try:
            payload = _read_private_json(self._root_guard_path)
            if (
                isinstance(payload, Mapping)
                and payload.get("schema_version")
                == "mingli-outcome-root-reservation-v1"
            ):
                reservation = self._authenticated_reservation_core(payload)
                guard = None
            else:
                reservation = None
                guard = self._authenticated_binding_core(payload)
        except ValueError:
            return None, None, True
        if reservation is not None:
            self._assert_reservation_targets_request(reservation)
            return None, reservation, False
        self._assert_binding_targets_request(guard)
        return guard, None, False

    def _trusted_binding_locked(
        self,
        descriptor: int,
    ) -> tuple[
        dict[str, str] | None,
        bool,
        bool,
        bool,
        dict[str, str] | None,
    ]:
        anchor_payload, anchor_damaged = self._root_anchor_locked(descriptor)
        anchor: dict[str, str] | None = None
        if anchor_payload is not None:
            try:
                anchor = self._authenticated_binding_core(anchor_payload)
            except ValueError:
                anchor_damaged = True
            else:
                self._assert_binding_targets_request(anchor)
        binding, binding_damaged = self._read_binding_candidate()
        guard, reservation, guard_damaged = self._read_root_guard_candidate()
        if guard_damaged:
            raise ValueError(
                "external outcome root identity guard cannot be authenticated"
            )
        digests = {
            candidate["binding_digest"]
            for candidate in (guard, anchor, binding)
            if candidate is not None
        }
        if len(digests) > 1:
            raise ValueError("outcome checkpoint identity copies conflict")
        trusted = guard or anchor or binding
        if trusted is not None:
            return (
                trusted,
                anchor_damaged,
                binding_damaged,
                guard_damaged,
                reservation,
            )
        # A v2 checkpoint may still authenticate the expected binding below;
        # otherwise initialization fails closed without writing identity.  An
        # empty/partial anchor alone may be a crash before first binding commit.
        return (
            None,
            anchor_damaged,
            binding_damaged,
            guard_damaged,
            reservation,
        )

    def _repair_binding_copies_locked(
        self,
        descriptor: int,
        trusted: Mapping[str, str],
    ) -> None:
        expected = self._checkpoint_binding_payload()
        if trusted["binding_digest"] != expected["binding_digest"]:
            raise ValueError("outcome checkpoint identity mismatch")
        guard, _, _ = self._read_root_guard_candidate()
        if guard is None:
            self._write_root_guard()
        elif guard["binding_digest"] != expected["binding_digest"]:
            raise ValueError("outcome checkpoint identity copies conflict")
        anchor_payload, _ = self._root_anchor_locked(descriptor)
        try:
            anchor = (
                None
                if anchor_payload is None
                else self._validate_binding_payload(anchor_payload)
            )
        except ValueError:
            anchor = None
        if anchor is None:
            self._write_root_anchor_locked(descriptor)
        binding, _ = self._read_binding_candidate()
        if binding is None:
            self._write_checkpoint_binding()
        elif binding["binding_digest"] != expected["binding_digest"]:
            raise ValueError("outcome checkpoint identity copies conflict")

    def _initial_checkpoint_entries_locked(
        self,
        *,
        allow_legacy: bool,
    ) -> dict[str, str]:
        if not self.checkpoint_path.exists():
            if any(self.outcomes.glob("*.json")):
                raise RuntimeError("outcome checkpoint is missing for a non-empty store")
            return {}
        entries, pending = self._manifest_state(allow_legacy=allow_legacy)
        if pending is not None:
            claim_id, record_digest = pending
            path = self._path(claim_id)
            if path.exists():
                record = self._load_record_file(claim_id)
                if (
                    record.record_digest != record_digest
                    or not self._record_matches_registry(record)
                ):
                    raise RuntimeError(
                        "pending outcome cannot be authenticated for recovery"
                    )
                entries[claim_id] = record_digest
        files = {path.stem for path in self.outcomes.glob("*.json")}
        if files != set(entries):
            raise RuntimeError("outcome store differs from the authenticated checkpoint")
        self._validate_checkpoint_records_locked(entries)
        return entries

    @contextmanager
    def _locked_checkpoint(self) -> Iterator[None]:
        with _secure_lock(self._root_guard_lock):
            with _secure_lock(self._root_lock) as root_lock:
                trusted, _, _, _, _ = self._trusted_binding_locked(root_lock)
                if trusted is None:
                    raise RuntimeError("outcome root identity anchor is missing")
                self._assert_reading_root_identity()
                self._assert_reading_store_identity()
                if trusted["reading_store_id"] != self._reading_store_id:
                    raise ValueError("reading store identity mismatch")
                self._repair_binding_copies_locked(root_lock, trusted)
                self._assert_checkpoint_binding()
                with _secure_lock(self._checkpoint_lock):
                    yield

    def _checkpoint_payload(
        self,
        entries: Mapping[str, str],
        *,
        pending: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        core = {
            "schema_version": "mingli-outcome-checkpoint-v2",
            "outcome_store": str(self.root.resolve()),
            "checkpoint_binding_digest": self._checkpoint_binding_payload()[
                "binding_digest"
            ],
            "entries": [
                {"claim_id": claim_id, "record_digest": entries[claim_id]}
                for claim_id in sorted(entries)
            ],
            "pending": (
                None
                if pending is None
                else {"claim_id": pending[0], "record_digest": pending[1]}
            ),
        }
        manifest_digest = _digest(core)
        authenticated = {**core, "manifest_digest": manifest_digest}
        return {
            **authenticated,
            "integrity_mac": hmac.new(
                self._integrity_key,
                _canonical_json(authenticated).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest(),
        }

    def _write_manifest(
        self,
        entries: Mapping[str, str],
        *,
        pending: tuple[str, str] | None = None,
    ) -> None:
        payload = self._checkpoint_payload(entries, pending=pending)
        _atomic_replace(
            self.checkpoint_path,
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )

    def _manifest_state(
        self,
        *,
        allow_legacy: bool = False,
    ) -> tuple[dict[str, str], tuple[str, str] | None]:
        payload = _read_private_json(self.checkpoint_path)
        if not isinstance(payload, dict):
            raise ValueError("outcome checkpoint must be an object")
        integrity_mac = str(payload.get("integrity_mac") or "")
        authenticated = dict(payload)
        authenticated.pop("integrity_mac", None)
        expected = hmac.new(
            self._integrity_key,
            _canonical_json(authenticated).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(integrity_mac, expected):
            raise ValueError("outcome checkpoint MAC mismatch")
        core = dict(authenticated)
        manifest_digest = str(core.pop("manifest_digest", ""))
        if manifest_digest != _digest(core):
            raise ValueError("outcome checkpoint digest mismatch")
        schema_version = core.get("schema_version")
        if core.get("outcome_store") != str(self.root.resolve()):
            raise ValueError("outcome checkpoint identity mismatch")
        if schema_version == "mingli-outcome-checkpoint-v1":
            if not allow_legacy:
                raise ValueError("legacy outcome checkpoint requires locked migration")
        elif schema_version == "mingli-outcome-checkpoint-v2":
            if core.get("checkpoint_binding_digest") != self._checkpoint_binding_payload()[
                "binding_digest"
            ]:
                raise ValueError("outcome checkpoint binding mismatch")
        else:
            raise ValueError("outcome checkpoint identity mismatch")
        entries: dict[str, str] = {}
        for item in core.get("entries") or ():
            if not isinstance(item, Mapping):
                raise ValueError("outcome checkpoint entry is invalid")
            claim_id = str(item.get("claim_id") or "")
            record_digest = str(item.get("record_digest") or "")
            if not DIGEST_RE.fullmatch(claim_id) or not DIGEST_RE.fullmatch(record_digest):
                raise ValueError("outcome checkpoint entry is invalid")
            if claim_id in entries:
                raise ValueError("outcome checkpoint contains duplicate claims")
            entries[claim_id] = record_digest
        pending_payload = core.get("pending")
        pending = None
        if pending_payload is not None:
            if not isinstance(pending_payload, Mapping):
                raise ValueError("outcome checkpoint pending entry is invalid")
            claim_id = str(pending_payload.get("claim_id") or "")
            record_digest = str(pending_payload.get("record_digest") or "")
            if (
                not DIGEST_RE.fullmatch(claim_id)
                or not DIGEST_RE.fullmatch(record_digest)
                or claim_id in entries
            ):
                raise ValueError("outcome checkpoint pending entry is invalid")
            pending = (claim_id, record_digest)
        return entries, pending

    def _record_matches_registry(self, record: OutcomeRecord) -> bool:
        canonical = {
            item.claim_id: item
            for item in self.claims(
                reading_id=record.reading_id,
                prepared_digest=record.prepared_digest,
            )
        }.get(record.claim_id)
        if canonical is None:
            return False
        expected = canonical.to_dict()
        actual = record.to_dict()
        return {key: actual[key] for key in expected} == expected

    def _recover_pending_locked(self, *, allow_legacy: bool = False) -> dict[str, str]:
        entries, pending = self._manifest_state(allow_legacy=allow_legacy)
        if pending is not None:
            claim_id, record_digest = pending
            path = self._path(claim_id)
            if path.exists():
                record = self._load_record_file(claim_id)
                if (
                    record.record_digest != record_digest
                    or not self._record_matches_registry(record)
                ):
                    raise RuntimeError("pending outcome cannot be authenticated for recovery")
                entries[claim_id] = record_digest
            self._write_manifest(entries)
        files = {path.stem for path in self.outcomes.glob("*.json")}
        if files != set(entries):
            raise RuntimeError("outcome store differs from the authenticated checkpoint")
        return entries

    def _validate_checkpoint_records_locked(self, entries: Mapping[str, str]) -> None:
        for claim_id, record_digest in entries.items():
            record = self._load_record_file(claim_id)
            if (
                record.record_digest != record_digest
                or not self._record_matches_registry(record)
            ):
                raise RuntimeError(
                    "legacy outcome record cannot be authenticated for migration"
                )

    def _checkpoint_entries(self) -> dict[str, str]:
        with self._locked_checkpoint():
            return self._recover_pending_locked()

    def _path(self, claim_id: str) -> Path:
        if not DIGEST_RE.fullmatch(str(claim_id or "")):
            raise ValueError("invalid claim_id")
        return self.outcomes / f"{claim_id}.json"

    def _exact_reading(self, reading_id: str, prepared_digest: str) -> ReadingRecord:
        current = self.reading_store.load(reading_id)
        if current.accepted.prepared_digest == prepared_digest:
            return current
        for version in range(1, current.accepted.version):
            candidate = self.reading_store.load_version(reading_id, version)
            if candidate.accepted.prepared_digest == prepared_digest:
                return candidate
        raise ValueError("accepted reading identity was not found")

    @staticmethod
    def _claims_from_reading(reading: ReadingRecord) -> tuple[CalibratableClaim, ...]:
        """Derive the calibratable registry from deterministic judgment.

        The accepted public copy is the final authority and is never parsed,
        verified or intercepted here.  A calibration target exists only when
        the provider produced a real conclusion; the engine's own verdict
        placeholders (caller_review_required / unassessed / empty conclusion)
        are never calibrated.  When no dimension carries a conclusion the
        registry is empty, which disables outcome calibration instead of
        recording a placeholder.
        """
        accepted = reading.accepted
        horizon = reading.request.intent.get("horizon") or {}
        if not isinstance(horizon, Mapping) or not str(horizon.get("kind") or ""):
            raise ValueError("accepted reading has no calibratable time horizon")
        claims: list[CalibratableClaim] = []
        seen: set[str] = set()
        for dimension in reading.judgment.dimensions:
            claim_text = str(dimension.conclusion or "").strip()
            if not claim_text:
                continue
            contributor = _contributor(
                role="primary",
                system=reading.calculation.system,
                provider_id=reading.calculation.provider_id,
                provider_version=reading.calculation.provider_version,
                evidence=reading.evidence,
                judgment_claim_digest=judgment_dimension_digest(dimension),
                fact_refs=(),
                evidence_refs=dimension.evidence_ids,
                counter_evidence_refs=dimension.counter_evidence_ids,
            )
            claim = CalibratableClaim.create(
                claim_kind="judgment_dimension",
                reading_id=accepted.reading_id,
                reading_version=accepted.version,
                prepared_digest=accepted.prepared_digest,
                public_copy_sha256=accepted.public_copy_sha256,
                dimension=dimension.dimension,
                horizon=horizon,
                claim_text=claim_text,
                contributors=(contributor,),
            )
            if claim.claim_id in seen:
                raise ValueError("calibratable claim registry contains duplicate identities")
            seen.add(claim.claim_id)
            claims.append(claim)
        return tuple(claims)

    def claims(self, *, reading_id: str, prepared_digest: str) -> tuple[CalibratableClaim, ...]:
        return self._claims_from_reading(self._exact_reading(reading_id, prepared_digest))

    def record(
        self,
        *,
        reading_id: str,
        prepared_digest: str,
        claim_id: str,
        status: str,
        evidence: Mapping[str, Any],
        reported_at: str,
    ) -> OutcomeRecord:
        registry = {
            item.claim_id: item
            for item in self.claims(reading_id=reading_id, prepared_digest=prepared_digest)
        }
        claim = registry.get(claim_id)
        if claim is None:
            raise ValueError("claim_id is not in the immutable calibratable registry")
        outcome = OutcomeRecord.create(
            claim=claim,
            status=status,
            evidence=evidence,
            reported_at=reported_at,
            integrity_key=self._integrity_key,
        )
        path = self._path(claim_id)
        rendered = json.dumps(outcome.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with self._locked_checkpoint():
            entries = self._recover_pending_locked()
            with _secure_lock(self.outcomes / f".{claim_id}.lock"):
                if path.exists():
                    existing = self._load_record_file(claim_id)
                    if (
                        entries.get(claim_id) != existing.record_digest
                        or existing != outcome
                    ):
                        raise RuntimeError("an immutable outcome already exists for this claim")
                    return existing
                if claim_id in entries:
                    raise RuntimeError("checkpoint names a missing outcome record")
                self._write_manifest(
                    entries,
                    pending=(claim_id, outcome.record_digest),
                )
                _atomic_replace(path, rendered)
                entries[claim_id] = outcome.record_digest
                self._write_manifest(entries)
        return outcome

    def _load_record_file(self, claim_id: str) -> OutcomeRecord:
        payload = _read_private_json(self._path(claim_id))
        if not isinstance(payload, dict):
            raise ValueError("outcome record must be an object")
        record = OutcomeRecord.from_dict(payload, integrity_key=self._integrity_key)
        if record.claim_id != claim_id:
            raise ValueError("stored outcome claim identity mismatch")
        return record

    def load(self, claim_id: str) -> OutcomeRecord:
        entries = self._checkpoint_entries()
        record = self._load_record_file(claim_id)
        if entries.get(claim_id) != record.record_digest:
            raise ValueError("outcome record is absent from the authenticated checkpoint")
        return record

    def list_all(self) -> list[OutcomeRecord]:
        entries = self._checkpoint_entries()
        files = {path.stem for path in self.outcomes.glob("*.json")}
        if files != set(entries):
            raise RuntimeError("outcome store differs from the authenticated checkpoint")
        records = []
        for path in sorted(self.outcomes.glob("*.json")):
            if path.is_symlink():
                raise RuntimeError(f"unsafe outcome store file: {path.name}")
            record = self._load_record_file(path.stem)
            if entries[path.stem] != record.record_digest:
                raise ValueError("outcome checkpoint record digest mismatch")
            records.append(record)
        return records

    def aggregate(self, records: Sequence[OutcomeRecord]) -> dict[str, Any]:
        checkpoint = self._checkpoint_entries()
        axes: dict[str, dict[str, dict[str, int]]] = {
            name: {}
            for name in (
                "by_provider_version", "by_dimension", "by_horizon",
            )
        }
        polarized: dict[str, dict[str, dict[str, dict[str, int]]]] = {
            "by_rule_id": {},
            "by_source_lineage": {},
        }

        def add(axis: str, key: str, status: str) -> None:
            bucket = axes[axis].setdefault(
                key,
                {"sample_count": 0, "hit": 0, "partial": 0, "miss": 0, "unknown": 0},
            )
            bucket["sample_count"] += 1
            bucket[status] += 1

        def add_polarized(axis: str, key: str, polarity: str, status: str) -> None:
            lanes = polarized[axis].setdefault(key, {})
            bucket = lanes.setdefault(
                polarity,
                {"sample_count": 0, "hit": 0, "partial": 0, "miss": 0, "unknown": 0},
            )
            bucket["sample_count"] += 1
            bucket[status] += 1

        seen: set[str] = set()
        for record in records:
            # Aggregation is a trust boundary too: callers may construct an
            # OutcomeRecord directly instead of loading it through this store.
            # Re-verify every record before it can influence calibration data.
            record = OutcomeRecord.from_dict(
                record.to_dict(), integrity_key=self._integrity_key
            )
            if record.claim_id in seen:
                raise ValueError("aggregate input contains a duplicate claim outcome")
            seen.add(record.claim_id)
            if checkpoint.get(record.claim_id) != record.record_digest:
                raise ValueError("aggregate input differs from the authenticated checkpoint")
            if not self._record_matches_registry(record):
                raise ValueError("aggregate claim differs from the accepted reading registry")
            provider_keys: set[str] = set()
            support_rule_ids: set[str] = set()
            counter_rule_ids: set[str] = set()
            support_lineages: set[str] = set()
            counter_lineages: set[str] = set()
            for contributor in record.contributors:
                provider_keys.add(
                    f"{contributor['provider_id']}@{contributor['provider_version']}"
                )
                support_rule_ids.update(contributor.get("support_rule_ids") or ())
                counter_rule_ids.update(contributor.get("counter_rule_ids") or ())
                support_lineages.update(
                    contributor.get("support_source_lineages") or ()
                )
                counter_lineages.update(
                    contributor.get("counter_source_lineages") or ()
                )
            for key in provider_keys:
                add("by_provider_version", key, record.status)
            for key in support_rule_ids:
                add_polarized("by_rule_id", key, "support", record.status)
            for key in counter_rule_ids:
                add_polarized("by_rule_id", key, "counter", record.status)
            for key in support_lineages:
                add_polarized("by_source_lineage", key, "support", record.status)
            for key in counter_lineages:
                add_polarized("by_source_lineage", key, "counter", record.status)
            add("by_dimension", record.dimension, record.status)
            add("by_horizon", _canonical_json(record.horizon), record.status)
        if seen != set(checkpoint):
            raise ValueError("aggregate input omits authenticated outcome records")
        return {
            "schema_version": "mingli-outcome-aggregate-v1",
            **axes,
            **polarized,
        }
