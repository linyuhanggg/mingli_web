"""One opaque state token mapped to internal reading state.

Tokens are high-entropy random values handed to the host. Only their
SHA-256 lands on disk. The authoritative record is an append-only per-store
log written first; the per-hash index is a derived, repairable artifact and
never a second ledger. Write order follows the transaction contract:
authoritative log, fsync, derived index, fsync, then return the token.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import secrets
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal, TextIO

from .storage import _ensure_private_directory, _exclusive_lock

PHASES = ("pending_input", "prepared", "accepted")

_LOG_NAME = "token-log.jsonl"
_INDEX_DIR = "index"


class TokenConflict(ValueError):
    """A stale parent tried to seat a second, different child."""


@dataclass(frozen=True)
class TokenRecord:
    token_hash: str
    reading_id: str
    version: int
    phase: Literal["pending_input", "prepared", "accepted"]
    parent_token_hash: str | None = None
    commit_ref: str | None = None
    intake_id: str | None = None
    request_digest: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "token_hash": self.token_hash,
            "reading_id": self.reading_id,
            "version": self.version,
            "phase": self.phase,
            "parent_token_hash": self.parent_token_hash,
            "commit_ref": self.commit_ref,
            "intake_id": self.intake_id,
            "request_digest": self.request_digest,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "TokenRecord":
        return cls(
            token_hash=str(payload["token_hash"]),
            reading_id=str(payload["reading_id"]),
            version=int(payload["version"]),
            phase=str(payload["phase"]),  # type: ignore[arg-type]
            parent_token_hash=(
                None
                if payload.get("parent_token_hash") is None
                else str(payload["parent_token_hash"])
            ),
            commit_ref=(
                None
                if payload.get("commit_ref") is None
                else str(payload["commit_ref"])
            ),
            intake_id=(
                None
                if payload.get("intake_id") is None
                else str(payload["intake_id"])
            ),
            request_digest=(
                None
                if payload.get("request_digest") is None
                else str(payload["request_digest"])
            ),
        )


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _append_log_line(log_path: Path, payload: dict[str, object]) -> None:
    """Append one immutable log line through a private, non-following fd.

    ``Path.exists()`` is False for a broken symlink, so a plain ``open(..., "a")``
    would follow the link and create or modify an external victim.  The append
    is done with ``os.open`` under ``O_APPEND | O_CREAT | O_WRONLY`` plus
    ``O_NOFOLLOW`` where the platform provides it; the returned fd is verified
    to be a regular file owned by the current user before anything is written,
    the file is kept at 0600, and flush/fsync happen before returning.
    """

    if not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("safe no-follow token writes are unavailable")
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    descriptor = os.open(log_path, flags, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError(
                f"refusing to append through a non-private log file: {log_path}"
            )
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    _fsync_directory(log_path.parent)


@contextmanager
def _open_private_text(path: Path) -> Iterator[TextIO]:
    """Open one private regular file without following a symlink."""

    if not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("safe no-follow token reads are unavailable")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError(f"refusing to read through symlink: {path}") from exc
        raise
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise RuntimeError(f"unsafe token store file: {path}")
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            yield handle
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_private_json(path: Path) -> dict[str, object]:
    with _open_private_text(path) as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"invalid token store record: {path}")
    return payload


def _atomic_private_write(path: Path, content: str) -> None:
    """Atomically write ``content`` to ``path`` as a private regular file.

    Uses a random temporary file opened with O_NOFOLLOW, verifies the fd is
    a regular file owned by the current user, writes at 0600, fsyncs, then
    replaces.  This defeats a pre-placed symlink at the fixed .tmp name and
    keeps the final file private.
    """

    import tempfile

    if path.exists():
        _ensure_regular_private_file(path)
    directory = path.parent
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(directory)
    )
    try:
        os.fchmod(descriptor, 0o600)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("refusing to write through a non-private fd")
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        os.chmod(path, 0o600)
        _fsync_directory(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary_name)
        except OSError:
            pass


def _write_index_entry(index_dir: Path, record: TokenRecord) -> None:
    # Re-verify the private-directory seam before every write: the index may
    # have been replaced by a symlink to an external directory since it was
    # last validated, and a derived index write must never follow it out of
    # the store root.
    _ensure_private_directory(index_dir)
    path = index_dir / f"{record.token_hash}.json"
    _atomic_private_write(
        path,
        json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True),
    )


def _ensure_regular_private_file(path: Path) -> None:
    """Refuse to append to a symlink or a non-regular private file."""

    if path.is_symlink():
        raise ValueError(f"refusing to write through symlink: {path}")
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode):
        raise ValueError(f"refusing to write non-regular file: {path}")
    if path.stat().st_uid != os.getuid():
        raise ValueError(f"refusing to write foreign-owned file: {path}")


class StateTokenStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        _ensure_private_directory(self.root)
        self._log_path = self.root / _LOG_NAME
        self._index_dir = self.root / _INDEX_DIR
        _ensure_private_directory(self._index_dir)

    # -- issue / resolve -------------------------------------------------

    def issue(
        self,
        *,
        reading_id: str,
        version: int,
        phase: str,
        parent_token: str | None = None,
        intake_id: str | None = None,
        request_digest: str | None = None,
    ) -> str:
        if phase not in PHASES:
            raise ValueError(f"unknown token phase: {phase!r}")
        token = secrets.token_urlsafe(32)
        record = TokenRecord(
            token_hash=token_hash(token),
            reading_id=str(reading_id),
            version=int(version),
            phase=phase,  # type: ignore[arg-type]
            parent_token_hash=(
                token_hash(parent_token) if parent_token else None
            ),
            intake_id=intake_id,
            request_digest=request_digest,
        )
        # 1) authoritative append-only log, 2) derived per-hash index.
        _append_log_line(
            self._log_path, {"event": "issue", **record.to_dict()}
        )
        _write_index_entry(self._index_dir, record)
        return token

    def resolve(self, token: str) -> TokenRecord | None:
        try:
            digest = token_hash(token)
        except UnicodeEncodeError:
            return None
        record = self._read_index(digest)
        if record is not None:
            return record
        # Derived index may be lost or stale; repair from the log.
        self.rebuild_index()
        return self._read_index(digest)

    # -- state transitions ------------------------------------------------

    def mark_accepted(self, token: str, *, commit_ref: str) -> str:
        """First commit wins; replays return the original commit reference."""

        record = self.resolve(token)
        if record is None:
            raise ValueError("unknown state token")
        if record.phase == "accepted" and record.commit_ref:
            return record.commit_ref
        updated = TokenRecord(
            token_hash=record.token_hash,
            reading_id=record.reading_id,
            version=record.version,
            phase="accepted",
            parent_token_hash=record.parent_token_hash,
            commit_ref=str(commit_ref),
            intake_id=record.intake_id,
            request_digest=record.request_digest,
        )
        _append_log_line(
            self._log_path, {"event": "accept", **updated.to_dict()}
        )
        _write_index_entry(self._index_dir, updated)
        return updated.commit_ref or str(commit_ref)

    def promote_to_prepared(
        self,
        token: str,
        *,
        reading_id: str,
        version: int,
        request_digest: str,
    ) -> str:
        """Atomically advance a pending intake token to the prepared phase.

        The host already holds the pending token string; re-issuing a new
        prepared token would leave the old one dangling and break resume
        idempotency (two resumes mint two sibling prepared tokens, only one
        of which can ever commit).  Promoting the same token in place keeps
        one identity for the whole pending->prepared->accepted lifecycle, so
        a lost/double resume converges on the same prepared result.
        """

        record = self.resolve(token)
        if record is None:
            raise ValueError("unknown state token")
        if record.phase != "pending_input":
            raise ValueError(
                f"cannot promote a {record.phase} token to prepared"
            )
        updated = TokenRecord(
            token_hash=record.token_hash,
            reading_id=str(reading_id),
            version=int(version),
            phase="prepared",
            parent_token_hash=record.parent_token_hash,
            commit_ref=None,
            intake_id=record.intake_id,
            request_digest=request_digest,
        )
        _append_log_line(
            self._log_path,
            {"event": "promote", **updated.to_dict()},
        )
        _write_index_entry(self._index_dir, updated)
        return token

    def lineage_claim(self, parent_token: str) -> dict[str, object] | None:
        parent = self.resolve(parent_token)
        if parent is None:
            return None
        claim_path = self._index_dir / f"lineage-{parent.token_hash}.json"
        try:
            return _read_private_json(claim_path)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            return None

    @contextmanager
    def advance_lock(self, parent_token: str) -> Iterator[None]:
        """Serialize one accepted parent's prepare/replay decision."""

        parent = self.resolve(parent_token)
        if parent is None:
            raise ValueError("unknown parent state token")
        with _exclusive_lock(
            self._index_dir / f".advance-{parent.token_hash}.lock"
        ):
            yield

    def claim_lineage(
        self,
        parent_token: str,
        child_token: str,
        *,
        request_digest: str | None = None,
        child_reading_id: str | None = None,
    ) -> str:
        """Seat one child under an accepted parent; late rivals conflict.

        Replaying the same canonical turn after a lost response may rotate
        the child token; a different turn on the same parent conflicts.
        """

        parent = self.resolve(parent_token)
        if parent is None:
            raise ValueError("unknown parent state token")
        child_digest = token_hash(child_token)
        claim_path = self._index_dir / f"lineage-{parent.token_hash}.json"
        payload = {
            "event": "claim",
            "parent_token_hash": parent.token_hash,
            "child_token_hash": child_digest,
            "request_digest": request_digest,
            "child_reading_id": child_reading_id,
        }
        # The exists->write sequence must be atomic: concurrent rivals racing
        # for the same parent must yield exactly one winner.  Re-verify the
        # index directory before touching claim/lock files so a replaced index
        # symlink can never redirect the lineage write outside the store.
        _ensure_private_directory(self._index_dir)
        with _exclusive_lock(
            self._index_dir / f".lineage-{parent.token_hash}.lock"
        ):
            try:
                existing = _read_private_json(claim_path)
            except FileNotFoundError:
                existing = None
            if existing is not None:
                if str(existing.get("child_token_hash")) == child_digest:
                    return "replay"
                if (
                    request_digest is not None
                    and existing.get("request_digest") == request_digest
                ):
                    if (
                        child_reading_id is not None
                        and existing.get("child_reading_id") != child_reading_id
                    ):
                        raise TokenConflict(
                            "the same turn resolved to a different reading"
                        )
                    return "rotated"
                raise TokenConflict(
                    "this reading already advanced to a newer version"
                )
            _append_log_line(self._log_path, payload)
            _atomic_private_write(
                claim_path,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
            )
            _fsync_directory(self._index_dir)
            return "won"

    # -- derived index repair ----------------------------------------------

    def rebuild_index(self) -> None:
        # Re-verify the index directory through the private-directory seam
        # before rebuilding: a plain ``mkdir(exist_ok=True)`` would leave a
        # umask-dependent 0755 directory and would silently follow a replaced
        # symlink out of the store.
        _ensure_private_directory(self._index_dir)
        latest: dict[str, TokenRecord] = {}
        claims: dict[str, dict[str, object]] = {}
        try:
            with _open_private_text(self._log_path) as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    event = payload.get("event")
                    if event in {"issue", "accept", "promote"}:
                        record = TokenRecord.from_dict(payload)
                        latest[record.token_hash] = record
                    elif event == "claim":
                        claims[str(payload["parent_token_hash"])] = payload
        except FileNotFoundError:
            return
        for record in latest.values():
            _write_index_entry(self._index_dir, record)
        for parent_hash, payload in claims.items():
            claim_path = self._index_dir / f"lineage-{parent_hash}.json"
            _atomic_private_write(
                claim_path,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
            )
        _fsync_directory(self._index_dir)

    def _read_index(self, digest: str) -> TokenRecord | None:
        path = self._index_dir / f"{digest}.json"
        try:
            payload = _read_private_json(path)
            return TokenRecord.from_dict(payload)
        except (
            FileNotFoundError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return None


__all__ = [
    "PHASES",
    "StateTokenStore",
    "TokenConflict",
    "TokenRecord",
    "token_hash",
]
