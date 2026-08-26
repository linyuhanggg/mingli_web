"""Active artifact contains exactly one production pipeline."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RETIRED_MODULES = (
    "route_capabilities",
    "query_intent",
    "reading_followup",
    "gate_check",
    "inference_contract",
    "public_answer_contract",
    "public_answer_finalize",
    "reading_public_brief",
    "legacy_v3",
    "reading_engine.drafting",
    "reading_engine.routing",
    "reading_engine.answer_contract",
    "reading_engine.transaction",
    "reading_engine.cross_check",
    "reading_engine.legacy",
    "reading_engine.ziwei",
    "reading_engine.fortune",
    "reading_engine.capability_resolver",
)

SOURCE_ONLY_MODULES = (
    "reading_engine.cross_art_synthesis",
    "reading_engine.dream_interpretation",
    "reading_engine.name_analysis",
)

RETIRED_ARCHIVE_PATHS = (
    "scripts/route_capabilities.py",
    "scripts/query_intent.py",
    "scripts/reading_followup.py",
    "scripts/gate_check.py",
    "scripts/legacy_v3",
    "scripts/reading_engine/drafting.py",
    "scripts/reading_engine/routing.py",
    "scripts/reading_engine/transaction.py",
    "scripts/reading_engine/cross_check.py",
    "scripts/reading_engine/legacy.py",
    "scripts/reading_engine/ziwei.py",
    "scripts/reading_engine/fortune.py",
    "scripts/reading_engine/capability_resolver.py",
)


class ProductionImportGraphTests(unittest.TestCase):
    def test_private_calculators_do_not_expose_the_retired_pipeline(self) -> None:
        import bazi_calc
        import fortune_calc
        import liuren_calc

        for module in (bazi_calc, fortune_calc, liuren_calc):
            with self.subTest(module=module.__name__):
                self.assertFalse(hasattr(module, "_build_pipeline_manifest"))
                self.assertFalse(hasattr(module, "_judgment_contract"))
                parser = module._parser()
                destinations = {
                    action.dest
                    for action in parser._actions
                }
                for action in parser._actions:
                    choices = getattr(action, "choices", None)
                    if isinstance(choices, dict):
                        for child in choices.values():
                            destinations.update(item.dest for item in child._actions)
                self.assertNotIn("pipeline", destinations)

    def test_contracts_expose_artifacts_not_a_second_cross_check_ledger(self) -> None:
        from reading_engine import contracts

        for retired in (
            "ProviderConsideration",
            "CapabilityResolution",
            "RouteDecision",
            "CrossCheckSide",
            "CrossCheckRecord",
            "CrossCheckReviewDimension",
            "CrossCheckReview",
        ):
            self.assertFalse(hasattr(contracts, retired), retired)
        fields = contracts.ReadingRecord.__dataclass_fields__
        self.assertNotIn("capability_resolution", fields)
        self.assertNotIn("cross_check", fields)
        self.assertNotIn("cross_check_review", fields)
        self.assertIn("artifacts", fields)

    def test_entrypoint_import_graph_excludes_retired_pipeline(self) -> None:
        probe = (
            "import sys;"
            "sys.path.insert(0, 'scripts');"
            "from adapters import json_cli;"
            "from reading_engine.interface import ReadingInterface;"
            "interface = ReadingInterface(skill_root='.');"
            "interface.execute.__name__;"
            "banned = "
            + repr(list((*RETIRED_MODULES, *SOURCE_ONLY_MODULES)))
            + ";"
            "loaded = sorted(name for name in banned if name in sys.modules);"
            "print(json.dumps(loaded)) if False else print(','.join(loaded))"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", probe],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
            check=True,
        )
        self.assertEqual(completed.stdout.strip(), "", completed.stdout)

    def test_production_prepare_flow_stays_free_of_retired_modules(self) -> None:
        probe = (
            "import sys, tempfile;"
            "sys.path.insert(0, 'scripts');"
            "from reading_engine.interface import ReadingInterface;"
            "from reading_engine.interface_contracts import ("
            "    HorizonSelection, IntentSelection, Prepare, Prepared);"
            "tmp = tempfile.TemporaryDirectory();"
            "interface = ReadingInterface(skill_root='.', store_root=tmp.name);"
            "result = interface.execute(Prepare("
            "    query='看一下这个八字',"
            "    intent=IntentSelection("
            "        subject_refs=('subject:client',),"
            "        capability_id='bazi',"
            "        object_id='natal',"
            "        dimension_ids=(),"
            "        horizon=HorizonSelection(kind_id='year'),"
            "    ),"
            "    facts={'subject:client': {"
            "        'birth_datetime_or_four_pillars': '1994-04-30T05:55:00',"
            "        'timezone': 'Asia/Shanghai',"
            "        'location': '福建省福州市',"
            "        'gender': 'female',"
            "        'time_basis_policy': 'civil',"
            "    }},"
            "));"
            "assert isinstance(result, Prepared), type(result).__name__;"
            "banned = "
            + repr(list((*RETIRED_MODULES, *SOURCE_ONLY_MODULES)))
            + ";"
            "loaded = sorted(name for name in banned if name in sys.modules);"
            "print(','.join(loaded))"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", probe],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[-2000:])
        self.assertEqual(completed.stdout.strip(), "", completed.stdout)


class ReleaseArchiveMinimalismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        completed = subprocess.run(
            ["git", "-C", str(ROOT), "archive", "--format=tar", "HEAD"],
            check=True,
            capture_output=True,
        )
        with tarfile.open(fileobj=io.BytesIO(completed.stdout), mode="r:") as archive:
            cls.member_names = [member.name for member in archive.getmembers()]
            cls.text_blobs = {}
            for member in archive.getmembers():
                if member.isfile() and member.name in (
                    "README.md",
                    "SKILL.md",
                ):
                    extracted = archive.extractfile(member)
                    assert extracted is not None
                    cls.text_blobs[member.name] = extracted.read().decode("utf-8")

    def test_archive_excludes_retired_paths(self) -> None:
        for retired in RETIRED_ARCHIVE_PATHS:
            with self.subTest(path=retired):
                for name in self.member_names:
                    self.assertFalse(
                        name == retired or name.startswith(retired + "/"),
                        name,
                    )

    def test_active_documents_do_not_reference_retired_modules(self) -> None:
        for document, text in self.text_blobs.items():
            for token in ("route_capabilities", "query_intent", "reading_followup"):
                with self.subTest(document=document, token=token):
                    self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
