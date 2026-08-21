#!/usr/bin/env python3
"""Run repository unittest modules across a bounded set of processes.

The coordinator uses threads only to supervise child interpreters.  Each test
module runs in its own Python process, so CPU-heavy deterministic calculations
can use multiple cores without sharing unittest globals.
"""

from __future__ import annotations

import argparse
import ast
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from fnmatch import fnmatch
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_START_DIRECTORY = ROOT / "scripts"
DEFAULT_PATTERN = "test_*.py"
MAX_AUTOMATIC_WORKERS = 10
TEST_COUNT_RE = re.compile(r"Ran\s+(\d+)\s+tests?\b")

# These suites exercise repository-wide release audits or shared state/storage
# boundaries.  Running them after the parallel lane prevents source-audit CPU
# contention and keeps stateful regressions deterministic.
SERIAL_PATTERNS = (
    "test_release_deploy.py",
    "test_*state*.py",
    "test_*store*.py",
    "test_*atomicity*.py",
    "test_accepted_index.py",
)

# These modules are pure audits with expensive class-local setup.  Splitting
# only this reviewed allow-list shortens the critical path without changing
# discovery semantics for arbitrary future tests.
SHARDED_MODULES = {
    "test_v51_dedicated_audit_contract.py",
    "test_v51_provider_completeness.py",
    "test_v51_selection_completion.py",
}
METHOD_SHARDED_CLASSES = {
    "test_v51_dedicated_audit_contract.py": {
        "DedicatedAuditMachineContractTests",
        "DedicatedAuditIdentityContractTests",
    },
}

# Start measured long poles first so they overlap with the short tail.  This is
# scheduling metadata only; it neither selects nor skips tests.
LONG_TARGET_ORDER = {
    "test_v51_provider_completeness.py::CanonicalMatrixSnapshotTests": 0,
    "test_v51_provider_completeness.py::ProviderCompletenessMatrixTests": 1,
    "test_v51_dedicated_audit_contract.py::DedicatedAuditMachineContractTests": 2,
    "test_v51_dedicated_audit_contract.py::DedicatedAuditIdentityContractTests": 3,
    "test_v51_remaining_provider_replays.py": 4,
    "test_v51_selection_completion.py::SelectionProviderActivationTests": 5,
    "test_v51_qimen_completion.py": 6,
    "test_v51_liuren_completion.py": 7,
}
TARGET_PROCESS_SLOTS = {
    "test_v51_provider_completeness.py::CanonicalMatrixSnapshotTests": 6,
    "test_v51_remaining_provider_replays.py": 3,
}


@dataclass(frozen=True)
class TestModule:
    path: Path
    label: str
    serial: bool
    unittest_target: str | None = None
    process_slots: int = 1


@dataclass(frozen=True)
class TestResult:
    module: TestModule
    returncode: int
    output: str
    test_count: int
    elapsed_seconds: float


def _positive_jobs(value: str) -> int:
    try:
        jobs = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("jobs must be an integer") from exc
    if jobs < 1:
        raise argparse.ArgumentTypeError("jobs must be at least 1")
    return jobs


def _automatic_jobs() -> int:
    cpu_count = os.cpu_count() or 1
    return max(1, min(MAX_AUTOMATIC_WORKERS, cpu_count))


def _default_jobs() -> int:
    configured = os.environ.get("MINGLI_TEST_JOBS")
    if configured is None:
        return _automatic_jobs()
    try:
        return _positive_jobs(configured)
    except argparse.ArgumentTypeError as exc:
        raise SystemExit(f"invalid MINGLI_TEST_JOBS: {exc}") from exc


def _is_serial(path: Path) -> bool:
    return any(fnmatch(path.name, pattern) for pattern in SERIAL_PATTERNS)


def _test_case_classes(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if any(
            (isinstance(base, ast.Name) and base.id == "TestCase")
            or (isinstance(base, ast.Attribute) and base.attr == "TestCase")
            for base in node.bases
        ):
            names.append(node.name)
    return names


def _test_case_methods(path: Path) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name: [
            child.name
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            and child.name.startswith("test_")
        ]
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


def _module_targets(path: Path, *, start: Path) -> list[TestModule]:
    relative = path.relative_to(start)
    serial = _is_serial(path)
    if path.name not in SHARDED_MODULES:
        label = str(relative)
        return [
            TestModule(
                path=path,
                label=label,
                serial=serial,
                process_slots=TARGET_PROCESS_SLOTS.get(label, 1),
            )
        ]
    class_names = _test_case_classes(path)
    if not class_names:
        label = str(relative)
        return [
            TestModule(
                path=path,
                label=label,
                serial=serial,
                process_slots=TARGET_PROCESS_SLOTS.get(label, 1),
            )
        ]
    module_name = path.stem
    methods = _test_case_methods(path)
    targets = []
    method_shards = METHOD_SHARDED_CLASSES.get(path.name, set())
    for class_name in class_names:
        class_methods = methods.get(class_name, ()) if class_name in method_shards else ()
        suffixes = class_methods or (None,)
        for method_name in suffixes:
            test_name = class_name if method_name is None else f"{class_name}.{method_name}"
            label = f"{relative}::{test_name}"
            targets.append(
                TestModule(
                    path=path,
                    label=label,
                    serial=serial,
                    unittest_target=f"{module_name}.{test_name}",
                    process_slots=TARGET_PROCESS_SLOTS.get(label, 1),
                )
            )
    return targets


def _target_priority(label: str) -> int:
    if label in LONG_TARGET_ORDER:
        return LONG_TARGET_ORDER[label]
    for prefix, priority in LONG_TARGET_ORDER.items():
        if label.startswith(f"{prefix}."):
            return priority
    return 100


def discover_modules(start_directory: Path, pattern: str) -> list[TestModule]:
    start = start_directory.resolve()
    if not start.is_dir():
        raise ValueError(f"test start directory does not exist: {start}")
    modules = []
    candidates = (candidate for candidate in start.rglob(pattern) if candidate.is_file())
    for path in sorted(candidates):
        modules.extend(_module_targets(path, start=start))
    return sorted(
        modules,
        key=lambda module: (_target_priority(module.label), module.label),
    )


def _child_environment(
    module: TestModule,
    *,
    allocated_slots: int | None = None,
) -> dict[str, str]:
    env = os.environ.copy()
    python_paths = [str(module.path.parent), str(ROOT / "scripts")]
    inherited_python_path = env.get("PYTHONPATH")
    if inherited_python_path:
        python_paths.append(inherited_python_path)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("MINGLI_PYTHON", sys.executable)
    if allocated_slots is not None:
        if module.label == (
            "test_v51_provider_completeness.py::"
            "CanonicalMatrixSnapshotTests"
        ):
            env.setdefault("MINGLI_MATRIX_JOBS", str(min(8, allocated_slots)))
        if module.label in {
            "test_v51_remaining_provider_replays.py",
        }:
            env.setdefault("MINGLI_AUDIT_JOBS", str(allocated_slots))
    return env


def run_module(
    module: TestModule,
    *,
    verbose: bool,
    allocated_slots: int | None = None,
) -> TestResult:
    command = [sys.executable, "-B", "-m", "unittest"]
    if module.unittest_target is None:
        command.extend(
            [
                "discover",
                "-s",
                str(module.path.parent),
                "-p",
                module.path.name,
            ]
        )
    else:
        command.append(module.unittest_target)
    if verbose:
        command.append("-v")
    started_at = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=_child_environment(module, allocated_slots=allocated_slots),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    elapsed_seconds = time.monotonic() - started_at
    matches = TEST_COUNT_RE.findall(completed.stdout)
    test_count = int(matches[-1]) if matches else 0
    return TestResult(
        module=module,
        returncode=completed.returncode,
        output=completed.stdout,
        test_count=test_count,
        elapsed_seconds=elapsed_seconds,
    )


def _report_progress(result: TestResult) -> None:
    status = "PASS" if result.returncode == 0 else "FAIL"
    print(
        f"[{status}] {result.module.label} "
        f"tests={result.test_count} elapsed={result.elapsed_seconds:.2f}s",
        flush=True,
    )


def _run_parallel(
    modules: Sequence[TestModule],
    *,
    jobs: int,
    verbose: bool,
) -> list[TestResult]:
    if not modules:
        return []
    worker_count = min(jobs, len(modules))
    results: list[TestResult] = []
    pending = list(modules)
    available_slots = jobs
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures: dict[Future[TestResult], tuple[TestModule, int]] = {}
        while pending or futures:
            while pending:
                runnable_index = next(
                    (
                        index
                        for index, module in enumerate(pending)
                        if min(module.process_slots, jobs) <= available_slots
                    ),
                    None,
                )
                if runnable_index is None:
                    break
                module = pending.pop(runnable_index)
                reserved_slots = min(module.process_slots, jobs)
                available_slots -= reserved_slots
                future = executor.submit(
                    run_module,
                    module,
                    verbose=verbose,
                    allocated_slots=reserved_slots,
                )
                futures[future] = (module, reserved_slots)
            if not futures:
                raise RuntimeError("parallel scheduler could not reserve a test target")
            completed, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in completed:
                _module, reserved_slots = futures.pop(future)
                available_slots += reserved_slots
                result = future.result()
                results.append(result)
                _report_progress(result)
    return results


def _run_serial(modules: Sequence[TestModule], *, verbose: bool) -> list[TestResult]:
    results = []
    for module in modules:
        result = run_module(module, verbose=verbose)
        results.append(result)
        _report_progress(result)
    return results


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run unittest files in bounded parallel child processes.",
    )
    parser.add_argument(
        "--start-directory",
        type=Path,
        default=DEFAULT_START_DIRECTORY,
        help="directory to search (default: scripts)",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help="test filename glob (default: test_*.py)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=_positive_jobs,
        default=None,
        help="parallel process budget (default: auto, capped at 10)",
    )
    parser.add_argument(
        "--research-root",
        type=Path,
        default=None,
        help=(
            "external source tree used by fulltext verification tests; "
            "defaults to MINGLI_RESEARCH_ROOT"
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="show scheduling lanes without running tests",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="run each unittest module with verbose output",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    jobs = args.jobs if args.jobs is not None else _default_jobs()
    configured_research_root = args.research_root
    if configured_research_root is None:
        environment_root = os.environ.get("MINGLI_RESEARCH_ROOT")
        configured_research_root = Path(environment_root) if environment_root else None
    if configured_research_root is not None:
        research_root = configured_research_root.expanduser().resolve()
        if not research_root.is_dir():
            print(
                f"error: research root does not exist: {research_root}",
                file=sys.stderr,
            )
            return 2
        os.environ["MINGLI_RESEARCH_ROOT"] = str(research_root)
    try:
        modules = discover_modules(args.start_directory, args.pattern)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not modules:
        print("error: no test modules matched", file=sys.stderr)
        return 2

    parallel_modules = [module for module in modules if not module.serial]
    serial_modules = [module for module in modules if module.serial]
    print(
        f"test plan: targets={len(modules)} "
        f"modules={len({module.path for module in modules})} workers={jobs} "
        f"parallel={len(parallel_modules)} serial={len(serial_modules)}",
        flush=True,
    )
    if args.list:
        for module in parallel_modules:
            print(f"[parallel] {module.label}")
        for module in serial_modules:
            print(f"[serial] {module.label}")
        return 0

    matrix_target = (
        "test_v51_provider_completeness.py::"
        "CanonicalMatrixSnapshotTests"
    )
    with tempfile.TemporaryDirectory(prefix="mingli-test-session-") as session:
        os.environ["MINGLI_TEST_SESSION_DIR"] = session
        os.environ["MINGLI_MATRIX_SESSION_EXPECTED"] = (
            "1" if any(module.label == matrix_target for module in modules) else "0"
        )
        started_at = time.monotonic()
        if parallel_modules and serial_modules and jobs > 1:
            with ThreadPoolExecutor(max_workers=2) as lanes:
                parallel_future = lanes.submit(
                    _run_parallel,
                    parallel_modules,
                    jobs=jobs - 1,
                    verbose=args.verbose,
                )
                serial_future = lanes.submit(
                    _run_serial,
                    serial_modules,
                    verbose=args.verbose,
                )
                results = parallel_future.result()
                results.extend(serial_future.result())
        else:
            results = _run_parallel(
                parallel_modules,
                jobs=jobs,
                verbose=args.verbose,
            )
            results.extend(_run_serial(serial_modules, verbose=args.verbose))
        elapsed_seconds = time.monotonic() - started_at
        failures = [result for result in results if result.returncode != 0]
        if failures:
            print("\nFailure details:")
            for result in failures:
                print(f"\n===== {result.module.label} =====")
                print(result.output.rstrip())
        test_count = sum(result.test_count for result in results)
        print(
            f"summary: targets={len(results)} "
            f"modules={len({result.module.path for result in results})} tests={test_count} "
            f"failed_modules={len(failures)} elapsed={elapsed_seconds:.2f}s",
            flush=True,
        )
        return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
