#!/usr/bin/env python3
"""Behavior tests for the Provider-owned FactContract seam.

The seam is discovered through the existing Provider catalog: a manifest may
carry an optional ``fact_contract`` entrypoint. The registry only trusts
modules below the Skill root, and every failure mode must degrade into an
explicit finding - never an exception that could empty a reply.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import adapter_validate  # noqa: E402
from fact_contracts import FactContract  # noqa: E402
from fact_contracts.registry import FactContractError  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _manifest(provider_id: str = "fixture.system", **overrides: object) -> dict:
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
            "dimension_ids": ["dimension.one"],
            "default_dimension_ids": ["dimension.one"],
            "required_input_groups": [
                {"any_of": ["input.one"]},
            ],
            "exact_horizon_ids": [],
            "independent_lineage_id": "lineage.one",
            "assumption_cost": 0,
            "default_priority": 100,
        },
        "input_fields": {
            "input.one": {"type": "string", "display": {"zh-CN": "资料一"}},
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


def _bazi_pillars_payload() -> dict:
    """A real supplied-pillars bazi payload from the production adapter."""

    import subprocess

    args = [
        sys.executable,
        str(ROOT / "scripts" / "bazi_fact_adapter.py"),
        "pillars",
        "--pillars",
        "乙酉",
        "辛巳",
        "丙午",
        "癸巳",
        "--gender",
        "male",
        "--source",
        "text",
    ]
    completed = subprocess.run(
        args, cwd=ROOT, text=True, capture_output=True, check=True, timeout=60
    )
    return json.loads(completed.stdout)


class FixtureFactContract(FactContract):
    """Domain-free fixture contract living inside the Skill root."""

    contract_id = "fixture.contract"
    replaces_legacy_validation = True

    def required_output_ids(self, payload, base_required):
        return tuple(key for key in base_required if key != "fixture.drop")

    def required_calendar_keys(self, payload, base_required):
        return ("status",)

    def validate_output(self, payload, output):
        if output.get("fixture_marker") != "present":
            return [
                {
                    "level": "error",
                    "code": "fixture_contract_marker_missing",
                    "message": "Fixture contract requires its marker",
                }
            ]
        return []


class BrokenFactContract(FactContract):
    contract_id = "fixture.broken"

    def validate_output(self, payload, output):  # noqa: D401 - hostile body
        raise RuntimeError("the fixture contract always fails internally")


class DictReturnFactContract(FactContract):
    """Hostile: validate_output returns a mapping instead of list[Finding]."""

    contract_id = "fixture.dict_return"

    def validate_output(self, payload, output):
        return {"level": "error", "code": "not_a_finding_list", "message": "x"}


class MalformedFindingsFactContract(FactContract):
    """Hostile: returns a list whose items break the Finding shape."""

    contract_id = "fixture.malformed_findings"

    def validate_output(self, payload, output):
        return [
            {"level": "fatal", "code": "x", "message": "HOSTILE_LEVEL_TEXT"},
            {"level": "error", "message": "HOSTILE_NOCODE_TEXT"},
            "HOSTILE_NONDICT_TEXT",
        ]


class RuntimeCtorFactContract(FactContract):
    """Hostile: the constructor raises a non-TypeError exception."""

    contract_id = "fixture.runtime_ctor"

    def __init__(self) -> None:
        raise RuntimeError("constructor side effect must never leak raw")


class EmptyIdFactContract(FactContract):
    """Hostile: keeps the base class empty contract_id."""


class FactContractRegistryTests(unittest.TestCase):
    def _registry(self, manifests: list[dict]):
        from fact_contracts.registry import FactContractRegistry

        fixture = _CatalogDir(manifests)
        self.addCleanup(fixture.cleanup)
        return FactContractRegistry(fixture.root, skill_root=ROOT)

    def test_undelcared_system_has_no_contract(self) -> None:
        registry = self._registry([_manifest()])
        self.assertIsNone(registry.resolve("fixture.system"))

    def test_declared_entrypoint_inside_skill_root_loads(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:FixtureFactContract"
        )
        registry = self._registry([manifest])
        contract = registry.resolve("fixture.system")
        self.assertIsNotNone(contract)
        self.assertEqual(contract.contract_id, "fixture.contract")
        self.assertEqual(
            contract.required_output_ids({}, ("a", "fixture.drop")), ("a",)
        )
        self.assertEqual(contract.required_calendar_keys({}, ("status", "ganzhi")), ("status",))
        self.assertEqual(
            contract.validate_output({}, {"fixture_marker": "present"}), []
        )

    def test_production_ziwei_manifest_loads_the_source_integrity_contract(
        self,
    ) -> None:
        manifest = json.loads(
            (
                ROOT
                / "resources"
                / "runtime"
                / "providers"
                / "ziwei.json"
            ).read_text(encoding="utf-8")
        )
        registry = self._registry([manifest])
        contract = registry.resolve("ziwei")
        self.assertIsNotNone(contract)
        self.assertEqual(
            contract.contract_id,
            "ziwei.source-pattern-integrity-v1",
        )

    def test_ziwei_contract_is_independent_from_the_generator(self) -> None:
        source = (
            ROOT / "scripts" / "fact_contracts" / "ziwei.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("ziwei_fact_adapter", source)
        self.assertNotIn("_source_conditioned_patterns", source)

    def test_missing_ziwei_contract_module_degrades_into_a_finding(self) -> None:
        manifest = json.loads(
            (
                ROOT
                / "resources"
                / "runtime"
                / "providers"
                / "ziwei.json"
            ).read_text(encoding="utf-8")
        )
        manifest["fact_contract"] = (
            "fact_contracts.missing_ziwei:ZiweiFactContract"
        )
        fixture = _CatalogDir([manifest])
        self.addCleanup(fixture.cleanup)
        report = adapter_validate._validate_payload(
            "ziwei", {}, catalog_root=fixture.root
        )
        self.assertFalse(report["ok"])
        self.assertIn("fact_contract_load_failed", report["codes"])

    def test_damaged_ziwei_contract_class_degrades_into_a_finding(self) -> None:
        manifest = json.loads(
            (
                ROOT
                / "resources"
                / "runtime"
                / "providers"
                / "ziwei.json"
            ).read_text(encoding="utf-8")
        )
        manifest["fact_contract"] = (
            "fact_contracts.ziwei:MissingZiweiFactContract"
        )
        fixture = _CatalogDir([manifest])
        self.addCleanup(fixture.cleanup)
        report = adapter_validate._validate_payload(
            "ziwei", {}, catalog_root=fixture.root
        )
        self.assertFalse(report["ok"])
        self.assertIn("fact_contract_load_failed", report["codes"])

    def test_entrypoint_outside_skill_root_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = "json:JSONDecoder"
        registry = self._registry([manifest])
        with self.assertRaises(FactContractError) as caught:
            registry.resolve("fixture.system")
        self.assertIn("fact_contract", str(caught.exception))

    def test_dotted_entrypoint_parent_outside_root_never_executes(self) -> None:
        """Adversarial: a dotted entrypoint whose parent package lives outside
        the Skill root must be rejected BEFORE any of its code executes.

        The parent ``__init__.py`` writes a marker file as a side effect; the
        marker must not exist after the rejection, and no hostile module may
        linger in ``sys.modules``.
        """

        hostile = tempfile.TemporaryDirectory()
        self.addCleanup(hostile.cleanup)
        hostile_root = Path(hostile.name)
        marker = hostile_root / "parent_executed.marker"
        package = hostile_root / "hostile_fixture_pkg"
        package.mkdir()
        (package / "__init__.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n",
            encoding="utf-8",
        )
        (package / "child.py").write_text(
            "class Contract:\n    pass\n", encoding="utf-8"
        )
        sys.path.insert(0, str(hostile_root))
        self.addCleanup(lambda: sys.path.remove(str(hostile_root)))
        self.addCleanup(sys.modules.pop, "hostile_fixture_pkg", None)
        self.addCleanup(sys.modules.pop, "hostile_fixture_pkg.child", None)

        manifest = _manifest()
        manifest["fact_contract"] = "hostile_fixture_pkg.child:Contract"
        registry = self._registry([manifest])
        with self.assertRaises(FactContractError):
            registry.resolve("fixture.system")
        self.assertFalse(
            marker.exists(),
            "parent package code ran before the Skill-root rejection",
        )
        self.assertNotIn("hostile_fixture_pkg", sys.modules)
        self.assertNotIn("hostile_fixture_pkg.child", sys.modules)

    def test_dotted_entrypoint_inside_skill_root_loads(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = "fact_contracts.bazi:BaziFactContract"
        registry = self._registry([manifest])
        contract = registry.resolve("fixture.system")
        self.assertIsNotNone(contract)
        self.assertEqual(contract.contract_id, "bazi.supplied-and-computed.v1")

    def test_relative_path_entrypoint_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = "../escape:Contract"
        registry = self._registry([manifest])
        with self.assertRaises(FactContractError):
            registry.resolve("fixture.system")

    def test_malformed_entrypoint_string_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = "no-colon-entrypoint"
        registry = self._registry([manifest])
        with self.assertRaises(FactContractError):
            registry.resolve("fixture.system")

    def test_unknown_module_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = "fixture_missing_module:Contract"
        registry = self._registry([manifest])
        with self.assertRaises(FactContractError):
            registry.resolve("fixture.system")

    def test_malformed_catalog_json_is_rejected(self) -> None:
        fixture = _CatalogDir([_manifest()])
        self.addCleanup(fixture.cleanup)
        (fixture.root / "catalog-v1.json").write_text("{ not json", encoding="utf-8")
        from fact_contracts.registry import FactContractRegistry

        registry = FactContractRegistry(fixture.root, skill_root=ROOT)
        with self.assertRaises(FactContractError):
            registry.resolve("fixture.system")

    def test_constructor_exception_is_normalized_to_fact_contract_error(
        self,
    ) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:RuntimeCtorFactContract"
        )
        registry = self._registry([manifest])
        # The raw RuntimeError must be normalized: the raised object is a
        # FactContractError naming the construction failure, never the
        # contract's own exception type escaping to callers.
        with self.assertRaises(FactContractError) as caught:
            registry.resolve("fixture.system")
        self.assertIs(type(caught.exception), FactContractError)
        self.assertIn("constructible", str(caught.exception))

    def test_empty_contract_id_is_rejected(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:EmptyIdFactContract"
        )
        registry = self._registry([manifest])
        with self.assertRaises(FactContractError) as caught:
            registry.resolve("fixture.system")
        self.assertIn("contract_id", str(caught.exception))


class FactContractShadowLoadingTests(unittest.TestCase):
    """Extension-suffix shadows must never bypass the Skill-root trust walk.

    CPython's FileFinder prefers extension modules over ``.py`` sources, so a
    same-named ``.so`` sitting next to a trusted ``.py`` would be dlopened
    instead of the audited source. The registry must fail closed on any
    shadow candidate, and it must verify the loaded module's origin after
    ``import_module`` so a hostile ``sys.modules`` entry cannot bypass the
    walk either.
    """

    def _registry_for_root(self, manifest: dict, skill_root: Path):
        from fact_contracts.registry import FactContractRegistry

        fixture = _CatalogDir([manifest])
        self.addCleanup(fixture.cleanup)
        return FactContractRegistry(fixture.root, skill_root=skill_root)

    def _trusted_package(self, skill_root: Path, name: str) -> None:
        package = skill_root / name
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "child.py").write_text(
            "class Contract:\n    pass\n", encoding="utf-8"
        )

    def test_shadow_extension_symlink_outside_root_is_rejected_before_import(
        self,
    ) -> None:
        import importlib.machinery

        trusted = Path(tempfile.mkdtemp())
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(trusted, ignore_errors=True))
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        self._trusted_package(trusted, "shadowpkg")
        payload = outside / "payload.so"
        payload.write_bytes(b"not a real shared object")
        shadow = trusted / "shadowpkg" / (
            "child" + importlib.machinery.EXTENSION_SUFFIXES[0]
        )
        shadow.symlink_to(payload)
        sys.path.insert(0, str(trusted))
        self.addCleanup(lambda: sys.path.remove(str(trusted)))
        self.addCleanup(sys.modules.pop, "shadowpkg", None)
        self.addCleanup(sys.modules.pop, "shadowpkg.child", None)

        manifest = _manifest()
        manifest["fact_contract"] = "shadowpkg.child:Contract"
        registry = self._registry_for_root(manifest, trusted)
        with self.assertRaises(FactContractError) as caught:
            registry.resolve("fixture.system")
        message = str(caught.exception)
        self.assertNotIn(
            "cannot be imported",
            message,
            "the shadow extension file must be rejected before any import"
            " attempt reaches it",
        )
        self.assertNotIn("shadowpkg", sys.modules)
        self.assertNotIn("shadowpkg.child", sys.modules)

    def test_same_named_extension_file_inside_root_is_also_rejected(
        self,
    ) -> None:
        import importlib.machinery

        trusted = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(trusted, ignore_errors=True))
        self._trusted_package(trusted, "shadowpkg2")
        shadow = trusted / "shadowpkg2" / (
            "child" + importlib.machinery.EXTENSION_SUFFIXES[0]
        )
        shadow.write_bytes(b"not a real shared object")
        sys.path.insert(0, str(trusted))
        self.addCleanup(lambda: sys.path.remove(str(trusted)))
        self.addCleanup(sys.modules.pop, "shadowpkg2", None)
        self.addCleanup(sys.modules.pop, "shadowpkg2.child", None)

        manifest = _manifest()
        manifest["fact_contract"] = "shadowpkg2.child:Contract"
        registry = self._registry_for_root(manifest, trusted)
        with self.assertRaises(FactContractError) as caught:
            registry.resolve("fixture.system")
        self.assertNotIn("cannot be imported", str(caught.exception))
        self.assertNotIn("shadowpkg2.child", sys.modules)

    def test_cached_module_with_a_forged_in_root_origin_is_rejected(
        self,
    ) -> None:
        # A hostile sys.modules entry may forge __spec__.origin to point at
        # a REAL file inside the Skill root while the loaded object is
        # something else entirely. The post-import check must therefore pin
        # the origin to the exact file the trust walk computed, not merely
        # accept any path below the root.
        import importlib.machinery
        import types

        trusted = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(trusted, ignore_errors=True))
        (trusted / "realfile.py").write_text(
            "class Contract:\n    pass\n", encoding="utf-8"
        )
        (trusted / "forgedorigin.py").write_text(
            "class Contract:\n    pass\n", encoding="utf-8"
        )
        sys.path.insert(0, str(trusted))
        self.addCleanup(lambda: sys.path.remove(str(trusted)))

        forged = types.ModuleType("forgedorigin")
        forged.Contract = FixtureFactContract
        forged.__spec__ = importlib.machinery.ModuleSpec(
            "forgedorigin",
            None,
            origin=str(trusted / "realfile.py"),
        )
        sys.modules["forgedorigin"] = forged
        self.addCleanup(sys.modules.pop, "forgedorigin", None)

        manifest = _manifest()
        manifest["fact_contract"] = "forgedorigin:Contract"
        registry = self._registry_for_root(manifest, trusted)
        with self.assertRaises(FactContractError):
            registry.resolve("fixture.system")

    def test_trusted_module_syntax_error_is_normalized_to_contract_error(
        self,
    ) -> None:
        # A trusted module inside the Skill root that fails to compile must
        # degrade into a structured FactContractError, matching the module's
        # documented contract, instead of leaking a raw SyntaxError.
        trusted = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(trusted, ignore_errors=True))
        (trusted / "brokenmod.py").write_text(
            "class Contract(:\n", encoding="utf-8"
        )
        sys.path.insert(0, str(trusted))
        self.addCleanup(lambda: sys.path.remove(str(trusted)))
        self.addCleanup(sys.modules.pop, "brokenmod", None)

        manifest = _manifest()
        manifest["fact_contract"] = "brokenmod:Contract"
        registry = self._registry_for_root(manifest, trusted)
        with self.assertRaises(FactContractError) as caught:
            registry.resolve("fixture.system")
        self.assertIn("cannot be imported", str(caught.exception))

    def test_sys_modules_cache_of_an_outside_module_cannot_bypass_the_walk(
        self,
    ) -> None:
        import types

        trusted = Path(tempfile.mkdtemp())
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(trusted, ignore_errors=True))
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        self._trusted_package(trusted, "cachepkg")
        outside_file = outside / "evil.py"
        outside_file.write_text("class Contract:\n    pass\n", encoding="utf-8")
        sys.path.insert(0, str(trusted))
        self.addCleanup(lambda: sys.path.remove(str(trusted)))
        self.addCleanup(sys.modules.pop, "cachepkg", None)
        self.addCleanup(sys.modules.pop, "cachepkg.child", None)

        stale = types.ModuleType("cachepkg.child")
        stale.__spec__ = __import__("importlib.machinery", fromlist=["ModuleSpec"]).ModuleSpec(
            "cachepkg.child", None, origin=str(outside_file)
        )
        stale.Contract = FixtureFactContract
        sys.modules["cachepkg.child"] = stale

        manifest = _manifest()
        manifest["fact_contract"] = "cachepkg.child:Contract"
        registry = self._registry_for_root(manifest, trusted)
        with self.assertRaises(FactContractError):
            registry.resolve("fixture.system")


class FactContractFacadeFindingsTests(unittest.TestCase):
    """The facade converts every contract failure into an explicit finding."""

    @staticmethod
    def _hostile_required_keys_report(*, output_keys, calendar_keys):
        class HostileRequiredKeysContract(FactContract):
            contract_id = "fixture.hostile_required_keys"
            replaces_legacy_validation = True

            def required_output_ids(self, payload, base_required):
                return output_keys

            def required_calendar_keys(self, payload, base_required):
                return calendar_keys

        payload = {
            "fact_layer_status": "fixture_facts",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {"junk": 1},
            "calendar_normalization": {"junk": 1},
            "trace": ["fixture"],
        }
        with mock.patch.object(
            adapter_validate,
            "_load_fact_contract",
            return_value=(HostileRequiredKeysContract(), [], True),
        ):
            try:
                return adapter_validate.validate_payload("fixture.system", payload)
            except Exception as error:  # pragma: no cover - RED regression path
                raise AssertionError(
                    f"facade leaked {type(error).__name__} from required-key hook"
                ) from error

    def _report(self, manifest: dict, payload: dict) -> dict:
        fixture = _CatalogDir([manifest])
        self.addCleanup(fixture.cleanup)
        return adapter_validate._validate_payload(
            "fixture.system",
            payload,
            catalog_root=fixture.root,
        )

    def test_contract_findings_flow_into_the_facade_report(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:FixtureFactContract"
        )
        payload = {
            "fact_layer_status": "fixture_facts",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {"fixture_marker": "absent"},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = self._report(manifest, payload)
        self.assertFalse(report["ok"])
        self.assertIn("fixture_contract_marker_missing", report["codes"])

    def test_contract_required_sets_replace_generic_defaults(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:FixtureFactContract"
        )
        # ``fixture.drop`` must not be demanded once the contract trims it,
        # and the calendar requirement shrinks to ``status`` only.
        payload = {
            "fact_layer_status": "fixture_facts",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {"fixture_marker": "present"},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = self._report(manifest, payload)
        self.assertNotIn("missing_calendar:ganzhi", report["codes"])

    def test_unhashable_required_output_key_becomes_a_structured_finding(
        self,
    ) -> None:
        report = self._hostile_required_keys_report(
            output_keys=[{}],
            calendar_keys=(),
        )
        self.assertFalse(report["ok"])
        self.assertIn("fact_contract_invalid_return", report["codes"])

    def test_string_required_output_keys_cannot_bypass_validation(self) -> None:
        report = self._hostile_required_keys_report(
            output_keys="",
            calendar_keys=(),
        )
        self.assertFalse(report["ok"])
        self.assertIn("fact_contract_invalid_return", report["codes"])

    def test_string_required_calendar_keys_cannot_bypass_validation(self) -> None:
        report = self._hostile_required_keys_report(
            output_keys=(),
            calendar_keys="",
        )
        self.assertFalse(report["ok"])
        self.assertIn("fact_contract_invalid_return", report["codes"])

    def test_tuple_subclass_cannot_raise_while_required_keys_are_normalized(
        self,
    ) -> None:
        class ExplodingTuple(tuple):
            def __iter__(self):
                raise RuntimeError("hostile tuple iterator")

        report = self._hostile_required_keys_report(
            output_keys=ExplodingTuple(),
            calendar_keys=(),
        )
        self.assertFalse(report["ok"])
        self.assertIn("fact_contract_invalid_return", report["codes"])

    def test_string_subclass_cannot_raise_while_required_keys_are_normalized(
        self,
    ) -> None:
        class ExplodingString(str):
            def strip(self, *args, **kwargs):
                raise RuntimeError("hostile string strip")

        report = self._hostile_required_keys_report(
            output_keys=(ExplodingString("key"),),
            calendar_keys=(),
        )
        self.assertFalse(report["ok"])
        self.assertIn("fact_contract_invalid_return", report["codes"])

    def test_load_failure_becomes_an_explicit_error_finding(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = "json:JSONDecoder"  # escapes skill root
        payload = {
            "fact_layer_status": "fixture_facts",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = self._report(manifest, payload)
        self.assertFalse(report["ok"])
        self.assertTrue(
            any(code.startswith("fact_contract_load_failed") for code in report["codes"]),
            report["codes"],
        )

    def test_contract_runtime_exception_becomes_an_explicit_finding(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:BrokenFactContract"
        )
        payload = {
            "fact_layer_status": "fixture_facts",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {"anything": 1},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = self._report(manifest, payload)
        self.assertFalse(report["ok"])
        self.assertTrue(
            any(code.startswith("fact_contract_error") for code in report["codes"]),
            report["codes"],
        )

    def test_dict_returning_contract_degrades_into_a_structured_finding(
        self,
    ) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:DictReturnFactContract"
        )
        payload = {
            "fact_layer_status": "fixture_facts",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {"fixture_marker": "present"},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = self._report(manifest, payload)  # must not raise TypeError
        self.assertEqual(set(report), {"ok", "system", "findings", "codes"})
        self.assertFalse(report["ok"])
        self.assertTrue(report["findings"])
        for item in report["findings"]:
            self.assertEqual(set(item), {"level", "code", "message"}, item)
        self.assertTrue(
            any(
                code.startswith("fact_contract_invalid_return")
                for code in report["codes"]
            ),
            report["codes"],
        )

    def test_malformed_finding_items_carry_reason_without_item_content(
        self,
    ) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:MalformedFindingsFactContract"
        )
        payload = {
            "fact_layer_status": "fixture_facts",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {"fixture_marker": "present"},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = self._report(manifest, payload)
        self.assertFalse(report["ok"])
        invalid = [
            item
            for item in report["findings"]
            if item["code"].startswith("fact_contract_invalid_return")
        ]
        self.assertEqual(len(invalid), 3, report["findings"])
        reasons = [item["message"] for item in invalid]
        self.assertTrue(
            any("invalid level" in message for message in reasons), reasons
        )
        self.assertTrue(
            any("missing code" in message for message in reasons), reasons
        )
        self.assertTrue(
            any("non-dict item" in message for message in reasons), reasons
        )
        # The hostile item content must never be inlined into the report.
        serialized = json.dumps(report)
        self.assertNotIn("HOSTILE_", serialized)

    def test_broken_constructor_degrades_into_a_load_finding(self) -> None:
        manifest = _manifest()
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:RuntimeCtorFactContract"
        )
        payload = {
            "fact_layer_status": "fixture_facts",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = self._report(manifest, payload)
        self.assertFalse(report["ok"])
        self.assertIn("fact_contract_load_failed", report["codes"])
        self.assertIn("fact_contract_unavailable", report["codes"])
        self.assertNotIn("unknown_system", report["codes"])

    def test_declared_system_with_a_missing_entrypoint_module_reports_unavailable(
        self,
    ) -> None:
        """A declared Provider whose contract cannot load must be
        reported as an unavailable capability, never as an unknown system;
        the two findings together used to contradict the severed-contract
        semantics introduced for the deletion drill."""

        manifest = _manifest()
        manifest["fact_contract"] = "fixture_missing_module:Contract"
        payload = {
            "fact_layer_status": "fixture_facts",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = self._report(manifest, payload)
        self.assertFalse(report["ok"])
        self.assertIn("fact_contract_load_failed", report["codes"])
        self.assertIn("fact_contract_unavailable", report["codes"])
        self.assertNotIn("unknown_system", report["codes"])

    def test_malformed_catalog_becomes_an_explicit_finding(self) -> None:
        fixture = _CatalogDir([_manifest()])
        self.addCleanup(fixture.cleanup)
        (fixture.root / "catalog-v1.json").write_text("{ broken", encoding="utf-8")
        report = adapter_validate._validate_payload(
            "fixture.system",
            {
                "fact_layer_status": "fixture_facts",
                "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
                "output": {},
                "calendar_normalization": {"status": "not_applicable"},
                "trace": ["fixture"],
            },
            catalog_root=fixture.root,
        )
        self.assertFalse(report["ok"])
        self.assertTrue(
            any(code.startswith("fact_contract_load_failed") for code in report["codes"]),
            report["codes"],
        )

    def test_declared_contract_makes_a_new_system_known_without_dispatch_edit(self) -> None:
        # Locality: a brand-new system needs only a manifest plus a contract
        # module; the generic facade must not demand an unknown_system edit.
        manifest = _manifest("fixture.newsystem")
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:FixtureFactContract"
        )
        fixture = _CatalogDir([manifest])
        self.addCleanup(fixture.cleanup)
        report = adapter_validate._validate_payload(
            "fixture.newsystem",
            {
                "fact_layer_status": "fixture_facts",
                "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
                "output": {"fixture_marker": "present"},
                "calendar_normalization": {"status": "not_applicable"},
                "trace": ["fixture"],
            },
            catalog_root=fixture.root,
        )
        self.assertNotIn("unknown_system", report["codes"], report)
        self.assertTrue(report["ok"], report)

    def test_undeclared_unknown_system_still_reports_unknown_system(self) -> None:
        fixture = _CatalogDir([_manifest()])
        self.addCleanup(fixture.cleanup)
        report = adapter_validate._validate_payload(
            "not.a.real.system", {}, catalog_root=fixture.root
        )
        self.assertFalse(report["ok"])
        self.assertIn("unknown_system", report["codes"])


class BaziContractDeletionTests(unittest.TestCase):
    """Deleting the bazi FactContract must delete the bazi contract behavior.

    Behavioral deletion test: the same fabricated partial-luck payload is
    validated once through the production catalog (contract wired) and once
    through a catalog whose bazi manifest no longer declares ``fact_contract``
    (contract deleted). The oracle finding must exist only in the first case,
    proving the bazi rules physically live behind the seam.

    Acceptance semantics (independent acceptance P2): the PASS criterion is
    that the system ACTIVELY REPORTS the missing capability/contract with a
    structured finding - recognizing its own unavailable state - not merely
    that the bazi strings disappear from the report.
    """

    def _fabricated_payload(self) -> dict:
        import json
        import subprocess

        args = [
            sys.executable,
            str(ROOT / "scripts" / "bazi_fact_adapter.py"),
            "pillars",
            "--pillars",
            "乙酉",
            "辛巳",
            "丙午",
            "癸巳",
            "--gender",
            "male",
            "--source",
            "text",
        ]
        completed = subprocess.run(
            args, cwd=ROOT, text=True, capture_output=True, check=True, timeout=60
        )
        payload = json.loads(completed.stdout)
        payload["output"]["luck_cycles"]["cycles"][0]["start_age_years"] = 3.0
        return payload

    def _catalog_without_contract(self) -> Path:
        production = json.loads(
            (ROOT / "resources" / "runtime" / "providers" / "bazi.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("fact_contract", production)
        del production["fact_contract"]
        fixture = _CatalogDir([production])
        self.addCleanup(fixture.cleanup)
        return fixture.root

    def test_production_catalog_enforces_the_bazi_oracle(self) -> None:
        report = adapter_validate.validate_payload("bazi", self._fabricated_payload())
        self.assertIn("bazi_partial_luck_fabricated_timing", report["codes"])

    def test_deleting_the_contract_reports_the_unavailable_state(self) -> None:
        # Positive conformance: once the wiring is cut, the system must
        # emit a structured error finding that explicitly reports the
        # missing fact contract / unavailable capability.
        report = adapter_validate._validate_payload(
            "bazi",
            self._fabricated_payload(),
            catalog_root=self._catalog_without_contract(),
        )
        self.assertEqual(set(report), {"ok", "system", "findings", "codes"})
        self.assertFalse(report["ok"])
        unavailable = [
            item
            for item in report["findings"]
            if item["code"] == "fact_contract_unavailable"
        ]
        self.assertTrue(
            unavailable,
            f"the severed contract must be reported as unavailable: {report}",
        )
        self.assertEqual(unavailable[0]["level"], "error")
        self.assertIn("bazi", unavailable[0]["message"])

    def test_deleting_the_contract_removes_every_bazi_code(self) -> None:
        # Both the fabricated-timing oracle and a conflict-status payload
        # must lose EVERY bazi code once the manifest wiring is deleted.
        # Matching only the ``bazi_`` prefix is insufficient: it would miss
        # ``conflicting_bazi_facts`` leaking from the generic facade.
        conflict = self._fabricated_payload()
        conflict["fact_layer_status"] = (
            "conflict_birth_data_vs_supplied_pillars"
        )
        for payload in (self._fabricated_payload(), conflict):
            with self.subTest(status=payload.get("fact_layer_status")):
                report = adapter_validate._validate_payload(
                    "bazi",
                    payload,
                    catalog_root=self._catalog_without_contract(),
                )
                self.assertFalse(
                    any("bazi" in code for code in report["codes"]), report
                )


class FactContractLocalityForExistingSystemsTests(unittest.TestCase):
    """Migrating any other system must not touch the generic dispatch."""

    def test_contract_bound_to_an_existing_system_id_is_honored(self) -> None:
        manifest = _manifest("qimen")
        manifest["fact_contract"] = (
            "test_v51_fact_contracts:FixtureFactContract"
        )
        fixture = _CatalogDir([manifest])
        self.addCleanup(fixture.cleanup)
        payload = {
            "fact_layer_status": "fixture_facts",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {"fixture_marker": "absent"},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = adapter_validate._validate_payload(
            "qimen", payload, catalog_root=fixture.root
        )
        # The fixture contract (not the legacy qimen validator) owns the
        # findings: proof that migration is a manifest edit plus one module.
        self.assertIn("fixture_contract_marker_missing", report["codes"])
        self.assertFalse(
            any(code.startswith("qimen_") for code in report["codes"]), report
        )


class BaziKnowledgeLocalityTests(unittest.TestCase):
    """Bazi domain knowledge must live in BaziFactContract, not the facade.

    Independent acceptance found the generic facade still owning bazi
    knowledge: any system's payload carrying the bazi conflict status
    received ``conflicting_bazi_facts``, and the bazi required-output list
    was maintained twice (facade table plus contract).
    """

    def test_non_bazi_payload_with_conflict_status_gets_no_bazi_finding(
        self,
    ) -> None:
        manifest = _manifest("qimen")
        fixture = _CatalogDir([manifest])
        self.addCleanup(fixture.cleanup)
        payload = {
            "fact_layer_status": "conflict_birth_data_vs_supplied_pillars",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {"anything": 1},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = adapter_validate._validate_payload(
            "qimen", payload, catalog_root=fixture.root
        )
        self.assertNotIn("conflicting_bazi_facts", report["codes"], report)

    def test_bazi_conflict_payload_still_reports_the_conflict(self) -> None:
        # Behavior compatibility: the same conflict finding must still fire
        # for a real bazi payload, now owned by the contract.
        payload = _bazi_pillars_payload()
        payload["output"]["luck_cycles"]["cycles"][0]["start_age_years"] = 3.0
        payload["fact_layer_status"] = (
            "conflict_birth_data_vs_supplied_pillars"
        )
        report = adapter_validate.validate_payload("bazi", payload)
        self.assertFalse(report["ok"])
        self.assertIn("conflicting_bazi_facts", report["codes"], report)

    def test_conflict_state_fires_even_when_output_is_empty(self) -> None:
        # Behavior compatibility with the pre-migration facade: the legacy
        # conflict check ran regardless of whether ``output`` carried data.
        # The migrated check must not be gated behind a non-empty output.
        payload = _bazi_pillars_payload()
        payload["fact_layer_status"] = (
            "conflict_birth_data_vs_supplied_pillars"
        )
        payload["output"] = {}
        report = adapter_validate.validate_payload("bazi", payload)
        self.assertFalse(report["ok"])
        self.assertEqual(report["codes"][0], "conflicting_bazi_facts", report)

    def test_conflict_payload_for_other_systems_with_empty_output_stays_leak_free(
        self,
    ) -> None:
        manifest = _manifest("qimen")
        fixture = _CatalogDir([manifest])
        self.addCleanup(fixture.cleanup)
        payload = {
            "fact_layer_status": "conflict_birth_data_vs_supplied_pillars",
            "adapter": {"name": "fixture", "version": "1", "rule_profile": "r"},
            "output": {},
            "calendar_normalization": {"status": "not_applicable"},
            "trace": ["fixture"],
        }
        report = adapter_validate._validate_payload(
            "qimen", payload, catalog_root=fixture.root
        )
        self.assertNotIn("conflicting_bazi_facts", report["codes"], report)
        self.assertFalse(
            any("bazi" in code for code in report["codes"]), report
        )

    def test_facade_carries_no_bazi_required_outputs_or_conflict_status(
        self,
    ) -> None:
        self.assertNotIn("bazi", adapter_validate.REQUIRED_OUTPUTS)
        source = Path(adapter_validate.__file__).read_text(encoding="utf-8")
        self.assertNotIn("conflict_birth_data_vs_supplied_pillars", source)
        self.assertNotIn("conflicting_bazi_facts", source)

    def test_bazi_contract_is_the_sole_required_output_authority(self) -> None:
        from fact_contracts.bazi import BaziFactContract

        self.assertEqual(
            BaziFactContract().required_output_ids({}, ()),
            (
                "four_pillars",
                "hidden_stems",
                "ten_gods",
                "nayin",
                "twelve_growth_stages",
                "xunkong",
                "san_yuan",
                "month_command",
                "seasonal_profile",
                "tiaohou_markers",
                "interpretive_candidates",
                "shensha_auxiliary",
                "luck_cycles",
            ),
        )


class ProductionManifestRoutingRegressionTests(unittest.TestCase):
    """Production manifests must never carry natural-language routing data."""

    FORBIDDEN = ("keywords", "aliases", "synonyms", "regex")

    def _walk(self, value, path="$"):
        if isinstance(value, dict):
            for key, child in value.items():
                self.assertNotIn(
                    key,
                    self.FORBIDDEN,
                    f"forbidden routing key at {path}.{key}",
                )
                self._walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self._walk(child, f"{path}[{index}]")

    def test_no_production_manifest_declares_routing_fields(self) -> None:
        provider_dir = ROOT / "resources" / "runtime" / "providers"
        manifests = sorted(provider_dir.glob("*.json"))
        self.assertGreaterEqual(len(manifests), 13)
        for manifest_path in manifests:
            with self.subTest(manifest=manifest_path.name):
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                self._walk(payload, manifest_path.name)

    def test_injected_routing_keys_still_reject_every_production_manifest(
        self,
    ) -> None:
        from reading_engine.catalog import CatalogError, CatalogLoader

        for banned in self.FORBIDDEN:
            with self.subTest(banned=banned):
                fixture = _CatalogDir(
                    [_manifest("bazi", **{banned: ["anything"]})]
                )
                self.addCleanup(fixture.cleanup)
                with self.assertRaises(CatalogError):
                    CatalogLoader(fixture.root).load()


class AlgorithmAndClassicalSourceLocalityTests(unittest.TestCase):
    """New algorithms and new classical books are data-only extensions.

    A temporary Skill root receives one synthetic classical fulltext plus one
    dependency declaration; the existing audit machinery must discover and
    verify it byte-for-byte without any change to transaction, complete,
    Gateway or generic dispatch code.
    """

    FULLTEXT_LINES = [
        "fixture classical line one",
        "fixture classical line two",
        "甲子循环始于fixture条",
        "fixture classical line four",
    ]

    def _fulltext(self, root: Path) -> Path:
        path = root / "references" / "fulltext" / "fixture" / "fulltext.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(self.FULLTEXT_LINES) + "\n", encoding="utf-8")
        return path

    def _sample_source(self, root: Path) -> Path:
        path = root / "references" / "samples" / "fixture-sample.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("sample line one\n独立样本行 fixture-sample-anchor\n", encoding="utf-8")
        return path

    def _fixture_dependency(
        self,
        root: Path,
        *,
        category: str = "classical_rule_bundle",
        dependency_id: str = "bazi.fixture.classical-locality",
    ) -> dict:
        import hashlib

        fulltext = self._fulltext(root)
        digest = hashlib.sha256(fulltext.read_bytes()).hexdigest()
        return {
            "id": dependency_id,
            "category": category,
            "version": "fixture-locality-v1",
            "status": "verified",
            "convention": {
                "id": "fixture-convention-v1",
                "version": "1.0.0",
                "disputed": False,
                "boundary_rules": ["fixture boundary stays declarative"],
            },
            "primary_sources": [
                {
                    "title": "fixture classical book",
                    "edition_or_recension": "合成 fixture 底本",
                    "normalized_path": "references/fulltext/fixture/fulltext.md",
                    "sha256": digest,
                    "anchor": "L3",
                    "exact_excerpt": "甲子循环始于fixture条",
                    "material": "synthetic fixture row used by the locality test",
                    "license_status": "synthetic fixture; no redistribution",
                }
            ],
            "independent_test_sample": {
                "id": "fixture-sample",
                "source": "fixture classical book",
                "source_path": "references/samples/fixture-sample.md",
                "source_anchor": "fixture-sample-anchor",
                "input": {"fixture": "input"},
                "expected": {"fixture": "expected"},
                "independence": "oracle recomputed inside this test module",
            },
        }

    def _payload(self, root: Path, *, mutate=None) -> dict:
        import yaml

        real = yaml.safe_load(
            (
                ROOT
                / "references"
                / "matrices"
                / "algorithm-source-dependencies.yaml"
            ).read_text(encoding="utf-8")
        )
        providers = {}
        for system in real["providers"]:
            if system == "bazi":
                provider = {
                    "source_audit_status": "source_verified",
                    "dependencies": [self._fixture_dependency(root)],
                }
                if mutate is not None:
                    mutate(provider)
                providers[system] = provider
            else:
                providers[system] = {"source_audit_status": "fixture_stub"}
        return {
            "schema_version": "mingli-algorithm-source-dependencies-v1",
            "providers": providers,
        }

    def test_new_classical_declaration_is_found_and_verified_by_the_audit(
        self,
    ) -> None:
        import tempfile

        import audit_algorithm_sources

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._sample_source(root)
            payload = self._payload(root)
            report = audit_algorithm_sources.audit_matrix(
                payload,
                root=root,
                systems=("bazi",),
                verify_research_sources=True,
                research_root=root,
            )
            bazi_findings = [
                finding
                for finding in report["findings"]
                if "bazi" in finding
            ]
            self.assertEqual(bazi_findings, [], report["findings"])
            self.assertEqual(report["dependency_count"], 1)

    def test_new_algorithm_declaration_is_found_and_verified_by_the_audit(
        self,
    ) -> None:
        import tempfile

        import audit_algorithm_sources

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._sample_source(root)
            payload = self._payload(root)
            payload["providers"]["bazi"]["dependencies"] = [
                self._fixture_dependency(
                    root,
                    category="calendar_formula_and_epoch",
                    dependency_id="bazi.fixture.algorithm-locality",
                )
            ]
            report = audit_algorithm_sources.audit_matrix(
                payload,
                root=root,
                systems=("bazi",),
                verify_research_sources=True,
                research_root=root,
            )
            bazi_findings = [
                finding
                for finding in report["findings"]
                if "bazi" in finding
            ]
            self.assertEqual(bazi_findings, [], report["findings"])
            self.assertEqual(report["dependency_count"], 1)

    def test_corrupted_classical_declaration_is_caught_by_the_audit(self) -> None:
        import tempfile

        import audit_algorithm_sources

        def flip_sha(provider: dict) -> None:
            source = provider["dependencies"][0]["primary_sources"][0]
            source["sha256"] = "0" * 64

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._sample_source(root)
            payload = self._payload(root, mutate=flip_sha)
            report = audit_algorithm_sources.audit_matrix(
                payload,
                root=root,
                systems=("bazi",),
                verify_research_sources=True,
                research_root=root,
            )
            self.assertTrue(
                any(
                    "bazi.fixture.classical-locality" in finding
                    for finding in report["findings"]
                ),
                report["findings"],
            )

    def test_unverified_algorithm_status_is_caught_by_the_audit(self) -> None:
        import tempfile

        import audit_algorithm_sources

        def downgrade(provider: dict) -> None:
            provider["dependencies"][0]["status"] = "pending"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._sample_source(root)
            payload = self._payload(root, mutate=downgrade)
            report = audit_algorithm_sources.audit_matrix(
                payload,
                root=root,
                systems=("bazi",),
                verify_research_sources=True,
                research_root=root,
            )
            self.assertTrue(
                any("status must be verified" in finding for finding in report["findings"]),
                report["findings"],
            )



class FactContractFailClosedTests(unittest.TestCase):
    """validate_payload must stay lawful under every catalog IO corruption.

    The facade's never-raise contract covers mixed-version installs (missing
    or broken fact_contracts package) and hostile catalog trees (non-UTF-8
    bytes, a directory where catalog-v1.json belongs): every failure mode
    must degrade into an explicit finding instead of escaping as a raw
    exception that could empty a reply.
    """

    def _report_shape(self, report: dict) -> None:
        self.assertEqual(set(report), {"ok", "system", "findings", "codes"})
        self.assertFalse(report["ok"])
        self.assertTrue(report["findings"])

    def test_non_utf8_catalog_degrades_into_a_finding(self) -> None:
        fixture = _CatalogDir([_manifest("bazi")])
        self.addCleanup(fixture.cleanup)
        (fixture.root / "catalog-v1.json").write_bytes(
            b"\xff\xfe\x00\x81 not utf-8 \x82"
        )
        report = adapter_validate._validate_payload(
            "bazi", {}, catalog_root=fixture.root
        )
        self.assertIn("fact_contract_load_failed", report["codes"])
        self._report_shape(report)

    def test_catalog_file_that_is_a_directory_degrades_into_a_finding(self) -> None:
        fixture = _CatalogDir([_manifest("bazi")])
        self.addCleanup(fixture.cleanup)
        (fixture.root / "catalog-v1.json").unlink()
        (fixture.root / "catalog-v1.json").mkdir()
        report = adapter_validate._validate_payload(
            "bazi", {}, catalog_root=fixture.root
        )
        self.assertIn("fact_contract_load_failed", report["codes"])
        self._report_shape(report)

    def test_broken_fact_contract_import_degrades_into_a_finding(self) -> None:
        previous = sys.modules.get("fact_contracts.registry", "__absent__")
        sys.modules["fact_contracts.registry"] = None  # forces ImportError

        def restore() -> None:
            if previous == "__absent__":
                sys.modules.pop("fact_contracts.registry", None)
            else:
                sys.modules["fact_contracts.registry"] = previous

        self.addCleanup(restore)
        report = adapter_validate.validate_payload("bazi", {})
        self.assertIn("fact_contract_load_failed", report["codes"])
        self._report_shape(report)


class ClassicalExtensionFullChainLocalityTests(unittest.TestCase):
    """Adding one classical book must be a data-only, pin-guarded extension.

    The independent acceptance rejected the previous locality proof because
    it only covered the first link (one algorithm-source dependency). This
    drill copies the entire release tree into a temporary root, adds one
    synthetic book, and walks the whole classical chain on that copy:

        source pack -> classical bindings -> scope bindings -> generator
        -> evidence index -> runtime matching

    It must prove three things: no Python source is modified at any point,
    the unaudited book can never reach the runtime evidence index (the
    pinned manifest hash rejects it), and runtime matching stays zero-hit
    for it even against facts that satisfy its predicates.
    """

    PACK = "bazi/fixture-locality-classic"
    RULE_ID = f"{PACK}#FXL-01"
    PREDICATE = {
        "path_suffix": "/locality/fixture_probe",
        "operator": "eq",
        "value": "fixture-locality-v1",
    }
    BINDINGS_REL = Path("references/matrices/classical-evidence-bindings-v1.json")
    INDEX_REL = Path("references/index/evidence-rules.jsonl")

    @classmethod
    def setUpClass(cls) -> None:
        import shutil

        # Assign the temporary directory first, then copy: if the copy
        # raises, unittest will NOT call tearDownClass for a failed
        # setUpClass, so this method must release the temporary tree itself.
        cls._tmp = tempfile.TemporaryDirectory()
        try:
            cls.copy_root = Path(cls._tmp.name) / "skill"
            shutil.copytree(
                ROOT,
                cls.copy_root,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
        except Exception:
            cls._tmp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    @staticmethod
    def _sha256(path: Path) -> str:
        import hashlib

        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _script_hashes(self, root: Path) -> dict[str, str]:
        return {
            str(path.relative_to(root)): self._sha256(path)
            for path in sorted(root.rglob("*.py"))
            if "__pycache__" not in path.parts
        }

    def _add_fixture_book(self, root: Path) -> None:
        import yaml

        pack_dir = root / "references" / "books" / "bazi" / "fixture-locality-classic"
        pack_dir.mkdir(parents=True, exist_ok=True)
        index = pack_dir / "index.md"
        index.write_text(
            "# Synthetic Locality Classic\n\n"
            "Synthetic pack proving classical extension is data-only.\n",
            encoding="utf-8",
        )
        rules = pack_dir / "rules.md"
        rules.write_text(
            "# Synthetic Locality Classic rules\n"
            "\n"
            "## FXL-01 fixture locality rule for the extension drill\n"
            "\n"
            "- exact_quote: synthetic classical quote proving data-only extension\n",
            encoding="utf-8",
        )

        catalog_path = root / "references" / "catalog" / "catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["ready_reference_packs"].append(
            {
                "system": "bazi",
                "slug": "fixture-locality-classic",
                "title": "合成 locality 古籍",
                "d2_status": "ready",
                "source_layer": "primary_or_commentary_see_pack_index",
                "source_anchor_url": "synthetic-fixture-not-a-real-source",
                "source_risk": "synthetic fixture; no redistribution",
                "skill_index_path": "references/books/bazi/fixture-locality-classic/index.md",
                "skill_index_sha256": self._sha256(index),
                "local_fulltext_path": None,
                "local_fulltext_sha256": None,
                "local_fulltext_policy": "local_only_not_distributed",
                "local_fulltext_required_for_runtime": False,
                "redistribution_status": "distilled_pack_only_source_licence_review_pending",
                "source_provenance_status": "synthetic_locality_drill",
                "source_manifest_path": None,
                "load_policy": "load index.md first",
            }
        )
        catalog["ready_count"] = len(catalog["ready_reference_packs"])
        catalog_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )

        scope_path = root / "references" / "matrices" / "evidence-scope-bindings-v1.yaml"
        scope = yaml.safe_load(scope_path.read_text(encoding="utf-8"))
        scope["bindings"][self.RULE_ID] = {
            "route": "bazi",
            "rationale": (
                "synthetic drill binding proving scope bindings accept a new"
                " pack declaratively"
            ),
            "evidence_role": "issue_specific_judgment_rule",
            "predicates": [dict(self.PREDICATE)],
        }
        scope_path.write_text(
            yaml.safe_dump(scope, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _run_script(self, root: Path, script: str, *args: str):
        import os
        import subprocess

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(root / "scripts" / script), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=600,
        )

    def test_adding_a_classical_book_is_data_only_and_zero_hit_persists(self) -> None:
        import build_evidence_index
        from reading_engine.contracts import FactRef
        from reading_engine.evidence_rules import EvidenceRule, match_rule

        production_bindings_sha_before = self._sha256(ROOT / self.BINDINGS_REL)
        production_index_sha_before = self._sha256(ROOT / self.INDEX_REL)
        production_bindings = json.loads(
            (ROOT / self.BINDINGS_REL).read_text(encoding="utf-8")
        )
        script_hashes_before = self._script_hashes(self.copy_root)

        self._add_fixture_book(self.copy_root)

        # Link 1+2+4: source pack -> generator -> classical bindings. The
        # generator runs inside the temporary tree, so only the temporary
        # matrix is rewritten; the production matrix is never touched.
        completed = self._run_script(
            self.copy_root, "generate_classical_evidence_bindings.py"
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        stats = json.loads(completed.stdout.strip().splitlines()[-1])
        self.assertEqual(
            stats["records"], len(production_bindings["bindings"]) + 1
        )
        copy_bindings = json.loads(
            (self.copy_root / self.BINDINGS_REL).read_text(encoding="utf-8")
        )
        self.assertEqual(copy_bindings["policy"], production_bindings["policy"])
        fixture_binding = copy_bindings["bindings"].get(self.RULE_ID)
        self.assertIsNotNone(
            fixture_binding,
            "the generator must discover the new book without code changes",
        )
        self.assertEqual(fixture_binding["verification_status"], "inactive_unverified")
        self.assertEqual(fixture_binding["classical_sources"], [])
        for rule_id, binding in production_bindings["bindings"].items():
            self.assertEqual(
                copy_bindings["bindings"].get(rule_id),
                binding,
                f"existing binding drifted while adding a book: {rule_id}",
            )

        # Link 3: scope bindings reach the compiled record declaratively.
        records = build_evidence_index.compile_evidence_rules(
            root=self.copy_root,
            enforce_classical_bindings=False,
        )
        fixture_record = next(
            record for record in records if record["rule_id"] == self.RULE_ID
        )
        self.assertEqual(
            fixture_record["required_fact_predicates"], [dict(self.PREDICATE)]
        )
        self.assertEqual(
            fixture_record["evidence_role"], "issue_specific_judgment_rule"
        )
        self.assertEqual(
            fixture_record["quote"],
            "synthetic classical quote proving data-only extension",
        )

        # Link 5 fail-closed: the evidence index build must refuse the
        # unaudited book because the pinned manifest hash no longer matches.
        # This is what keeps runtime hits at zero for anything new.
        blocked = self._run_script(
            self.copy_root,
            "build_evidence_index.py",
            "--output",
            str(self.copy_root / "references" / "index" / "fixture-drill.jsonl"),
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn(
            "classical evidence binding manifest hash mismatch",
            blocked.stderr,
        )
        self.assertFalse(
            (self.copy_root / "references" / "index" / "fixture-drill.jsonl").exists()
        )

        # Runtime semantics: even if the record were shaped for the index,
        # an inactive classical binding can never match, so a fact that
        # satisfies the predicate still produces zero hits.
        runtime_payload = dict(fixture_record)
        runtime_payload.update(
            {
                "runtime_active": False,
                "classical_binding_status": fixture_binding["verification_status"],
                "applicability_signature": fixture_binding["applicability_signature"],
                "rule_record_digest": fixture_binding["rule_record_digest"],
                "classical_binding_digest": fixture_binding["binding_digest"],
                "classical_sources": [],
            }
        )
        rule = EvidenceRule.from_dict(runtime_payload)
        satisfying_fact = FactRef(
            fact_id="f" * 64,
            path=f"/test{self.PREDICATE['path_suffix']}",
            value=self.PREDICATE["value"],
            provider_id="test",
            provider_version="1",
            reading_id="r" * 32,
            version=1,
        )
        self.assertEqual(match_rule(rule, (satisfying_fact,)), (False, (), ()))

        # Locality proof: the whole drill changed declarative data only; not a
        # single Python source in the tree was touched, and the production
        # matrices stayed byte-identical.
        self.assertEqual(self._script_hashes(self.copy_root), script_hashes_before)
        self.assertEqual(
            self._sha256(ROOT / self.BINDINGS_REL), production_bindings_sha_before
        )
        self.assertEqual(
            self._sha256(ROOT / self.INDEX_REL), production_index_sha_before
        )


if __name__ == "__main__":
    unittest.main()
