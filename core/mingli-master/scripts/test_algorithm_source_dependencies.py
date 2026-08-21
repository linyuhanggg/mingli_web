"""Regression tests for the algorithm-source dependency preflight audit."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import yaml

import audit_algorithm_sources


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "references" / "matrices" / "algorithm-source-dependencies.yaml"
TASK6_SYSTEMS = ("bazi", "fortune", "ziwei", "liuren")


class AlgorithmSourceDependencyAuditTests(unittest.TestCase):
    def _matrix(self) -> dict:
        return yaml.safe_load(MATRIX.read_text(encoding="utf-8"))

    def test_task6_dependencies_are_source_verified_before_fact_extension(self) -> None:
        report = audit_algorithm_sources.audit_matrix(
            self._matrix(),
            root=ROOT,
            systems=TASK6_SYSTEMS,
            verify_research_sources=True,
        )

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["audited_systems"], list(TASK6_SYSTEMS))
        self.assertGreaterEqual(report["dependency_count"], 9)
        self.assertEqual(report["findings"], [])

    def test_all_thirteen_provider_dependencies_are_source_verified(self) -> None:
        report = audit_algorithm_sources.audit_matrix(
            self._matrix(),
            root=ROOT,
            verify_research_sources=True,
        )

        self.assertTrue(report["ok"], report)
        self.assertEqual(
            report["audited_systems"],
            list(audit_algorithm_sources.REQUIRED_PROVIDER_SYSTEMS),
        )
        self.assertGreaterEqual(report["dependency_count"], 35)

    def test_tampered_research_hash_is_rejected(self) -> None:
        payload = self._matrix()
        tampered = copy.deepcopy(payload)
        tampered["providers"]["bazi"]["dependencies"][0]["primary_sources"][0][
            "sha256"
        ] = "0" * 64

        report = audit_algorithm_sources.audit_matrix(
            tampered,
            root=ROOT,
            systems=("bazi",),
            verify_research_sources=True,
        )

        self.assertFalse(report["ok"])
        self.assertTrue(any("sha256 mismatch" in item for item in report["findings"]))

    def test_missing_independent_sample_is_rejected(self) -> None:
        payload = self._matrix()
        broken = copy.deepcopy(payload)
        del broken["providers"]["ziwei"]["dependencies"][0][
            "independent_test_sample"
        ]

        report = audit_algorithm_sources.audit_matrix(
            broken,
            root=ROOT,
            systems=("ziwei",),
            verify_research_sources=False,
        )

        self.assertFalse(report["ok"])
        self.assertTrue(
            any("independent_test_sample" in item for item in report["findings"])
        )

    def test_independent_sample_must_resolve_to_a_real_anchored_file(self) -> None:
        payload = self._matrix()
        broken = copy.deepcopy(payload)
        sample = broken["providers"]["bazi"]["dependencies"][0][
            "independent_test_sample"
        ]
        sample["source_path"] = "references/fixtures/does-not-exist.yaml"
        sample["source_anchor"] = "missing-case"

        report = audit_algorithm_sources.audit_matrix(
            broken,
            root=ROOT,
            systems=("bazi",),
            verify_research_sources=False,
        )

        self.assertFalse(report["ok"])
        self.assertTrue(
            any(
                "independent_test_sample" in item and "source_path" in item
                for item in report["findings"]
            ),
            report,
        )

    def test_independent_sample_anchor_must_name_its_exact_case(self) -> None:
        payload = self._matrix()
        broken = copy.deepcopy(payload)
        sample = broken["providers"]["xingming"]["dependencies"][0][
            "independent_test_sample"
        ]
        sample["source_anchor"] = "xingming-house-and-mingshen-opposition"

        report = audit_algorithm_sources.audit_matrix(
            broken,
            root=ROOT,
            systems=("xingming",),
            verify_research_sources=False,
        )

        self.assertFalse(report["ok"])
        self.assertTrue(
            any("must equal sample id" in item for item in report["findings"]),
            report,
        )

    def test_structured_independent_sample_requires_complete_case_fields(self) -> None:
        payload = self._matrix()
        broken = copy.deepcopy(payload)
        fixture = {
            "schema_version": "mingli-algorithm-source-samples-v1",
            "cases": {
                "xingming-seven-luminaries-j2000": {
                    "source_reference": "independent oracle",
                    "input": "2000-01-01T12:00:00Z",
                    "verification": "values were recorded from the pinned distribution",
                }
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_path = Path(temp_dir) / "samples.yaml"
            fixture_path.write_text(
                yaml.safe_dump(fixture, allow_unicode=True),
                encoding="utf-8",
            )
            sample = broken["providers"]["xingming"]["dependencies"][0][
                "independent_test_sample"
            ]
            sample["source_path"] = str(fixture_path)

            report = audit_algorithm_sources.audit_matrix(
                broken,
                root=ROOT,
                systems=("xingming",),
                verify_research_sources=False,
            )

        self.assertFalse(report["ok"])
        self.assertTrue(
            any("fixture case" in item and "expected" in item for item in report["findings"]),
            report,
        )

    def test_structured_independent_sample_rejects_deferred_verification(self) -> None:
        payload = self._matrix()
        broken = copy.deepcopy(payload)
        fixture = {
            "schema_version": "mingli-algorithm-source-samples-v1",
            "cases": {
                "xingming-seven-luminaries-j2000": {
                    "source_reference": "independent oracle",
                    "input": "2000-01-01T12:00:00Z",
                    "expected": {"Sun": 280.368738639819},
                    "verification": "numeric values will be frozen in Task 7A",
                }
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_path = Path(temp_dir) / "samples.yaml"
            fixture_path.write_text(
                yaml.safe_dump(fixture, allow_unicode=True),
                encoding="utf-8",
            )
            sample = broken["providers"]["xingming"]["dependencies"][0][
                "independent_test_sample"
            ]
            sample["source_path"] = str(fixture_path)

            report = audit_algorithm_sources.audit_matrix(
                broken,
                root=ROOT,
                systems=("xingming",),
                verify_research_sources=False,
            )

        self.assertFalse(report["ok"])
        self.assertTrue(
            any("deferred verification" in item for item in report["findings"]),
            report,
        )

    def test_commentary_dependency_must_resolve_to_a_real_anchor(self) -> None:
        payload = self._matrix()
        broken = copy.deepcopy(payload)
        commentary = broken["providers"]["bazi"]["dependencies"][0][
            "commentary_dependencies"
        ][0]
        commentary["anchor"] = "ANCHOR-THAT-DOES-NOT-EXIST"

        report = audit_algorithm_sources.audit_matrix(
            broken,
            root=ROOT,
            systems=("bazi",),
            verify_research_sources=False,
        )

        self.assertFalse(report["ok"])
        self.assertTrue(
            any(
                "commentary dependency" in item and "anchor not found" in item
                for item in report["findings"]
            ),
            report,
        )

    def test_engineering_reference_requires_upstream_and_reviewed_hash(self) -> None:
        payload = self._matrix()
        broken = copy.deepcopy(payload)
        reference = broken["providers"]["bazi"]["dependencies"][0][
            "engineering_references"
        ][0]
        reference.pop("distribution_sha256")
        reference.pop("upstream")

        report = audit_algorithm_sources.audit_matrix(
            broken,
            root=ROOT,
            systems=("bazi",),
            verify_research_sources=False,
        )

        self.assertFalse(report["ok"])
        self.assertTrue(
            any("reviewed hash" in item or "upstream" in item for item in report["findings"]),
            report,
        )

    def test_placeholder_vocabulary_is_rejected(self) -> None:
        payload = self._matrix()
        broken = copy.deepcopy(payload)
        broken["providers"]["liuren"]["dependencies"][0]["version"] = "TODO"

        report = audit_algorithm_sources.audit_matrix(
            broken,
            root=ROOT,
            systems=("liuren",),
            verify_research_sources=False,
        )

        self.assertFalse(report["ok"])
        self.assertTrue(any("placeholder" in item for item in report["findings"]))

    def test_engineering_provenance_must_match_the_audited_distribution(self) -> None:
        payload = self._matrix()
        broken = copy.deepcopy(payload)
        reference = broken["providers"]["ziwei"]["dependencies"][0][
            "engineering_references"
        ][0]
        reference["npm_integrity"] = "sha512-not-the-reviewed-distribution"

        report = audit_algorithm_sources.audit_matrix(
            broken,
            root=ROOT,
            systems=("ziwei",),
            verify_research_sources=False,
        )

        self.assertFalse(report["ok"])
        self.assertTrue(
            any("provenance" in item for item in report["findings"]),
            report,
        )

    def test_compiled_source_artifact_must_match_its_declared_hash(self) -> None:
        payload = self._matrix()
        broken = copy.deepcopy(payload)
        artifact = broken["providers"]["liuyao"]["dependencies"][0][
            "source_artifact"
        ]
        artifact["sha256"] = "0" * 64

        report = audit_algorithm_sources.audit_matrix(
            broken,
            root=ROOT,
            systems=("liuyao",),
            verify_research_sources=False,
        )

        self.assertFalse(report["ok"])
        self.assertTrue(
            any("source artifact" in item and "sha256 mismatch" in item for item in report["findings"]),
            report,
        )


if __name__ == "__main__":
    unittest.main()
