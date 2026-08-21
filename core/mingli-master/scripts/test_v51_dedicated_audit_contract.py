#!/usr/bin/env python3
"""Cross-route Task 7N contracts for dedicated provider audits."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import yaml

import audit_test_session
import audit_bazi_provider
import audit_fengshui_provider
import audit_fortune_provider
import audit_liuren_provider
import audit_liuyao_provider
import audit_luming_provider
import audit_meihua_provider
import audit_physiognomy_provider
import audit_qimen_provider
import audit_selection_provider
import audit_taiyi_provider
import audit_xingming_provider
import audit_ziwei_provider
from reading_engine.providers import (
    FengshuiProvider,
    LiurenProvider,
    LiuyaoProvider,
    MeihuaProvider,
    PhysiognomyProvider,
    QimenProvider,
    SelectionProvider,
    TaiyiProvider,
    PROVIDER_CAPABILITIES,
)


ROOT = Path(__file__).resolve().parents[1]


ROUTES = {
    "bazi": (audit_bazi_provider.audit_bazi_provider, 30, "calculation"),
    "fortune": (audit_fortune_provider.audit_fortune_provider, 30, "calculation"),
    "ziwei": (audit_ziwei_provider.audit_ziwei_provider, 30, "calculation"),
    "luming-nayin": (audit_luming_provider.audit_luming_provider, 30, "calculation"),
    "xingming": (audit_xingming_provider.audit_xingming_provider, 30, "calculation"),
    "liuyao": (audit_liuyao_provider.audit_liuyao_provider, 30, "calculation"),
    "meihua": (audit_meihua_provider.audit_meihua_provider, 30, "calculation"),
    "liuren": (audit_liuren_provider.audit_liuren_provider, 30, "calculation"),
    "qimen": (audit_qimen_provider.audit_qimen_provider, 30, "calculation"),
    "taiyi": (audit_taiyi_provider.audit_taiyi_provider, 30, "calculation"),
    "selection": (audit_selection_provider.audit_selection_provider, 30, "calculation"),
    "fengshui": (
        audit_fengshui_provider.audit_fengshui_provider,
        20,
        "observation_driven_ready",
    ),
    "physiognomy": (
        audit_physiognomy_provider.audit_physiognomy_provider,
        20,
        "observation_driven_ready",
    ),
}


MODE_MUTATIONS = {
    "liuyao": (audit_liuyao_provider.audit_liuyao_provider, LiuyaoProvider),
    "meihua": (audit_meihua_provider.audit_meihua_provider, MeihuaProvider),
    "liuren": (audit_liuren_provider.audit_liuren_provider, LiurenProvider),
    "qimen": (audit_qimen_provider.audit_qimen_provider, QimenProvider),
    "taiyi": (audit_taiyi_provider.audit_taiyi_provider, TaiyiProvider),
    "selection": (audit_selection_provider.audit_selection_provider, SelectionProvider),
    "fengshui": (audit_fengshui_provider.audit_fengshui_provider, FengshuiProvider),
    "physiognomy": (
        audit_physiognomy_provider.audit_physiognomy_provider,
        PhysiognomyProvider,
    ),
}


IDENTITY_MUTATIONS = {
    "meihua": (audit_meihua_provider.audit_meihua_provider, MeihuaProvider),
    "liuren": (audit_liuren_provider.audit_liuren_provider, LiurenProvider),
    "qimen": (audit_qimen_provider.audit_qimen_provider, QimenProvider),
    "taiyi": (audit_taiyi_provider.audit_taiyi_provider, TaiyiProvider),
    "selection": (audit_selection_provider.audit_selection_provider, SelectionProvider),
    "fengshui": (audit_fengshui_provider.audit_fengshui_provider, FengshuiProvider),
    "physiognomy": (
        audit_physiognomy_provider.audit_physiognomy_provider,
        PhysiognomyProvider,
    ),
}
SYSTEM_IDENTITY_MUTATIONS = {
    "liuyao": (audit_liuyao_provider.audit_liuyao_provider, LiuyaoProvider),
    "meihua": (audit_meihua_provider.audit_meihua_provider, MeihuaProvider),
}


class DedicatedAuditLiveContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.reports = {}
        for system, (audit, _minimum, _mode) in ROUTES.items():
            report = audit_test_session.load_report(system)
            cls.reports[system] = report if report is not None else audit()

    def test_all_thirteen_reports_use_one_route_owned_replay_contract(self) -> None:
        required_counts = {
            "qualifying_cases",
            "route_owned_cases",
            "provider_calculations",
            "provider_extensions",
            "determinism_checks",
            "boundary_case_count",
        }
        for system, (_, minimum, expected_mode) in ROUTES.items():
            with self.subTest(system=system):
                report = self.reports[system]
                counts = report["counts"]
                self.assertTrue(report["provider_ready"], report)
                self.assertTrue(required_counts <= set(counts), report)
                self.assertEqual(counts["qualifying_cases"], counts["route_owned_cases"])
                self.assertGreaterEqual(counts["route_owned_cases"], minimum)
                self.assertGreaterEqual(
                    counts["provider_calculations"],
                    2 * counts["route_owned_cases"],
                )
                self.assertGreaterEqual(
                    counts["determinism_checks"],
                    counts["route_owned_cases"],
                )
                self.assertGreaterEqual(counts["provider_extensions"], 0)
                self.assertGreater(counts["boundary_case_count"], 0)
                route_owned_case_ids = report["route_owned_case_ids"]
                self.assertEqual(len(route_owned_case_ids), counts["route_owned_cases"])
                self.assertEqual(len(set(route_owned_case_ids)), len(route_owned_case_ids))
                self.assertTrue(all(route_owned_case_ids))
                self.assertTrue(report["boundary_categories"])
                self.assertEqual(report["provider"]["capability_mode"], expected_mode)

    def test_all_thirteen_reports_publish_fixed_route_fixture_identity(self) -> None:
        for system, (audit, _, _) in ROUTES.items():
            del audit
            with self.subTest(system=system):
                report = self.reports[system]
                fixture = report.get("fixture")
                self.assertIsInstance(fixture, dict, report)
                actual = fixture.get("sha256") if isinstance(fixture, dict) else None
                expected = (
                    fixture.get("expected_sha256")
                    if isinstance(fixture, dict)
                    else None
                )
                self.assertRegex(str(actual or ""), r"^[0-9a-f]{64}$")
                self.assertEqual(actual, expected)


class DedicatedAuditMachineContractTests(unittest.TestCase):
    def _assert_mode_fails_closed(self, system: str) -> None:
        audit, _provider_class = MODE_MUTATIONS[system]
        unavailable = replace(PROVIDER_CAPABILITIES[system], mode="unavailable")
        with patch.dict(PROVIDER_CAPABILITIES, {system: unavailable}):
            report = audit()
        self.assertFalse(report["provider_ready"], report)
        self.assertTrue(
            any("capability mode" in item for item in report["findings"]),
            report,
        )

    def test_duplicate_route_owned_id_fails_closed(self) -> None:
        payload = yaml.safe_load(audit_luming_provider.FIXTURE.read_text(encoding="utf-8"))
        payload["source_examples"].append(copy.deepcopy(payload["source_examples"][0]))
        with tempfile.TemporaryDirectory() as temp_dir:
            mutated = Path(temp_dir) / "luming-v51.yaml"
            mutated.write_text(
                yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            digest = hashlib.sha256(mutated.read_bytes()).hexdigest()
            with patch.object(audit_luming_provider, "EXPECTED_FIXTURE_SHA256", digest):
                report = audit_luming_provider.audit_luming_provider(
                    fixture_path=mutated
                )
        self.assertFalse(report["provider_ready"], report)
        route_owned_case_ids = report["route_owned_case_ids"]
        self.assertNotEqual(len(route_owned_case_ids), len(set(route_owned_case_ids)))
        self.assertTrue(
            any("ids are not unique" in finding for finding in report["findings"]),
            report,
        )

    def test_liuyao_mode_fails_closed(self) -> None:
        self._assert_mode_fails_closed("liuyao")

    def test_meihua_mode_fails_closed(self) -> None:
        self._assert_mode_fails_closed("meihua")

    def test_liuren_mode_fails_closed(self) -> None:
        self._assert_mode_fails_closed("liuren")

    def test_qimen_mode_fails_closed(self) -> None:
        self._assert_mode_fails_closed("qimen")

    def test_taiyi_mode_fails_closed(self) -> None:
        self._assert_mode_fails_closed("taiyi")

    def test_selection_mode_fails_closed(self) -> None:
        self._assert_mode_fails_closed("selection")

    def test_fengshui_mode_fails_closed(self) -> None:
        self._assert_mode_fails_closed("fengshui")

    def test_physiognomy_mode_fails_closed(self) -> None:
        self._assert_mode_fails_closed("physiognomy")

class DedicatedAuditIdentityContractTests(unittest.TestCase):
    def _assert_identity_fails_closed(self, system: str, field: str, drifted: str) -> None:
        audit, provider_class = IDENTITY_MUTATIONS[system]
        with patch.object(provider_class, field, drifted):
            report = audit()
        self.assertFalse(report["provider_ready"], report)
        self.assertTrue(
            any("provider identity" in item for item in report["findings"]),
            report,
        )

    def _assert_system_fails_closed(self, system: str) -> None:
        audit, provider_class = SYSTEM_IDENTITY_MUTATIONS[system]
        original_calculate = provider_class.calculate

        def drifted_calculate(self, request):
            return replace(original_calculate(self, request), system="drifted-system")

        with patch.object(provider_class, "calculate", drifted_calculate):
            report = audit()
        self.assertFalse(report["provider_ready"], report)
        self.assertTrue(
            any("provider system" in item for item in report["findings"]),
            report,
        )

    def test_meihua_provider_id_drift(self) -> None:
        self._assert_identity_fails_closed("meihua", "provider_id", "mingli-master.drifted.v0")

    def test_meihua_provider_version_drift(self) -> None:
        self._assert_identity_fails_closed("meihua", "provider_version", "drifted-version")

    def test_liuren_provider_id_drift(self) -> None:
        self._assert_identity_fails_closed("liuren", "provider_id", "mingli-master.drifted.v0")

    def test_liuren_provider_version_drift(self) -> None:
        self._assert_identity_fails_closed("liuren", "provider_version", "drifted-version")

    def test_qimen_provider_id_drift(self) -> None:
        self._assert_identity_fails_closed("qimen", "provider_id", "mingli-master.drifted.v0")

    def test_qimen_provider_version_drift(self) -> None:
        self._assert_identity_fails_closed("qimen", "provider_version", "drifted-version")

    def test_taiyi_provider_id_drift(self) -> None:
        self._assert_identity_fails_closed("taiyi", "provider_id", "mingli-master.drifted.v0")

    def test_taiyi_provider_version_drift(self) -> None:
        self._assert_identity_fails_closed("taiyi", "provider_version", "drifted-version")

    def test_selection_provider_id_drift(self) -> None:
        self._assert_identity_fails_closed("selection", "provider_id", "mingli-master.drifted.v0")

    def test_selection_provider_version_drift(self) -> None:
        self._assert_identity_fails_closed("selection", "provider_version", "drifted-version")

    def test_fengshui_provider_id_drift(self) -> None:
        self._assert_identity_fails_closed("fengshui", "provider_id", "mingli-master.drifted.v0")

    def test_fengshui_provider_version_drift(self) -> None:
        self._assert_identity_fails_closed("fengshui", "provider_version", "drifted-version")

    def test_physiognomy_provider_id_drift(self) -> None:
        self._assert_identity_fails_closed("physiognomy", "provider_id", "mingli-master.drifted.v0")

    def test_physiognomy_provider_version_drift(self) -> None:
        self._assert_identity_fails_closed("physiognomy", "provider_version", "drifted-version")

    def test_liuyao_result_system_drift(self) -> None:
        self._assert_system_fails_closed("liuyao")

    def test_meihua_result_system_drift(self) -> None:
        self._assert_system_fails_closed("meihua")


class ReleaseBoundFixtureTests(unittest.TestCase):
    CASES = (
        (audit_ziwei_provider, "ziwei-v51.yaml", {}),
        (audit_liuren_provider, "liuren-v51.yaml", {}),
        (audit_qimen_provider, "qimen-v51.yaml", {}),
    )

    def test_qualifying_fixture_artifacts_are_fixed_and_reported(self) -> None:
        for module, fixture_name, _ in self.CASES:
            with self.subTest(fixture=fixture_name):
                report = getattr(module, module.__name__)()
                artifacts = report["fixture_artifacts"]
                self.assertEqual(
                    artifacts["route_fixture_sha256"],
                    hashlib.sha256(
                        (ROOT / "references" / "fixtures" / fixture_name).read_bytes()
                    ).hexdigest(),
                )
                self.assertRegex(artifacts["expected_route_fixture_sha256"], r"^[0-9a-f]{64}$")
                self.assertEqual(
                    artifacts["route_fixture_sha256"],
                    artifacts["expected_route_fixture_sha256"],
                )
                self.assertTrue(artifacts["qualifying_artifact_hashes"])

    def test_inert_top_level_mutation_fails_closed(self) -> None:
        for module, fixture_name, kwargs in self.CASES:
            source = ROOT / "references" / "fixtures" / fixture_name
            payload = yaml.safe_load(source.read_text(encoding="utf-8"))
            payload["inert_mutation_probe"] = True
            with self.subTest(fixture=fixture_name), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / fixture_name
                path.write_text(
                    yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                    encoding="utf-8",
                )
                report = getattr(module, module.__name__)(fixture_path=path, **kwargs)
                self.assertFalse(report["provider_ready"], report)
                self.assertTrue(
                    any("fixture artifact hash mismatch" in item for item in report["findings"]),
                    report,
                )

    def test_ziwei_distinguishes_regressions_from_independent_oracles(self) -> None:
        report = audit_ziwei_provider.audit_ziwei_provider()
        self.assertEqual(report["counts"]["provider_regression_cases"], 32)
        self.assertEqual(report["counts"]["independent_oracles"], 1)
        self.assertEqual(report["counts"]["qualifying_cases"], 32)


class IndependentOracleStrengthTests(unittest.TestCase):
    def _luming_virtual_research_tree(self):
        """Build a temp fulltext tree whose hashes match a patched SOURCE_BOOKS.

        Fulltext verification is a release-time gate: it runs only when an
        explicit research root is available.  These tests build that tree
        locally so the gate's fail-closed behaviour is exercised without an
        installed external corpus.
        """
        import audit_algorithm_sources

        payload = yaml.safe_load(
            audit_luming_provider.FIXTURE.read_text(encoding="utf-8")
        )
        examples = payload.get("source_examples") or ()
        new_books: dict[str, tuple[str, str]] = {}
        temp = tempfile.mkdtemp()
        root = Path(temp)
        for title, (relative, _old_sha) in audit_luming_provider.SOURCE_BOOKS.items():
            cases = [case for case in examples if case.get("source") == title]
            rows: dict[int, list[str]] = {}
            for case in cases:
                anchor = str(case.get("anchor") or "")
                if not anchor.startswith("L"):
                    continue
                start = int(anchor[1:])
                rows.setdefault(start, []).extend(
                    str(pillar) for pillar in (case.get("pillars") or ())
                )
            lines: list[str] = []
            for start, pillars in sorted(rows.items()):
                while len(lines) < start:
                    lines.append("")
                lines[start - 1] = "".join(pillars)
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines), encoding="utf-8")
            new_books[title] = (
                relative,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

        # ``audit_matrix``'s own optional research-root wiring must stay
        # closed in a portable checkout (return None) so it cannot re-open
        # fulltext checks against this synthetic tree; the luming audit uses
        # the explicit ``research_root`` argument to drive ``source_verification``.
        def _fake_research_root(*_args):
            return None

        return new_books, root, patch.object(
            audit_algorithm_sources, "_research_root", _fake_research_root
        )

    def test_luming_verifies_every_source_example_at_hash_bound_text(self) -> None:
        new_books, root, research_patch = self._luming_virtual_research_tree()
        with research_patch, patch.object(
            audit_luming_provider, "SOURCE_BOOKS", new_books
        ):
            report = audit_luming_provider.audit_luming_provider(
                research_root=root
            )
        counts = report["counts"]
        # Runtime Nayin table correctness is independent of the fulltext tree.
        self.assertGreaterEqual(counts["source_expectation_checks"], 30)
        self.assertEqual(counts["source_example_mismatches"], 0)
        # Release source verification runs when an explicit research root is
        # provided, and the reconstructed tree verifies every example anchor.
        self.assertEqual(report["source_verification"]["status"], "verified")
        self.assertGreaterEqual(counts["source_anchor_checks"], 30)

    def test_luming_anchor_mutation_fails_after_hash_gate_is_rebound(self) -> None:
        payload = yaml.safe_load(
            audit_luming_provider.FIXTURE.read_text(encoding="utf-8")
        )
        payload["source_examples"][0]["anchor"] = "L999999"
        new_books, root, research_patch = self._luming_virtual_research_tree()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "luming-v51.yaml"
            path.write_text(
                yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            rebound = hashlib.sha256(path.read_bytes()).hexdigest()
            with research_patch, patch.object(
                audit_luming_provider, "EXPECTED_FIXTURE_SHA256", rebound
            ), patch.object(
                audit_luming_provider, "SOURCE_BOOKS", new_books
            ):
                report = audit_luming_provider.audit_luming_provider(
                    fixture_path=path, research_root=root
                )
        # The release gate reports the broken anchor, but runtime readiness is
        # a separate property and does not depend on the external fulltext.
        self.assertTrue(report["provider_ready"], report)
        self.assertEqual(report["source_verification"]["status"], "failed")
        self.assertTrue(
            any(
                "source anchor" in item
                for item in report["source_verification"].get("findings") or ()
            ),
            report,
        )

    def test_meihua_independent_formula_recomputes_all_thirty_cases(self) -> None:
        report = audit_meihua_provider.audit_meihua_provider()
        self.assertEqual(report["counts"]["independent_formula_cases"], 30)
        self.assertEqual(report["counts"]["independent_formula_mismatches"], 0)


if __name__ == "__main__":
    unittest.main()
