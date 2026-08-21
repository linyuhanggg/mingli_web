#!/usr/bin/env python3
"""Contract tests for live provider algorithm dependency declarations."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

import yaml

from reading_engine import contracts
from reading_engine.providers import PROVIDER_CAPABILITIES


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "references/matrices/algorithm-source-dependencies.yaml"


def _manifest_pairs(payload: dict, system: str) -> tuple[tuple[str, str], ...]:
    dependencies = payload["providers"][system]["dependencies"]
    return tuple((row["id"], row["version"]) for row in dependencies)


class AlgorithmDependencyDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_contract_exposes_typed_algorithm_dependency(self) -> None:
        self.assertTrue(hasattr(contracts, "ProviderAlgorithmDependency"))
        dependency_type = getattr(contracts, "ProviderAlgorithmDependency")
        dependency = dependency_type(id="example.formula", version="formula-v1")
        self.assertEqual(
            dependency.to_dict(),
            {"id": "example.formula", "version": "formula-v1"},
        )

    def test_all_live_routes_exactly_declare_manifest_ids_and_versions(self) -> None:
        capabilities = PROVIDER_CAPABILITIES
        self.assertEqual(set(capabilities), set(self.manifest["providers"]))
        for system, capability in capabilities.items():
            with self.subTest(system=system):
                declared = tuple(
                    (dependency.id, dependency.version)
                    for dependency in capability.algorithm_dependencies
                )
                self.assertTrue(declared)
                self.assertEqual(declared, _manifest_pairs(self.manifest, system))

    def test_manifest_version_mutation_no_longer_matches_live_declaration(self) -> None:
        capabilities = PROVIDER_CAPABILITIES
        for system, capability in capabilities.items():
            with self.subTest(system=system):
                mutated = copy.deepcopy(self.manifest)
                mutated["providers"][system]["dependencies"][0]["version"] += "-mutated"
                declared = tuple(
                    (dependency.id, dependency.version)
                    for dependency in capability.algorithm_dependencies
                )
                self.assertNotEqual(declared, _manifest_pairs(mutated, system))

    def test_dependency_serialization_is_stable_nonempty_and_duplicate_free(self) -> None:
        for system, capability in PROVIDER_CAPABILITIES.items():
            with self.subTest(system=system):
                first = capability.to_dict()
                second = capability.to_dict()
                self.assertEqual(first, second)
                serialized = first["algorithm_dependencies"]
                self.assertTrue(serialized)
                pairs = tuple((row["id"], row["version"]) for row in serialized)
                self.assertEqual(len(pairs), len(set(pairs)))
                self.assertEqual(len({row["id"] for row in serialized}), len(serialized))
                self.assertTrue(
                    all(row["id"].strip() and row["version"].strip() for row in serialized)
                )

    def test_capability_round_trip_preserves_dependency_declaration(self) -> None:
        for system, capability in PROVIDER_CAPABILITIES.items():
            with self.subTest(system=system):
                restored = contracts.ProviderCapability.from_dict(capability.to_dict())
                self.assertEqual(restored, capability)


if __name__ == "__main__":
    unittest.main()
