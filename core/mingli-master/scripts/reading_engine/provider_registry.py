"""Instantiate provider adapters from catalog entrypoints, never by name.

The registry loads only entrypoints declared in the bundled manifests and
whose module files live strictly below the skill root. Construction keyword
arguments are matched against each adapter's signature so no generic code
ever names a concrete provider.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
from typing import Any, Mapping

from .catalog import ProviderDescriptor, RuntimeCatalog
from .provider_protocol import ProviderAdapter


class RegistryError(ValueError):
    """Raised when an entrypoint is missing, untrusted or not constructible."""


class ProviderRegistry:
    def __init__(
        self,
        catalog: RuntimeCatalog,
        *,
        skill_root: Path,
        construction: Mapping[str, Any] | None = None,
    ) -> None:
        self.catalog = catalog
        self.skill_root = Path(skill_root).resolve()
        self.construction = dict(construction or {})

    def descriptor(self, provider_id: str) -> ProviderDescriptor:
        return self.catalog.descriptor(provider_id)

    def instantiate(self, descriptor: ProviderDescriptor) -> Any:
        module_name, separator, class_name = descriptor.entrypoint.partition(":")
        if not separator or not module_name or not class_name:
            raise RegistryError(
                f"{descriptor.id}: entrypoint must look like module:Class"
            )
        try:
            module = importlib.import_module(module_name)
        except ImportError as error:
            raise RegistryError(
                f"{descriptor.id}: cannot import entrypoint module"
            ) from error
        self._require_module_below_root(descriptor.id, module)
        adapter_class = getattr(module, class_name, None)
        if adapter_class is None or not inspect.isclass(adapter_class):
            raise RegistryError(
                f"{descriptor.id}: entrypoint class not found: {class_name}"
            )
        keyword_arguments = self._supported_arguments(adapter_class)
        try:
            instance = adapter_class(**keyword_arguments)
        except Exception as error:
            raise RegistryError(
                f"{descriptor.id}: adapter construction failed"
            ) from error
        bind = getattr(instance, "bind_descriptor", None)
        if callable(bind):
            bind(descriptor)
        else:
            instance._descriptor = descriptor
        if not isinstance(instance, ProviderAdapter):
            raise RegistryError(
                f"{descriptor.id}: adapter does not satisfy the provider"
                " protocol (descriptor + prepare)"
            )
        capability = getattr(instance, "capability", None)
        declared_system = getattr(capability, "system", None)
        if declared_system != descriptor.id:
            raise RegistryError(
                f"{descriptor.id}: adapter capability declares system"
                f" {declared_system!r} instead of the manifest id"
            )
        return instance

    def adapters(self) -> dict[str, Any]:
        return {
            descriptor.id: self.instantiate(descriptor)
            for descriptor in self.catalog.descriptors
        }

    def _require_module_below_root(self, provider_id: str, module: Any) -> None:
        module_file = getattr(module, "__file__", None)
        if not module_file:
            raise RegistryError(
                f"{provider_id}: entrypoint module has no source location"
            )
        resolved = Path(module_file).resolve()
        if not resolved.is_relative_to(self.skill_root):
            raise RegistryError(
                f"{provider_id}: entrypoint module escapes the skill root"
            )

    def _supported_arguments(self, adapter_class: type) -> dict[str, Any]:
        signature = inspect.signature(adapter_class.__init__)
        parameters = signature.parameters
        accepts_any = any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )
        return {
            name: value
            for name, value in self.construction.items()
            if accepts_any or name in parameters
        }


__all__ = ["ProviderRegistry", "RegistryError"]
