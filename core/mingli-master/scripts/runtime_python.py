"""Resolve the declared Python interpreter for deterministic adapters."""

from __future__ import annotations

import base64
import csv
import errno
import fcntl
import hashlib
import importlib.metadata
import json
import os
import re
import stat
import subprocess
import sys
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

ENV_NAME = "MINGLI_PYTHON"
MINIMUM_VERSION = (3, 10)
REQUIRED_MODULES = ("yaml", "sxtwl", "astronomy", "cnlunar", "zhconv")
PINNED_VERSIONS = {
    "yaml": "6.0.3",
    "sxtwl": "2.0.7",
    "astronomy": "2.1.19",
    "cnlunar": "0.2.4",
    "zhconv": "1.4.3",
}
PROBE_MARKER = "mingli-runtime-v1"
ROOT = Path(__file__).resolve().parents[1]
CNLUNAR_PROVENANCE = ROOT / "vendor/cnlunar-0.2.4/PROVENANCE.json"
CNLUNAR_REVIEWED_FILES = (
    "cnlunar/__init__.py",
    "cnlunar/lunar.py",
    "cnlunar/config.py",
    "cnlunar/solar24.py",
    "cnlunar/tools.py",
    "cnlunar/holidays.py",
    "cnlunar/demo.py",
)
RUNTIME_MANIFEST = "runtime-integrity.json"
RUNTIME_LOCK_SUFFIX = ".runtime.lock"
REQUIRED_DISTRIBUTIONS = {
    "pyyaml": "6.0.3",
    "sxtwl": "2.0.7",
    "astronomy_engine": "2.1.19",
    "cnlunar": "0.2.4",
    "zhconv": "1.4.3",
}
LOCKED_REQUIREMENT_PATTERN = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\]+)(?:\s+(.+))?$"
)
LOCKED_HASH_PATTERN = re.compile(r"--hash=sha256:([0-9a-f]{64})")


def assert_runtime_path_not_symlink(runtime_root: Path) -> None:
    runtime_root = runtime_root.expanduser().absolute()
    if runtime_root.is_symlink() or runtime_root.parent.is_symlink():
        raise RuntimeError("runtime root and its parent must not be symlinks")


def runtime_root_for_executable(executable: str | Path) -> Path:
    path = Path(executable).absolute()
    parent = path.parent
    root = parent.parent
    assert_runtime_path_not_symlink(root)
    if not (root / "pyvenv.cfg").is_file():
        raise RuntimeError(f"{ENV_NAME} must be a dedicated virtual environment")
    return root


def runtime_site_roots(executable: str | Path) -> list[Path]:
    root = runtime_root_for_executable(executable)
    if os.name == "nt":
        candidates = [root / "Lib/site-packages"]
    else:
        version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidates = [root / "lib" / version / "site-packages"]
    roots = [candidate.absolute() for candidate in candidates]
    if not roots or any(not path.is_dir() or path.is_symlink() for path in roots):
        raise RuntimeError("runtime site-packages root is missing or unsafe")
    return roots


@contextmanager
def runtime_lock(
    runtime_root: Path,
    *,
    exclusive: bool,
    blocking: bool = True,
):
    runtime_root = runtime_root.expanduser().absolute()
    lock_path = runtime_root.parent / f".{runtime_root.name}{RUNTIME_LOCK_SUFFIX}"
    flags = os.O_RDWR | os.O_CREAT
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        mode = os.fstat(descriptor).st_mode
        if not stat.S_ISREG(mode):
            raise RuntimeError("runtime lock must be a regular file")
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        if not blocking:
            operation |= fcntl.LOCK_NB
        try:
            fcntl.flock(descriptor, operation)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN}:
                raise RuntimeError("runtime lock is already held") from exc
            raise
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def load_hash_locked_distributions(requirements: Path) -> dict[str, str]:
    try:
        physical_lines = requirements.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError("runtime requirements lock is unavailable") from exc
    statements: list[str] = []
    current: list[str] = []
    for physical_line in physical_lines:
        line = physical_line.strip()
        if not line or line.startswith("#"):
            continue
        continued = line.endswith("\\")
        current.append(line[:-1].rstrip() if continued else line)
        if not continued:
            statements.append(" ".join(current))
            current = []
    if current or not statements:
        raise RuntimeError("runtime requirements lock has an invalid continuation")

    distributions: dict[str, str] = {}
    for statement in statements:
        match = LOCKED_REQUIREMENT_PATTERN.fullmatch(statement)
        if match is None:
            raise RuntimeError("runtime requirements lock contains an unsupported entry")
        name, version, options = match.groups()
        option_tokens = (options or "").split()
        if not option_tokens or any(
            LOCKED_HASH_PATTERN.fullmatch(token) is None for token in option_tokens
        ):
            raise RuntimeError("runtime requirements lock entry is not fully hash locked")
        normalized = _normalized_distribution_name(name)
        if normalized in distributions:
            raise RuntimeError(
                f"runtime requirements lock duplicates a distribution: {normalized}"
            )
        distributions[normalized] = version
    return distributions


def validate_runtime_requirements_lock(requirements: Path) -> None:
    distributions = load_hash_locked_distributions(requirements)
    if distributions != REQUIRED_DISTRIBUTIONS:
        raise RuntimeError(
            "runtime requirements lock does not match the distribution allowlist"
        )


def build_runtime_tree_manifest(
    site_roots: list[Path],
    *,
    owned_paths: set[str],
) -> dict[str, object]:
    if len(site_roots) != 1:
        raise RuntimeError("runtime manifest currently requires one site-packages root")
    root = site_roots[0].absolute()
    files: dict[str, str] = {}
    for relative in sorted(owned_paths):
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"runtime manifest path is missing or a symlink: {relative}")
        files[relative] = _file_digest(path)
    return {"schema_version": 1, "files": files}


def validate_runtime_tree(site_roots: list[Path], manifest: dict[str, object]) -> None:
    if len(site_roots) != 1 or manifest.get("schema_version") != 1:
        raise RuntimeError("runtime integrity manifest contract is invalid")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise RuntimeError("runtime integrity manifest files are invalid")
    root = site_roots[0].absolute()
    expected = set(files)
    observed: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"runtime package contains a symlink: {path}")
        if path.is_file() and (
            "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}
        ):
            raise RuntimeError(f"unchecked runtime bytecode is forbidden: {path}")
        if not path.is_file():
            continue
        observed.add(path.relative_to(root).as_posix())
    extras = observed - expected
    if extras:
        raise RuntimeError(f"unrecorded runtime drift: {sorted(extras)}")
    if expected - observed:
        raise RuntimeError(f"runtime files are missing: {sorted(expected - observed)}")
    for relative, digest in files.items():
        if not isinstance(digest, str) or _file_digest(root / relative) != digest:
            raise RuntimeError(f"runtime file hash mismatch: {relative}")


def _distribution_record_paths(site_root: Path) -> tuple[set[str], dict[str, str]]:
    owned: set[str] = set()
    versions: dict[str, str] = {}
    for normalized, expected_version in REQUIRED_DISTRIBUTIONS.items():
        matches = list(site_root.glob(f"{normalized}-{expected_version}.dist-info"))
        if len(matches) != 1 or matches[0].is_symlink():
            raise RuntimeError(f"runtime distribution identity is invalid: {normalized}")
        dist_info = matches[0]
        metadata = (dist_info / "METADATA").read_text(encoding="utf-8")
        version_lines = [line for line in metadata.splitlines() if line.startswith("Version: ")]
        if version_lines != [f"Version: {expected_version}"]:
            raise RuntimeError(f"runtime distribution version is invalid: {normalized}")
        versions[normalized] = expected_version
        record = dist_info / "RECORD"
        if record.is_symlink() or not record.is_file():
            raise RuntimeError(f"runtime distribution RECORD is invalid: {normalized}")
        with record.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.reader(stream))
        for row in rows:
            if len(row) != 3:
                raise RuntimeError(f"runtime distribution RECORD row is invalid: {normalized}")
            relative = Path(row[0])
            if relative.is_absolute() or ".." in relative.parts:
                continue
            relative_text = relative.as_posix()
            if "__pycache__" in relative.parts or relative.suffix == ".pyc":
                continue
            installed = site_root / relative
            if installed.is_symlink() or not installed.is_file():
                raise RuntimeError(f"runtime distribution file is unsafe: {relative_text}")
            if row[1]:
                algorithm, separator, encoded = row[1].partition("=")
                if algorithm != "sha256" or not separator:
                    raise RuntimeError(f"runtime RECORD hash is unsupported: {relative_text}")
                expected = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).hex()
                if _file_digest(installed) != expected:
                    raise RuntimeError(f"runtime RECORD hash mismatch: {relative_text}")
            owned.add(relative_text)
    return owned, versions


def build_installed_runtime_manifest(executable: str | Path) -> dict[str, object]:
    roots = runtime_site_roots(executable)
    owned, versions = _distribution_record_paths(roots[0])
    manifest = build_runtime_tree_manifest(roots, owned_paths=owned)
    manifest["distributions"] = versions
    return manifest


def write_installed_runtime_manifest(executable: str | Path) -> Path:
    root = runtime_root_for_executable(executable)
    target = root / RUNTIME_MANIFEST
    temporary = root / f".{RUNTIME_MANIFEST}.tmp-{os.getpid()}"
    payload = build_installed_runtime_manifest(executable)
    data = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        finally:
            raise
    return target


def validate_installed_runtime(executable: str | Path) -> list[Path]:
    root = runtime_root_for_executable(executable)
    manifest_path = root / RUNTIME_MANIFEST
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeError("runtime integrity manifest is missing or unsafe")
    mode = manifest_path.stat().st_mode
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeError("runtime integrity manifest is writable by group or others")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("runtime integrity manifest is invalid") from exc
    if not isinstance(manifest, dict) or manifest.get("distributions") != REQUIRED_DISTRIBUTIONS:
        raise RuntimeError("runtime integrity distribution contract is invalid")
    roots = runtime_site_roots(executable)
    for root_path in roots:
        hooks = [
            *root_path.glob("*.pth"),
            root_path / "sitecustomize.py",
            root_path / "usercustomize.py",
        ]
        if any(path.exists() or path.is_symlink() for path in hooks):
            raise RuntimeError("runtime site hook drift is forbidden")
    validate_runtime_tree(roots, manifest)
    return roots


def isolated_runtime_identity(executable: str | Path) -> dict[str, object]:
    root = runtime_root_for_executable(executable)
    with runtime_lock(root, exclusive=False):
        site_roots = validate_installed_runtime(executable)
        for site_root in site_roots:
            sys.path.append(str(site_root))
        identity = current_runtime_identity()
        validate_runtime_identity(identity)
        return identity


def load_cnlunar_reviewed_hashes(
    provenance_path: Path = CNLUNAR_PROVENANCE,
) -> dict[str, str]:
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("cnlunar provenance is unavailable or invalid") from exc
    if not isinstance(provenance, dict):
        raise RuntimeError("cnlunar provenance must be a JSON object")
    reviewed_files = provenance.get("reviewed_files")
    expected_keys = set(CNLUNAR_REVIEWED_FILES)
    if (
        provenance.get("project") != "OPN48/cnlunar"
        or provenance.get("version") != PINNED_VERSIONS["cnlunar"]
        or not isinstance(reviewed_files, dict)
        or set(reviewed_files) != expected_keys
        or any(
            not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            for digest in reviewed_files.values()
        )
    ):
        raise RuntimeError("cnlunar provenance reviewed_files contract is invalid")
    return dict(reviewed_files)


def current_runtime_identity() -> dict[str, object]:
    from datetime import datetime

    import astronomy
    import cnlunar
    import sxtwl
    import yaml
    import zhconv

    lunar = cnlunar.Lunar(datetime(2024, 2, 10, 12))
    package_root = Path(cnlunar.__file__).resolve().parent
    reviewed_files: dict[str, str] = {}
    for relative in CNLUNAR_REVIEWED_FILES:
        installed = (package_root / Path(relative).name).resolve()
        if installed.parent != package_root or not installed.is_file():
            raise RuntimeError(f"cnlunar reviewed runtime file is missing: {relative}")
        reviewed_files[relative] = hashlib.sha256(installed.read_bytes()).hexdigest()
    modules = (astronomy, cnlunar, yaml, sxtwl, zhconv)
    return {
        "marker": PROBE_MARKER,
        "python": list(sys.version_info[:3]),
        "yaml": yaml.__version__,
        "sxtwl": importlib.metadata.version("sxtwl"),
        "astronomy": importlib.metadata.version("astronomy-engine"),
        "cnlunar": importlib.metadata.version("cnlunar"),
        "zhconv": importlib.metadata.version("zhconv"),
        "origins": {
            module.__name__: str(Path(module.__file__).resolve()) for module in modules
        },
        "prefix": str(runtime_root_for_executable(sys.executable)),
        "site_roots": [str(path) for path in runtime_site_roots(sys.executable)],
        "cnlunar_known_answer": [
            lunar.lunarYear,
            lunar.lunarMonth,
            lunar.lunarDay,
            lunar.year8Char,
            lunar.month8Char,
            lunar.day8Char,
        ],
        "cnlunar_reviewed_files": reviewed_files,
    }


def validate_runtime_identity(
    result: dict[str, object],
    provenance_path: Path = CNLUNAR_PROVENANCE,
) -> None:
    if not isinstance(result, dict):
        raise RuntimeError(f"{ENV_NAME} runtime probe returned invalid output")
    python_version = result.get("python")
    if (
        result.get("marker") != PROBE_MARKER
        or not isinstance(python_version, list)
        or len(python_version) < 2
        or not all(isinstance(part, int) for part in python_version[:2])
        or tuple(python_version[:2]) < MINIMUM_VERSION
    ):
        raise RuntimeError(f"{ENV_NAME} runtime probe returned an invalid Python identity")
    actual_versions = {module: str(result.get(module) or "") for module in REQUIRED_MODULES}
    if actual_versions != PINNED_VERSIONS:
        raise RuntimeError(
            f"{ENV_NAME} does not match pinned dependency versions "
            f"{PINNED_VERSIONS} (got {actual_versions})"
        )
    prefix = Path(str(result.get("prefix") or "")).resolve()
    site_roots = result.get("site_roots")
    resolved_site_roots = (
        [Path(str(path)).resolve() for path in site_roots]
        if isinstance(site_roots, list) and site_roots
        else []
    )
    origins = result.get("origins")
    origins_are_isolated = (
        isinstance(origins, dict)
        and set(origins) == {"astronomy", "cnlunar", "yaml", "sxtwl", "zhconv"}
        and all(root.name in {"site-packages", "dist-packages"} for root in resolved_site_roots)
        and all(root.is_relative_to(prefix) for root in resolved_site_roots)
        and all(
            any(Path(str(origin)).resolve().is_relative_to(root) for root in resolved_site_roots)
            for origin in origins.values()
        )
    )
    if (
        not origins_are_isolated
        or result.get("cnlunar_known_answer")
        != [2024, 1, 1, "甲辰", "丙寅", "甲辰"]
    ):
        raise RuntimeError(f"{ENV_NAME} failed isolated runtime identity checks")
    expected_hashes = load_cnlunar_reviewed_hashes(provenance_path)
    if result.get("cnlunar_reviewed_files") != expected_hashes:
        raise RuntimeError(f"{ENV_NAME} failed cnlunar reviewed-file hashes")


def _runtime_probe_source() -> str:
    return (
        "import sys;sys.dont_write_bytecode=True;sys.pycache_prefix='/dev/null';"
        "import importlib.util,json;from pathlib import Path;"
        "helper=Path(sys.argv[1]).resolve(strict=True);"
        "spec=importlib.util.spec_from_file_location('_mingli_runtime_guard',helper);"
        "guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);"
        "print(json.dumps(guard.isolated_runtime_identity(sys.executable),sort_keys=True))"
    )


def probe_runtime_identity(executable: str) -> dict[str, object]:
    completed = subprocess.run(
        [
            executable,
            "-I",
            "-S",
            "-B",
            "-c",
            _runtime_probe_source(),
            str(Path(__file__).resolve()),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if completed.returncode != 0:
        detail = (completed.stdout or completed.stderr or "probe failed").strip()
        raise RuntimeError(
            f"{ENV_NAME} requires Python {MINIMUM_VERSION[0]}.{MINIMUM_VERSION[1]}+ "
            f"with {', '.join(REQUIRED_MODULES)}; runtime probe failed ({detail})"
        )
    try:
        result = json.loads(completed.stdout.strip())
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError(f"{ENV_NAME} runtime probe returned invalid output") from exc
    validate_runtime_identity(result)
    return result


@lru_cache(maxsize=16)
def _probe_runtime(executable: str) -> None:
    probe_runtime_identity(executable)


def resolve_runtime_python() -> Path:
    configured = os.environ.get(ENV_NAME)
    candidate = Path(configured).expanduser() if configured else Path(sys.executable)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    candidate = candidate.absolute()
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise RuntimeError(f"{ENV_NAME} must name an executable Python file")
    _probe_runtime(str(candidate))
    return candidate


def runtime_command() -> list[str]:
    """Return the pinned child-interpreter prefix without cache side effects."""

    return [str(resolve_runtime_python()), "-B"]
