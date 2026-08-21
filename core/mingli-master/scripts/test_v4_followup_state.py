"""Continuity is carried by opaque state tokens, never by wording."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reading_engine.contracts import (
    AcceptedReading,
    InternalFailure,
    NeedUserFact,
    PreparedReading,
)
from test_reading_engine_v2 import (
    StaticProvider,
    build_engine,
    provider_request,
)


class TokenStateTransitionTests(unittest.TestCase):
    """External callers only ever hold one opaque token plus a transition."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.provider = StaticProvider()
        self.engine = build_engine(Path(self._tmp.name), self.provider)
        self.descriptor = self.provider.descriptor

    def _accept(self, token: str, text: str = "事实已列明。\n第一轮结论。") -> str:
        accepted = self.engine.complete_turn(token, text)
        self.assertIsInstance(accepted, AcceptedReading, accepted)
        return text

    def test_no_token_starts_a_new_root(self) -> None:
        turn = self.engine.prepare_turn(self.descriptor, provider_request())

        self.assertIsInstance(turn.result, PreparedReading, turn.result)
        self.assertIsNotNone(turn.state_token)
        record = self.engine.token_store.resolve(turn.state_token)
        self.assertEqual(record.phase, "prepared")

    def test_pending_token_merges_facts_without_published_question(self) -> None:
        missing = provider_request(
            facts={
                "subject:test": {
                    "event_datetime_or_reference_datetime": (
                        "2026-07-22T22:13:00+08:00"
                    ),
                }
            }
        )
        first = self.engine.prepare_turn(self.descriptor, missing)
        self.assertIsInstance(first.result, NeedUserFact, first.result)
        self.assertIsNotNone(first.state_token)

        supplement = provider_request(
            "补充时区",
            facts={"subject:test": {"timezone": "Asia/Shanghai"}},
        )
        second = self.engine.prepare_turn(
            self.descriptor, supplement, state_token=first.state_token
        )

        self.assertIsInstance(second.result, PreparedReading, second.result)
        self.assertIsNotNone(second.state_token)
        # The pending token is promoted in place: the host keeps one identity
        # for the whole pending->prepared lifecycle, so a repeated supplement
        # of the same pending token converges on the same prepared result.
        self.assertEqual(second.state_token, first.state_token)

    def test_accepted_token_continues_implicitly(self) -> None:
        root = self.engine.prepare_turn(self.descriptor, provider_request())
        self.assertIsInstance(root.result, PreparedReading, root.result)
        text = self._accept(root.state_token)

        turn = self.engine.prepare_turn(
            self.descriptor,
            provider_request("那她会主动联系吗？"),
            state_token=root.state_token,
        )

        self.assertIsInstance(turn.result, PreparedReading, turn.result)
        self.assertEqual(turn.result.reading_id, root.result.reading_id)
        self.assertEqual(turn.result.version, 2)
        self.assertEqual(turn.prior_answer, text)
        staged = self.engine.store.load_prepared(turn.result.reading_id)
        self.assertEqual(staged.parent_reading_id, root.result.reading_id)
        self.assertEqual(staged.root_reading_id, root.result.reading_id)
        self.assertEqual(staged.action, "continue")

    def test_explicit_correct_supersedes_the_prior_version(self) -> None:
        root = self.engine.prepare_turn(self.descriptor, provider_request())
        self.assertIsInstance(root.result, PreparedReading, root.result)
        self._accept(root.state_token)

        turn = self.engine.prepare_turn(
            self.descriptor,
            provider_request(
                "时间记错了，换成晚上九点",
                facts={
                    "subject:test": {
                        "event_datetime_or_reference_datetime": (
                            "2026-07-22T21:00:00+08:00"
                        ),
                        "timezone": "Asia/Shanghai",
                    }
                },
            ),
            state_token=root.state_token,
            transition="correct",
        )

        self.assertIsInstance(turn.result, PreparedReading, turn.result)
        self.assertIsNone(turn.prior_answer)
        staged = self.engine.store.load_prepared(turn.result.reading_id)
        self.assertEqual(staged.parent_reading_id, root.result.reading_id)
        self.assertEqual(staged.action, "correct")

    def test_explicit_restart_creates_a_child_reading(self) -> None:
        root = self.engine.prepare_turn(self.descriptor, provider_request())
        self.assertIsInstance(root.result, PreparedReading, root.result)
        self._accept(root.state_token)

        turn = self.engine.prepare_turn(
            self.descriptor,
            provider_request("重新起一局再看"),
            state_token=root.state_token,
            transition="restart",
        )

        self.assertIsInstance(turn.result, PreparedReading, turn.result)
        self.assertNotEqual(turn.result.reading_id, root.result.reading_id)
        staged = self.engine.store.load_prepared(turn.result.reading_id)
        self.assertEqual(staged.parent_reading_id, root.result.reading_id)
        self.assertEqual(staged.root_reading_id, root.result.reading_id)
        self.assertEqual(staged.action, "recast")

    def test_external_continue_transition_is_rejected(self) -> None:
        root = self.engine.prepare_turn(self.descriptor, provider_request())
        self._accept(root.state_token)

        turn = self.engine.prepare_turn(
            self.descriptor,
            provider_request("继续"),
            state_token=root.state_token,
            transition="continue",
        )

        self.assertIsInstance(turn.result, InternalFailure)
        self.assertEqual(turn.result.code, "invalid_transition")

    def test_stale_parent_cannot_seat_a_second_child(self) -> None:
        root = self.engine.prepare_turn(self.descriptor, provider_request())
        self._accept(root.state_token)
        first = self.engine.prepare_turn(
            self.descriptor,
            provider_request("那她会主动联系吗？"),
            state_token=root.state_token,
        )
        self.assertIsInstance(first.result, PreparedReading, first.result)

        second = self.engine.prepare_turn(
            self.descriptor,
            provider_request("完全不同的另一个追问"),
            state_token=root.state_token,
        )

        self.assertIsInstance(second.result, InternalFailure)
        self.assertEqual(second.result.code, "token_conflict")

    def test_replaying_the_same_lineage_turn_reuses_the_child(self) -> None:
        root = self.engine.prepare_turn(self.descriptor, provider_request())
        self._accept(root.state_token)
        first = self.engine.prepare_turn(
            self.descriptor,
            provider_request("那她会主动联系吗？"),
            state_token=root.state_token,
        )
        self.assertIsInstance(first.result, PreparedReading, first.result)

        replay = self.engine.prepare_turn(
            self.descriptor,
            provider_request("那她会主动联系吗？"),
            state_token=root.state_token,
        )

        self.assertIsInstance(replay.result, PreparedReading, replay.result)
        self.assertEqual(replay.result.reading_id, first.result.reading_id)
        self.assertEqual(self.provider.calls, 2)

    def test_unknown_token_fails_closed(self) -> None:
        turn = self.engine.prepare_turn(
            self.descriptor,
            provider_request("随便问问"),
            state_token="never-issued",
        )

        self.assertIsInstance(turn.result, InternalFailure)
        self.assertEqual(turn.result.code, "unknown_state_token")


if __name__ == "__main__":
    unittest.main()
