"""A shared OS account must not make two Skill installations share a reading store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters import json_cli
from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import (
    Complete,
    HorizonSelection,
    IntentSelection,
    Prepare,
    Prepared,
    Stopped,
)


ROOT = Path(__file__).resolve().parents[1]


def _prepare() -> Prepare:
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
                "event_datetime_or_reference_datetime": "2026-07-22T22:13:00+08:00",
                "timezone": "Asia/Shanghai",
            }
        },
    )


class ProfileStoreIsolationTests(unittest.TestCase):
    def test_explicit_state_base_still_scopes_each_installation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            configured_base = Path(temporary) / "state-base"
            environment = {
                "HOME": str(home),
                "MINGLI_STORE_ROOT": str(configured_base),
            }
            first = json_cli.resolve_store_root(
                Path(temporary) / "install-default",
                environment=environment,
            )
            second = json_cli.resolve_store_root(
                Path(temporary) / "install-liujing",
                environment=environment,
            )

        self.assertNotEqual(first, second)
        self.assertTrue(first.is_relative_to(configured_base.resolve()))
        self.assertTrue(second.is_relative_to(configured_base.resolve()))

    def test_same_home_distinct_installations_resolve_distinct_state_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            environment = {"HOME": str(home)}
            first = json_cli.resolve_store_root(
                Path(temporary) / "install-default", environment=environment
            )
            second = json_cli.resolve_store_root(
                Path(temporary) / "install-liujing", environment=environment
            )

        self.assertNotEqual(first, second)
        expected_parent = (home / ".local/state/mingli-master/instances").resolve()
        self.assertTrue(first.is_relative_to(expected_parent))
        self.assertTrue(second.is_relative_to(expected_parent))

    def test_token_cannot_cross_installation_state_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            environment = {
                "HOME": str(home),
                "MINGLI_STORE_ROOT": str(Path(temporary) / "shared-base"),
            }
            default_root = json_cli.resolve_store_root(
                Path(temporary) / "install-default", environment=environment
            )
            liujing_root = json_cli.resolve_store_root(
                Path(temporary) / "install-liujing", environment=environment
            )
            default = ReadingInterface(skill_root=ROOT, store_root=default_root)
            liujing = ReadingInterface(skill_root=ROOT, store_root=liujing_root)

            prepared = default.execute(_prepare())
            self.assertIsInstance(prepared, Prepared)
            foreign = liujing.execute(
                Complete(state_token=prepared.state_token, public_copy="不应跨 profile 接受")
            )

        self.assertIsInstance(foreign, Stopped)
        self.assertEqual(foreign.reason, "error")


if __name__ == "__main__":
    unittest.main()
