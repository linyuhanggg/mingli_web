from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "release/version.json"
LEGACY_TOKENS = ("v" + "41", "v" + "4.1", "v" + "5.0")


def _tracked_paths() -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return tuple(
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    )


class ReleaseVersionIdentityTests(unittest.TestCase):
    def test_canonical_release_version_is_5_1(self) -> None:
        payload = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        self.assertEqual(
            payload,
            {
                "name": "mingli-master",
                "version": "5.1",
            },
        )

    def test_public_release_surfaces_identify_v5_1(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("版本-V5.1", readme)
        self.assertIn("当前版本 | V5.1", readme)
        self.assertIn("## V5.1 ", changelog)

    def test_current_provider_adapters_use_the_v5_1_version(self) -> None:
        from reading_engine import qimen, taiyi

        self.assertEqual(qimen.ADAPTER_VERSION, "5.2.0")
        self.assertEqual(taiyi.ADAPTER_VERSION, "5.2.0")

    def test_tracked_tree_has_no_legacy_version_identity(self) -> None:
        findings: list[str] = []
        for relative in _tracked_paths():
            folded_path = relative.casefold()
            if any(token in folded_path for token in LEGACY_TOKENS):
                findings.append(f"path:{relative}")
            path = ROOT / relative
            if not path.is_file():
                continue
            folded_content = path.read_bytes().decode("utf-8", errors="ignore").casefold()
            if any(token in folded_content for token in LEGACY_TOKENS):
                findings.append(f"content:{relative}")
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
