#!/usr/bin/env python3
"""Deploy one hash-bound Mingli release to local Codex and Hermes installs."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import secrets
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator, Mapping, TextIO


MANIFEST_NAME = ".mingli-release-manifest.json"
RUNTIME_CLOSURE_RELATIVE = "release/runtime-closure-v1.json"
RUNTIME_CLOSURE_SCHEMA = "mingli-runtime-closure-v1"
PRESERVE_PREFIXES = (
    ".git",
    ".venv",
    ".benchmarks",
    "references/fulltext",
)
PROTECTION_EXCLUDES = (".git", ".venv", ".benchmarks")
SOURCE_VERIFICATION_TIMEOUT_SECONDS = 60 * 60
SOURCE_VERIFICATION_MAX_JOBS = 4
SOURCE_VERIFICATION_PROGRESS_PREFIX = "MINGLI_SOURCE_VERIFY "
SOURCE_VERIFICATION_TERMINATE_GRACE_SECONDS = 2.0
SOURCE_VERIFICATION_REGISTRY_RELATIVE = (
    "scripts/audit_provider_completeness.py"
)
SOURCE_VERIFICATION_AUDIT_PATTERN = "scripts/audit_*_provider.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(raw: str) -> str:
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe release path: {raw!r}")
    return path.as_posix()


def _matches_prefix(relative: str, prefixes: Iterable[str]) -> bool:
    return any(relative == prefix or relative.startswith(f"{prefix}/") for prefix in prefixes)


def _safe_release_pattern(raw: object) -> str:
    if not isinstance(raw, str) or not raw:
        raise ValueError("runtime closure pattern must be non-empty text")
    if "\\" in raw:
        raise ValueError(f"unsafe runtime closure pattern: {raw!r}")
    path = PurePosixPath(raw)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or not any(token in raw for token in ("*", "?", "["))
    ):
        raise ValueError(f"unsafe runtime closure pattern: {raw!r}")
    return path.as_posix()


def _git_scope(source: Path) -> tuple[Path, str]:
    """Return (repo_root, posix prefix of source inside the repo).

    prefix is empty when source is the git root; otherwise it ends with '/'.
    The source may be a subdirectory of a parent repository.
    """

    root = Path(
        subprocess.run(
            ["git", "-C", str(source), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    prefix = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "--show-prefix"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    return root, prefix


def _git_tracked_paths(source: Path) -> set[str]:
    result = subprocess.run(
        ["git", "-C", str(source), "ls-files", "-z", "--", "."],
        check=True,
        capture_output=True,
    )
    return {
        _safe_relative_path(item.decode("utf-8"))
        for item in result.stdout.split(b"\0")
        if item
    }


def _repo_relative_pathspecs(
    source: Path,
    source_pathspecs: Iterable[str],
) -> list[str]:
    _, prefix = _git_scope(source)
    specs: list[str] = []
    for raw in source_pathspecs:
        spec = PurePosixPath(str(raw)).as_posix().lstrip("/")
        if not spec or spec.startswith("/") or ".." in PurePosixPath(spec).parts:
            raise ValueError(f"unsafe release path: {raw!r}")
        specs.append(f"{prefix}{spec}" if prefix else spec)
    return specs


def extra_gate_pathspecs(source: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Gate scripts that must be committed with the release, even if not shipped."""

    source_extras = [
        relative
        for relative in ("scripts/release_deploy.py", "scripts/test_release_deploy.py")
        if (source / relative).is_file()
    ]
    tracked = _git_tracked_paths(source)
    if SOURCE_VERIFICATION_REGISTRY_RELATIVE not in tracked:
        raise ValueError("source verification registry is not tracked")
    dedicated_audits = sorted(
        relative
        for relative in tracked
        if PurePosixPath(relative).match(
            SOURCE_VERIFICATION_AUDIT_PATTERN
        )
    )
    if not dedicated_audits:
        raise ValueError("dedicated provider audits are not tracked")
    source_extras.extend(
        [SOURCE_VERIFICATION_REGISTRY_RELATIVE, *dedicated_audits]
    )
    repo_root, _prefix = _git_scope(source)
    repo_extras = tuple(
        relative
        for relative in ("scripts/check_mingli_core_workspace.py",)
        if (repo_root / relative).is_file()
    )
    return tuple(dict.fromkeys(source_extras)), repo_extras


def _runtime_closure(
    source: Path,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    closure_path = source / RUNTIME_CLOSURE_RELATIVE
    if closure_path.is_symlink() or not closure_path.is_file():
        raise ValueError("runtime closure file is missing or unsafe")
    try:
        payload = json.loads(closure_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("runtime closure file is invalid") from exc
    required_keys = {
        "schema_version",
        "files",
        "patterns",
    }
    allowed_keys = required_keys | {"excluded_files"}
    if (
        not isinstance(payload, dict)
        or not required_keys <= set(payload)
        or not set(payload) <= allowed_keys
    ):
        raise ValueError("runtime closure schema is invalid")
    if payload.get("schema_version") != RUNTIME_CLOSURE_SCHEMA:
        raise ValueError("runtime closure schema_version is invalid")
    raw_files = payload.get("files")
    raw_patterns = payload.get("patterns")
    raw_excluded_files = payload.get("excluded_files", [])
    if (
        not isinstance(raw_files, list)
        or not isinstance(raw_patterns, list)
        or not isinstance(raw_excluded_files, list)
    ):
        raise ValueError(
            "runtime closure files, patterns and excluded_files must be lists"
        )
    try:
        files = tuple(_safe_relative_path(item) for item in raw_files)
        patterns = tuple(_safe_release_pattern(item) for item in raw_patterns)
        excluded_files = tuple(
            _safe_relative_path(item) for item in raw_excluded_files
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("runtime closure contains an unsafe path") from exc
    if not files or len(files) != len(set(files)):
        raise ValueError("runtime closure files must be non-empty and unique")
    if len(patterns) != len(set(patterns)):
        raise ValueError("runtime closure patterns must be unique")
    if len(excluded_files) != len(set(excluded_files)):
        raise ValueError("runtime closure excluded_files must be unique")
    if set(files) & set(excluded_files):
        raise ValueError(
            "runtime closure files and excluded_files must not overlap"
        )
    if RUNTIME_CLOSURE_RELATIVE not in files:
        raise ValueError("runtime closure must include itself")
    return files, patterns, excluded_files


def tracked_release_files(source: Path) -> list[str]:
    """Return the explicit production closure, never a broad repository copy.

    The closure declaration is intentionally tracked with the release.  This
    keeps historical plans, tests, host-specific metadata and developer tools
    out of an installed Skill unless a runtime dependency is deliberately
    added to the one allow-list.
    """

    tracked = _git_tracked_paths(source)
    files, patterns, excluded_files = _runtime_closure(source)
    untracked = sorted((set(files) | set(excluded_files)) - tracked)
    if untracked:
        raise ValueError(
            "runtime closure references a path that is not tracked: "
            + ", ".join(untracked)
        )

    selected = set(files)
    for pattern in patterns:
        matches = {
            path for path in tracked if PurePosixPath(path).match(pattern)
        }
        if not matches:
            raise ValueError(
                f"runtime closure pattern matches no tracked paths: {pattern}"
            )
        selected.update(matches)
    unmatched_exclusions = sorted(set(excluded_files) - selected)
    if unmatched_exclusions:
        raise ValueError(
            "runtime closure excludes paths outside its selected surface: "
            + ", ".join(unmatched_exclusions)
        )
    selected.difference_update(excluded_files)
    return sorted(selected)


def source_commit(source: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def require_clean_source(
    source: Path,
    pathspecs: Iterable[str] | None = None,
    extra_repo_pathspecs: Iterable[str] = (),
) -> None:
    """Fail if the selected source paths (not the whole parent tree) are dirty.

    When pathspecs is omitted, the entire source prefix is checked. Callers that
    ship a runtime closure should pass those files plus extra_gate_pathspecs so
    unrelated dirty files in the source tree do not block a faithful sign.
    """

    repo_root, prefix = _git_scope(source)
    specs: list[str] = []
    if pathspecs is None:
        specs.append(prefix.rstrip("/") if prefix else ".")
    else:
        specs.extend(_repo_relative_pathspecs(source, pathspecs))
    for raw in extra_repo_pathspecs:
        spec = PurePosixPath(str(raw)).as_posix().lstrip("/")
        if not spec or spec.startswith("/") or ".." in PurePosixPath(spec).parts:
            raise ValueError(f"unsafe release path: {raw!r}")
        specs.append(spec)
    if not specs:
        raise ValueError("source worktree must be clean before deployment")
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *specs,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        raise ValueError("source worktree must be clean before deployment")


def build_manifest(
    source: Path,
    relative_paths: Iterable[str],
    commit: str,
    *,
    committed_modes: Mapping[str, int] | None = None,
) -> dict:
    files: dict[str, str] = {}
    modes: dict[str, int] = {}
    for raw in sorted(relative_paths):
        relative = _safe_relative_path(raw)
        path = source / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"release file must be a regular file: {relative}")
        files[relative] = _sha256(path)
        modes[relative] = (
            int(committed_modes[relative])
            if committed_modes is not None
            else stat.S_IMODE(path.stat().st_mode)
        )
    return {
        "schema_version": 3,
        "release": "mingli-master-portable-core",
        "source_commit": commit,
        "files": files,
        "modes": modes,
    }


def committed_release_modes(
    source: Path,
    relative_paths: Iterable[str],
    commit: str,
) -> dict[str, int]:
    expected = {_safe_relative_path(path) for path in relative_paths}
    _, prefix = _git_scope(source)
    result = subprocess.run(
        ["git", "-C", str(source), "ls-tree", "-rz", "--full-tree", "-r", commit],
        check=True,
        capture_output=True,
    )
    modes: dict[str, int] = {}
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        metadata, encoded_path = raw.split(b"\t", 1)
        git_mode, object_type, _ = metadata.split(b" ", 2)
        relative = encoded_path.decode("utf-8")
        if prefix:
            if not relative.startswith(prefix):
                continue
            relative = relative[len(prefix) :]
        if relative not in expected:
            continue
        if object_type != b"blob" or git_mode not in {b"100644", b"100755"}:
            raise ValueError(f"unsupported committed release mode: {relative}")
        modes[relative] = 0o755 if git_mode == b"100755" else 0o644
    missing = sorted(expected - set(modes))
    if missing:
        raise ValueError(
            "release files missing from committed tree: " + ", ".join(missing)
        )
    return modes


def build_committed_manifest(
    source: Path,
    relative_paths: Iterable[str],
    commit: str,
) -> dict:
    paths = list(relative_paths)
    return build_manifest(
        source,
        paths,
        commit,
        committed_modes=committed_release_modes(source, paths, commit),
    )


def validate_destination_layout(destination: Path) -> None:
    """Reject links that could redirect release writes outside the install root."""
    if destination.is_symlink():
        raise ValueError(f"destination must not be a symbolic link: {destination}")
    if not destination.exists():
        return
    for root, directories, filenames in os.walk(
        destination,
        topdown=True,
        followlinks=False,
    ):
        root_path = Path(root)
        for name in (*directories, *filenames):
            child = root_path / name
            if child.is_symlink():
                relative = child.relative_to(destination).as_posix()
                raise ValueError(
                    f"destination contains a symbolic link: {relative}"
                )


class _SafeDestination:
    """Write beneath one pinned, no-follow destination directory handle."""

    def __init__(self, destination: Path) -> None:
        self.destination = destination
        self.root_fd: int | None = None

    def __enter__(self) -> "_SafeDestination":
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            self.root_fd = os.open(self.destination, flags)
        except OSError as exc:
            raise ValueError(
                f"destination cannot be opened without following links: {self.destination}"
            ) from exc
        if not stat.S_ISDIR(os.fstat(self.root_fd).st_mode):
            self.close()
            raise ValueError(f"destination is not a directory: {self.destination}")
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close(self) -> None:
        if self.root_fd is not None:
            os.close(self.root_fd)
            self.root_fd = None

    def _open_parent(self, relative: str, *, create: bool) -> tuple[int, str]:
        if self.root_fd is None:
            raise RuntimeError("destination handle is closed")
        parts = PurePosixPath(_safe_relative_path(relative)).parts
        current = os.dup(self.root_fd)
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            for part in parts[:-1]:
                try:
                    child = os.open(part, flags, dir_fd=current)
                except FileNotFoundError:
                    if not create:
                        raise
                    os.mkdir(part, mode=0o755, dir_fd=current)
                    child = os.open(part, flags, dir_fd=current)
                os.close(current)
                current = child
            return current, parts[-1]
        except BaseException:
            os.close(current)
            raise

    def write_from(self, source: Path, relative: str, mode: int) -> None:
        parent_fd, leaf = self._open_parent(relative, create=True)
        temporary = f".{leaf}.mingli-{os.getpid()}-{secrets.token_hex(6)}"
        descriptor: int | None = None
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                mode,
                dir_fd=parent_fd,
            )
            with source.open("rb") as source_handle, os.fdopen(descriptor, "wb") as target:
                descriptor = None
                shutil.copyfileobj(source_handle, target, length=1024 * 1024)
                target.flush()
                os.fchmod(target.fileno(), mode)
                os.fsync(target.fileno())
            os.replace(
                temporary,
                leaf,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
            os.close(parent_fd)

    def write_bytes(self, relative: str, content: bytes, mode: int = 0o600) -> None:
        descriptor, temporary = tempfile.mkstemp(prefix=".mingli-bytes-", dir=self.destination.parent)
        source = Path(temporary)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            self.write_from(source, relative, mode)
        finally:
            source.unlink(missing_ok=True)

    def copy_out(self, relative: str, target: Path) -> None:
        parent_fd, leaf = self._open_parent(relative, create=False)
        descriptor: int | None = None
        try:
            descriptor = os.open(
                leaf,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
            file_stat = os.fstat(descriptor)
            if not stat.S_ISREG(file_stat.st_mode):
                raise ValueError(f"managed path is not a regular file: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with os.fdopen(descriptor, "rb") as source_handle, target.open("wb") as output:
                descriptor = None
                shutil.copyfileobj(source_handle, output, length=1024 * 1024)
            target.chmod(stat.S_IMODE(file_stat.st_mode))
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(parent_fd)

    def unlink(self, relative: str) -> None:
        try:
            parent_fd, leaf = self._open_parent(relative, create=False)
        except FileNotFoundError:
            return
        try:
            try:
                os.unlink(leaf, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        finally:
            os.close(parent_fd)


def _copy_release_file(
    destination: _SafeDestination,
    source: Path,
    relative: str,
    mode: int,
) -> None:
    destination.write_from(source, relative, mode)


def _destination_files(destination: Path) -> list[str]:
    found: list[str] = []
    if not destination.exists():
        return found
    for root, directories, filenames in os.walk(destination, topdown=True, followlinks=False):
        root_path = Path(root)
        relative_root = root_path.relative_to(destination).as_posix()
        if relative_root == ".":
            relative_root = ""
        directories[:] = [
            name
            for name in directories
            if not _matches_prefix(
                f"{relative_root}/{name}".lstrip("/"), PRESERVE_PREFIXES
            )
        ]
        for name in filenames:
            relative = f"{relative_root}/{name}".lstrip("/")
            if relative != MANIFEST_NAME and not _matches_prefix(relative, PRESERVE_PREFIXES):
                found.append(relative)
    return sorted(found)


def _plan_sync(destination: Path, manifest: dict) -> tuple[list[str], list[str]]:
    expected = set(manifest["files"])
    copy: list[str] = []
    for relative, expected_hash in manifest["files"].items():
        path = destination / relative
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected_hash:
            copy.append(relative)
    remove = sorted(set(_destination_files(destination)) - expected)
    return copy, remove


def _remove_empty_unmanaged_directories(destination: Path) -> None:
    for root, directories, _ in os.walk(destination, topdown=False, followlinks=False):
        root_path = Path(root)
        relative = root_path.relative_to(destination).as_posix()
        if relative == "." or _matches_prefix(relative, PRESERVE_PREFIXES):
            continue
        for name in directories:
            child = root_path / name
            child_relative = child.relative_to(destination).as_posix()
            if _matches_prefix(child_relative, PRESERVE_PREFIXES) or child.is_symlink():
                continue
            try:
                child.rmdir()
            except OSError:
                pass


def _manifest_bytes(manifest: dict) -> bytes:
    return (json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def verify_destination(destination: Path, manifest: dict) -> None:
    validate_destination_layout(destination)
    for relative, expected_hash in manifest["files"].items():
        path = destination / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing release file: {relative}")
        actual_hash = _sha256(path)
        if actual_hash != expected_hash:
            raise ValueError(f"hash mismatch: {relative}")
        expected_mode = int(manifest.get("modes", {}).get(relative, -1))
        actual_mode = stat.S_IMODE(path.stat().st_mode)
        if actual_mode != expected_mode:
            raise ValueError(
                f"mode mismatch: {relative} expected {expected_mode:o}, got {actual_mode:o}"
            )

    extras = sorted(set(_destination_files(destination)) - set(manifest["files"]))
    if extras:
        raise ValueError(f"unexpected release files: {', '.join(extras)}")

    manifest_path = destination / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.read_bytes() != _manifest_bytes(manifest):
        raise ValueError("installed release manifest mismatch")


def _copy_managed_snapshot(
    destination: Path,
    backup: Path,
    handle: _SafeDestination,
) -> tuple[list[str], bool]:
    previous = _destination_files(destination)
    for relative in previous:
        target = backup / relative
        handle.copy_out(relative, target)
    manifest_path = destination / MANIFEST_NAME
    had_manifest = manifest_path.is_file()
    if had_manifest:
        handle.copy_out(MANIFEST_NAME, backup / MANIFEST_NAME)
    return previous, had_manifest


def _restore_managed_snapshot(
    destination: Path,
    backup: Path,
    previous: Iterable[str],
    had_manifest: bool,
    handle: _SafeDestination,
) -> None:
    for relative in _destination_files(destination):
        handle.unlink(relative)
    handle.unlink(MANIFEST_NAME)
    _remove_empty_unmanaged_directories(destination)
    for relative in previous:
        source = backup / relative
        _copy_release_file(
            handle,
            source,
            relative,
            stat.S_IMODE(source.stat().st_mode),
        )
    if had_manifest:
        handle.write_from(
            backup / MANIFEST_NAME,
            MANIFEST_NAME,
            stat.S_IMODE((backup / MANIFEST_NAME).stat().st_mode),
        )


def _write_manifest_atomic(destination: _SafeDestination, manifest: dict) -> None:
    destination.write_bytes(MANIFEST_NAME, _manifest_bytes(manifest))


def sync_destination(
    source: Path,
    destination: Path,
    manifest: dict,
    *,
    apply: bool,
) -> dict:
    validate_destination_layout(destination)
    copy, remove = _plan_sync(destination, manifest)
    result = {"destination": str(destination), "copy": copy, "remove": remove, "verified": False}
    if not apply:
        return result

    destination.mkdir(parents=True, exist_ok=True)
    validate_destination_layout(destination)
    with _SafeDestination(destination) as handle:
        with tempfile.TemporaryDirectory(
            prefix=".mingli-deploy-backup-",
            dir=destination.parent,
        ) as temporary:
            backup = Path(temporary)
            previous, had_manifest = _copy_managed_snapshot(
                destination,
                backup,
                handle,
            )
            try:
                for relative in remove:
                    handle.unlink(relative)
                _remove_empty_unmanaged_directories(destination)

                for relative in manifest["files"]:
                    _copy_release_file(
                        handle,
                        source / relative,
                        relative,
                        int(manifest["modes"][relative]),
                    )

                _write_manifest_atomic(handle, manifest)
                verify_destination(destination, manifest)
            except BaseException as exc:
                try:
                    _restore_managed_snapshot(
                        destination,
                        backup,
                        previous,
                        had_manifest,
                        handle,
                    )
                except BaseException as rollback_error:
                    exc.add_note(
                        "deployment rollback also failed: "
                        f"{type(rollback_error).__name__}: {rollback_error}"
                    )
                raise
    result["verified"] = True
    return result


def _protection_paths(destination: Path) -> list[Path]:
    paths: list[Path] = []
    if not destination.exists():
        return paths
    for root, directories, filenames in os.walk(destination, topdown=True, followlinks=False):
        root_path = Path(root)
        relative_root = root_path.relative_to(destination).as_posix()
        if relative_root == ".":
            relative_root = ""
        directories[:] = [
            name
            for name in directories
            if not _matches_prefix(
                f"{relative_root}/{name}".lstrip("/"), PROTECTION_EXCLUDES
            )
        ]
        if root_path != destination:
            paths.append(root_path)
        paths.extend(root_path / name for name in filenames)
    paths.sort(key=lambda path: len(path.parts), reverse=True)
    paths.append(destination)
    return paths


def _run_chflags(flag: str, paths: Iterable[Path]) -> None:
    executable = shutil.which("chflags")
    if not executable:
        raise RuntimeError("chflags is required for immutable deployment protection")
    batch: list[str] = []
    for path in paths:
        batch.append(str(path))
        if len(batch) == 100:
            subprocess.run([executable, flag, *batch], check=True)
            batch.clear()
    if batch:
        subprocess.run([executable, flag, *batch], check=True)


def unprotect_destination(destination: Path) -> None:
    if not destination.exists():
        return
    _run_chflags("nouchg", [destination])
    _run_chflags("nouchg", reversed(_protection_paths(destination)[:-1]))


def protect_destination(destination: Path) -> None:
    probe = destination / ".mingli-protection-probe"
    probe.unlink(missing_ok=True)
    _run_chflags("uchg", _protection_paths(destination))

    immutable_flag = getattr(stat, "UF_IMMUTABLE", 0x00000002)
    if not (destination.stat().st_flags & immutable_flag):
        raise RuntimeError(f"immutable flag missing on {destination}")
    try:
        probe.write_text("probe\n", encoding="utf-8")
    except OSError:
        pass
    else:
        probe.unlink(missing_ok=True)
        raise RuntimeError(f"immutable write probe unexpectedly succeeded: {destination}")


def destination_is_protected(destination: Path) -> bool:
    if not destination.exists():
        return False
    immutable_flag = getattr(stat, "UF_IMMUTABLE", 0x00000002)
    return bool(getattr(destination.stat(), "st_flags", 0) & immutable_flag)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="clean Git worktree containing the release",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        action="append",
        required=True,
        help="installed skill root; repeat for every Codex/Hermes profile",
    )
    parser.add_argument("--apply", action="store_true", help="perform the planned sync")
    parser.add_argument(
        "--protect",
        action="store_true",
        help="set macOS user-immutable flags after every destination verifies",
    )
    parser.add_argument(
        "--research-root",
        type=Path,
        default=None,
        help=(
            "explicit classical fulltext tree for release source verification; "
            "when omitted the release gate reports sources as unverified "
            "unless the environment already supplies MINGLI_RESEARCH_ROOT"
        ),
    )
    return parser.parse_args(argv)


def _deployment_destination(path: Path) -> Path:
    destination = path.expanduser()
    if not destination.is_absolute():
        destination = Path.cwd() / destination
    destination = destination.absolute()
    validate_destination_layout(destination)
    return destination


def _restore_destination_protection(
    destinations: Iterable[Path],
    protected_before: Mapping[Path, bool],
    force: bool,
) -> list[BaseException]:
    failures: list[BaseException] = []
    for destination in destinations:
        if not (force or protected_before[destination]):
            continue
        try:
            protect_destination(destination)
        except BaseException as exc:
            failures.append(exc)
    return failures


# Runs inside a fresh one-shot subprocess so the release gate is immune to
# the parent interpreter's sys.path, sys.modules and previously audited
# checkouts.  The process rebuilds its import path to the selected checkout's
# scripts directory and fails closed if any loaded audit module resolves
# outside it.
_VERIFY_SOURCE_SUBPROCESS = r"""
import concurrent.futures
import importlib
import inspect
import json
import multiprocessing
import os
import resource
import signal
import sys
import threading
import time
from pathlib import Path


PROGRESS_PREFIX = "MINGLI_SOURCE_VERIFY "
STARTED = time.monotonic()
STATE = {"provider": None, "stage": "subprocess_start"}
STOP_HEARTBEAT = threading.Event()


def _resource_snapshot():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    peak_rss_bytes = int(usage.ru_maxrss)
    if sys.platform != "darwin":
        peak_rss_bytes *= 1024
    return {
        "user_cpu_seconds": round(float(usage.ru_utime), 3),
        "system_cpu_seconds": round(float(usage.ru_stime), 3),
        "process_peak_rss_bytes": peak_rss_bytes,
    }


def _completed_metrics(provider_started, resource_before):
    resource_after = _resource_snapshot()
    return {
        "elapsed_seconds": round(time.monotonic() - provider_started, 3),
        "user_cpu_seconds": round(
            resource_after["user_cpu_seconds"]
            - resource_before["user_cpu_seconds"],
            3,
        ),
        "system_cpu_seconds": round(
            resource_after["system_cpu_seconds"]
            - resource_before["system_cpu_seconds"],
            3,
        ),
        "process_peak_rss_bytes_after": resource_after[
            "process_peak_rss_bytes"
        ],
    }


def _emit(event, **fields):
    payload = {
        "event": event,
        "elapsed_seconds": round(time.monotonic() - STARTED, 3),
        "pid": os.getpid(),
        **fields,
    }
    print(
        PROGRESS_PREFIX + json.dumps(payload, sort_keys=True),
        file=sys.stderr,
        flush=True,
    )


def _set_stage(provider, stage):
    STATE["provider"] = provider
    STATE["stage"] = stage


def _heartbeat():
    while not STOP_HEARTBEAT.wait(15.0):
        _emit(
            "heartbeat",
            provider=STATE["provider"],
            stage=STATE["stage"],
            resource=_resource_snapshot(),
        )


def _cancel(signum, _frame):
    _emit(
        "cancel_received",
        provider=STATE["provider"],
        stage=STATE["stage"],
        signal=signal.Signals(signum).name,
        resource=_resource_snapshot(),
    )
    raise SystemExit(128 + signum)


def _fail(message):
    STOP_HEARTBEAT.set()
    _emit(
        "subprocess_failed",
        provider=STATE["provider"],
        stage=STATE["stage"],
        failure=message,
        resource=_resource_snapshot(),
    )
    print(
        json.dumps(
            {
                "research_root": sys.argv[2] or None,
                "provider_source_verification": {},
                "provider_metrics": {},
                "verified": False,
                "failures": [message],
                "elapsed_seconds": round(time.monotonic() - STARTED, 3),
                "resource": _resource_snapshot(),
            }
        ),
        flush=True,
    )
    raise SystemExit(1)


signal.signal(signal.SIGINT, _cancel)
signal.signal(signal.SIGTERM, _cancel)
source = Path(sys.argv[1]).resolve()
research = sys.argv[2] or None
scripts_dir = source / "scripts"
_emit("subprocess_start", provider=None, stage="checkout_validation")
if not scripts_dir.is_dir():
    _fail(f"source checkout has no scripts directory: {scripts_dir}")

# A fresh interpreter has no parent audit modules cached.  Rebuild the import
# path so the checked-out scripts directory is the only place a provider
# audit can come from: never cwd, never an inherited PYTHONPATH.
os.environ.pop("PYTHONPATH", None)
os.environ.pop("MINGLI_RESEARCH_ROOT", None)
sys.path[:] = [str(scripts_dir)] + [
    p
    for p in sys.path
    if p and not str(Path(p).resolve()).endswith("scripts")
]

try:
    from audit_provider_completeness import DEDICATED_AUDIT_MODULES
except BaseException as exc:  # noqa: BLE001 - gate must fail closed
    _fail(f"source audit registry could not be loaded: {type(exc).__name__}")

provider_systems = sorted(DEDICATED_AUDIT_MODULES)
provider_audits = {
    system: module.__name__
    for system, module in DEDICATED_AUDIT_MODULES.items()
}
requested_jobs = int(sys.argv[3])
worker_count = min(requested_jobs, max(1, len(provider_systems)))
resolved_root = Path(research).resolve() if research else None
_emit(
    "registry_complete",
    provider=None,
    stage="audit_registry",
    provider_count=len(provider_systems),
    provider_jobs=worker_count,
)
scripts_resolved = scripts_dir.resolve()


def _run_provider(system, module_name, ordinal, provider_count):
    STOP_HEARTBEAT.clear()
    provider_started = time.monotonic()
    resource_before = _resource_snapshot()
    status = "error"
    provider_failures = []
    _set_stage(system, "audit_module_import")
    _emit(
        "provider_start",
        provider=system,
        stage="audit_module_import",
        audit_module=module_name,
        ordinal=ordinal,
        provider_count=provider_count,
    )
    heartbeat_thread = threading.Thread(
        target=_heartbeat,
        name=f"source-verification-heartbeat-{system}",
        daemon=True,
    )
    heartbeat_thread.start()
    try:
        try:
            module = importlib.import_module(module_name)
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as exc:  # noqa: BLE001 - gate must fail closed
            provider_failures.append(
                f"{system}: audit module import raised {type(exc).__name__}"
            )
        else:
            module_file = Path(getattr(module, "__file__", "")).resolve()
            if not module_file.is_relative_to(scripts_resolved):
                provider_failures.append(
                    f"{system}: audit module {module_name} resolves outside "
                    f"the source checkout: {module_file}"
                )
                _set_stage(system, "audit_module_origin")
            elif resolved_root is None:
                # With no research checkout there is nothing an audit can
                # prove about source fidelity.  Every registered audit is
                # still loaded from the selected checkout and origin-checked.
                status = "skipped"
                provider_failures.append(
                    f"{system}: source verification skipped; "
                    "pass --research-root"
                )
                _set_stage(system, "fulltext_gate")
            else:
                audit = getattr(module, module_name)
                _set_stage(system, "provider_fulltext_audit")
                _emit(
                    "provider_stage",
                    provider=system,
                    stage="provider_fulltext_audit",
                    audit_module=module_name,
                )
                try:
                    def audit_progress(substage, **details):
                        stage = f"provider_fulltext_audit:{substage}"
                        _set_stage(system, stage)
                        safe_details = {
                            str(key): value
                            for key, value in details.items()
                            if str(key) not in {"event", "provider", "stage"}
                        }
                        _emit(
                            "provider_substage",
                            provider=system,
                            stage=stage,
                            audit_module=module_name,
                            **safe_details,
                        )

                    audit_kwargs = {"research_root": resolved_root}
                    if "progress" in inspect.signature(audit).parameters:
                        audit_kwargs["progress"] = audit_progress
                    report = audit(**audit_kwargs)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except BaseException as exc:  # noqa: BLE001 - fail closed
                    provider_failures.append(
                        f"{system}: source verification raised "
                        f"{type(exc).__name__}"
                    )
                else:
                    status = str(
                        (report.get("source_verification") or {}).get("status")
                        or "skipped"
                    )
                    if status != "verified":
                        provider_failures.append(
                            f"{system}: source verification {status}"
                        )
    finally:
        STOP_HEARTBEAT.set()
        heartbeat_thread.join(timeout=1.0)
    metrics = _completed_metrics(provider_started, resource_before)
    metrics["pid"] = os.getpid()
    _emit(
        "provider_complete",
        provider=system,
        stage=STATE["stage"],
        status=status,
        metrics=metrics,
    )
    return {
        "provider": system,
        "status": status,
        "failures": provider_failures,
        "metrics": metrics,
    }


results = {}
provider_metrics = {}
failures = []
_set_stage(None, "provider_pool")
_emit(
    "provider_pool_start",
    provider=None,
    stage="provider_pool",
    provider_count=len(provider_systems),
    provider_jobs=worker_count,
)
fork_context = multiprocessing.get_context("fork")
with concurrent.futures.ProcessPoolExecutor(
    max_workers=worker_count,
    mp_context=fork_context,
) as executor:
    futures = {
        executor.submit(
            _run_provider,
            system,
            provider_audits[system],
            ordinal,
            len(provider_systems),
        ): system
        for ordinal, system in enumerate(provider_systems, start=1)
    }
    for future in concurrent.futures.as_completed(futures):
        system = futures[future]
        try:
            outcome = future.result()
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as exc:  # noqa: BLE001 - gate must fail closed
            results[system] = "error"
            failures.append(
                f"{system}: source verification worker raised "
                f"{type(exc).__name__}"
            )
            continue
        results[system] = outcome["status"]
        failures.extend(outcome["failures"])
        provider_metrics[system] = outcome["metrics"]

results = dict(sorted(results.items()))
provider_metrics = dict(sorted(provider_metrics.items()))
failures.sort()

_set_stage(None, "report")
elapsed_seconds = round(time.monotonic() - STARTED, 3)
resource_usage = _resource_snapshot()
worker_peaks = {}
for metrics in provider_metrics.values():
    worker_pid = str(metrics["pid"])
    worker_peaks[worker_pid] = max(
        worker_peaks.get(worker_pid, 0),
        metrics["process_peak_rss_bytes_after"],
    )
resource_usage.update(
    {
        "worker_process_count": len(worker_peaks),
        "worker_user_cpu_seconds": round(
            sum(item["user_cpu_seconds"] for item in provider_metrics.values()),
            3,
        ),
        "worker_system_cpu_seconds": round(
            sum(item["system_cpu_seconds"] for item in provider_metrics.values()),
            3,
        ),
        "worker_peak_rss_bytes_max": max(worker_peaks.values(), default=0),
        "parallel_peak_rss_upper_bound_bytes": (
            resource_usage["process_peak_rss_bytes"] + sum(worker_peaks.values())
        ),
    }
)
_emit(
    "subprocess_complete",
    provider=None,
    stage="report",
    provider_count=len(provider_systems),
    verified_count=sum(status == "verified" for status in results.values()),
    verified=not failures,
    resource=resource_usage,
)
print(
    json.dumps(
        {
            "research_root": (
                str(resolved_root) if resolved_root is not None else None
            ),
            "provider_source_verification": results,
            "provider_metrics": provider_metrics,
            "provider_count": len(provider_systems),
            "provider_jobs": worker_count,
            "verified_count": sum(
                status == "verified" for status in results.values()
            ),
            "verified": not failures,
            "failures": failures,
            "elapsed_seconds": elapsed_seconds,
            "resource": resource_usage,
        }
    ),
    flush=True,
)
"""


def _emit_source_verification_progress(
    progress_stream: TextIO,
    event: str,
    **fields: object,
) -> None:
    payload = {
        "event": event,
        **fields,
    }
    progress_stream.write(
        SOURCE_VERIFICATION_PROGRESS_PREFIX
        + json.dumps(payload, sort_keys=True)
        + "\n"
    )
    progress_stream.flush()


def _terminate_source_verification(
    process: subprocess.Popen[bytes],
) -> None:
    if process.poll() is not None:
        return
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGTERM)
    else:  # pragma: no cover - Windows is not a supported release host
        process.terminate()
    try:
        process.wait(timeout=SOURCE_VERIFICATION_TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:  # pragma: no cover - Windows is not a supported release host
            process.kill()
        process.wait()


@contextlib.contextmanager
def _committed_source_snapshot(
    source: Path,
    commit: str,
) -> Iterator[Path]:
    """Materialize exactly ``source`` from ``commit`` without its worktree."""

    repo_root, prefix = _git_scope(source)
    treeish = (
        f"{commit}:{prefix.rstrip('/')}"
        if prefix
        else commit
    )
    with tempfile.TemporaryDirectory(
        prefix="mingli-release-committed-source-"
    ) as temporary:
        root = Path(temporary)
        archive_path = root / "source.tar"
        snapshot = root / "source"
        snapshot.mkdir()
        with archive_path.open("wb") as archive_handle:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "archive",
                    "--format=tar",
                    treeish,
                ],
                check=True,
                stdout=archive_handle,
            )
        with tarfile.open(archive_path, mode="r:") as archive:
            members = archive.getmembers()
            for member in members:
                relative = member.name.rstrip("/")
                _safe_relative_path(relative)
                if not (member.isdir() or member.isfile()):
                    raise ValueError(
                        "committed source snapshot contains a non-regular path: "
                        f"{member.name}"
                    )
            archive.extractall(
                snapshot,
                members=members,
                filter="data",
            )
        yield snapshot


def _verify_committed_release_sources(
    source: Path,
    commit: str,
    research_root: Path | None,
    *,
    timeout_seconds: float = SOURCE_VERIFICATION_TIMEOUT_SECONDS,
    progress_stream: TextIO | None = None,
    jobs: int | None = None,
) -> dict:
    """Run source audits from the immutable commit tree, never live files."""

    with _committed_source_snapshot(source, commit) as snapshot:
        return _verify_release_sources(
            snapshot,
            research_root,
            timeout_seconds=timeout_seconds,
            progress_stream=progress_stream,
            jobs=jobs,
        )


def _verify_release_sources(
    source: Path,
    research_root: Path | None,
    *,
    timeout_seconds: float = SOURCE_VERIFICATION_TIMEOUT_SECONDS,
    progress_stream: TextIO | None = None,
    jobs: int | None = None,
) -> dict:
    """Run the release source-verification gate over every provider.

    Fulltext verification is a release-time responsibility: each dedicated
    provider audit reports ``source_verification.status`` (skipped /
    verified / failed).  A release must pass an explicit research root and
    every provider's gate must verify; otherwise the classical quotes in the
    artifact cannot be re-derived from their declared sources, so the release
    is refused.

    The gate runs the audit registry in a one-shot release subprocess that
    rebuilds its import path to ``source/scripts``.  The parent
    interpreter's ``sys.path``, ``sys.modules`` and previously audited
    checkouts cannot leak into the verification, and every loaded audit
    module's real file is checked to live under ``source/scripts``.
    ``audit_provider_completeness`` is the single authoritative
    provider/audit registry, so adding a provider cannot silently drop it
    from the release gate.
    """

    if timeout_seconds <= 0:
        raise ValueError("source verification timeout must be positive")
    if jobs is None:
        jobs = min(
            SOURCE_VERIFICATION_MAX_JOBS,
            max(1, os.cpu_count() or 1),
        )
    if jobs <= 0:
        raise ValueError("source verification jobs must be positive")
    stream = sys.stderr if progress_stream is None else progress_stream
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("MINGLI_RESEARCH_ROOT", None)
    command = [
        sys.executable,
        "-B",
        "-c",
        _VERIFY_SOURCE_SUBPROCESS,
        str(source),
        str(research_root) if research_root is not None else "",
        str(jobs),
    ]
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=str(source),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=(os.name == "posix"),
    )
    assert process.stdout is not None
    assert process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    stdout_chunks: list[bytes] = []
    stderr_buffer = ""
    observed: dict[str, object] = {
        "provider": None,
        "stage": "subprocess_start",
        "resource": None,
        "provider_source_verification": {},
    }
    active_providers: set[str] = set()
    provider_stages: dict[str, object] = {}
    timed_out = False

    def consume_stderr(data: bytes) -> None:
        nonlocal stderr_buffer
        rendered = data.decode("utf-8", errors="replace")
        stream.write(rendered)
        stream.flush()
        stderr_buffer += rendered
        while "\n" in stderr_buffer:
            line, stderr_buffer = stderr_buffer.split("\n", 1)
            if not line.startswith(SOURCE_VERIFICATION_PROGRESS_PREFIX):
                continue
            try:
                event = json.loads(
                    line.removeprefix(SOURCE_VERIFICATION_PROGRESS_PREFIX)
                )
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            observed["last_event"] = event
            if "provider" in event:
                observed["provider"] = event["provider"]
            if "stage" in event:
                observed["stage"] = event["stage"]
            if "resource" in event:
                observed["resource"] = event["resource"]
            provider = event.get("provider")
            if provider is not None and "stage" in event:
                provider_stages[str(provider)] = event["stage"]
            if event.get("event") == "provider_start":
                active_providers.add(str(provider))
            elif event.get("event") == "provider_complete":
                active_providers.discard(str(provider))
                statuses = observed["provider_source_verification"]
                if isinstance(statuses, dict):
                    statuses[str(provider)] = event.get("status")

    try:
        while selector.get_map():
            remaining = timeout_seconds - (time.monotonic() - started)
            if remaining <= 0 and process.poll() is None:
                timed_out = True
                active = sorted(active_providers)
                provider = active[0] if active else observed["provider"]
                stage = provider_stages.get(
                    str(provider),
                    observed["stage"],
                )
                _emit_source_verification_progress(
                    stream,
                    "timeout_cancel_requested",
                    elapsed_seconds=round(time.monotonic() - started, 3),
                    timeout_seconds=timeout_seconds,
                    provider=provider,
                    stage=stage,
                    active_providers=active,
                    provider_stages={
                        item: provider_stages.get(item) for item in active
                    },
                    resource=observed["resource"],
                )
                _terminate_source_verification(process)
            events = selector.select(timeout=max(0.0, min(0.25, remaining)))
            for key, _ in events:
                data = os.read(key.fileobj.fileno(), 64 * 1024)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stdout":
                    stdout_chunks.append(data)
                else:
                    consume_stderr(data)
        returncode = process.wait()
    except KeyboardInterrupt:
        _emit_source_verification_progress(
            stream,
            "user_cancel_requested",
            elapsed_seconds=round(time.monotonic() - started, 3),
            provider=observed["provider"],
            stage=observed["stage"],
            resource=observed["resource"],
        )
        _terminate_source_verification(process)
        raise
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()

    if stderr_buffer:
        stream.write("" if stderr_buffer.endswith("\n") else "\n")
        stream.flush()
    stdout = b"".join(stdout_chunks).decode("utf-8", errors="replace")
    if timed_out:
        active = sorted(active_providers)
        provider = active[0] if active else observed["provider"] or "unknown"
        stage = provider_stages.get(str(provider), observed["stage"]) or "unknown"
        return {
            "research_root": (
                str(research_root.resolve())
                if research_root is not None
                else None
            ),
            "provider_source_verification": observed[
                "provider_source_verification"
            ],
            "provider_metrics": {},
            "verified": False,
            "failures": [
                (
                    "release source verification exceeded "
                    f"{timeout_seconds:g} seconds and was cancelled at "
                    f"provider={provider}, stage={stage}"
                )
            ],
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "resource": observed["resource"],
            "cancellation": {
                "reason": "timeout",
                "timeout_seconds": timeout_seconds,
                "provider": provider,
                "stage": stage,
                "active_providers": active,
                "provider_stages": {
                    item: provider_stages.get(item) for item in active
                },
                "last_resource": observed["resource"],
            },
        }
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError:
        report = None
    if returncode != 0:
        failures = (
            list(report.get("failures") or ())
            if isinstance(report, dict)
            else []
        )
        failures.append(
            "release source verification subprocess failed with exit code "
            f"{returncode} at provider={observed['provider'] or 'unknown'}, "
            f"stage={observed['stage'] or 'unknown'}"
        )
        return {
            "research_root": (
                str(research_root.resolve())
                if research_root is not None
                else None
            ),
            "provider_source_verification": (
                report.get("provider_source_verification", {})
                if isinstance(report, dict)
                else observed["provider_source_verification"]
            ),
            "provider_metrics": (
                report.get("provider_metrics", {})
                if isinstance(report, dict)
                else {}
            ),
            "verified": False,
            "failures": failures,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "resource": (
                report.get("resource")
                if isinstance(report, dict)
                else observed["resource"]
            ),
        }
    if report is None:
        return {
            "research_root": (
                str(research_root.resolve())
                if research_root is not None
                else None
            ),
            "provider_source_verification": {},
            "verified": False,
            "failures": [
                "release source verification returned malformed output"
            ],
        }
    if not isinstance(report, dict):
        return {
            "research_root": (
                str(research_root.resolve())
                if research_root is not None
                else None
            ),
            "provider_source_verification": {},
            "verified": False,
            "failures": [
                "release source verification returned a non-object result"
            ],
        }
    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = args.source.expanduser().resolve()
    destinations = [_deployment_destination(path) for path in args.destination]
    if len(set(destinations)) != len(destinations):
        raise ValueError("duplicate deployment destination")
    release_files = tracked_release_files(source)
    source_extras, repo_extras = extra_gate_pathspecs(source)
    commit = source_commit(source)
    require_clean_source(
        source,
        pathspecs=list(dict.fromkeys([*release_files, *source_extras])),
        extra_repo_pathspecs=repo_extras,
    )
    source_verification = _verify_committed_release_sources(
        source,
        commit,
        args.research_root,
    )
    if not source_verification["verified"]:
        raise ValueError(
            "release source verification failed: "
            + "; ".join(source_verification["failures"])
        )
    manifest = build_committed_manifest(
        source,
        release_files,
        commit,
    )

    protected_before = {
        destination: destination_is_protected(destination)
        for destination in destinations
    }
    results: list[dict] = []
    operation_error: BaseException | None = None
    operation_traceback = None
    try:
        if args.apply:
            for destination in destinations:
                unprotect_destination(destination)

        results = [
            sync_destination(source, destination, manifest, apply=args.apply)
            for destination in destinations
        ]
    except BaseException as exc:
        operation_error = exc
        operation_traceback = exc.__traceback__

    protection_failures = (
        _restore_destination_protection(
            destinations,
            protected_before,
            args.protect,
        )
        if args.apply
        else []
    )
    if operation_error is not None:
        for failure in protection_failures:
            operation_error.add_note(
                "destination protection also failed: "
                f"{type(failure).__name__}: {failure}"
            )
        raise operation_error.with_traceback(operation_traceback)
    if protection_failures:
        rendered = "; ".join(
            f"{type(failure).__name__}: {failure}"
            for failure in protection_failures
        )
        raise RuntimeError(f"destination protection failed: {rendered}")

    print(
        json.dumps(
            {
                "manifest": manifest,
                "results": results,
                "source_verification": source_verification,
            },
            ensure_ascii=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"release deployment failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
