#!/usr/bin/env python3
"""The conversation regression fixture stays free of phrase triggers.

The old transaction-protocol trajectory runner was retired with the
legacy engine; multi-turn behaviour is now covered by the token state
transition tests against the slim turn engine.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TRAJECTORIES = ROOT / "references" / "regression" / "v4-conversation-trajectories.yaml"


class V4ConversationTrajectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = yaml.safe_load(TRAJECTORIES.read_text(encoding="utf-8"))

    def test_fixture_is_conversations_not_an_intent_dictionary(self) -> None:
        self.assertEqual(
            self.document["schema_version"],
            "mingli-v4-conversation-trajectories-v1",
        )
        trajectories = self.document["trajectories"]
        self.assertGreaterEqual(len(trajectories), 10)
        serialized = TRAJECTORIES.read_text(encoding="utf-8").casefold()
        for forbidden_key in (
            "trigger_words:",
            "keywords:",
            "synonyms:",
            "expected_sentence:",
            "expected_answer_text:",
        ):
            self.assertNotIn(forbidden_key, serialized)
        for trajectory in trajectories:
            self.assertGreaterEqual(len(trajectory["turns"]), 2)
            for turn in trajectory["turns"]:
                self.assertIn("user", turn)
                self.assertIn("expect", turn)


if __name__ == "__main__":
    unittest.main()
