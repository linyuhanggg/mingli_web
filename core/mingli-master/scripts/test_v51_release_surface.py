"""The installed Skill exposes only the portable runtime closure."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import release_deploy


ROOT = Path(__file__).resolve().parents[1]


def _selected_snapshot_paths() -> set[str]:
    """Exercise the same tracked-file rule without staging this test's edits."""

    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "source"
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git"))
        subprocess.run(["git", "init", "-q", str(source)], check=True)
        subprocess.run(["git", "-C", str(source), "add", "."], check=True)
        return set(release_deploy.tracked_release_files(source))


class ReleaseSurfaceTests(unittest.TestCase):
    def test_runtime_closure_excludes_host_polluting_documents_and_tests(self) -> None:
        selected = _selected_snapshot_paths()

        self.assertIn(release_deploy.RUNTIME_CLOSURE_RELATIVE, selected)
        self.assertIn("SKILL.md", selected)
        self.assertIn("scripts/adapters/json_cli.py", selected)
        self.assertIn("scripts/run_reading_transaction.sh", selected)
        self.assertIn("resources/runtime/catalog-v1.json", selected)
        self.assertIn("references/index/evidence-rules.jsonl", selected)
        self.assertIn("references/books/bazi/sanming-tonghui/rules.md", selected)
        self.assertIn("vendor/iztro-2.5.8/iztro.min.js", selected)

        forbidden_exact = {
            "README.md",
            "CHANGELOG.md",
            "agents/openai.yaml",
            "test-prompts.json",
            "references/tool-adapters.md",
            "references/production-pipelines.md",
            "references/fortune-cron-reminders.md",
            "scripts/reading_transaction.py",
            "scripts/test_release_deploy.py",
        }
        self.assertFalse(forbidden_exact & selected)
        self.assertFalse(any(path.startswith("docs/") for path in selected))
        self.assertFalse(any(path.startswith("tests/") for path in selected))
        self.assertFalse(any(path.startswith("agents/") for path in selected))
        self.assertFalse(any(path.startswith("references/fulltext/") for path in selected))
        self.assertFalse(
            any(path.startswith("scripts/test_") for path in selected)
        )

    def test_runtime_closure_keeps_the_artifacts_eager_validation_reads(self) -> None:
        selected = _selected_snapshot_paths()
        required = {
            "resources/runtime/messages/zh-CN.json",
            "references/matrices/classical-evidence-bindings-v1.json",
            "references/matrices/runtime-source-families-v1.yaml",
            "references/matrices/liuren-source-tables-v1.yaml",
            "references/matrices/liuyao-jingfang-tables-v1.yaml",
            "references/matrices/meihua-source-tables-v1.yaml",
            "references/matrices/qimen-source-tables-v1.yaml",
            "references/matrices/taiyi-source-tables-v1.yaml",
            "references/matrices/selection-source-tables-v1.yaml",
            "references/matrices/fengshui-source-tables-v1.yaml",
            "references/matrices/physiognomy-source-tables-v1.yaml",
            "references/source-excerpts/qimen-faqiao-chaibu-v1.md",
            "references/books/selection/donggong-zeri/monthly-day-table.md",
            "scripts/data/liuren-720-transmissions.json",
            "scripts/data/liuren-miben-general-imagery.json",
            "vendor/cnlunar-0.2.4/PROVENANCE.json",
        }
        self.assertTrue(required <= selected, sorted(required - selected))

        rule_files = {
            path
            for path in selected
            if path.startswith("references/books/") and path.endswith("/rules.md")
        }
        self.assertEqual(len(rule_files), 55)

    def test_materialized_runtime_closure_can_prepare_through_its_adapter(self) -> None:
        """A fresh install must boot without falling back to the source tree."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            destination = root / "installed"
            home = root / "home"
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git"))
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "add", "."], check=True)
            selected = release_deploy.tracked_release_files(source)
            manifest = release_deploy.build_manifest(source, selected, "fixture")
            release_deploy.sync_destination(
                source,
                destination,
                manifest,
                apply=True,
            )
            environment = {
                "HOME": str(home),
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            adapter = str(destination / "scripts/adapters/json_cli.py")
            described = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-B",
                    adapter,
                ],
                input=json.dumps({"kind": "describe"}),
                capture_output=True,
                text=True,
                cwd=str(destination),
                env=environment,
            )

            prepared = subprocess.run(
                [sys.executable, "-I", "-B", adapter],
                input=json.dumps(
                    {
                        "kind": "prepare",
                        "query": "请给出当前可用的解读材料。",
                        "intent": {
                            "subject_refs": ["subject:test"],
                            "object_id": "concrete_event",
                            "dimension_ids": ["outcome"],
                            "horizon": {"kind_id": "instant"},
                            "capability_id": "liuren",
                            "comparison_capability_ids": [],
                        },
                        "facts": {
                            "subject:test": {
                                "event_datetime_or_reference_datetime": (
                                    "2026-07-22T22:13:00+08:00"
                                ),
                                "timezone": "Asia/Shanghai",
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                capture_output=True,
                text=True,
                cwd=str(destination),
                env=environment,
            )
            need_input = subprocess.run(
                [sys.executable, "-I", "-B", adapter],
                input=json.dumps(
                    {
                        "kind": "prepare",
                        "query": "请帮我择日。",
                        "intent": {
                            "subject_refs": ["event"],
                            "object_id": "calendar_choice",
                            "dimension_ids": ["timing"],
                            "horizon": {"kind_id": "day"},
                            "capability_id": "selection",
                            "comparison_capability_ids": [],
                        },
                        "facts": {"event": {}},
                    },
                    ensure_ascii=False,
                ),
                capture_output=True,
                text=True,
                cwd=str(destination),
                env=environment,
            )
            selection = subprocess.run(
                [sys.executable, "-I", "-B", adapter],
                input=json.dumps(
                    {
                        "kind": "prepare",
                        "query": "为开业择日。",
                        "intent": {
                            "subject_refs": ["event"],
                            "object_id": "calendar_choice",
                            "dimension_ids": ["timing", "state"],
                            "horizon": {
                                "kind_id": "day",
                                "start": "2026-07-24",
                                "end": "2026-07-24",
                            },
                            "capability_id": "selection",
                            "comparison_capability_ids": [],
                        },
                        "facts": {
                            "event": {
                                "event_profile": "business_opening_transaction",
                                "requested_actions": ["开市"],
                                "date_range": {
                                    "start": "2026-07-24",
                                    "end": "2026-07-24",
                                },
                                "timezone": "Asia/Shanghai",
                                "location": "上海",
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                capture_output=True,
                text=True,
                cwd=str(destination),
                env=environment,
            )
            runner = subprocess.run(
                [str(destination / "scripts/run_reading_transaction.sh")],
                input=json.dumps({"kind": "describe"}),
                capture_output=True,
                text=True,
                cwd=str(destination),
                env={**environment, "MINGLI_PYTHON": sys.executable},
            )

        self.assertEqual(described.returncode, 0, described.stderr)
        payload = json.loads(described.stdout)
        self.assertEqual(payload.get("kind"), "described")
        self.assertTrue(payload.get("capabilities"))
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(json.loads(prepared.stdout).get("kind"), "prepared")
        self.assertEqual(need_input.returncode, 0, need_input.stderr)
        need_input_payload = json.loads(need_input.stdout)
        self.assertEqual(need_input_payload.get("kind"), "stopped")
        self.assertEqual(need_input_payload.get("reason"), "need_input")
        self.assertTrue(need_input_payload.get("public_copy", "").startswith("还需要："))
        self.assertEqual(selection.returncode, 0, selection.stderr)
        self.assertEqual(json.loads(selection.stdout).get("kind"), "prepared")
        self.assertEqual(runner.returncode, 0, runner.stderr)
        self.assertEqual(json.loads(runner.stdout).get("kind"), "described")


if __name__ == "__main__":
    unittest.main()
