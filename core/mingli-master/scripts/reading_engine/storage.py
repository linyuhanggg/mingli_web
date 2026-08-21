"""Private atomic persistence keyed only by an immutable reading_id."""

from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .contracts import (
    IntakeRecord,
    PreparedReadingRecord,
    ReadingRecord,
    canonical_digest,
)


READING_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError(f"unsafe reading store directory: {path}")
    os.chmod(path, 0o700)


def _atomic_replace(path: Path, content: str) -> None:
    _ensure_private_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            os.chmod(temporary, 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _read_private_text(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"unsafe reading store file: {path}")
    return path.read_text(encoding="utf-8")


def _write_immutable(path: Path, content: str) -> None:
    if path.exists():
        if _read_private_text(path) != content:
            raise RuntimeError(f"immutable reading artifact conflict: {path.name}")
        return
    _atomic_replace(path, content)


def _same_base_facts(left: ReadingRecord, right: PreparedReadingRecord) -> bool:
    """Return whether a continuation preserved its deterministic fact base.

    A continuation is allowed to bind a new question, diagnostics, fact
    extension, and evidence.  Those values participate in ``result_hash``, so
    comparing that digest would reject a valid continuation.  Provider
    identity plus the unextended facts are the actual continuity invariant.
    """

    return (
        left.calculation.system == right.calculation.system
        and left.calculation.provider_id == right.calculation.provider_id
        and left.calculation.provider_version
        == right.calculation.provider_version
        and canonical_digest(left.calculation.facts)
        == canonical_digest(right.calculation.facts)
    )


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    _ensure_private_directory(path.parent)
    if not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("safe no-follow file locking is unavailable")
    descriptor = os.open(
        path,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        os.close(descriptor)
        raise RuntimeError(f"unsafe reading store lock: {path}")
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "r+") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        yield


class AtomicReadingStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        self.readings = self.root / "readings"
        self.intakes = self.root / "intakes"
        _ensure_private_directory(self.root)
        _ensure_private_directory(self.readings)
        _ensure_private_directory(self.intakes)

    def _reading_dir(self, reading_id: str) -> Path:
        if not READING_ID_RE.fullmatch(str(reading_id or "")):
            raise ValueError("invalid reading_id")
        return self.readings / reading_id

    def _intake_path(self, intake_id: str) -> Path:
        if not READING_ID_RE.fullmatch(str(intake_id or "")):
            raise ValueError("invalid intake_id")
        return self.intakes / f"{intake_id}.json"

    def load_intake(self, intake_id: str) -> IntakeRecord:
        payload = json.loads(_read_private_text(self._intake_path(intake_id)))
        if not isinstance(payload, dict):
            raise ValueError("intake record must be an object")
        record = IntakeRecord.from_dict(payload)
        if record.intake_id != intake_id:
            raise ValueError("stored intake_id mismatch")
        return record

    def save_intake(self, record: IntakeRecord) -> None:
        rendered = (
            json.dumps(
                record.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        _atomic_replace(self._intake_path(record.intake_id), rendered)

    def publish_intake_question(
        self,
        intake_id: str,
        question: str,
    ) -> IntakeRecord:
        with self.intake_lock(intake_id):
            record = self.load_intake(intake_id)
            if record.question is not None and record.question != question:
                raise RuntimeError("a different intake question is already published")
            updated = record.with_question(question)
            self.save_intake(updated)
            return updated

    def delete_intake(self, intake_id: str) -> None:
        path = self._intake_path(intake_id)
        try:
            os.unlink(path)
        except FileNotFoundError:
            return
        _fsync_directory(self.intakes)

    @contextmanager
    def intake_lock(self, intake_id: str) -> Iterator[None]:
        self._intake_path(intake_id)
        with _exclusive_lock(self.intakes / f".{intake_id}.lock"):
            yield

    def load(self, reading_id: str) -> ReadingRecord:
        path = self._reading_dir(reading_id) / "current.json"
        payload = json.loads(_read_private_text(path))
        if not isinstance(payload, dict):
            raise ValueError("stored reading record must be an object")
        record = ReadingRecord.from_dict(payload)
        if record.accepted.reading_id != reading_id:
            raise ValueError("stored reading_id mismatch")
        return record

    def load_version(self, reading_id: str, version: int) -> ReadingRecord:
        """Load one immutable committed version through the public store API."""

        if not isinstance(version, int) or version < 1:
            raise ValueError("reading version must be a positive integer")
        path = self._reading_dir(reading_id) / "events" / f"{version:06d}.json"
        payload = json.loads(_read_private_text(path))
        if not isinstance(payload, dict):
            raise ValueError("stored reading record must be an object")
        record = ReadingRecord.from_dict(payload)
        if (
            record.accepted.reading_id != reading_id
            or record.accepted.version != version
        ):
            raise ValueError("stored reading version identity mismatch")
        return record

    def load_prepared(self, reading_id: str) -> PreparedReadingRecord:
        path = self._reading_dir(reading_id) / "pending.json"
        payload = json.loads(_read_private_text(path))
        if not isinstance(payload, dict):
            raise ValueError("prepared reading record must be an object")
        record = PreparedReadingRecord.from_dict(payload)
        if record.reading_id != reading_id:
            raise ValueError("prepared reading_id mismatch")
        return record

    def stage(self, record: PreparedReadingRecord) -> None:
        reading_dir = self._reading_dir(record.reading_id)
        self._reading_dir(record.root_reading_id)
        if record.parent_reading_id is not None:
            self._reading_dir(record.parent_reading_id)
        external_parent = None
        if (
            record.parent_reading_id is not None
            and record.parent_reading_id != record.reading_id
        ):
            external_parent = self.load(record.parent_reading_id)
            expected_root = (
                external_parent.accepted.root_reading_id
                or external_parent.accepted.reading_id
            )
            if record.root_reading_id != expected_root:
                raise RuntimeError("reading root lineage mismatch")
        if record.action in {"new", "resume"}:
            if (
                record.version != 1
                or record.parent_reading_id is not None
                or record.root_reading_id != record.reading_id
                or record.supersedes_version is not None
            ):
                raise RuntimeError("invalid root reading lineage")
        elif record.action == "recast":
            if record.version != 1 or record.supersedes_version is not None:
                raise RuntimeError("invalid recast lineage")
        elif record.action == "continue":
            if (
                record.parent_reading_id is None
                or record.supersedes_version is not None
            ):
                raise RuntimeError("invalid continuation lineage")
            if external_parent is not None:
                if record.version != 1:
                    raise RuntimeError("imported continuation must start at version 1")
                # Each continuation re-prepares deterministically from the
                # current request, so its calculation identity legitimately
                # differs from the parent's; base-state continuity is the
                # provider adapter's own contract.
        elif record.action == "correct":
            if record.parent_reading_id is None or record.supersedes_version is None:
                raise RuntimeError("invalid correction lineage")
            if (
                external_parent is not None
                and record.supersedes_version != external_parent.accepted.version
            ):
                raise RuntimeError("correction supersedes the wrong parent version")
        elif record.action != "v3-import":
            raise RuntimeError("unsupported reading lineage action")
        prepared_dir = reading_dir / "prepared"
        _ensure_private_directory(prepared_dir)
        with _exclusive_lock(reading_dir / ".lock"):
            current_path = reading_dir / "current.json"
            current_version = 0
            current: ReadingRecord | None = None
            if current_path.exists():
                current = self.load(record.reading_id)
                current_version = current.accepted.version
            expected = current_version + 1
            if record.version != expected:
                raise RuntimeError(
                    f"prepared reading version conflict: expected {expected}, got {record.version}"
                )
            if record.action == "continue" and current is not None:
                if not _same_base_facts(current, record):
                    raise RuntimeError("continuation changed base calculation")
            if (
                record.action == "correct"
                and record.parent_reading_id == record.reading_id
                and record.supersedes_version != current_version
            ):
                raise RuntimeError("correction supersedes the wrong current version")
            pending_path = reading_dir / "pending.json"
            if pending_path.exists():
                pending = self.load_prepared(record.reading_id)
                if pending.prepared_digest == record.prepared_digest:
                    return
                raise RuntimeError("a different prepared reading is already pending")
            rendered = (
                json.dumps(
                    record.to_dict(),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            history_path = prepared_dir / f"{record.version:06d}.json"
            if history_path.exists() and _read_private_text(history_path) != rendered:
                event_path = reading_dir / "events" / f"{record.version:06d}.json"
                if current_version >= record.version or event_path.exists():
                    raise RuntimeError(
                        f"immutable reading artifact conflict: {history_path.name}"
                    )
                # A prepared history file without pending.json was never published
                # to a caller and cannot have been committed. It is an interrupted
                # stage artifact, so replacing it is crash recovery rather than a
                # rewrite of accepted history.
                os.unlink(history_path)
                _fsync_directory(prepared_dir)
            _write_immutable(history_path, rendered)
            _atomic_replace(pending_path, rendered)
            _fsync_directory(reading_dir)

    @staticmethod
    def _render_record(record: ReadingRecord) -> str:
        return (
            json.dumps(
                record.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    def _repair_committed_artifacts(
        self,
        reading_dir: Path,
        record: ReadingRecord,
    ) -> None:
        version = record.accepted.version
        rendered = self._render_record(record)
        events_dir = reading_dir / "events"
        public_dir = reading_dir / "public"
        _ensure_private_directory(events_dir)
        _ensure_private_directory(public_dir)
        _write_immutable(events_dir / f"{version:06d}.json", rendered)
        _write_immutable(
            public_dir / f"{version:06d}.txt",
            record.accepted.public_copy,
        )

    def _repair_public_alias(self, reading_dir: Path, public_copy: str) -> None:
        path = reading_dir / "public.txt"
        try:
            if not path.exists() or _read_private_text(path) != public_copy:
                _atomic_replace(path, public_copy)
        except OSError:
            # current.json is the commit point; this compatibility copy is derived.
            return

    def load_committed(
        self,
        reading_id: str,
        prepared_digest: str,
    ) -> ReadingRecord | None:
        reading_dir = self._reading_dir(reading_id)
        current_path = reading_dir / "current.json"
        if not current_path.exists():
            return None
        with _exclusive_lock(reading_dir / ".lock"):
            current = self.load(reading_id)
            if current.accepted.prepared_digest == prepared_digest:
                self._repair_committed_artifacts(reading_dir, current)
                pending_path = reading_dir / "pending.json"
                if pending_path.exists():
                    pending = self.load_prepared(reading_id)
                    if pending.prepared_digest == prepared_digest:
                        os.unlink(pending_path)
                        _fsync_directory(reading_dir)
                self._repair_public_alias(reading_dir, current.accepted.public_copy)
                return current

            events_dir = reading_dir / "events"
            for version in range(1, current.accepted.version):
                path = events_dir / f"{version:06d}.json"
                if not path.exists():
                    raise RuntimeError("committed reading history is incomplete")
                payload = json.loads(_read_private_text(path))
                candidate = ReadingRecord.from_dict(payload)
                if candidate.accepted.prepared_digest == prepared_digest:
                    return candidate
            return None

    def commit(self, record: ReadingRecord) -> ReadingRecord:
        record = ReadingRecord.from_dict(record.to_dict())
        reading_id = record.accepted.reading_id
        reading_dir = self._reading_dir(reading_id)
        events_dir = reading_dir / "events"
        public_dir = reading_dir / "public"
        _ensure_private_directory(events_dir)
        _ensure_private_directory(public_dir)
        with _exclusive_lock(reading_dir / ".lock"):
            current_path = reading_dir / "current.json"
            current_version = 0
            if current_path.exists():
                current = self.load(reading_id)
                if current.accepted.prepared_digest == record.accepted.prepared_digest:
                    self._repair_committed_artifacts(reading_dir, current)
                    pending_path = reading_dir / "pending.json"
                    if pending_path.exists():
                        pending = self.load_prepared(reading_id)
                        if pending.prepared_digest == record.accepted.prepared_digest:
                            os.unlink(pending_path)
                            _fsync_directory(reading_dir)
                    self._repair_public_alias(
                        reading_dir,
                        current.accepted.public_copy,
                    )
                    return current
                current_version = current.accepted.version
            expected = current_version + 1
            if record.accepted.version != expected:
                raise RuntimeError(
                    f"reading version conflict: expected {expected}, got {record.accepted.version}"
                )
            pending_path = reading_dir / "pending.json"
            if not pending_path.exists():
                raise RuntimeError("accepted reading has no pending preparation")
            pending = self.load_prepared(reading_id)
            if pending.version != record.accepted.version:
                raise RuntimeError("prepared and accepted versions differ")
            if record.accepted.prepared_digest != pending.prepared_digest:
                raise RuntimeError("accepted reading is not bound to pending digest")
            rendered = self._render_record(record)
            event_path = events_dir / f"{expected:06d}.json"
            public_version_path = public_dir / f"{expected:06d}.txt"
            _write_immutable(event_path, rendered)
            _write_immutable(public_version_path, record.accepted.public_copy)
            _atomic_replace(current_path, rendered)
            os.unlink(pending_path)
            _fsync_directory(reading_dir)
            self._repair_public_alias(reading_dir, record.accepted.public_copy)
            return record
