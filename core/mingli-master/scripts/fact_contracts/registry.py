"""Discovery of Provider-owned fact contracts through the runtime catalog.

The registry reuses the existing Provider catalog mechanism: a manifest may
declare one optional ``fact_contract`` entrypoint (``module:Class``), exactly
analogous to the Provider ``entrypoint`` key. Nothing else changes in the
manifest schema - no routing keywords, no new user-visible capability ids.

Security model (mirrors ``reading_engine.provider_registry``):

- only modules whose resolved file lives below the Skill root are trusted;
- relative/escaped module names, stdlib entrypoints and arbitrary dynamic
  imports are rejected;
- every failure raises :class:`FactContractError`; the facade converts it
  into an explicit error finding so a reply can never go empty.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import sys
from pathlib import Path
from typing import Any

from reading_engine.catalog import CatalogError, CatalogLoader


class FactContractError(RuntimeError):
    """A fact contract declaration exists but cannot be trusted or loaded."""


#: Successful catalog parses are shared process-wide: the catalog is a
#: read-only declaration, and validate_payload must not re-read all
#: provider manifests on every call. Failures are never cached.
_CATALOG_CACHE: dict[str, Any] = {}

_REQUIRED_HOOKS = (
    "required_output_ids",
    "required_calendar_keys",
    "validate_output",
)

#: CPython's FileFinder prefers extension modules over ``.py`` sources, and
#: accepts sourceless bytecode, so any same-named file with one of these
#: suffixes can shadow an audited source file. Fact contracts must always be
#: plain source; every candidate carrying such a suffix fails closed.
_FORBIDDEN_MODULE_SUFFIXES = tuple(
    importlib.machinery.EXTENSION_SUFFIXES
) + (".pyc",)


class FactContractRegistry:
    """Resolve the optional fact contract declared by a Provider manifest."""

    def __init__(self, catalog_root: Path, *, skill_root: Path) -> None:
        self.catalog_root = Path(catalog_root)
        self.skill_root = Path(skill_root).resolve()
        self._cache: dict[str, Any] = {}

    def resolve(self, system: str) -> Any | None:
        """Return the instantiated contract for *system*, or None.

        None means the system's manifest exists without a ``fact_contract``
        declaration (or has no descriptor at all): the caller keeps using the
        legacy validation path. Any declared-but-broken contract raises
        :class:`FactContractError` (fail closed).
        """

        if system in self._cache:
            return self._cache[system]
        descriptor = self._descriptor(system)
        if descriptor is None:
            self._cache[system] = None
            return None
        entrypoint = descriptor.canonical_payload.get("fact_contract")
        if entrypoint is None:
            self._cache[system] = None
            return None
        contract = self._instantiate(system, str(entrypoint))
        self._cache[system] = contract
        return contract

    def is_declared(self, system: str) -> bool:
        """True when the catalog declares a descriptor for *system*.

        Lets the facade distinguish a genuinely unknown system from a known
        Provider whose fact contract is absent, so a severed contract can be
        reported as an unavailable capability instead of an unknown system.
        A broken catalog raises :class:`FactContractError` exactly like
        :meth:`resolve` (fail closed).
        """

        return self._descriptor(system) is not None

    def _descriptor(self, system: str) -> Any | None:
        key = str(self.catalog_root.resolve())
        catalog = _CATALOG_CACHE.get(key)
        if catalog is None:
            try:
                catalog = CatalogLoader(self.catalog_root).load()
            except CatalogError as error:
                raise FactContractError(
                    f"fact contract catalog is unusable: {error}"
                ) from error
            _CATALOG_CACHE[key] = catalog
        for candidate in catalog.descriptors:
            if candidate.id == system:
                return candidate
        return None

    def _instantiate(self, system: str, entrypoint: str) -> Any:
        module_name, separator, class_name = entrypoint.partition(":")
        if (
            not separator
            or not module_name
            or not class_name
            or module_name.startswith(".")
            or "/" in module_name
            or "\\" in module_name
        ):
            raise FactContractError(
                f"{system}: fact_contract entrypoint must be 'module:Class':"
                f" {entrypoint!r}"
            )
        # Trust check happens strictly before execution. The top-level name
        # is located with PathFinder.find_spec (a pure path scan that runs
        # no code); every dotted remainder is resolved as a plain filesystem
        # walk beneath the owning package's directories. import_module only
        # runs after the FULL module chain is proven to live below the Skill
        # root, so a hostile parent package's __init__.py can never execute
        # before its rejection.
        expected_origins = self._verify_trusted_module(system, module_name)
        try:
            module = importlib.import_module(module_name)
        except Exception as error:
            # Any import-time failure of a trusted module -- SyntaxError,
            # a broken dependency chain, whatever short of BaseException --
            # must degrade into the structured contract error, matching the
            # module's documented never-leak contract.
            raise FactContractError(
                f"{system}: fact_contract module cannot be imported: {error}"
            ) from error
        # Post-import verification: ``import_module`` may return a cached
        # ``sys.modules`` entry without consulting the filesystem, so the
        # walk alone cannot prove what actually got loaded. ``__spec__.origin``
        # is attacker-influenceable too, so merely resolving below the Skill
        # root is insufficient: every prefix of the imported chain must equal,
        # character for character after resolve(), the exact source file the
        # trust walk computed for it.
        parts = module_name.split(".")
        for index in range(1, len(parts) + 1):
            prefix = ".".join(parts[:index])
            loaded = sys.modules.get(prefix)
            origin = getattr(
                getattr(loaded, "__spec__", None), "origin", None
            )
            if loaded is None or not origin:
                raise FactContractError(
                    f"{system}: fact_contract module cannot be verified"
                    f" after import: {prefix!r}"
                )
            if Path(origin).resolve() != expected_origins[prefix]:
                raise FactContractError(
                    f"{system}: fact_contract module does not match the"
                    f" trusted walk after import: {prefix!r}"
                )
        contract_class = getattr(module, class_name, None)
        if not isinstance(contract_class, type):
            raise FactContractError(
                f"{system}: fact_contract class not found: {entrypoint!r}"
            )
        try:
            contract = contract_class()
        except Exception as error:  # noqa: BLE001 - normalize every failure
            raise FactContractError(
                f"{system}: fact_contract must be constructible without"
                f" arguments: {error}"
            ) from error
        contract_id = getattr(contract, "contract_id", None)
        if not isinstance(contract_id, str) or not contract_id.strip():
            raise FactContractError(
                f"{system}: fact_contract must declare a non-empty"
                " contract_id"
            )
        for hook in _REQUIRED_HOOKS:
            if not callable(getattr(contract, hook, None)):
                raise FactContractError(
                    f"{system}: fact_contract is missing hook {hook!r}"
                )
        if not isinstance(
            getattr(contract, "replaces_legacy_validation", False), bool
        ):
            raise FactContractError(
                f"{system}: fact_contract replaces_legacy_validation must be"
                " a boolean"
            )
        return contract

    def _verify_trusted_module(
        self, system: str, module_name: str
    ) -> dict[str, Path]:
        """Assert *module_name* resolves entirely inside the Skill root.

        The walk never imports anything: the top-level component is located
        with ``PathFinder.find_spec`` (no code executes) and every further
        component is a filesystem lookup beneath the owning package's
        directories. Unresolvable names, namespace packages, non-package
        intermediates and anything outside the root all fail closed.

        Returns the resolved source file computed for every prefix of the
        module chain, so the caller can pin each loaded module's
        ``__spec__.origin`` to these exact paths after ``import_module``.
        """

        parts = module_name.split(".")
        expected_origins: dict[str, Path] = {}
        try:
            spec = importlib.machinery.PathFinder.find_spec(parts[0])
        except (ImportError, ValueError, AttributeError) as error:
            raise FactContractError(
                f"{system}: fact_contract module cannot be resolved: {error}"
            ) from error
        if spec is None or not spec.origin:
            raise FactContractError(
                f"{system}: fact_contract module cannot be resolved:"
                f" {module_name!r}"
            )
        resolved = Path(spec.origin).resolve()
        if resolved.suffix in _FORBIDDEN_MODULE_SUFFIXES:
            raise FactContractError(
                f"{system}: fact_contract module must be plain source:"
                f" {module_name!r}"
            )
        if not resolved.is_relative_to(self.skill_root):
            raise FactContractError(
                f"{system}: fact_contract module escapes the Skill root:"
                f" {module_name!r}"
            )
        expected_origins[parts[0]] = resolved
        if len(parts) == 1:
            return expected_origins
        if spec.submodule_search_locations is None:
            raise FactContractError(
                f"{system}: fact_contract module cannot be resolved:"
                f" {module_name!r}"
            )
        search_dirs = [
            Path(directory).resolve()
            for directory in spec.submodule_search_locations
        ]
        if any(
            not directory.is_relative_to(self.skill_root)
            for directory in search_dirs
        ):
            raise FactContractError(
                f"{system}: fact_contract module escapes the Skill root:"
                f" {module_name!r}"
            )
        last_index = len(parts) - 1
        module_file = resolved
        for index, part in enumerate(parts[1:], start=1):
            for directory in search_dirs:
                self._assert_no_shadow_files(
                    system, module_name, directory, part
                )
            found: tuple[Path, Path | None] | None = None
            for directory in search_dirs:
                package_init = directory / part / "__init__.py"
                candidate_module = directory / f"{part}.py"
                if package_init.is_file():
                    found = (package_init, directory / part)
                    break
                if candidate_module.is_file():
                    found = (candidate_module, None)
                    break
            if found is None:
                raise FactContractError(
                    f"{system}: fact_contract module cannot be resolved:"
                    f" {module_name!r}"
                )
            module_file, package_dir = found
            expected_origins[".".join(parts[: index + 1])] = (
                module_file.resolve()
            )
            if index < last_index:
                if package_dir is None:
                    raise FactContractError(
                        f"{system}: fact_contract module cannot be resolved:"
                        f" {module_name!r}"
                    )
                search_dirs = [package_dir]
        resolved = module_file.resolve()
        if not resolved.is_relative_to(self.skill_root):
            raise FactContractError(
                f"{system}: fact_contract module escapes the Skill root:"
                f" {module_name!r}"
            )
        return expected_origins

    def _assert_no_shadow_files(
        self,
        system: str,
        module_name: str,
        directory: Path,
        part: str,
    ) -> None:
        """Fail closed when *part* could be shadowed in *directory*.

        A same-named extension module or sourceless bytecode file would take
        precedence over the audited ``.py`` source during import, so its mere
        presence is a rejection - even inside the Skill root. Bytecode
        caches in ``__pycache__`` are only lawful while their source file
        exists next to them.
        """

        for suffix in importlib.machinery.EXTENSION_SUFFIXES:
            if (directory / f"{part}{suffix}").exists():
                raise FactContractError(
                    f"{system}: fact_contract module {module_name!r} has a"
                    f" shadow extension file: {part}{suffix}"
                )
        if (directory / f"{part}.pyc").exists():
            raise FactContractError(
                f"{system}: fact_contract module {module_name!r} has a"
                f" shadow bytecode file: {part}.pyc"
            )
        pycache = directory / "__pycache__"
        if pycache.is_dir():
            source_exists = (directory / f"{part}.py").is_file() or (
                directory / part / "__init__.py"
            ).is_file()
            if not source_exists:
                for entry in pycache.iterdir():
                    if (
                        entry.name.split(".")[0] == part
                        and entry.name.endswith(".pyc")
                    ):
                        raise FactContractError(
                            f"{system}: fact_contract module {module_name!r}"
                            f" has orphan bytecode in __pycache__:"
                            f" {entry.name}"
                        )
