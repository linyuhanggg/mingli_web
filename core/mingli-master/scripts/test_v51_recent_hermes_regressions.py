#!/usr/bin/env python3
"""Regression coverage for the recent Hermes conversation audit.

These tests stay on the portable Skill surface.  They deliberately do not
depend on, patch, or special-case any Hermes/Gateway implementation.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reading_engine.interface import ReadingInterface
from reading_engine.interface_contracts import (
    Accepted,
    Describe,
    HorizonSelection,
    IntentSelection,
    Prepare,
    Prepared,
    Stopped,
)


ROOT = Path(__file__).resolve().parents[1]
COORDS = {
    "longitude": 119.2965,
    "latitude": 26.0745,
    "coordinate_source": "regression-fixture",
}


def _bazi_command(facts: dict[str, object]) -> Prepare:
    return Prepare(
        query="看命盘的整体倾向",
        intent=IntentSelection(
            subject_refs=("subject:test",),
            object_id="natal",
            dimension_ids=("overview",),
            horizon=HorizonSelection(kind_id="life"),
            capability_id="bazi",
        ),
        facts={"subject:test": facts},
    )


class BirthplaceTimePolicyRegressionTests(unittest.TestCase):
    def _interface(self) -> ReadingInterface:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return ReadingInterface(skill_root=ROOT, store_root=temporary.name)

    @staticmethod
    def _birth_facts() -> dict[str, object]:
        return {
            "birth_datetime_or_four_pillars": "1994-04-30T05:55:00",
            "timezone": "Asia/Shanghai",
            "location": "福建省福州市",
            "gender": "female",
        }

    def test_bazi_manifest_defaults_birth_time_to_local_apparent_solar(self) -> None:
        payload = json.loads(
            (ROOT / "resources/runtime/providers/bazi.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            payload["time_semantics"]["default_policy"],
            "local_apparent_solar-v1",
        )

    def test_birthplace_without_coordinates_requests_coordinates_not_civil(self) -> None:
        result = self._interface().execute(_bazi_command(self._birth_facts()))

        self.assertIsInstance(result, Stopped, result)
        assert isinstance(result, Stopped)
        self.assertEqual(result.reason, "need_input")
        self.assertIsNotNone(result.input_request)
        assert result.input_request is not None
        asked = {
            field.id
            for requirement in result.input_request.requirements
            for field in requirement.any_of
        }
        self.assertEqual(
            asked,
            {"longitude", "latitude", "coordinate_source"},
        )

    def test_omitted_policy_with_coordinates_uses_manifest_default(self) -> None:
        interface = self._interface()
        result = interface.execute(
            _bazi_command({**self._birth_facts(), **COORDS})
        )

        self.assertIsInstance(result, Prepared, result)
        assert isinstance(result, Prepared)
        token = interface.engine.token_store.resolve(result.state_token)
        self.assertIsNotNone(token)
        assert token is not None and token.reading_id is not None
        stored = interface.engine.store.load_prepared(token.reading_id)
        calendar = stored.calculation.facts["chart_facts"][
            "calendar_normalization"
        ]
        self.assertEqual(
            calendar["time_basis"]["policy"],
            "local_apparent_solar-v1",
        )


class InterpretiveBoundaryRegressionTests(unittest.TestCase):
    def test_non_verdict_candidates_publish_an_explicit_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            interface = ReadingInterface(skill_root=ROOT, store_root=temporary)
            result = interface.execute(
                _bazi_command(
                    {
                        "birth_datetime_or_four_pillars": [
                            "乙酉",
                            "辛巳",
                            "丙午",
                            "癸巳",
                        ],
                        "gender": "male",
                    }
                )
            )

        self.assertIsInstance(result, Prepared, result)
        assert isinstance(result, Prepared)
        limits = {
            item.kind_id: item.public_text for item in result.brief.limits
        }
        self.assertIn("limit.interpretive_verdict_unavailable", limits)
        self.assertIn("喜用忌神", limits["limit.interpretive_verdict_unavailable"])
        self.assertIn("不得", limits["limit.interpretive_verdict_unavailable"])


class HostControlSignalRegressionTests(unittest.TestCase):
    def test_describe_exposes_the_complete_transition_vocabulary(self) -> None:
        described = ReadingInterface(skill_root=ROOT).execute(Describe())
        self.assertEqual(described.kind, "described")
        self.assertEqual(described.transition_ids, ("correct", "restart"))
        self.assertEqual(
            described.to_dict()["transition_ids"], ["correct", "restart"]
        )

    def test_terminal_and_completion_signals_are_machine_readable(self) -> None:
        need_input = Stopped(reason="need_input", public_copy="请补资料。")
        error = Stopped(reason="error", public_copy="本轮未完成。")
        accepted = Accepted(state_token="opaque", public_copy="最终正文。")

        self.assertEqual(
            {
                key: need_input.to_dict()[key]
                for key in (
                    "continuation_allowed",
                    "terminal",
                    "completion_committed",
                )
            },
            {
                "continuation_allowed": True,
                "terminal": False,
                "completion_committed": False,
            },
        )
        self.assertEqual(
            {
                key: error.to_dict()[key]
                for key in (
                    "continuation_allowed",
                    "terminal",
                    "completion_committed",
                )
            },
            {
                "continuation_allowed": False,
                "terminal": True,
                "completion_committed": False,
            },
        )
        self.assertTrue(accepted.to_dict()["terminal"])
        self.assertTrue(accepted.to_dict()["completion_committed"])


class SkillInstructionRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.flat = cls.text.replace("\n", "")
        cls.bazi_boundary = (
            ROOT / "references/bazi-input-and-image-gate.md"
        ).read_text(encoding="utf-8").replace("\n", "")

    def test_old_conversations_are_not_valid_prepare_fact_sources(self) -> None:
        self.assertIn("跨会话搜索、长期记忆或旧会话记录", self.flat)
        self.assertIn("本轮确认后再提交", self.flat)
        self.assertIn("不能把检索结果直接填入 `facts`", self.flat)

    def test_hosts_must_use_declared_time_and_transition_defaults(self) -> None:
        self.assertIn(
            "`time_semantics.default_policy` is`local_apparent_solar-v1`",
            self.bazi_boundary,
        )
        self.assertIn("never silently falls back to `civil`", self.bazi_boundary)
        self.assertIn("普通续问提交 `transition=null`", self.flat)
        self.assertIn("不得自造 `expand`", self.flat)

    def test_stopped_error_cannot_be_relabelled_as_completed(self) -> None:
        self.assertIn("只有 `accepted` 才表示 Skill 已完成提交", self.flat)
        self.assertIn("不得沿用失败分支的分数", self.flat)


if __name__ == "__main__":
    unittest.main()
