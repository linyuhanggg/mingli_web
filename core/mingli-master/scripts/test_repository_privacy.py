#!/usr/bin/env python3
"""Repository-level regressions for private profile and replay leakage."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".json", ".md", ".py", ".txt", ".yaml", ".yml"}
FORBIDDEN_FRAGMENTS = (
    "2000-10-18" + "T05:10:00",
    "2000-10-18" + " 05:10",
    "2000-10-18" + "T05:30:00",
    "2000-10-18" + " 05:30",
    "2001-01-" + "25",
    "2000年10月18日" + "早上5点10分",
    "福建" + "莆田",
    "Use when " + "Cher" + "ry",
    "current " + "LiuJing",
    "Current session " + "chart facts",
    "Known charts in " + "this session",
    "User calibration for " + "under-23",
    "Example from " + "this session",
    "a11479d1" + "95d2493cb69cb2fc5e927b17",
    "062d7811" + "8ac64ac1ad2d2031ea6b86aa",
    "source_" + "session",
    "source_" + "message_ids",
    "/Users/" + "yuhanglin",
)
REMOVED_PERSONAL_FILES = (
    "references/bazi-couple-future-six-year-pattern-2026-2031.md",
    "references/bazi-male-marriage-timing-cherry.md",
    "references/bazi-couple-marriage-probability.md",
    "references/bazi-marriage-year-review.md",
    "references/bazi-material-level-comparison-notes.md",
    "references/bazi-relationship-career-followups.md",
    "references/bazi-relationship-infidelity-risk.md",
    "references/bazi-relationship-year-followup-notes.md",
    "references/bazi-screenshot-qiyun-and-exam-review.md",
    "references/bazi-under23-family-material-comparison.md",
)


class RepositoryPrivacyTests(unittest.TestCase):
    def test_private_profile_and_production_replay_identifiers_are_absent(self) -> None:
        findings = []
        if (ROOT / ".git").exists() or (ROOT / ".git").is_file():
            tracked = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout.decode("utf-8").split("\0")
            paths = (ROOT / relative for relative in tracked if relative)
        else:
            paths = ROOT.rglob("*")
        for path in paths:
            if not path.is_file():
                continue
            if path.is_relative_to(ROOT / "references" / "fulltext"):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for fragment in FORBIDDEN_FRAGMENTS:
                if fragment in text:
                    findings.append(f"{path.relative_to(ROOT)}: {fragment!r}")

        self.assertEqual(findings, [])

    def test_personal_relationship_notes_are_not_distributed(self) -> None:
        present = [path for path in REMOVED_PERSONAL_FILES if (ROOT / path).exists()]
        self.assertEqual(present, [])


if __name__ == "__main__":
    unittest.main()
