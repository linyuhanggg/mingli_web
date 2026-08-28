import json
import re
import unittest
from pathlib import Path


RUNTIME_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CLOSURE_PATH = RUNTIME_ROOT / "release/runtime-closure-v1.json"
NOTICE_PATH = RUNTIME_ROOT / "THIRD_PARTY_NOTICES.md"
LOCK_PATH = RUNTIME_ROOT / "requirements-runtime.lock"
EVIDENCE_PATH = (
    REPOSITORY_ROOT
    / "artifacts/runtime-evidence/2026-08-28-oss-chart-release-closure"
    / "license-notice-closure.json"
)


class LicenseNoticeClosureTests(unittest.TestCase):
    def test_runtime_lock_keeps_the_reviewed_versions(self) -> None:
        lock = LOCK_PATH.read_text(encoding="utf-8")
        expected = {
            "PyYAML": "6.0.3",
            "sxtwl": "2.0.7",
            "astronomy-engine": "2.1.19",
            "cnlunar": "0.2.4",
            "zhconv": "1.4.3",
        }

        for name, version in expected.items():
            self.assertRegex(
                lock,
                rf"(?m)^{re.escape(name)}=={re.escape(version)}(?:\s|$)",
            )

    def test_release_closure_selects_notice_and_local_obligations(self) -> None:
        closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        selected = set(closure["files"])
        required = {
            "THIRD_PARTY_NOTICES.md",
            "vendor/pyyaml-6.0.3/LICENSE",
            "vendor/sxtwl-2.0.7/LICENSE",
            "vendor/zhconv-1.4.3/LICENSE",
            "vendor/zhconv-1.4.3/LICENSE.data",
            "vendor/zhconv-1.4.3/SOURCE_COMPLIANCE.md",
        }

        self.assertTrue(required <= selected)
        for relative in required:
            self.assertTrue((RUNTIME_ROOT / relative).is_file(), relative)

    def test_notice_and_evidence_report_the_same_four_results(self) -> None:
        evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        decisions = {item["id"]: item["decision"] for item in evidence["items"]}
        self.assertEqual(
            decisions,
            {
                "pyyaml-6.0.3": "CLEAR",
                "sxtwl-2.0.7": "CLEAR",
                "zhconv-1.4.3": "HOLD",
                "third-party-notices-release-closure": "CLEAR",
            },
        )
        self.assertEqual(evidence["summary"]["overall_decision"], "HOLD")

        notice = NOTICE_PATH.read_text(encoding="utf-8")
        self.assertIn("Release status is **HOLD**", notice)
        self.assertIn("### PyYAML 6.0.3", notice)
        self.assertIn("### sxtwl 2.0.7", notice)
        self.assertIn("### zhconv 1.4.3 — HOLD", notice)
        self.assertIn(
            "`release/runtime-closure-v1.json` selects this notice",
            notice,
        )


if __name__ == "__main__":
    unittest.main()
