"""Read-only provider vocabulary catalog loaded from versioned manifests.

The loader validates structure and references only. It never parses user
natural language, never stores trigger words, and never names any concrete
provider: every domain word it handles is opaque data from a manifest file.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

CATALOG_SCHEMA_VERSION = "catalog-v1"
PROVIDER_SCHEMA_VERSION = "provider-manifest-v1"
CATALOG_FILE_NAME = "catalog-v1.json"

# Manifest keys that would smuggle natural-language routing into data.
FORBIDDEN_ROUTING_KEYS = frozenset({"keywords", "aliases", "synonyms", "regex"})


class CatalogError(ValueError):
    """Raised when the catalog or a provider manifest is invalid."""


@dataclass(frozen=True)
class ProviderCapability:
    object_ids: tuple[str, ...]
    horizon_ids: tuple[str, ...]
    dimension_ids: tuple[str, ...]
    default_dimension_ids: tuple[str, ...] | None
    required_input_groups: tuple[tuple[str, ...], ...]
    exact_horizon_ids: tuple[str, ...]
    independent_lineage_id: str
    # Legacy metadata fields kept for schema compatibility with older
    # manifests.  They MUST NOT influence structural selection: the
    # catalog surfaces ambiguities to the host model rather than
    # picking the "cheapest" or "highest priority" candidate.  Treat
    # them as deprecated audit-only data; the closure audit rejects
    # any code path that branches on them.
    assumption_cost: int
    default_priority: int

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProviderCapability":
        defaults = payload.get("default_dimension_ids")
        return cls(
            object_ids=_id_tuple(payload, "object_ids"),
            horizon_ids=_id_tuple(payload, "horizon_ids"),
            dimension_ids=_id_tuple(payload, "dimension_ids"),
            default_dimension_ids=(
                None if defaults is None else _string_tuple(defaults)
            ),
            required_input_groups=tuple(
                _string_tuple(_require(group, "any_of"))
                for group in payload.get("required_input_groups", [])
            ),
            exact_horizon_ids=_string_tuple(
                payload.get("exact_horizon_ids", [])
            ),
            independent_lineage_id=str(_require(payload, "independent_lineage_id")),
            assumption_cost=int(payload.get("assumption_cost", 0)),
            default_priority=int(payload.get("default_priority", 0)),
        )


@dataclass(frozen=True)
class InputFieldSpec:
    id: str
    type_id: str
    display: Mapping[str, str]
    description: Mapping[str, str]
    choices: tuple["InputChoiceSpec", ...] = ()


@dataclass(frozen=True)
class InputChoiceSpec:
    id: str
    display: Mapping[str, str]
    description: Mapping[str, str]


@dataclass(frozen=True)
class ProviderDescriptor:
    id: str
    entrypoint: str
    display: Mapping[str, Mapping[str, str]]
    capability: ProviderCapability
    input_fields: tuple[InputFieldSpec, ...]
    evidence_profile_id: str
    canonical_payload: Mapping[str, Any]

    def input_field_ids(self) -> frozenset[str]:
        return frozenset(field.id for field in self.input_fields)

    @property
    def claim_policy(self) -> Mapping[str, Any]:
        policy = self.canonical_payload.get("claim_policy")
        if not isinstance(policy, Mapping):
            raise CatalogError(
                f"provider manifest {self.id!r} must declare claim_policy"
            )
        allowed = policy.get("allowed_kind_ids")
        ceiling = policy.get("certainty_ceiling_id")
        if (
            not isinstance(allowed, (list, tuple))
            or not allowed
            or not all(isinstance(item, str) and item for item in allowed)
            or not isinstance(ceiling, str)
            or not ceiling
        ):
            raise CatalogError(
                f"provider manifest {self.id!r} has an invalid claim_policy"
            )
        return policy


@dataclass(frozen=True)
class Selection:
    kind: str  # selected | ambiguous | unsupported | need_focus
    descriptor: ProviderDescriptor | None = None
    effective_dimension_ids: tuple[str, ...] = ()
    candidates: tuple[ProviderDescriptor, ...] = ()


@dataclass(frozen=True)
class RuntimeCatalog:
    manifest_digest: str
    descriptors: tuple[ProviderDescriptor, ...]

    def descriptor(self, provider_id: str) -> ProviderDescriptor:
        for descriptor in self.descriptors:
            if descriptor.id == provider_id:
                return descriptor
        raise CatalogError(f"unknown capability id: {provider_id!r}")

    def has_descriptor(self, provider_id: str) -> bool:
        return any(item.id == provider_id for item in self.descriptors)

    def select(
        self,
        *,
        object_id: str,
        horizon_kind_id: str,
        dimension_ids: tuple[str, ...],
        capability_id: str | None = None,
    ) -> Selection:
        if capability_id is not None:
            if not self.has_descriptor(capability_id):
                return Selection(kind="unsupported")
            descriptor = self.descriptor(capability_id)
            effective = self._effective_dimensions(descriptor, dimension_ids)
            if (
                not self._matches(descriptor, object_id, horizon_kind_id)
                or effective is None
            ):
                return Selection(kind="unsupported")
            if not effective:
                return Selection(kind="need_focus", descriptor=descriptor)
            return Selection(
                kind="selected",
                descriptor=descriptor,
                effective_dimension_ids=effective,
            )

        candidates: list[tuple[ProviderDescriptor, tuple[str, ...]]] = []
        broad_only_candidates: list[ProviderDescriptor] = []
        for descriptor in self.descriptors:
            if not self._matches(descriptor, object_id, horizon_kind_id):
                continue
            effective = self._effective_dimensions(descriptor, dimension_ids)
            if effective is None:
                continue
            if not effective:
                broad_only_candidates.append(descriptor)
                continue
            candidates.append((descriptor, effective))

        if not candidates:
            if broad_only_candidates:
                return Selection(
                    kind="need_focus",
                    candidates=tuple(broad_only_candidates),
                )
            return Selection(kind="unsupported")

        # The semantic capability is the host model's job, not the core's.
        # Any non-singleton structural set is ambiguous and must be surfaced
        # to the model; the core never picks the "cheapest" or "highest
        # priority" candidate as a proxy for what fits the user.
        if len(candidates) > 1:
            return Selection(
                kind="ambiguous",
                candidates=tuple(descriptor for descriptor, _ in candidates),
            )
        descriptor, effective = candidates[0]
        return Selection(
            kind="selected",
            descriptor=descriptor,
            effective_dimension_ids=effective,
        )

    @staticmethod
    def missing_input_groups(
        descriptor: ProviderDescriptor,
        provided_field_ids: frozenset[str],
    ) -> tuple[tuple[str, ...], ...]:
        """Return only the truly blocking any-of groups with no provided member."""
        return tuple(
            group
            for group in descriptor.capability.required_input_groups
            if not (set(group) & provided_field_ids)
        )

    @staticmethod
    def _matches(
        descriptor: ProviderDescriptor,
        object_id: str,
        horizon_kind_id: str,
    ) -> bool:
        capability = descriptor.capability
        return (
            object_id in capability.object_ids
            and horizon_kind_id in capability.horizon_ids
        )

    @staticmethod
    def _effective_dimensions(
        descriptor: ProviderDescriptor,
        dimension_ids: tuple[str, ...],
    ) -> tuple[str, ...] | None:
        """Explicit dimensions must be supported; empty means declared defaults.

        Returns None when explicit dimensions are unsupported, and () when a
        broad request has no declared default scope (one focused clarification).
        """
        capability = descriptor.capability
        if dimension_ids:
            if all(item in capability.dimension_ids for item in dimension_ids):
                return tuple(dimension_ids)
            return None
        if capability.default_dimension_ids:
            return capability.default_dimension_ids
        return ()


class CatalogLoader:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def load(self) -> RuntimeCatalog:
        catalog_payload = _read_json(self.root / CATALOG_FILE_NAME)
        if catalog_payload.get("schema_version") != CATALOG_SCHEMA_VERSION:
            raise CatalogError("unsupported catalog schema_version")
        provider_entries = catalog_payload.get("providers")
        if not isinstance(provider_entries, list):
            raise CatalogError("catalog providers must be a list of paths")

        descriptors: list[ProviderDescriptor] = []
        seen_ids: set[str] = set()
        for entry in provider_entries:
            manifest_path = self._resolve_below_root(str(entry))
            payload = _read_json(manifest_path)
            descriptor = self._parse_provider(payload)
            if descriptor.id in seen_ids:
                raise CatalogError(f"duplicate capability id: {descriptor.id!r}")
            seen_ids.add(descriptor.id)
            descriptors.append(descriptor)

        descriptors.sort(key=lambda item: item.id)
        digest = _manifest_digest(descriptors)
        return RuntimeCatalog(
            manifest_digest=digest,
            descriptors=tuple(descriptors),
        )

    def _resolve_below_root(self, entry: str) -> Path:
        candidate = (self.root / entry).resolve()
        if not candidate.is_relative_to(self.root):
            raise CatalogError(f"manifest path escapes catalog root: {entry!r}")
        return candidate

    def _parse_provider(self, payload: Mapping[str, Any]) -> ProviderDescriptor:
        if payload.get("schema_version") != PROVIDER_SCHEMA_VERSION:
            raise CatalogError("unsupported provider manifest schema_version")
        _reject_routing_keys(payload)

        provider_id = str(_require(payload, "id"))
        entrypoint = str(_require(payload, "entrypoint"))
        display = _require(payload, "display")
        if not isinstance(display, Mapping) or not display:
            raise CatalogError(f"{provider_id}: display must be a locale mapping")

        capability = ProviderCapability.from_dict(
            _mapping(_require(payload, "capability"), "capability")
        )
        input_fields = self._parse_input_fields(payload, provider_id)
        field_ids = frozenset(field.id for field in input_fields)

        if capability.default_dimension_ids is not None:
            defaults = capability.default_dimension_ids
            if not defaults:
                raise CatalogError(
                    f"{provider_id}: declared default_dimension_ids must be non-empty"
                )
            if not set(defaults) <= set(capability.dimension_ids):
                raise CatalogError(
                    f"{provider_id}: default_dimension_ids must be a subset of"
                    " dimension_ids"
                )
        for group in capability.required_input_groups:
            if not group:
                raise CatalogError(
                    f"{provider_id}: required input group must not be empty"
                )
            unknown = set(group) - field_ids
            if unknown:
                raise CatalogError(
                    f"{provider_id}: required group references unknown fields:"
                    f" {sorted(unknown)}"
                )

        return ProviderDescriptor(
            id=provider_id,
            entrypoint=entrypoint,
            display=display,
            capability=capability,
            input_fields=input_fields,
            evidence_profile_id=str(_require(payload, "evidence_profile_id")),
            canonical_payload=payload,
        )

    @staticmethod
    def _parse_input_fields(
        payload: Mapping[str, Any], provider_id: str
    ) -> tuple[InputFieldSpec, ...]:
        raw = payload.get("input_fields", {})
        if not isinstance(raw, Mapping):
            raise CatalogError(f"{provider_id}: input_fields must be a mapping")
        fields = []
        for field_id, spec in sorted(raw.items()):
            spec = _mapping(spec, f"input_fields[{field_id}]")
            _reject_routing_keys(spec)
            raw_choices = spec.get("choices", [])
            if not isinstance(raw_choices, list):
                raise CatalogError(
                    f"{provider_id}: input choices must be a list"
                )
            choices: list[InputChoiceSpec] = []
            seen_choice_ids: set[str] = set()
            for raw_choice in raw_choices:
                choice = _mapping(raw_choice, "input field choice")
                _reject_routing_keys(choice)
                choice_id = str(_require(choice, "id"))
                if not choice_id or choice_id in seen_choice_ids:
                    raise CatalogError(
                        f"{provider_id}: input choice ids must be unique"
                    )
                seen_choice_ids.add(choice_id)
                choices.append(
                    InputChoiceSpec(
                        id=choice_id,
                        display=_mapping(choice.get("display", {}), "display"),
                        description=_mapping(
                            choice.get("description", {}), "description"
                        ),
                    )
                )
            fields.append(
                InputFieldSpec(
                    id=str(field_id),
                    type_id=str(_require(spec, "type")),
                    display=_mapping(spec.get("display", {}), "display"),
                    description=_mapping(
                        spec.get("description", {}), "description"
                    ),
                    choices=tuple(choices),
                )
            )
        return tuple(fields)


def _manifest_digest(descriptors: list[ProviderDescriptor]) -> str:
    canonical = json.dumps(
        [descriptor.canonical_payload for descriptor in descriptors],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _reject_routing_keys(payload: Mapping[str, Any]) -> None:
    found = FORBIDDEN_ROUTING_KEYS & set(payload)
    if found:
        raise CatalogError(
            f"natural-language routing fields are forbidden: {sorted(found)}"
        )
    for value in payload.values():
        if isinstance(value, Mapping):
            _reject_routing_keys(value)


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CatalogError(f"missing catalog file: {path.name}") from error
    except json.JSONDecodeError as error:
        raise CatalogError(f"invalid JSON in {path.name}: {error}") from error
    except (OSError, UnicodeDecodeError) as error:
        # Non-UTF-8 bytes, a directory where a file belongs, or any other
        # IO failure must stay inside the CatalogError contract so every
        # caller can degrade into an explicit finding.
        raise CatalogError(f"unreadable catalog file {path.name}: {error}") from error
    return _mapping(payload, path.name)


def _require(payload: Mapping[str, Any], key: str) -> Any:
    if key not in payload:
        raise CatalogError(f"missing required field: {key!r}")
    return payload[key]


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CatalogError(f"{label} must be a JSON object")
    return value


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise CatalogError("expected a list of strings")
    return tuple(value)


def _id_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    return _string_tuple(_require(payload, key))
