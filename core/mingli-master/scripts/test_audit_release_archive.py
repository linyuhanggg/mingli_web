from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import audit_release_archive
import release_deploy


ROOT = Path(__file__).resolve().parents[1]


def _write_closure(root: Path, files: list[str]) -> None:
    closure = root / release_deploy.RUNTIME_CLOSURE_RELATIVE
    closure.parent.mkdir(parents=True, exist_ok=True)
    closure.write_text(
        json.dumps(
            {
                "schema_version": release_deploy.RUNTIME_CLOSURE_SCHEMA,
                "files": [release_deploy.RUNTIME_CLOSURE_RELATIVE, *files],
                "patterns": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _commit_fixture(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Release Surface Test",
            "-c",
            "user.email=release-surface@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=root,
        check=True,
    )


class ReleaseSurfaceAuditTests(unittest.TestCase):
    def test_every_retired_pipeline_path_is_rejected_when_selected_for_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = ["SKILL.md", *sorted(audit_release_archive.RETIRED_PATHS)]
            (root / "SKILL.md").write_text("skill\n", encoding="utf-8")
            for relative in audit_release_archive.RETIRED_PATHS:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("retired fixture\n", encoding="utf-8")
            _write_closure(root, selected)
            _commit_fixture(root)

            result = audit_release_archive.audit_release_surface(root)

        retired_errors = [
            item
            for item in result["errors"]
            if item.startswith("retired release path:")
        ]
        self.assertEqual(len(retired_errors), len(audit_release_archive.RETIRED_PATHS))

    def test_current_runtime_closure_is_distribution_clean(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git"))
            _commit_fixture(source)

            result = audit_release_archive.audit_release_surface(source)

        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(
            result["surface"],
            release_deploy.RUNTIME_CLOSURE_SCHEMA,
        )
        self.assertGreater(result["file_count"], 100)

    def test_private_fragment_in_a_selected_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            private = root / "private.md"
            private.write_text("地点：" + "福建" + "莆田" + "\n", encoding="utf-8")
            _write_closure(root, ["private.md"])
            _commit_fixture(root)

            result = audit_release_archive.audit_release_surface(root)

        self.assertFalse(result["ok"])
        self.assertTrue(any("private fragment" in item for item in result["errors"]))

    def test_host_private_runtime_lookup_in_a_selected_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "legacy.py"
            legacy.write_text("value = 'HERMES_HOME'\n", encoding="utf-8")
            _write_closure(root, ["legacy.py"])
            _commit_fixture(root)

            result = audit_release_archive.audit_release_surface(root)

        self.assertFalse(result["ok"])
        self.assertTrue(any("private fragment" in item for item in result["errors"]))

    def test_private_caller_view_pointer_in_a_selected_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "resources/runtime/providers/sample.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps(
                    {
                        "terms": {"finding.sample": {}},
                        "runtime_capability": {
                            "finding_bindings": [
                                {
                                    "id": "sample",
                                    "kind_id": "finding.sample",
                                    "json_pointers": ["/facts/private/seed"],
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            _write_closure(root, ["resources/runtime/providers/sample.json"])
            _commit_fixture(root)

            result = audit_release_archive.audit_release_surface(root)

        self.assertFalse(result["ok"])
        self.assertTrue(
            any("unsafe public finding pointer" in item for item in result["errors"]),
            result["errors"],
        )

    def test_every_known_private_note_path_is_rejected_when_selected_for_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selected = sorted(audit_release_archive.FORBIDDEN_PATHS)
            for relative in selected:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("private fixture\n", encoding="utf-8")
            _write_closure(root, selected)
            _commit_fixture(root)

            result = audit_release_archive.audit_release_surface(root)

        forbidden_errors = [
            item for item in result["errors"] if item.startswith("forbidden release path:")
        ]
        self.assertEqual(len(forbidden_errors), len(audit_release_archive.FORBIDDEN_PATHS))

    def test_unselected_developer_content_cannot_pollute_the_runtime_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "SKILL.md").write_text("skill\n", encoding="utf-8")
            note = root / "docs" / "private.md"
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text("地点：" + "福建" + "莆田" + "\n", encoding="utf-8")
            _write_closure(root, ["SKILL.md"])
            _commit_fixture(root)

            result = audit_release_archive.audit_release_surface(root)

        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["file_count"], 2)


if __name__ == "__main__":
    unittest.main()
