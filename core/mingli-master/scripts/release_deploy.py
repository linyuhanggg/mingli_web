#!/usr/bin/env python3
"""Deploy one hash-bound Mingli release to local Codex and Hermes installs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping


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


def _git_tracked_paths(source: Path) -> set[str]:
    result = subprocess.run(
        ["git", "-C", str(source), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return {
        _safe_relative_path(item.decode("utf-8"))
        for item in result.stdout.split(b"\0")
        if item
    }


def _runtime_closure(source: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    closure_path = source / RUNTIME_CLOSURE_RELATIVE
    if closure_path.is_symlink() or not closure_path.is_file():
        raise ValueError("runtime closure file is missing or unsafe")
    try:
        payload = json.loads(closure_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("runtime closure file is invalid") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "files",
        "patterns",
    }:
        raise ValueError("runtime closure schema is invalid")
    if payload.get("schema_version") != RUNTIME_CLOSURE_SCHEMA:
        raise ValueError("runtime closure schema_version is invalid")
    raw_files = payload.get("files")
    raw_patterns = payload.get("patterns")
    if not isinstance(raw_files, list) or not isinstance(raw_patterns, list):
        raise ValueError("runtime closure files and patterns must be lists")
    try:
        files = tuple(_safe_relative_path(item) for item in raw_files)
        patterns = tuple(_safe_release_pattern(item) for item in raw_patterns)
    except (TypeError, ValueError) as exc:
        raise ValueError("runtime closure contains an unsafe path") from exc
    if not files or len(files) != len(set(files)):
        raise ValueError("runtime closure files must be non-empty and unique")
    if len(patterns) != len(set(patterns)):
        raise ValueError("runtime closure patterns must be unique")
    if RUNTIME_CLOSURE_RELATIVE not in files:
        raise ValueError("runtime closure must include itself")
    return files, patterns


def tracked_release_files(source: Path) -> list[str]:
    """Return the explicit production closure, never a broad repository copy.

    The closure declaration is intentionally tracked with the release.  This
    keeps historical plans, tests, host-specific metadata and developer tools
    out of an installed Skill unless a runtime dependency is deliberately
    added to the one allow-list.
    """

    tracked = _git_tracked_paths(source)
    files, patterns = _runtime_closure(source)
    untracked = sorted(set(files) - tracked)
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
    return sorted(selected)


def source_commit(source: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def require_clean_source(source: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"],
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
    source_prefix = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "--show-prefix"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
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
        if source_prefix:
            if not relative.startswith(source_prefix):
                continue
            relative = relative[len(source_prefix) :]
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
import importlib
import json
import os
import sys
from pathlib import Path


def _fail(message):
    print(
        json.dumps(
            {
                "research_root": sys.argv[2] or None,
                "provider_source_verification": {},
                "verified": False,
                "failures": [message],
            }
        )
    )
    raise SystemExit(1)


source = Path(sys.argv[1]).resolve()
research = sys.argv[2] or None
scripts_dir = source / "scripts"
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
resolved_root = Path(research).resolve() if research else None

results = {}
failures = []
scripts_resolved = scripts_dir.resolve()
for system in provider_systems:
    module_name = provider_audits[system]
    module = importlib.import_module(module_name)
    module_file = Path(getattr(module, "__file__", "")).resolve()
    if not module_file.is_relative_to(scripts_resolved):
        failures.append(
            f"{system}: audit module {module_name} resolves outside the source"
            f" checkout: {module_file}"
        )
        results[system] = "error"
        continue
    # With no research checkout there is nothing an audit can prove about
    # source fidelity.  We still import every registered audit from the
    # selected release checkout and validate its origin above, then fail
    # closed without paying for thirteen exhaustive provider replays whose
    # only possible source status is ``skipped``.
    if resolved_root is None:
        results[system] = "skipped"
        failures.append(
            f"{system}: source verification skipped; pass --research-root"
        )
        continue
    audit = getattr(module, module_name)
    try:
        report = audit(research_root=resolved_root)
    except BaseException as exc:  # noqa: BLE001 - gate must fail closed
        results[system] = "error"
        failures.append(
            f"{system}: source verification raised {type(exc).__name__}"
        )
        continue
    status = str(
        (report.get("source_verification") or {}).get("status") or "skipped"
    )
    results[system] = status
    if status != "verified":
        failures.append(f"{system}: source verification {status}")

print(
    json.dumps(
        {
            "research_root": (
                str(resolved_root) if resolved_root is not None else None
            ),
            "provider_source_verification": results,
            "verified": not failures,
            "failures": failures,
        }
    )
)
"""


def _verify_release_sources(source: Path, research_root: Path | None) -> dict:
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

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("MINGLI_RESEARCH_ROOT", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            _VERIFY_SOURCE_SUBPROCESS,
            str(source),
            str(research_root) if research_root is not None else "",
        ],
        cwd=str(source),
        env=env,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return {
            "research_root": (
                str(research_root.resolve())
                if research_root is not None
                else None
            ),
            "provider_source_verification": {},
            "verified": False,
            "failures": [
                "release source verification subprocess failed: "
                + (completed.stderr.strip() or completed.stdout.strip() or "unknown")
            ],
        }
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError:
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
    require_clean_source(source)
    source_verification = _verify_release_sources(source, args.research_root)
    if not source_verification["verified"]:
        raise ValueError(
            "release source verification failed: "
            + "; ".join(source_verification["failures"])
        )
    manifest = build_committed_manifest(
        source,
        tracked_release_files(source),
        source_commit(source),
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
