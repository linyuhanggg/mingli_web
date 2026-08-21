#!/usr/bin/env python3
"""Public-contract tests for the repository's parallel unittest runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_test_suite.py"


class ParallelTestRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.tests_dir = Path(self._temporary_directory.name)

    def _write_test(self, name: str, body: str) -> None:
        (self.tests_dir / name).write_text(
            textwrap.dedent(body),
            encoding="utf-8",
        )

    def _run(
        self,
        *arguments: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        child_env = os.environ.copy()
        if env:
            child_env.update(env)
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(RUNNER),
                "--start-directory",
                str(self.tests_dir),
                *arguments,
            ],
            cwd=ROOT,
            env=child_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def test_list_exposes_parallel_and_serial_lanes(self) -> None:
        self._write_test(
            "test_fast.py",
            """
            import unittest

            class FastTests(unittest.TestCase):
                def test_ok(self):
                    self.assertTrue(True)
            """,
        )
        self._write_test(
            "test_release_deploy.py",
            """
            import unittest

            class ReleaseTests(unittest.TestCase):
                def test_ok(self):
                    self.assertTrue(True)
            """,
        )

        completed = self._run("--jobs", "3", "--list")

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("workers=3", completed.stdout)
        self.assertIn("[parallel] test_fast.py", completed.stdout)
        self.assertIn("[serial] test_release_deploy.py", completed.stdout)

    def test_provider_completeness_starts_in_parallel_lane(self) -> None:
        self._write_test(
            "test_v51_provider_completeness.py",
            """
            import unittest

            class ProviderCompletenessTests(unittest.TestCase):
                def test_ok(self):
                    self.assertTrue(True)
            """,
        )

        completed = self._run("--jobs", "3", "--list")

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn(
            "[parallel] test_v51_provider_completeness.py",
            completed.stdout,
        )
        self.assertNotIn(
            "[serial] test_v51_provider_completeness.py",
            completed.stdout,
        )

    def test_explicit_long_audit_module_is_sharded_by_test_case_class(self) -> None:
        self._write_test(
            "test_v51_dedicated_audit_contract.py",
            """
            import unittest

            class FirstAuditTests(unittest.TestCase):
                def test_first(self):
                    self.assertTrue(True)

            class SecondAuditTests(unittest.TestCase):
                def test_second(self):
                    self.assertTrue(True)
            """,
        )

        listed = self._run("--jobs", "2", "--list")
        completed = self._run("--jobs", "2")

        self.assertEqual(listed.returncode, 0, listed.stdout)
        self.assertIn(
            "[parallel] test_v51_dedicated_audit_contract.py::FirstAuditTests",
            listed.stdout,
        )
        self.assertIn(
            "[parallel] test_v51_dedicated_audit_contract.py::SecondAuditTests",
            listed.stdout,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("tests=2", completed.stdout)

    def test_long_running_targets_are_scheduled_before_fast_tail(self) -> None:
        self._write_test(
            "test_fast.py",
            """
            import unittest

            class FastTests(unittest.TestCase):
                def test_fast(self):
                    self.assertTrue(True)
            """,
        )
        self._write_test(
            "test_v51_dedicated_audit_contract.py",
            """
            import unittest

            class DedicatedAuditMachineContractTests(unittest.TestCase):
                def test_audit(self):
                    self.assertTrue(True)
            """,
        )

        completed = self._run("--jobs", "1", "--list")

        self.assertEqual(completed.returncode, 0, completed.stdout)
        heavy = completed.stdout.index("DedicatedAuditMachineContractTests")
        fast = completed.stdout.index("[parallel] test_fast.py")
        self.assertLess(heavy, fast, completed.stdout)

    def test_nested_parallel_target_reserves_its_process_budget(self) -> None:
        event_log = self.tests_dir / "resource-events.jsonl"
        recorder = """
            import json
            import os
            from pathlib import Path
            import time

            def record(phase):
                payload = json.dumps({
                    "name": Path(__file__).name,
                    "phase": phase,
                    "time": time.monotonic_ns(),
                }) + "\\n"
                descriptor = os.open(
                    os.environ["MINGLI_TEST_EVENT_LOG"],
                    os.O_APPEND | os.O_CREAT | os.O_WRONLY,
                    0o600,
                )
                try:
                    os.write(descriptor, payload.encode("utf-8"))
                finally:
                    os.close(descriptor)
        """
        self._write_test(
            "test_v51_provider_completeness.py",
            recorder
            + """
            import unittest

            class CanonicalMatrixSnapshotTests(unittest.TestCase):
                def test_heavy(self):
                    record("start")
                    time.sleep(0.25)
                    record("end")
            """,
        )
        self._write_test(
            "test_fast.py",
            recorder
            + """
            import unittest

            class FastTests(unittest.TestCase):
                def test_fast(self):
                    record("start")
                    time.sleep(0.10)
                    record("end")
            """,
        )

        completed = self._run(
            "--jobs",
            "4",
            env={"MINGLI_TEST_EVENT_LOG": str(event_log)},
        )

        self.assertEqual(completed.returncode, 0, completed.stdout)
        events = [
            json.loads(line)
            for line in event_log.read_text(encoding="utf-8").splitlines()
        ]
        intervals: dict[str, dict[str, int]] = {}
        for event in events:
            intervals.setdefault(event["name"], {})[event["phase"]] = event["time"]
        heavy = intervals["test_v51_provider_completeness.py"]
        fast = intervals["test_fast.py"]
        self.assertGreaterEqual(fast["start"], heavy["end"])

    def test_reduced_budget_is_forwarded_to_nested_matrix_pool(self) -> None:
        self._write_test(
            "test_v51_provider_completeness.py",
            """
            import os
            import unittest

            class CanonicalMatrixSnapshotTests(unittest.TestCase):
                def test_budget(self):
                    self.assertEqual(os.environ["MINGLI_MATRIX_JOBS"], "2")
            """,
        )

        completed = self._run("--jobs", "2")

        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_dedicated_mutations_are_sharded_by_test_method(self) -> None:
        self._write_test(
            "test_v51_dedicated_audit_contract.py",
            """
            import unittest

            class DedicatedAuditMachineContractTests(unittest.TestCase):
                def test_first_provider(self):
                    self.assertTrue(True)

                def test_second_provider(self):
                    self.assertTrue(True)
            """,
        )

        listed = self._run("--jobs", "2", "--list")
        completed = self._run("--jobs", "2")

        self.assertEqual(listed.returncode, 0, listed.stdout)
        self.assertIn(
            "DedicatedAuditMachineContractTests.test_first_provider",
            listed.stdout,
        )
        self.assertIn(
            "DedicatedAuditMachineContractTests.test_second_provider",
            listed.stdout,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("tests=2", completed.stdout)

    def test_serial_lane_stays_ordered_but_overlaps_parallel_lane(self) -> None:
        event_log = self.tests_dir / "events.jsonl"
        test_body = """
            import json
            import os
            from pathlib import Path
            import time
            import unittest

            def record(phase):
                payload = json.dumps({
                    "name": Path(__file__).name,
                    "phase": phase,
                    "time": time.monotonic_ns(),
                }) + "\\n"
                descriptor = os.open(
                    os.environ["MINGLI_TEST_EVENT_LOG"],
                    os.O_APPEND | os.O_CREAT | os.O_WRONLY,
                    0o600,
                )
                try:
                    os.write(descriptor, payload.encode("utf-8"))
                finally:
                    os.close(descriptor)

            class TimedTests(unittest.TestCase):
                def test_timed(self):
                    record("start")
                    time.sleep(0.35)
                    record("end")
        """
        self._write_test("test_parallel_a.py", test_body)
        self._write_test("test_parallel_b.py", test_body)
        self._write_test("test_release_deploy.py", test_body)

        completed = self._run(
            "--jobs",
            "3",
            env={"MINGLI_TEST_EVENT_LOG": str(event_log)},
        )

        self.assertEqual(completed.returncode, 0, completed.stdout)
        event_lines = event_log.read_text(encoding="utf-8").splitlines()
        events = [json.loads(line) for line in event_lines]
        intervals: dict[str, dict[str, int]] = {}
        for event in events:
            intervals.setdefault(event["name"], {})[event["phase"]] = event["time"]

        a = intervals["test_parallel_a.py"]
        b = intervals["test_parallel_b.py"]
        serial = intervals["test_release_deploy.py"]
        self.assertLess(max(a["start"], b["start"]), min(a["end"], b["end"]))
        self.assertLess(serial["start"], max(a["end"], b["end"]))

    def test_failure_is_aggregated_and_returns_nonzero(self) -> None:
        self._write_test(
            "test_good.py",
            """
            import unittest

            class GoodTests(unittest.TestCase):
                def test_good(self):
                    self.assertEqual(2 + 2, 4)
            """,
        )
        self._write_test(
            "test_bad.py",
            """
            import unittest

            class BadTests(unittest.TestCase):
                def test_bad(self):
                    self.assertEqual("actual", "expected")
            """,
        )

        completed = self._run("--jobs", "2")

        self.assertNotEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("[FAIL] test_bad.py", completed.stdout)
        self.assertIn("FAILED (failures=1)", completed.stdout)
        self.assertIn("modules=2", completed.stdout)

    def test_research_root_is_explicitly_forwarded_to_children(self) -> None:
        research_root = self.tests_dir / "research tree"
        research_root.mkdir()
        self._write_test(
            "test_research_root.py",
            f"""
            import os
            from pathlib import Path
            import unittest

            class ResearchRootTests(unittest.TestCase):
                def test_exact_root(self):
                    self.assertEqual(
                        Path(os.environ["MINGLI_RESEARCH_ROOT"]),
                        Path({str(research_root.resolve())!r}),
                    )
            """,
        )

        completed = self._run(
            "--jobs",
            "1",
            "--research-root",
            str(research_root),
            env={"MINGLI_RESEARCH_ROOT": str(self.tests_dir / "wrong-root")},
        )

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("tests=1", completed.stdout)

    def test_invalid_research_root_fails_before_running_tests(self) -> None:
        self._write_test(
            "test_never_runs.py",
            """
            import unittest

            class NeverRunsTests(unittest.TestCase):
                def test_never_runs(self):
                    self.fail("runner should reject the root first")
            """,
        )

        missing = self.tests_dir / "missing-research"
        completed = self._run("--research-root", str(missing))

        self.assertEqual(completed.returncode, 2, completed.stdout)
        self.assertIn("research root does not exist", completed.stdout)
        self.assertNotIn("test plan:", completed.stdout)


if __name__ == "__main__":
    unittest.main()
