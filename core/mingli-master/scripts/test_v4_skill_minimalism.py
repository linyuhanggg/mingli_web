#!/usr/bin/env python3
"""Behavioral contract checks for the portable reading interface skill."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class SkillDocumentBehaviorTests(unittest.TestCase):
    """SKILL.md describes only the portable three-command protocol."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = _read("SKILL.md")
        # CJK prose wraps mid-phrase, so behavioral phrases match unwrapped.
        cls.flat_skill_text = cls.skill_text.replace("\n", "")

    def test_skill_declares_exactly_three_commands(self) -> None:
        for kind in ("describe", "prepare", "complete"):
            self.assertIn(f"`{kind}`", self.skill_text)
        # no retired subcommands
        for retired in ("resume", "publish-question", "probe", "run", "capabilities"):
            self.assertNotIn(f"`{retired}`", self.skill_text)

    def test_skill_declares_exactly_four_results(self) -> None:
        for kind in ("described", "prepared", "accepted", "stopped"):
            self.assertIn(f"`{kind}`", self.skill_text)

    def test_skill_mentions_opaque_state_token(self) -> None:
        self.assertIn("state_token", self.skill_text)

    def test_skill_does_not_hardcode_provider_names(self) -> None:
        for provider in ("八字", "紫微", "六壬", "六爻", "梅花", "奇门", "太乙", "择日", "风水", "相学", "星命"):
            self.assertNotIn(provider, self.skill_text)

    def test_skill_does_not_expose_internal_paths_or_commands(self) -> None:
        for internal in (
            "--skill-dir",
            "--store-root",
            "chmod",
            "reading_id",
            "prepared_digest",
            "scripts/",
            "json_cli.py",
            "run_reading_transaction.sh",
        ):
            self.assertNotIn(internal, self.skill_text)

    def test_skill_does_not_mention_gateway_or_observer(self) -> None:
        for gateway_term in ("observer", "guard", "gateway", "8642", "8645"):
            self.assertNotIn(gateway_term, self.skill_text.lower())

    def test_skill_instructs_brief_only_drafting(self) -> None:
        self.assertIn("brief", self.skill_text)
        self.assertIn("成稿", self.skill_text)

    def test_skill_keeps_the_callers_question_scope_in_prepare(self) -> None:
        self.assertIn("保留用户最新问题的原始语义范围", self.flat_skill_text)
        self.assertIn("不改变范围的最小结构化转写", self.flat_skill_text)
        self.assertIn("固定输出栏目", self.flat_skill_text)

    def test_skill_forbids_uncalibrated_confidence_numbers(self) -> None:
        self.assertIn("经过声明和校准的数值", self.flat_skill_text)
        self.assertIn("不生成任何数字或百分比", self.flat_skill_text)

    def test_skill_stays_generic_without_fixed_answer_templates(self) -> None:
        for template_term in ("主断一句", "结尾评分", "评分模板"):
            self.assertNotIn(template_term, self.skill_text)
        for domain_term in ("小人", "疾病", "土重", "旺衰", "用神"):
            self.assertNotIn(domain_term, self.skill_text)


class BaziBoundaryReferenceTests(unittest.TestCase):
    """The bazi boundary note stays provider-local and portable."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.doc_text = _read("references/bazi-input-and-image-gate.md")

    def test_no_legacy_host_gate_or_fixed_tags(self) -> None:
        for legacy in (
            "Hermes",
            "delivery guard",
            "gate_check",
            "玄枢",
            "【截图四柱已校验",
            "【未校盘】",
            "/tmp/",
            "python3 scripts/",
        ):
            self.assertNotIn(legacy, self.doc_text)

    def test_partial_luck_boundary_is_documented(self) -> None:
        self.assertIn("sequence_only", self.doc_text)
        self.assertIn("not_calculated_missing_gender", self.doc_text)
        self.assertIn("limit.partial_luck_timing", self.doc_text)
        self.assertIn("limit.partial_luck_no_gender", self.doc_text)


class ProductionEntrypointTests(unittest.TestCase):
    """The CLI and Interface form the only production surface."""

    def test_json_cli_is_the_one_production_entrypoint(self) -> None:
        cli_source = _read("scripts/adapters/json_cli.py")
        self.assertIn("json_cli", cli_source)
        self.assertIn("ReadingInterface", cli_source)

    def test_interface_can_be_imported_without_retired_modules(self) -> None:
        probe = (
            "import sys; sys.path.insert(0, 'scripts');"
            "from reading_engine.interface import ReadingInterface;"
            "print('ok')"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", probe],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[-1000:])
        self.assertIn("ok", completed.stdout)

    def test_describe_returns_capabilities_from_manifests(self) -> None:
        from reading_engine.interface import ReadingInterface
        from reading_engine.interface_contracts import Describe, Described

        interface = ReadingInterface(skill_root=ROOT)
        result = interface.execute(Describe())
        self.assertIsInstance(result, Described)
        self.assertTrue(result.capabilities)
        self.assertTrue(result.manifest_digest)

    def test_prepare_with_complete_facts_returns_prepared(self) -> None:
        from reading_engine.interface import ReadingInterface
        from reading_engine.interface_contracts import (
            HorizonSelection,
            IntentSelection,
            Prepare,
            Prepared,
        )

        with tempfile.TemporaryDirectory() as tmp:
            interface = ReadingInterface(skill_root=ROOT, store_root=tmp)
            result = interface.execute(
                Prepare(
                    query="看一下这个八字",
                    intent=IntentSelection(
                        subject_refs=("subject:client",),
                        object_id="natal",
                        dimension_ids=(),
                        horizon=HorizonSelection(kind_id="year"),
                        capability_id="bazi",
                    ),
                    facts={
                        "subject:client": {
                            "birth_datetime_or_four_pillars": "1994-04-30T05:55:00",
                            "timezone": "Asia/Shanghai",
                            "location": "福建省福州市",
                            "gender": "female",
                            "time_basis_policy": "civil",
                        }
                    },
                )
            )
        self.assertIsInstance(result, Prepared, result)
        self.assertTrue(result.brief.facts)
        self.assertTrue(result.brief.claim_scopes)
        self.assertTrue(result.state_token)


if __name__ == "__main__":
    unittest.main()
