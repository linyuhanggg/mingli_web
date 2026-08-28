"""Shared vocabulary for Provider-owned fact contracts.

The facade (``adapter_validate.validate_payload``) keeps the generic
envelope and finding assembly; a contract only contributes:

- the required output ids for its fact shape (possibly trimmed from the
  generic table, e.g. a static-scope payload drops ``luck_cycles``);
- the required calendar normalization keys;
- structured findings for its own output block.

Contracts must stay independent from the generator: they may recompute
deterministic facts with their own oracle implementation, but they must not
import the generating adapter's calculation functions ("self-proving"
validation is forbidden).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


class CanonicalFactsError(ValueError):
    """An art-specific fact snapshot is not safe or provenance-complete."""


CanonicalObjectFieldRules = tuple[
    tuple[tuple[str, ...], frozenset[str]],
    ...,
]


def canonical_object_fields(
    *rules: tuple[str, str],
) -> CanonicalObjectFieldRules:
    """Build auditable path-specific positive object-field rules.

    Paths are slash separated and use ``*`` for one list item.  Field names
    are whitespace separated because Runtime JSON keys cannot contain
    whitespace.  Keeping this representation compact lets each art own its
    full recursive object vocabulary without depending on a fixture or raw
    engine response at runtime.
    """

    result: list[tuple[tuple[str, ...], frozenset[str]]] = []
    seen: set[tuple[str, ...]] = set()
    for path_text, fields_text in rules:
        path = tuple(part for part in path_text.split("/") if part)
        if not path or path in seen:
            raise ValueError(f"duplicate or empty canonical object path: {path_text!r}")
        seen.add(path)
        result.append((path, frozenset(fields_text.split())))
    return tuple(result)


@dataclass(frozen=True)
class CanonicalFactsFieldClosure:
    """Positive field closure for one art-specific fact boundary.

    Root and ``output`` keep their required-field checks.  Every deeper JSON
    object must also match one art-owned path rule, and may contain only that
    rule's positive field set.  This closes arrays and nested objects without
    relying on guessed raw-field aliases.
    """

    root_fields: frozenset[str]
    output_fields: frozenset[str]
    optional_root_fields: frozenset[str] = frozenset()
    optional_output_fields: frozenset[str] = frozenset()
    nested_object_fields: CanonicalObjectFieldRules = ()

    @staticmethod
    def _path_matches(
        pattern: tuple[str, ...],
        path: tuple[str, ...],
    ) -> bool:
        return len(pattern) == len(path) and all(
            expected == "*" or expected == actual
            for expected, actual in zip(pattern, path)
        )

    def _allowed_nested_fields(
        self,
        path: tuple[str, ...],
    ) -> frozenset[str] | None:
        matches = [
            (sum(part != "*" for part in pattern), fields)
            for pattern, fields in self.nested_object_fields
            if self._path_matches(pattern, path)
        ]
        if not matches:
            return None
        best_specificity = max(specificity for specificity, _fields in matches)
        return frozenset().union(
            *(
                fields
                for specificity, fields in matches
                if specificity == best_specificity
            )
        )

    def validate_object(
        self,
        value: dict[str, Any],
        path: tuple[str, ...],
    ) -> None:
        actual = frozenset(value)
        if not path:
            if (
                not self.root_fields <= actual
                or not actual <= self.root_fields | self.optional_root_fields
            ):
                raise CanonicalFactsError(
                    "canonical facts contain unknown or missing root fields"
                )
            return
        if path == ("output",):
            if (
                not self.output_fields <= actual
                or not actual <= self.output_fields | self.optional_output_fields
            ):
                raise CanonicalFactsError(
                    "canonical facts contain unknown or missing output fields"
                )
            return

        allowed = self._allowed_nested_fields(path)
        path_text = "/" + "/".join(path)
        if allowed is None:
            raise CanonicalFactsError(
                f"canonical facts contain an unclosed object at {path_text}"
            )
        if not actual <= allowed:
            raise CanonicalFactsError(
                f"canonical facts contain unknown fields at {path_text}"
            )

    def validate(self, payload: dict[str, Any]) -> None:
        self.validate_object(payload, ())
        output = payload.get("output")
        if type(output) is not dict:
            raise CanonicalFactsError(
                "canonical facts contain unknown or missing output fields"
            )
        self.validate_object(output, ("output",))


COMMON_CANONICAL_OBJECT_FIELDS = canonical_object_fields(
    (
        "calendar_normalization",
        "algorithm_version calendar_convention calendar_digest changed_pillars "
        "civil_datetime day_boundary digest dst_offset_seconds effective_datetime "
        "effective_lunar_date effective_solar_date ganzhi instant_utc location "
        "lunar_date schema_version solar_date solar_terms status time_basis timezone "
        "timezone_details timezone_offset_seconds true_solar_time utc_datetime "
        "zi_hour_policy",
    ),
    (
        "calendar_normalization/calendar_convention",
        "day_rollover engine engine_version hour_basis id month_boundary "
        "source_dependency_id version year_boundary zi_hour_policy",
    ),
    (
        "calendar_normalization/day_boundary",
        "correction_crossed_date zi_policy_advanced_day_pillar",
    ),
    ("calendar_normalization/effective_lunar_date", "day is_leap_month month year"),
    ("calendar_normalization/ganzhi", "day hour month year"),
    (
        "calendar_normalization/location",
        "coordinate_accuracy_meters coordinate_source latitude longitude "
        "longitude_offset_degrees name",
    ),
    ("calendar_normalization/lunar_date", "day is_leap_month month year"),
    (
        "calendar_normalization/solar_terms",
        "active_month_boundary_jie active_year_boundary_li_chun exact_boundary "
        "month_switch_policy next next_month_boundary_jie next_year_boundary_li_chun "
        "previous previous_month_boundary_jie",
    ),
    (
        "calendar_normalization/solar_terms/*",
        "datetime index instant_utc is_month_boundary_jie name",
    ),
    (
        "calendar_normalization/time_basis",
        "algorithm boundary equation_of_time_seconds local_apparent_solar_datetime "
        "local_mean_solar_datetime longitude_correction_seconds policy "
        "standard_meridian_degrees total_correction_seconds",
    ),
    (
        "calendar_normalization/time_basis/algorithm",
        "id source supported_range uncertainty_seconds version",
    ),
    (
        "calendar_normalization/time_basis/boundary",
        "correction_changes_hour_branch distance_seconds "
        "nearest_double_hour_boundary within_uncertainty",
    ),
    (
        "calendar_normalization/timezone_details",
        "dst_offset_seconds fold name standard_meridian_degrees "
        "standard_offset_seconds utc_offset_seconds",
    ),
    (
        "calendar_normalization/true_solar_time",
        "equation_of_time_seconds longitude_correction_seconds policy status "
        "total_correction_seconds",
    ),
    ("capabilities", "allowed blocked"),
    (
        "public_calendar_normalization",
        "algorithm_version calendar_convention changed_pillars day_boundary "
        "effective_datetime solar_terms status time_basis true_solar_time",
    ),
    (
        "public_calendar_normalization/calendar_convention",
        "day_rollover hour_basis id month_boundary version year_boundary zi_hour_policy",
    ),
    (
        "public_calendar_normalization/day_boundary",
        "correction_crossed_date zi_policy_advanced_day_pillar",
    ),
    (
        "public_calendar_normalization/solar_terms",
        "month_switch_policy next previous",
    ),
    (
        "public_calendar_normalization/solar_terms/*",
        "datetime index instant_utc is_month_boundary_jie name",
    ),
    (
        "public_calendar_normalization/time_basis",
        "algorithm boundary equation_of_time_seconds longitude_correction_seconds "
        "policy standard_meridian_degrees total_correction_seconds",
    ),
    (
        "public_calendar_normalization/time_basis/algorithm",
        "id source uncertainty_seconds version",
    ),
    (
        "public_calendar_normalization/time_basis/boundary",
        "correction_changes_hour_branch distance_seconds within_uncertainty",
    ),
    (
        "public_calendar_normalization/true_solar_time",
        "equation_of_time_seconds longitude_correction_seconds policy status "
        "total_correction_seconds",
    ),
)


@dataclass(frozen=True)
class EngineProvenance:
    """The only envelope shared by art-specific Canonical Facts.

    The values are owned by the Runtime adapter, never selected from a
    third-party engine response.  Art contracts independently verify that
    the existing fact payload carries strict equivalent fields.
    """

    engine_id: str
    engine_version: str
    policy_profile: str
    time_basis: str

    def __post_init__(self) -> None:
        for name in (
            "engine_id",
            "engine_version",
            "policy_profile",
            "time_basis",
        ):
            value = getattr(self, name)
            if (
                type(value) is not str
                or not value.strip()
                or "\x00" in value
                or "\n" in value
                or "\r" in value
            ):
                raise CanonicalFactsError(
                    f"engine provenance {name} must be non-empty text"
                )

    def to_dict(self) -> dict[str, str]:
        return {
            "engine_id": self.engine_id,
            "engine_version": self.engine_version,
            "policy_profile": self.policy_profile,
            "time_basis": self.time_basis,
        }


def canonical_json_snapshot(
    payload: Any,
    *,
    field_closure: CanonicalFactsFieldClosure,
) -> dict[str, Any]:
    """Return a detached JSON object or fail closed on private/raw values.

    Canonical Facts cross the Provider boundary, so only exact JSON runtime
    types are admitted.  In particular, engine classes, Mapping subclasses,
    exception objects and fields outside the art-specific positive closure
    cannot be smuggled into a public calculation record.
    """

    def clone(
        value: Any,
        path: str,
        object_path: tuple[str, ...],
    ) -> Any:
        value_type = type(value)
        if value is None or value_type in (str, bool, int):
            return value
        if value_type is float:
            if not math.isfinite(value):
                raise CanonicalFactsError(
                    f"canonical facts contain a non-finite number at {path}"
                )
            return value
        if value_type is list:
            return [
                clone(item, f"{path}/{index}", object_path + ("*",))
                for index, item in enumerate(value)
            ]
        if value_type is dict:
            for key in value:
                if type(key) is not str:
                    raise CanonicalFactsError(
                        f"canonical facts contain a non-text key at {path}"
                    )
            field_closure.validate_object(value, object_path)
            result: dict[str, Any] = {}
            for key, item in value.items():
                result[key] = clone(
                    item,
                    f"{path}/{key}",
                    object_path + (key,),
                )
            return result
        raise CanonicalFactsError(
            f"canonical facts contain a private runtime value at {path}"
        )

    snapshot = clone(payload, "", ())
    if type(snapshot) is not dict:
        raise CanonicalFactsError("canonical facts must be a JSON object")
    field_closure.validate(snapshot)
    # Exercise the strict JSON encoder as a second, independent closed-world
    # check.  This is an in-memory snapshot, not a baseline hash or checksum.
    try:
        json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CanonicalFactsError("canonical facts are not strict JSON") from exc
    return snapshot


def valid_text(value: Any) -> bool:
    """True for non-blank strings; the generic fact-shape text predicate."""

    return isinstance(value, str) and bool(value.strip())


def finding(code: str, message: str, level: str = "error") -> dict[str, str]:
    """Build one structured finding in the facade's canonical shape."""

    return {"level": level, "code": code, "message": message}


class FactContract:
    """Interface every Provider-owned fact contract implements.

    Subclasses set ``contract_id`` and override the three hooks. All hooks
    receive the raw payload dicts; they must never raise for hostile input.
    The facade converts any unexpected exception into an explicit finding,
    but contracts should treat hostile shapes as findings, not crashes.
    """

    contract_id = ""

    #: When True the contract fully owns the system's fact validation: the
    #: facade skips the legacy required-output table and the legacy
    #: system-specific validators for that system. Default False keeps
    #: unmigrated systems on the legacy path untouched.
    replaces_legacy_validation = False

    #: Optional nominal Canonical Facts type owned by this art.  It is not a
    #: universal payload schema; Bazi and Ziwei bind distinct classes.
    canonical_facts_type: type[Any] | None = None

    def bind_canonical_facts(
        self,
        payload: dict[str, Any],
        provenance: EngineProvenance,
    ) -> Any:
        """Bind an existing fact payload to this art's nominal type."""

        fact_type = self.canonical_facts_type
        factory = getattr(fact_type, "from_payload", None)
        if fact_type is None or not callable(factory):
            raise CanonicalFactsError(
                f"{self.contract_id or 'fact contract'} has no Canonical Facts type"
            )
        return factory(payload, provenance)

    def required_output_ids(
        self,
        payload: dict[str, Any],
        base_required: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Return the required ``output`` keys for this payload's fact shape."""

        return tuple(base_required)

    def required_calendar_keys(
        self,
        payload: dict[str, Any],
        base_required: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Return the required ``calendar_normalization`` keys."""

        return tuple(base_required)

    def validate_output(
        self,
        payload: dict[str, Any],
        output: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Return structured findings for the Provider's output block."""

        del payload, output
        return []
