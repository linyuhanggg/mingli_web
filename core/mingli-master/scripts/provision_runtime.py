#!/usr/bin/env python3
"""Provision and verify the dedicated Mingli deterministic-adapter runtime."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from runtime_python import (
    assert_runtime_path_not_symlink,
    probe_runtime_identity,
    runtime_lock,
    runtime_site_roots,
    validate_runtime_requirements_lock,
    write_installed_runtime_manifest,
)

DEFAULT_VENV = Path("~/.local/share/mingli-master/venv").expanduser()
DEFAULT_REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements-runtime.lock"
DEFAULT_BUILD_REQUIREMENTS = (
    Path(__file__).resolve().parents[1] / "requirements-runtime-build.lock"
)


def runtime_python(venv_root: Path) -> Path:
    return venv_root / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def runtime_install_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("PYTHONPYCACHEPREFIX", None)
    return environment


def run_pip(executable: Path, *arguments: str) -> None:
    subprocess.run(
        [str(executable), "-B", "-m", "pip", *arguments],
        check=True,
        env=runtime_install_environment(),
    )


def remove_runtime_bytecode(site_roots: list[Path]) -> None:
    for site_root in site_roots:
        for cache in site_root.rglob("__pycache__"):
            if cache.is_symlink():
                raise RuntimeError("runtime bytecode cache is a symlink")
            if cache.is_dir():
                shutil.rmtree(cache)
        for bytecode in (*site_root.rglob("*.pyc"), *site_root.rglob("*.pyo")):
            if bytecode.is_symlink() or not bytecode.is_file():
                raise RuntimeError("runtime bytecode path is unsafe")
            bytecode.unlink()


def assert_provision_interpreter_compatible(venv_root: Path) -> None:
    existing = runtime_python(venv_root)
    if not existing.is_file():
        return
    completed = subprocess.run(
        [
            str(existing),
            "-I",
            "-S",
            "-c",
            "import json,sys;print(json.dumps(list(sys.version_info[:2])))",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        existing_minor = json.loads(completed.stdout.strip())
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("existing runtime Python identity is invalid") from exc
    current_minor = list(sys.version_info[:2])
    if completed.returncode != 0 or existing_minor != current_minor:
        raise RuntimeError(
            f"existing runtime Python minor {existing_minor} differs from "
            f"provisioning interpreter {current_minor}"
        )


def provision(
    venv_root: Path,
    requirements: Path,
    *,
    install: bool,
    allow_python_change: bool = False,
) -> dict[str, object]:
    venv_root = venv_root.expanduser().absolute()
    requirements = requirements.expanduser().absolute()
    if not requirements.is_file():
        raise RuntimeError(f"requirements file does not exist: {requirements}")
    if install:
        if not DEFAULT_BUILD_REQUIREMENTS.is_file():
            raise RuntimeError("runtime build requirements lock does not exist")
        if not allow_python_change:
            assert_provision_interpreter_compatible(venv_root)
        venv_root.parent.mkdir(parents=True, exist_ok=True)
        assert_runtime_path_not_symlink(venv_root)
    else:
        executable = runtime_python(venv_root)
        if not executable.is_file():
            raise RuntimeError(f"runtime does not exist: {executable}")
    validate_runtime_requirements_lock(requirements)
    if install:
        with runtime_lock(venv_root, exclusive=True):
            with tempfile.TemporaryDirectory(
                prefix=f".{venv_root.name}.stage-", dir=venv_root.parent
            ) as temporary:
                staged = Path(temporary) / "runtime"
                venv.EnvBuilder(with_pip=True, clear=False, symlinks=False).create(staged)
                staged_executable = runtime_python(staged)
                run_pip(
                    staged_executable,
                    "install",
                    "--require-hashes",
                    "--no-compile",
                    "--only-binary",
                    ":all:",
                    "--requirement",
                    str(DEFAULT_BUILD_REQUIREMENTS),
                )
                run_pip(
                    staged_executable,
                    "install",
                    "--require-hashes",
                    "--no-compile",
                    "--no-build-isolation",
                    "--only-binary",
                    "PyYAML",
                    "--no-binary",
                    "sxtwl",
                    "--requirement",
                    str(requirements),
                )
                run_pip(
                    staged_executable,
                    "uninstall",
                    "--yes",
                    "pip",
                    "setuptools",
                    "wheel",
                    "packaging",
                )
                remove_runtime_bytecode(runtime_site_roots(staged_executable))
                write_installed_runtime_manifest(staged_executable)
                probe_runtime_identity(str(staged_executable))
                backup = venv_root.parent / f".{venv_root.name}.backup-{os.getpid()}"
                if backup.exists() or backup.is_symlink():
                    raise RuntimeError("stale runtime backup blocks atomic provision")
                replaced = False
                try:
                    if venv_root.exists():
                        os.replace(venv_root, backup)
                        replaced = True
                    os.replace(staged, venv_root)
                except BaseException:
                    if replaced and backup.exists() and not venv_root.exists():
                        os.replace(backup, venv_root)
                    raise
                if replaced:
                    shutil.rmtree(backup)
        identity = probe_runtime_identity(str(runtime_python(venv_root)))
        return {"runtime_python": str(runtime_python(venv_root)), **identity}
    executable = runtime_python(venv_root)
    identity = probe_runtime_identity(str(executable))
    return {"runtime_python": str(executable), **identity}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", type=Path, default=DEFAULT_VENV)
    parser.add_argument(
        "--requirements",
        type=Path,
        default=DEFAULT_REQUIREMENTS,
    )
    parser.add_argument("--check", action="store_true", help="verify without installing")
    parser.add_argument(
        "--replace-python",
        action="store_true",
        help="explicitly permit replacing an existing runtime with this Python minor",
    )
    args = parser.parse_args(argv)
    result = provision(
        args.venv,
        args.requirements,
        install=not args.check,
        allow_python_change=args.replace_python,
    )
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"runtime provisioning failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
