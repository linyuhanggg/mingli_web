"""One JSON contract across in-process, subprocess CLI, and codec fakes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from reading_engine.interface_contracts import (
    Accepted,
    Complete,
    Describe,
    Prepare,
    Prepared,
    HorizonSelection,
    IntentSelection,
    command_from_dict,
    result_from_dict,
)

ROOT = Path(__file__).resolve().parents[1]


def _store_under(home: Path) -> Path:
    # The production codec scopes state to the installed artifact as well as
    # HOME; this reproduces the same namespace for an in-process host.
    from adapters import json_cli

    return json_cli.resolve_store_root(ROOT, environment={"HOME": str(home)})


def _run_cli(payload: dict, home: Path) -> dict:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "scripts")
    environment.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    environment["HOME"] = str(home)
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(ROOT / "scripts/adapters/json_cli.py"),
        ],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, completed.stdout
    return json.loads(lines[0])


def _run_installed_runner(payload: dict, home: Path) -> dict:
    environment = dict(os.environ)
    environment["HOME"] = str(home)
    environment["MINGLI_PYTHON"] = str(Path(sys.executable).resolve())
    environment.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    completed = subprocess.run(
        [str(ROOT / "scripts/run_reading_transaction.sh")],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, completed.stdout
    return json.loads(lines[0])


def _prepare_payload() -> dict:
    return Prepare(
        query="她现在大概在哪里？",
        intent=IntentSelection(
            subject_refs=("subject:test",),
            object_id="concrete_event",
            dimension_ids=("outcome",),
            horizon=HorizonSelection(kind_id="instant"),
            capability_id="liuren",
        ),
        facts={
            "subject:test": {
                "event_datetime_or_reference_datetime": (
                    "2026-07-22T22:13:00+08:00"
                ),
                "timezone": "Asia/Shanghai",
            }
        },
    ).to_dict()


def _liuren_specific_event_payload() -> dict:
    return Prepare(
        query="起卦算下我对象此时此刻在干嘛",
        intent=IntentSelection(
            subject_refs=("subject:target",),
            object_id="concrete_event",
            dimension_ids=("state", "work", "location", "relationship"),
            horizon=HorizonSelection(kind_id="instant"),
            capability_id="liuren",
        ),
        facts={
            "subject:target": {
                "event_datetime_or_reference_datetime": (
                    "2026-07-30T21:29:29+08:00"
                ),
                "timezone": "Asia/Shanghai",
            }
        },
    ).to_dict()


class CrossHostContractTests(unittest.TestCase):
    def test_describe_is_identical_in_process_and_via_cli(self) -> None:
        from reading_engine.interface import ReadingInterface

        with tempfile.TemporaryDirectory() as store_root:
            via_cli = _run_cli(Describe().to_dict(), Path(store_root))
        direct = ReadingInterface(skill_root=ROOT).execute(Describe())
        self.assertEqual(via_cli, direct.to_dict())

    def test_prepare_then_complete_share_bytes_across_processes(self) -> None:
        from reading_engine.interface import ReadingInterface

        with tempfile.TemporaryDirectory() as store_root:
            prepared_payload = _run_cli(_prepare_payload(), Path(store_root))
            self.assertEqual(prepared_payload.get("kind"), "prepared")
            token = prepared_payload["state_token"]
            self.assertTrue(token)
            draft = "事实已列明。\n候应偏向仍在熟悉场所，直接联系更省力。"
            accepted_payload = _run_cli(
                Complete(state_token=token, public_copy=draft).to_dict(),
                Path(store_root),
            )
            self.assertEqual(accepted_payload.get("kind"), "accepted")
            self.assertEqual(accepted_payload.get("public_copy"), draft)
            # a second host process replays byte-identical Accepted
            replay_payload = _run_cli(
                Complete(
                    state_token=token,
                    public_copy="完全不同的第二稿",
                ).to_dict(),
                Path(store_root),
            )
            self.assertEqual(
                replay_payload.get("public_copy"),
                accepted_payload.get("public_copy"),
            )
            # in-process host over the same store sees the same bytes
            interface = ReadingInterface(
                skill_root=ROOT, store_root=_store_under(Path(store_root))
            )
            direct = interface.execute(
                Complete(state_token=token, public_copy="第三稿")
            )
            self.assertIsInstance(direct, Accepted)
            self.assertEqual(
                direct.public_copy, accepted_payload.get("public_copy")
            )

    def test_liuren_specific_event_runner_prepares_and_commits(self) -> None:
        with tempfile.TemporaryDirectory() as store_root:
            prepared_payload = _run_installed_runner(
                _liuren_specific_event_payload(), Path(store_root)
            )
            self.assertEqual(prepared_payload.get("kind"), "prepared", prepared_payload)
            accepted_payload = _run_installed_runner(
                Complete(
                    state_token=str(prepared_payload["state_token"]),
                    public_copy="本轮仅按已列明的材料作答。",
                ).to_dict(),
                Path(store_root),
            )

        self.assertEqual(accepted_payload.get("kind"), "accepted", accepted_payload)
        self.assertEqual(
            accepted_payload.get("public_copy"), "本轮仅按已列明的材料作答。"
        )

    def test_malformed_stdin_yields_parsable_stopped_error(self) -> None:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "scripts")
        with tempfile.TemporaryDirectory() as store_root:
            environment["HOME"] = store_root
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(ROOT / "scripts/adapters/json_cli.py"),
                ],
                input="{not json",
                capture_output=True,
                text=True,
                cwd=str(ROOT),
                env=environment,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout.strip())
        self.assertEqual(payload.get("kind"), "stopped")
        self.assertEqual(payload.get("reason"), "error")
        self.assertTrue(str(payload.get("public_copy") or "").strip())

    def test_unknown_command_kind_yields_stopped_error(self) -> None:
        with tempfile.TemporaryDirectory() as store_root:
            payload = _run_cli({"kind": "probe"}, Path(store_root))
        self.assertEqual(payload.get("kind"), "stopped")
        self.assertEqual(payload.get("reason"), "error")
        self.assertTrue(str(payload.get("public_copy") or "").strip())

    def test_mcp_style_codec_round_trip_matches_direct_results(self) -> None:
        """An MCP-shaped host only maps dicts through the shared codec."""

        from reading_engine.interface import ReadingInterface

        interface = ReadingInterface(skill_root=ROOT)

        def mcp_fake(tool_arguments: dict) -> dict:
            command = command_from_dict(tool_arguments)
            return interface.execute(command).to_dict()

        direct = interface.execute(Describe()).to_dict()
        self.assertEqual(mcp_fake(Describe().to_dict()), direct)
        self.assertEqual(
            result_from_dict(mcp_fake(Describe().to_dict())).to_dict(),
            direct,
        )



class FixedCliSurfaceTests(unittest.TestCase):
    """The production CLI accepts no caller paths and no subcommands."""

    def test_cli_rejects_skill_dir_and_store_root_arguments(self) -> None:
        import io
        from unittest import mock

        from adapters import json_cli

        for forbidden in (["--skill-dir", "/tmp/x"], ["--store-root", "/tmp/x"]):
            with self.subTest(argument=forbidden[0]):
                with mock.patch("sys.stdin", io.StringIO("{}")), mock.patch(
                    "sys.stderr", io.StringIO()
                ):
                    with self.assertRaises(SystemExit) as caught:
                        json_cli.main(forbidden)
                self.assertNotEqual(caught.exception.code, 0)

    def test_launcher_forwards_no_arbitrary_argv(self) -> None:
        source = (ROOT / "scripts/runtime_launcher.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("--skill-dir", source)
        self.assertNotIn("--store-root", source)


if __name__ == "__main__":
    unittest.main()
