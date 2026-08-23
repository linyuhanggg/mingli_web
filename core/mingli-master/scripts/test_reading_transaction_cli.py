"""The production CLI is one JSON codec: one Command in, one Result out."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reading_engine.interface_contracts import Describe

ROOT = Path(__file__).resolve().parents[1]


def _run(entry: list[str], stdin_text: str, home_dir: str) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "scripts")
    environment.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    # The codec accepts no caller paths: its store root is fixed under HOME,
    # so tests isolate persistence by pointing HOME at a scratch directory.
    environment["HOME"] = home_dir
    return subprocess.run(
        [*entry],
        input=stdin_text,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=environment,
    )


class JsonCodecCliTests(unittest.TestCase):
    def _codec_entry(self) -> list[str]:
        return [sys.executable, "-B", str(ROOT / "scripts/reading_transaction.py")]

    def test_stdout_carries_exactly_one_result_json(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir:
            completed = _run(
                self._codec_entry(),
                json.dumps(Describe().to_dict()),
                home_dir,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, completed.stdout)
        payload = json.loads(lines[0])
        self.assertEqual(payload.get("kind"), "described")
        self.assertTrue(payload.get("capabilities"))

    def test_malformed_stdin_is_a_parsable_stopped_error(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir:
            completed = _run(self._codec_entry(), "{broken", home_dir)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout.strip())
        self.assertEqual(payload.get("kind"), "stopped")
        self.assertEqual(payload.get("reason"), "error")
        self.assertTrue(str(payload.get("public_copy") or "").strip())
        self.assertEqual(
            payload.get("failure"),
            {
                "schema_version": "mingli-runtime-failure/v1",
                "code": "input_contract.malformed_json",
                "category": "input_contract",
                "retryable": False,
            },
        )

    def test_cli_offers_no_subcommands_or_transaction_paths(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "scripts/reading_transaction.py"),
                "capabilities",
            ],
            input="{}",
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env={
                **os.environ,
                "PYTHONPATH": str(ROOT / "scripts"),
            },
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unrecognized arguments", completed.stderr)

    def test_launcher_rejects_probe_and_run_modes(self) -> None:
        for retired in ("--probe", "--run"):
            with self.subTest(mode=retired):
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(ROOT / "scripts/runtime_launcher.py"),
                        retired,
                    ],
                    input="{}",
                    capture_output=True,
                    text=True,
                    cwd=str(ROOT),
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
                combined = completed.stdout + completed.stderr
                self.assertNotIn("mingli-runtime-v1", combined)


if __name__ == "__main__":
    unittest.main()
