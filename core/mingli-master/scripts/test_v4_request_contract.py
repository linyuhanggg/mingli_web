"""Characterization tests for the caller-owned v4 request contract."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from reading_engine.contracts import ReadingRequest
from reading_engine.request_contract import (
    RequestContractError,
    validate_request_contract,
)


def _intent(
    *,
    reading_id: str | None = None,
    requested_method: str | None = "liuren",
) -> dict:
    return {
        "subject_refs": ["subject:test"],
        "calculation_object": "concrete_event",
        "question_dimensions": ["outcome"],
        "horizon": {"kind": "instant", "start": None, "end": None},
        "requested_method": requested_method,
        "requested_granularity": "directional",
        "continuity": {
            "reading_id": reading_id,
            "same_subject": reading_id is not None,
            "same_event": reading_id is not None,
        },
        "facts_present": [],
        "facts_corrected": [],
        "evidence_questions": ["哪些规则适用于当前事实"],
    }


class V4RequestContractTests(unittest.TestCase):
    def test_instant_horizon_requires_absent_or_same_point_boundaries(self) -> None:
        valid = _intent()
        valid["horizon"] = {
            "kind": "instant",
            "start": "2026-07-27",
            "end": "2026-07-27",
        }
        validate_request_contract(
            ReadingRequest(
                query="同点边界",
                action="new",
                system="liuren",
                intent=valid,
            )
        )

        for horizon in (
            {"kind": "instant", "start": "2026-07-27", "end": None},
            {"kind": "instant", "start": None, "end": "2026-07-27"},
            {
                "kind": "instant",
                "start": "2026-07-27",
                "end": "2026-07-28",
            },
        ):
            with self.subTest(horizon=horizon), self.assertRaisesRegex(
                RequestContractError,
                "instant boundaries must be absent or the same point",
            ):
                invalid = _intent()
                invalid["horizon"] = horizon
                validate_request_contract(
                    ReadingRequest(
                        query="非法瞬时边界",
                        action="new",
                        system="liuren",
                        intent=invalid,
                    )
                )

    def test_v4_request_requires_extensible_structured_intent(self) -> None:
        without_intent = ReadingRequest(
            query="任意原文",
            action="new",
            system="liuren",
        )

        with self.assertRaises(RequestContractError):
            validate_request_contract(without_intent)

        intent = {
            "subject_refs": ["subject-1"],
            "calculation_object": "concrete_event",
            "question_dimensions": ["outcome"],
            "horizon": {"kind": "instant", "start": None, "end": None},
            "requested_method": None,
            "requested_granularity": "directional",
            "continuity": {
                "reading_id": None,
                "same_subject": False,
                "same_event": False,
            },
            "facts_present": [],
            "facts_corrected": [],
            "evidence_questions": ["哪些规则适用于当前课体"],
            "caller_extension": {"任意新字段": "原样保留"},
        }
        with_intent = ReadingRequest(
            query="另一种任意原文",
            action="new",
            system="liuren",
            intent=intent,
        )

        validated = validate_request_contract(with_intent)

        self.assertEqual(validated.intent, intent)

    def test_every_v4_request_requires_a_structured_intent_frame(self) -> None:
        intent = {
            "subject_refs": ["subject:test"],
            "calculation_object": "concrete_event",
            "question_dimensions": ["outcome"],
            "horizon": {"kind": "instant", "start": None, "end": None},
            "requested_method": "liuren",
            "requested_granularity": "directional",
            "continuity": {
                "reading_id": None,
                "same_subject": False,
                "same_event": False,
            },
            "facts_present": [],
            "facts_corrected": [],
            "evidence_questions": ["哪些课体规则适用于当前问题"],
        }
        request = ReadingRequest(
            query="任意自然表达",
            action="new",
            system="liuren",
            intent=intent,
        )

        self.assertEqual(validate_request_contract(request).intent, intent)
        with self.assertRaises(RequestContractError):
            validate_request_contract(
                ReadingRequest(query="缺少 intent", action="new", system="liuren")
            )

    def test_actionless_production_prepare_rejects_before_legacy_routing(self) -> None:
        real_import = __import__

        def reject_legacy_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "legacy_v3" or name.startswith("legacy_v3."):
                raise AssertionError("legacy router was imported")
            return real_import(name, globals, locals, fromlist, level)

        with patch(
            "builtins.__import__",
            side_effect=reject_legacy_import,
        ):
            with self.assertRaises(RequestContractError):
                validate_request_contract(
                    ReadingRequest(query="missing v4 action")
                )

    def test_v4_production_import_graph_excludes_language_routing(self) -> None:
        scripts_dir = Path(__file__).resolve().parent
        probe = """
import sys
import reading_engine.factory
import reading_transaction
import reading_engine.request_contract as request_contract

forbidden = {"query_intent", "reading_engine.routing"}
loaded = forbidden.intersection(sys.modules)
if loaded:
    raise SystemExit("forbidden production imports: " + ", ".join(sorted(loaded)))
if "re" in request_contract.__dict__:
    raise SystemExit("request_contract must not import re")
"""
        environment = dict(os.environ)
        existing = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = (
            str(scripts_dir)
            if not existing
            else os.pathsep.join((str(scripts_dir), existing))
        )

        completed = subprocess.run(
            [sys.executable, "-c", probe],
            check=False,
            capture_output=True,
            text=True,
            cwd=scripts_dir.parent,
            env=environment,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_unseen_natural_language_is_not_parsed_by_engine(self) -> None:
        request = ReadingRequest(
            query="整点玄乎的瞅瞅她这会儿猫哪儿呢",
            action="new",
            system="liuren",
            intent=_intent(),
        )

        validated = validate_request_contract(request)

        self.assertEqual(validated.system, "liuren")

    def test_query_words_cannot_override_explicit_system(self) -> None:
        request = ReadingRequest(
            query="这句话故意同时提到八字六壬和普通计算",
            action="new",
            system="liuren",
            intent=_intent(),
        )

        validated = validate_request_contract(request)

        self.assertEqual(validated.system, "liuren")

    def test_open_ended_goal_is_preserved_without_taxonomy(self) -> None:
        goal = {
            "subject": "她眼下的状态",
            "requested_resolution": "给一个主判断，并说明反证",
            "evidence_questions": ["何处见动", "哪些古籍规则相冲"],
            "caller_extension": {"任意新字段": "原样保留"},
        }
        request = ReadingRequest(
            query="随便用一种从没见过的说法",
            action="new",
            system="liuren",
            goal=goal,
            intent=_intent(),
        )

        validated = validate_request_contract(request)

        self.assertEqual(validated.goal, goal)

    def test_all_supported_actions_accept_their_valid_identity_shape(self) -> None:
        reading_id = "a" * 32
        intake_id = "b" * 32
        requests = (
            ReadingRequest(
                query="新问题", action="new", system="liuren", intent=_intent()
            ),
            ReadingRequest(
                query="重起一课",
                action="recast",
                system="liuren",
                reading_id=reading_id,
                intent=_intent(reading_id=reading_id),
            ),
            ReadingRequest(
                query="接着说",
                action="continue",
                reading_id=reading_id,
                intent=_intent(reading_id=reading_id, requested_method=None),
            ),
            ReadingRequest(
                query="时间写错了",
                action="correct",
                reading_id=reading_id,
                intent=_intent(reading_id=reading_id, requested_method=None),
            ),
            ReadingRequest(
                query="北京",
                action="resume",
                intake_id=intake_id,
                location="北京",
                intent=_intent(reading_id=reading_id, requested_method=None),
            ),
        )

        for request in requests:
            with self.subTest(action=request.action):
                self.assertEqual(validate_request_contract(request), request)

    def test_invalid_action_and_identity_combinations_are_rejected(self) -> None:
        reading_id = "a" * 32
        intake_id = "b" * 32
        invalid_requests = (
            ReadingRequest(query="x", action="guess", system="liuren"),
            ReadingRequest(query="x", action="new"),
            ReadingRequest(
                query="x", action="new", system="liuren", reading_id=reading_id
            ),
            ReadingRequest(
                query="x", action="new", system="liuren", intake_id=intake_id
            ),
            ReadingRequest(query="x", action="recast"),
            ReadingRequest(
                query="x", action="recast", system="liuren", intake_id=intake_id
            ),
            ReadingRequest(query="x", action="continue"),
            ReadingRequest(
                query="x", action="continue", reading_id=reading_id, system="bazi"
            ),
            ReadingRequest(
                query="x", action="continue", reading_id=reading_id, intake_id=intake_id
            ),
            ReadingRequest(query="x", action="correct"),
            ReadingRequest(
                query="x", action="correct", reading_id=reading_id, system="bazi"
            ),
            ReadingRequest(
                query="x", action="correct", reading_id=reading_id, intake_id=intake_id
            ),
            ReadingRequest(query="x", action="resume"),
            ReadingRequest(
                query="x", action="resume", intake_id=intake_id, system="liuren"
            ),
            ReadingRequest(
                query="x", action="resume", intake_id=intake_id, reading_id=reading_id
            ),
        )

        for request in invalid_requests:
            with self.subTest(request=request):
                with self.assertRaises(RequestContractError):
                    validate_request_contract(request)

    def test_unknown_system_and_non_object_structured_fields_are_rejected(self) -> None:
        invalid_requests = (
            ReadingRequest(query="x", action="new", system="unknown-system"),
            ReadingRequest(
                query="x",
                action="new",
                system="liuren",
                goal=["not", "an", "object"],  # type: ignore[arg-type]
            ),
            ReadingRequest(
                query="x",
                action="new",
                system="liuren",
                metadata="not an object",  # type: ignore[arg-type]
            ),
        )

        for request in invalid_requests:
            with self.subTest(request=request):
                with self.assertRaises(RequestContractError):
                    validate_request_contract(request)


if __name__ == "__main__":
    unittest.main()
