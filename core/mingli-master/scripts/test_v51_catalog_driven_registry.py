"""Catalog loader behavior with domain-free fixture vocabulary."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reading_engine.catalog import CatalogError, CatalogLoader

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_CATALOG_ROOT = ROOT / "resources/runtime"


def _manifest(provider_id: str = "capability.alpha", **overrides: object) -> dict:
    manifest = {
        "schema_version": "provider-manifest-v1",
        "id": provider_id,
        "entrypoint": "fixture.module:Adapter",
        "display": {
            "zh-CN": {
                "name": "示例能力",
                "description": "根据已声明资料生成确定性事实。",
            }
        },
        "capability": {
            "object_ids": ["object.one"],
            "horizon_ids": ["horizon.one"],
            "dimension_ids": ["dimension.one", "dimension.two"],
            "default_dimension_ids": ["dimension.one"],
            "required_input_groups": [
                {"any_of": ["input.one", "input.two"]},
            ],
            "exact_horizon_ids": [],
            "independent_lineage_id": "lineage.one",
            "assumption_cost": 0,
            "default_priority": 100,
        },
        "input_fields": {
            "input.one": {"type": "string", "display": {"zh-CN": "资料一"}},
            "input.two": {"type": "string", "display": {"zh-CN": "资料二"}},
            "input.extra": {"type": "string", "display": {"zh-CN": "扩展资料"}},
        },
        "evidence_profile_id": "evidence.alpha",
    }
    manifest.update(overrides)
    return manifest


class _CatalogDir:
    def __init__(self, manifests: list[dict]) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "providers").mkdir()
        entries = []
        for manifest in manifests:
            name = f"providers/{manifest['id']}.json"
            (root / name).write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            entries.append(name)
        (root / "catalog-v1.json").write_text(
            json.dumps(
                {"schema_version": "catalog-v1", "providers": entries},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.root = root

    def cleanup(self) -> None:
        self._tmp.cleanup()


class CatalogTests(unittest.TestCase):
    def _load(self, manifests: list[dict]):
        fixture = _CatalogDir(manifests)
        self.addCleanup(fixture.cleanup)
        return CatalogLoader(fixture.root).load()

    def test_loads_fixture_manifest_without_domain_knowledge(self) -> None:
        catalog = self._load([_manifest()])
        descriptor = catalog.descriptor("capability.alpha")
        self.assertEqual(descriptor.entrypoint, "fixture.module:Adapter")
        self.assertEqual(
            descriptor.capability.dimension_ids,
            ("dimension.one", "dimension.two"),
        )
        self.assertEqual(
            descriptor.capability.required_input_groups,
            (("input.one", "input.two"),),
        )

    def test_rejects_duplicate_provider_ids(self) -> None:
        fixture = _CatalogDir([_manifest()])
        self.addCleanup(fixture.cleanup)
        duplicate = _manifest()
        (fixture.root / "providers/duplicate.json").write_text(
            json.dumps(duplicate, ensure_ascii=False),
            encoding="utf-8",
        )
        catalog_path = fixture.root / "catalog-v1.json"
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        payload["providers"].append("providers/duplicate.json")
        catalog_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaises(CatalogError):
            CatalogLoader(fixture.root).load()

    def test_rejects_language_routing_fields(self) -> None:
        for banned in ("keywords", "aliases", "synonyms", "regex"):
            with self.subTest(banned=banned):
                bad = _manifest()
                bad[banned] = ["anything"]
                with self.assertRaises(CatalogError):
                    self._load([bad])
                nested = _manifest()
                nested["capability"] = dict(nested["capability"])
                nested["capability"][banned] = ["anything"]
                with self.assertRaises(CatalogError):
                    self._load([nested])

    def test_rejects_default_dimensions_outside_capability(self) -> None:
        bad = _manifest()
        bad["capability"] = dict(bad["capability"])
        bad["capability"]["default_dimension_ids"] = ["dimension.unknown"]
        with self.assertRaises(CatalogError):
            self._load([bad])

    def test_rejects_empty_declared_default_dimensions(self) -> None:
        bad = _manifest()
        bad["capability"] = dict(bad["capability"])
        bad["capability"]["default_dimension_ids"] = []
        with self.assertRaises(CatalogError):
            self._load([bad])

    def test_rejects_required_group_with_unknown_field(self) -> None:
        bad = _manifest()
        bad["capability"] = dict(bad["capability"])
        bad["capability"]["required_input_groups"] = [
            {"any_of": ["input.unknown"]}
        ]
        with self.assertRaises(CatalogError):
            self._load([bad])

    def test_rejects_path_escape_in_catalog(self) -> None:
        fixture = _CatalogDir([_manifest()])
        self.addCleanup(fixture.cleanup)
        catalog_path = fixture.root / "catalog-v1.json"
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        payload["providers"] = ["../outside.json"]
        catalog_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaises(CatalogError):
            CatalogLoader(fixture.root).load()

    def test_broad_request_uses_declared_default_dimensions(self) -> None:
        catalog = self._load([_manifest()])
        selection = catalog.select(
            object_id="object.one",
            horizon_kind_id="horizon.one",
            dimension_ids=(),
        )
        self.assertEqual(selection.kind, "selected")
        self.assertEqual(selection.descriptor.id, "capability.alpha")
        self.assertEqual(selection.effective_dimension_ids, ("dimension.one",))

    def test_broad_request_without_defaults_asks_for_focus(self) -> None:
        manifest = _manifest()
        manifest["capability"] = dict(manifest["capability"])
        del manifest["capability"]["default_dimension_ids"]
        catalog = self._load([manifest])
        selection = catalog.select(
            object_id="object.one",
            horizon_kind_id="horizon.one",
            dimension_ids=(),
        )
        self.assertEqual(selection.kind, "need_focus")

    def test_explicit_capability_must_stay_compatible(self) -> None:
        catalog = self._load([_manifest()])
        selection = catalog.select(
            object_id="object.other",
            horizon_kind_id="horizon.one",
            dimension_ids=(),
            capability_id="capability.alpha",
        )
        self.assertEqual(selection.kind, "unsupported")

    def test_assumption_cost_does_not_pick_a_semantic_capability(self) -> None:
        # Even when one candidate declares a lower assumption_cost /
        # default_priority, the catalog must surface the ambiguity to
        # the host model rather than choose for it.
        cheap = _manifest("capability.cheap")
        expensive = _manifest("capability.expensive")
        expensive["capability"] = dict(expensive["capability"])
        expensive["capability"]["assumption_cost"] = 5
        expensive["capability"]["default_priority"] = 200
        expensive["capability"]["independent_lineage_id"] = "lineage.two"
        catalog = self._load([cheap, expensive])
        selection = catalog.select(
            object_id="object.one",
            horizon_kind_id="horizon.one",
            dimension_ids=("dimension.one",),
        )
        self.assertEqual(selection.kind, "ambiguous")
        self.assertEqual(
            {descriptor.id for descriptor in selection.candidates},
            {"capability.cheap", "capability.expensive"},
        )

    def test_structural_tie_returns_ambiguous_not_lexical_pick(self) -> None:
        first = _manifest("capability.tie-a")
        second = _manifest("capability.tie-b")
        second["capability"] = dict(second["capability"])
        second["capability"]["independent_lineage_id"] = "lineage.two"
        catalog = self._load([first, second])
        selection = catalog.select(
            object_id="object.one",
            horizon_kind_id="horizon.one",
            dimension_ids=("dimension.one",),
        )
        self.assertEqual(selection.kind, "ambiguous")
        self.assertEqual(
            {descriptor.id for descriptor in selection.candidates},
            {"capability.tie-a", "capability.tie-b"},
        )

    def test_missing_required_inputs_report_minimal_gaps_only(self) -> None:
        catalog = self._load([_manifest()])
        descriptor = catalog.descriptor("capability.alpha")
        self.assertEqual(
            catalog.missing_input_groups(descriptor, frozenset()),
            (("input.one", "input.two"),),
        )
        self.assertEqual(
            catalog.missing_input_groups(descriptor, frozenset({"input.two"})),
            (),
        )
        # precision-only fields never appear as blocking gaps
        self.assertEqual(
            catalog.missing_input_groups(
                descriptor, frozenset({"input.one"})
            ),
            (),
        )

    def test_manifest_digest_is_stable_and_content_sensitive(self) -> None:
        first = self._load([_manifest()])
        second = self._load([_manifest()])
        self.assertEqual(first.manifest_digest, second.manifest_digest)
        changed = _manifest()
        changed["capability"] = dict(changed["capability"])
        changed["capability"]["default_priority"] = 99
        third = self._load([changed])
        self.assertNotEqual(first.manifest_digest, third.manifest_digest)

    def test_provider_count_is_not_fixed(self) -> None:
        one = self._load([_manifest("capability.alpha")])
        beta = _manifest("capability.beta")
        beta["capability"] = dict(beta["capability"])
        beta["capability"]["object_ids"] = ["object.two"]
        beta["capability"]["independent_lineage_id"] = "lineage.two"
        two = self._load([_manifest("capability.alpha"), beta])
        self.assertEqual(len(one.descriptors), 1)
        self.assertEqual(len(two.descriptors), 2)


class ProviderManifestExportTests(unittest.TestCase):
    """Exported production manifests stay equivalent to live declarations."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = CatalogLoader(RUNTIME_CATALOG_ROOT).load()

    def test_every_live_capability_has_one_manifest(self) -> None:
        from reading_engine.providers import PROVIDER_CAPABILITIES

        live = PROVIDER_CAPABILITIES
        loaded_ids = {descriptor.id for descriptor in self.catalog.descriptors}
        self.assertTrue(live, "live declarations must not be empty")
        self.assertEqual(loaded_ids, set(live))

    def test_manifest_capability_round_trips_against_live_descriptor(self) -> None:
        from reading_engine.providers import PROVIDER_CAPABILITIES
        from reading_engine.contracts import ProviderCapability

        for descriptor in self.catalog.descriptors:
            live = PROVIDER_CAPABILITIES[descriptor.id]
            payload = descriptor.canonical_payload.get("runtime_capability")
            self.assertIsInstance(payload, dict, descriptor.id)
            capability_payload = {
                key: value
                for key, value in payload.items()
                if key in ProviderCapability.__dataclass_fields__
            }
            restored = ProviderCapability.from_dict(capability_payload)
            with self.subTest(capability=descriptor.id):
                self.assertEqual(restored.objects, live.objects)
                self.assertEqual(restored.horizons, live.horizons)
                self.assertEqual(restored.dimensions, live.dimensions)
                self.assertEqual(restored.required_inputs, live.required_inputs)
                self.assertEqual(restored.outputs, live.outputs)
                self.assertEqual(
                    restored.extension_outputs, live.extension_outputs
                )
                self.assertEqual(restored.output_bindings, live.output_bindings)
                self.assertEqual(
                    restored.extension_output_bindings,
                    live.extension_output_bindings,
                )
                self.assertEqual(restored.exact_horizons, live.exact_horizons)
                self.assertEqual(
                    restored.independent_lineage, live.independent_lineage
                )
                # capability view must agree with the same live declaration
                capability = descriptor.capability
                self.assertEqual(capability.object_ids, live.objects)
                self.assertEqual(capability.horizon_ids, live.horizons)
                self.assertEqual(capability.dimension_ids, live.dimensions)
                self.assertEqual(
                    capability.required_input_groups,
                    tuple((field,) for field in live.required_inputs),
                )
                self.assertEqual(
                    capability.exact_horizon_ids, live.exact_horizons
                )
                self.assertEqual(
                    capability.independent_lineage_id, live.independent_lineage
                )
                self.assertEqual(capability.assumption_cost, live.assumption_cost)
                self.assertEqual(capability.default_priority, live.default_priority)

    def test_broad_defaults_match_current_unrestricted_broad_behavior(self) -> None:
        """Existing broad requests impose no dimension subset restriction."""
        from reading_engine.providers import PROVIDER_CAPABILITIES

        for descriptor in self.catalog.descriptors:
            live = PROVIDER_CAPABILITIES[descriptor.id]
            defaults = descriptor.capability.default_dimension_ids
            with self.subTest(capability=descriptor.id):
                self.assertIsNotNone(defaults, descriptor.id)
                self.assertTrue(defaults)
                self.assertTrue(set(defaults) <= set(live.dimensions))
                self.assertEqual(defaults, live.dimensions)

    def test_manifests_do_not_carry_algorithm_authority(self) -> None:
        for descriptor in self.catalog.descriptors:
            serialized = json.dumps(
                descriptor.canonical_payload, ensure_ascii=False
            )
            self.assertNotIn("algorithm_dependencies", serialized, descriptor.id)

    def test_each_entrypoint_reports_pinned_live_algorithm_dependencies(
        self,
    ) -> None:
        import importlib

        from reading_engine.providers import PROVIDER_CAPABILITIES

        for descriptor in self.catalog.descriptors:
            module_name, _, class_name = descriptor.entrypoint.partition(":")
            with self.subTest(capability=descriptor.id):
                module = importlib.import_module(module_name)
                self.assertTrue(hasattr(module, class_name), descriptor.entrypoint)
                live = PROVIDER_CAPABILITIES[descriptor.id]
                self.assertTrue(live.algorithm_dependencies, descriptor.id)
                for dependency in live.algorithm_dependencies:
                    self.assertTrue(dependency.id.strip())
                    self.assertTrue(dependency.version.strip())


class _FixtureCapability:
    """Minimal capability view declaring the bound manifest id as system."""

    def __init__(self, system: str) -> None:
        self.system = system


class FixtureFourteenthProvider:
    """Domain-free fixture adapter used to prove open-ended registration."""

    provider_id = "fixture.fourteenth.v1"
    provider_version = "1.0.0"

    def __init__(self, skill_dir: object = None) -> None:
        self.skill_dir = skill_dir
        self._descriptor = None

    def bind_descriptor(self, descriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self):
        return self._descriptor

    @property
    def capability(self) -> _FixtureCapability:
        return _FixtureCapability(
            self._descriptor.id if self._descriptor is not None else ""
        )

    def prepare(self, request, context):
        raise NotImplementedError("the fixture adapter never prepares")


class ProviderRegistryTests(unittest.TestCase):
    def _fixture_catalog(self, extra: list[dict] | None = None):
        manifests = [_manifest()]
        if extra:
            manifests.extend(extra)
        fixture = _CatalogDir(manifests)
        self.addCleanup(fixture.cleanup)
        return CatalogLoader(fixture.root).load()

    def test_fourteenth_provider_needs_no_factory_edit(self) -> None:
        from reading_engine.provider_registry import ProviderRegistry

        fourteenth = _manifest("capability.fourteenth")
        fourteenth["entrypoint"] = (
            "test_v51_catalog_driven_registry:FixtureFourteenthProvider"
        )
        fourteenth["capability"] = dict(fourteenth["capability"])
        fourteenth["capability"]["independent_lineage_id"] = "lineage.fourteen"
        catalog = self._fixture_catalog([fourteenth])
        registry = ProviderRegistry(
            catalog,
            skill_root=ROOT,
            construction={"skill_dir": ROOT},
        )
        adapter = registry.instantiate(
            catalog.descriptor("capability.fourteenth")
        )
        # The registry may import the fixture module under its own name, so
        # assert on adapter identity data instead of class object identity.
        self.assertEqual(
            type(adapter).__name__, "FixtureFourteenthProvider"
        )
        self.assertEqual(adapter.provider_id, "fixture.fourteenth.v1")
        self.assertEqual(
            registry.descriptor("capability.fourteenth").id,
            "capability.fourteenth",
        )

    def test_entrypoint_outside_skill_root_is_rejected(self) -> None:
        from reading_engine.provider_registry import (
            ProviderRegistry,
            RegistryError,
        )

        outside = _manifest("capability.outside")
        outside["entrypoint"] = "json:JSONDecoder"
        outside["capability"] = dict(outside["capability"])
        outside["capability"]["independent_lineage_id"] = "lineage.outside"
        catalog = self._fixture_catalog([outside])
        registry = ProviderRegistry(
            catalog,
            skill_root=ROOT,
            construction={"skill_dir": ROOT},
        )
        with self.assertRaises(RegistryError):
            registry.instantiate(catalog.descriptor("capability.outside"))

    def test_production_registry_instantiates_all_catalog_providers(self) -> None:
        from reading_engine.provider_registry import ProviderRegistry

        catalog = CatalogLoader(RUNTIME_CATALOG_ROOT).load()
        registry = ProviderRegistry(
            catalog,
            skill_root=ROOT,
            construction={"skill_dir": ROOT, "fortune_profile": None},
        )
        adapters = registry.adapters()
        self.assertEqual(set(adapters), {d.id for d in catalog.descriptors})
        for provider_id, adapter in adapters.items():
            with self.subTest(capability=provider_id):
                self.assertTrue(getattr(adapter, "provider_id", ""))
                self.assertTrue(hasattr(adapter, "capability"))

    def test_adapter_capability_is_bound_from_its_manifest(self) -> None:
        """A manifest edit must not require a duplicate Python capability edit."""
        from dataclasses import replace

        from reading_engine.provider_registry import ProviderRegistry

        catalog = CatalogLoader(RUNTIME_CATALOG_ROOT).load()
        descriptor = catalog.descriptors[0]
        payload = dict(descriptor.canonical_payload)
        runtime = dict(payload["runtime_capability"])
        runtime["outputs"] = ["fixture.manifest-owned-output"]
        payload["runtime_capability"] = runtime
        rebound = replace(descriptor, canonical_payload=payload)
        registry = ProviderRegistry(
            catalog,
            skill_root=ROOT,
            construction={"skill_dir": ROOT},
        )

        adapter = registry.instantiate(rebound)

        self.assertEqual(
            adapter.capability.outputs,
            ("fixture.manifest-owned-output",),
        )

    def test_provider_classes_do_not_keep_a_second_capability_table(self) -> None:
        from reading_engine.provider_registry import ProviderRegistry

        catalog = CatalogLoader(RUNTIME_CATALOG_ROOT).load()
        adapters = ProviderRegistry(
            catalog,
            skill_root=ROOT,
            construction={"skill_dir": ROOT},
        ).adapters()

        for provider_id, adapter in adapters.items():
            with self.subTest(capability=provider_id):
                self.assertNotIn("capability", type(adapter).__dict__)

    def test_ziwei_provider_import_defers_unrelated_implementations(self) -> None:
        """A one-shot Ziwei import must not compile every other art first."""

        probe = """
import json
import sys

from reading_engine import providers

unrelated = (
    "bazi_calc",
    "liuren_calc",
    "reading_engine.physiognomy",
    "reading_engine.selection",
    "reading_engine.xingming",
)
before = [name for name in unrelated if name in sys.modules]
ziwei_version = providers.ZiweiProvider.provider_version
after = [name for name in unrelated if name in sys.modules]
print(json.dumps({"before": before, "after": after, "ziwei": ziwei_version}))
"""
        completed = subprocess.run(
            [sys.executable, "-B", "-c", probe],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env={"PYTHONPATH": str(ROOT / "scripts"), "PATH": "/usr/bin:/bin"},
            check=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["before"], [])
        self.assertEqual(result["after"], [])
        self.assertIn("iztro-", result["ziwei"])

    def test_ziwei_prepare_scopes_production_evidence(self) -> None:
        from reading_engine import providers

        adapter = providers.ZiweiProvider(ROOT)
        expected = object()
        with (
            mock.patch.object(
                providers.evidence_rules,
                "production_evidence_scope",
            ) as scope,
            mock.patch.object(
                providers._AdapterSeam,
                "prepare",
                return_value=expected,
            ) as base_prepare,
        ):
            actual = adapter.prepare(mock.sentinel.request, mock.sentinel.context)

        self.assertIs(actual, expected)
        scope.assert_called_once_with("ziwei")
        base_prepare.assert_called_once_with(
            mock.sentinel.request,
            mock.sentinel.context,
        )


if __name__ == "__main__":
    unittest.main()
