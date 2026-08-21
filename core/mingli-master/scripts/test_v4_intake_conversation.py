"""Conversation tests for stateful pending-input turns on the turn chain."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reading_engine.contracts import NeedUserFact, PreparedReading
from test_reading_engine_v2 import StaticProvider, build_engine, provider_request


class V4IntakeConversationTests(unittest.TestCase):
    def test_structured_supplement_resumes_after_engine_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = StaticProvider()
            first_engine = build_engine(root, provider)
            pending = first_engine.prepare_turn(
                provider.descriptor,
                provider_request(
                    "原问题：看看接下来两天的状态",
                    facts={
                        "subject:test": {
                            "event_datetime_or_reference_datetime": (
                                "2026-07-25T12:00:00+08:00"
                            )
                        }
                    },
                ),
            )
            self.assertIsInstance(pending.result, NeedUserFact)
            self.assertEqual(pending.result.missing_facts, ("timezone",))
            self.assertIsNotNone(pending.state_token)

            restarted_provider = StaticProvider()
            restarted = build_engine(root, restarted_provider)
            resumed = restarted.prepare_turn(
                restarted_provider.descriptor,
                provider_request(
                    "北京",
                    facts={
                        "subject:test": {
                            "timezone": "Asia/Shanghai",
                            "location": "北京",
                        }
                    },
                ),
                state_token=pending.state_token,
            )

            self.assertIsInstance(resumed.result, PreparedReading, resumed.result)
            staged = restarted.store.load_prepared(resumed.result.reading_id)
            self.assertEqual(staged.request.timezone, "Asia/Shanghai")
            self.assertEqual(
                staged.request.event_datetime, "2026-07-25T12:00:00+08:00"
            )

    def test_multiple_pending_rounds_accumulate_structured_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            provider = StaticProvider()
            engine = build_engine(Path(temporary), provider)
            first = engine.prepare_turn(
                provider.descriptor,
                provider_request(
                    "保留这一句作为原问题", facts={"subject:test": {}}
                ),
            )
            self.assertIsInstance(first.result, NeedUserFact)
            self.assertEqual(
                first.result.missing_facts,
                ("event_datetime_or_reference_datetime", "timezone"),
            )

            second = engine.prepare_turn(
                provider.descriptor,
                provider_request(
                    "一种从未见过的回答写法",
                    facts={
                        "subject:test": {
                            "event_datetime_or_reference_datetime": (
                                "2026-07-25T12:00:00+08:00"
                            )
                        }
                    },
                ),
                state_token=first.state_token,
            )
            self.assertIsInstance(second.result, NeedUserFact)
            self.assertEqual(second.result.missing_facts, ("timezone",))
            self.assertNotEqual(second.state_token, first.state_token)

            completed = engine.prepare_turn(
                provider.descriptor,
                provider_request(
                    "上海，用中国标准时间",
                    facts={"subject:test": {"timezone": "Asia/Shanghai"}},
                ),
                state_token=second.state_token,
            )

            self.assertIsInstance(
                completed.result, PreparedReading, completed.result
            )
            record = engine.store.load_prepared(completed.result.reading_id)
            self.assertEqual(
                record.request.event_datetime, "2026-07-25T12:00:00+08:00"
            )
            self.assertEqual(record.request.timezone, "Asia/Shanghai")

    def test_resume_requires_structured_mapping_not_reply_word_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            provider = StaticProvider()
            engine = build_engine(Path(temporary), provider)
            pending = engine.prepare_turn(
                provider.descriptor,
                provider_request(
                    "原问题",
                    facts={"subject:test": {"timezone": "Asia/Shanghai"}},
                ),
            )
            self.assertIsInstance(pending.result, NeedUserFact)
            self.assertEqual(
                pending.result.missing_facts,
                ("event_datetime_or_reference_datetime",),
            )

            unmapped = engine.prepare_turn(
                provider.descriptor,
                provider_request("北京", facts={"subject:test": {}}),
                state_token=pending.state_token,
            )

            self.assertIsInstance(unmapped.result, NeedUserFact)
            self.assertEqual(
                unmapped.result.missing_facts,
                ("event_datetime_or_reference_datetime",),
            )


if __name__ == "__main__":
    unittest.main()
