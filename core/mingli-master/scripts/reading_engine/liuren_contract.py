"""Stable public Runtime projection for deterministic Daliuren facts."""

from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "mingli-liuren-runtime-core-facts-v1"

EARTH_PLATE_ORDER = tuple("子丑寅卯辰巳午未申酉戌亥")
TRANSMISSION_STAGES = ("initial", "middle", "final")

_TOP_LEVEL_REQUIRED = (
    "schema_version",
    "day_hour",
    "earth_plate",
    "heaven_plate",
    "heavenly_generals",
    "month_general",
    "noble_person",
    "lesson_method",
    "four_lessons",
    "three_transmissions",
    "plate_offset",
    "xunkong",
    "structural_patterns",
    "dimension_facts",
)
_TOP_LEVEL_OPTIONAL = ("timing_candidates",)
_LESSON_METHOD_FIELDS = (
    "primary",
    "use_method",
    "direct_direction",
    "selected_initial",
    "calculated_transmissions",
    "calculation_source",
    "source_anchor",
)
_DIMENSION_ENVELOPE = (
    "requested_dimension",
    "canonical_dimension",
    "status",
    "source_rule_ids",
    "rule_evidence",
)
_DIMENSION_FIELDS = {
    "outcome": (
        "subject_object_relation",
        "transmissions_to_day",
        "initial_final_relation",
        "stage_flow",
    ),
    "timing": ("relative_speed", "candidate_branch", "candidate_date"),
    "state": ("stage_status", "general_landing_correspondences"),
    "location": ("stage_branch_directions",),
    "relationship": (
        "six_relative_stages",
        "subject_object_relation",
        "stage_flow",
    ),
    "work": (
        "six_relative_stages",
        "stage_status",
        "subject_object_relation",
        "target_relative",
        "target_contract_status",
        "target_presence",
        "target_strength",
        "target_general_modifier",
    ),
    "money": (
        "wealth_presence",
        "wealth_stage_strength",
        "wealth_void_status",
        "wealth_general_modifier",
    ),
}
_REQUESTED_CANONICAL = {
    "outcome": "outcome",
    "timing": "timing",
    "state": "state",
    "current_state": "state",
    "location": "location",
    "location_direction": "location",
    "relationship": "relationship",
    "work": "work",
    "career": "work",
    "money": "money",
}
_EVIDENCE_FIELDS = (
    "status",
    "hard_verdict",
    "requires_school_adjudication",
    "matched",
    "scope_boundaries",
    "not_evaluated",
    "catalog_schema",
)
_EVIDENCE_RECORD_REQUIRED = (
    "rule_key",
    "activation_id",
    "rule_id",
    "status",
    "polarity",
    "weight_class",
    "dependency_group",
    "source_refs",
    "fact_paths",
    "observation",
)
_EVIDENCE_RECORD_OPTIONAL = ("confidence_ceiling", "stop_conditions")
_NOT_EVALUATED_FIELDS = (
    "rule_key",
    "activation_id",
    "rule_id",
    "status",
    "reason",
    "source_refs",
)
_SOURCE_REF_REQUIRED = ("pack", "rule_id", "source_anchor")
_SOURCE_REF_OPTIONAL = ("quote_id",)
_TIMING_CANDIDATE_FIELDS = (
    "id",
    "role",
    "anchor_earth_branch",
    "branch",
    "solar_date",
    "day_ganzhi",
    "days_after_cast",
    "source_pack",
    "source_rule",
    "candidate_not_guarantee",
)

_MISSING = object()


class LiurenRuntimeContractError(ValueError):
    """Raised when a public Daliuren Runtime payload violates v1."""


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LiurenRuntimeContractError(f"{path} must be an object")
    return value


def _sequence(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, (list, tuple)):
        raise LiurenRuntimeContractError(f"{path} must be an array")
    return value


def _exact_keys(
    value: Any,
    *,
    required: Sequence[str],
    optional: Sequence[str] = (),
    path: str,
) -> Mapping[str, Any]:
    item = _mapping(value, path)
    actual = set(item)
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - actual)
    unknown = sorted(actual - allowed)
    if missing:
        raise LiurenRuntimeContractError(
            f"{path} missing required keys: {', '.join(missing)}"
        )
    if unknown:
        raise LiurenRuntimeContractError(
            f"{path} contains unknown keys: {', '.join(unknown)}"
        )
    return item


def _nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LiurenRuntimeContractError(f"{path} must be a non-empty string")
    return value


def _nullable_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _nonempty_string(value, path)


def _string_array(value: Any, path: str) -> Sequence[Any]:
    rows = _sequence(value, path)
    for index, item in enumerate(rows):
        _nonempty_string(item, f"{path}[{index}]")
    return rows


def _validate_source_refs(value: Any, path: str) -> None:
    rows = _sequence(value, path)
    if not rows:
        raise LiurenRuntimeContractError(f"{path} must contain at least one source")
    for index, raw in enumerate(rows):
        row_path = f"{path}[{index}]"
        row = _exact_keys(
            raw,
            required=_SOURCE_REF_REQUIRED,
            optional=_SOURCE_REF_OPTIONAL,
            path=row_path,
        )
        for field in _SOURCE_REF_REQUIRED:
            _nonempty_string(row[field], f"{row_path}.{field}")
        if "quote_id" in row:
            _nonempty_string(row["quote_id"], f"{row_path}.quote_id")


def _validate_evidence_record(value: Any, path: str) -> None:
    row = _exact_keys(
        value,
        required=_EVIDENCE_RECORD_REQUIRED,
        optional=_EVIDENCE_RECORD_OPTIONAL,
        path=path,
    )
    for field in (
        "rule_key",
        "activation_id",
        "rule_id",
        "status",
        "polarity",
        "weight_class",
        "dependency_group",
    ):
        _nonempty_string(row[field], f"{path}.{field}")
    _validate_source_refs(row["source_refs"], f"{path}.source_refs")
    _string_array(row["fact_paths"], f"{path}.fact_paths")
    _mapping(row["observation"], f"{path}.observation")
    if "confidence_ceiling" in row:
        _nonempty_string(row["confidence_ceiling"], f"{path}.confidence_ceiling")
    if "stop_conditions" in row:
        _string_array(row["stop_conditions"], f"{path}.stop_conditions")


def _validate_rule_evidence(value: Any, path: str) -> None:
    evidence = _exact_keys(value, required=_EVIDENCE_FIELDS, path=path)
    if evidence["hard_verdict"] is not None:
        raise LiurenRuntimeContractError(f"{path}.hard_verdict must be null")
    if evidence["requires_school_adjudication"] is not True:
        raise LiurenRuntimeContractError(
            f"{path}.requires_school_adjudication must be true"
        )
    _nonempty_string(evidence["status"], f"{path}.status")
    _nonempty_string(evidence["catalog_schema"], f"{path}.catalog_schema")
    for group in ("matched", "scope_boundaries"):
        rows = _sequence(evidence[group], f"{path}.{group}")
        for index, row in enumerate(rows):
            _validate_evidence_record(row, f"{path}.{group}[{index}]")
    rows = _sequence(evidence["not_evaluated"], f"{path}.not_evaluated")
    for index, raw in enumerate(rows):
        row_path = f"{path}.not_evaluated[{index}]"
        row = _exact_keys(raw, required=_NOT_EVALUATED_FIELDS, path=row_path)
        for field in ("rule_key", "activation_id", "rule_id", "status", "reason"):
            _nonempty_string(row[field], f"{row_path}.{field}")
        _validate_source_refs(row["source_refs"], f"{row_path}.source_refs")


def _validate_timing_candidate(value: Any, path: str) -> None:
    row = _exact_keys(value, required=_TIMING_CANDIDATE_FIELDS, path=path)
    for field in (
        "id",
        "role",
        "anchor_earth_branch",
        "branch",
        "solar_date",
        "day_ganzhi",
        "source_pack",
        "source_rule",
    ):
        _nonempty_string(row[field], f"{path}.{field}")
    if not isinstance(row["days_after_cast"], int) or isinstance(
        row["days_after_cast"], bool
    ):
        raise LiurenRuntimeContractError(f"{path}.days_after_cast must be an integer")
    if row["candidate_not_guarantee"] is not True:
        raise LiurenRuntimeContractError(
            f"{path}.candidate_not_guarantee must be true"
        )


def _validate_dimension_facts(value: Any, path: str) -> None:
    dimensions = _mapping(value, path)
    for requested, raw in dimensions.items():
        dimension_path = f"{path}.{requested}"
        expected_canonical = _REQUESTED_CANONICAL.get(str(requested))
        if expected_canonical is None:
            raise LiurenRuntimeContractError(
                f"{path} contains unsupported requested dimension: {requested}"
            )
        fields = _DIMENSION_FIELDS[expected_canonical]
        row = _exact_keys(
            raw,
            required=(*_DIMENSION_ENVELOPE, *fields),
            path=dimension_path,
        )
        if row["requested_dimension"] != requested:
            raise LiurenRuntimeContractError(
                f"{dimension_path}.requested_dimension must match its object key"
            )
        if row["canonical_dimension"] != expected_canonical:
            raise LiurenRuntimeContractError(
                f"{dimension_path}.canonical_dimension must be {expected_canonical}"
            )
        if row["status"] != "calculated_facts_not_verdict":
            raise LiurenRuntimeContractError(
                f"{dimension_path}.status must be calculated_facts_not_verdict"
            )
        _string_array(row["source_rule_ids"], f"{dimension_path}.source_rule_ids")
        _validate_rule_evidence(row["rule_evidence"], f"{dimension_path}.rule_evidence")
        if expected_canonical == "timing":
            if row["candidate_branch"] is not None:
                branch = _exact_keys(
                    row["candidate_branch"],
                    required=("branch", "anchor_earth_branch", "source_rule"),
                    path=f"{dimension_path}.candidate_branch",
                )
                for field in branch:
                    _nonempty_string(
                        branch[field], f"{dimension_path}.candidate_branch.{field}"
                    )
            _nullable_string(row["relative_speed"], f"{dimension_path}.relative_speed")
            if row["candidate_date"] is not None:
                _validate_timing_candidate(
                    row["candidate_date"], f"{dimension_path}.candidate_date"
                )


def validate_runtime_core_facts(value: Any) -> None:
    """Reject missing and unknown public-contract fields at every fixed layer."""

    contract = _exact_keys(
        value,
        required=_TOP_LEVEL_REQUIRED,
        optional=_TOP_LEVEL_OPTIONAL,
        path="runtime_core_facts",
    )
    if contract["schema_version"] != SCHEMA_VERSION:
        raise LiurenRuntimeContractError("runtime_core_facts.schema_version is unsupported")

    day_hour = _exact_keys(
        contract["day_hour"], required=("day", "hour"), path="runtime_core_facts.day_hour"
    )
    _nonempty_string(day_hour["day"], "runtime_core_facts.day_hour.day")
    _nonempty_string(day_hour["hour"], "runtime_core_facts.day_hour.hour")

    earth_plate = tuple(_sequence(contract["earth_plate"], "runtime_core_facts.earth_plate"))
    if earth_plate != EARTH_PLATE_ORDER:
        raise LiurenRuntimeContractError(
            "runtime_core_facts.earth_plate must use fixed Zi-through-Hai order"
        )

    heaven_plate = _sequence(contract["heaven_plate"], "runtime_core_facts.heaven_plate")
    if len(heaven_plate) != 12:
        raise LiurenRuntimeContractError("runtime_core_facts.heaven_plate must have 12 rows")
    heaven_values: list[str] = []
    for index, raw in enumerate(heaven_plate):
        path = f"runtime_core_facts.heaven_plate[{index}]"
        row = _exact_keys(raw, required=("earth", "heaven"), path=path)
        if row["earth"] != EARTH_PLATE_ORDER[index]:
            raise LiurenRuntimeContractError(f"{path}.earth is out of plate order")
        heaven_values.append(_nonempty_string(row["heaven"], f"{path}.heaven"))
    if set(heaven_values) != set(EARTH_PLATE_ORDER):
        raise LiurenRuntimeContractError(
            "runtime_core_facts.heaven_plate must be a branch permutation"
        )

    generals = _sequence(
        contract["heavenly_generals"], "runtime_core_facts.heavenly_generals"
    )
    if len(generals) != 12:
        raise LiurenRuntimeContractError(
            "runtime_core_facts.heavenly_generals must have 12 rows"
        )
    for index, raw in enumerate(generals):
        path = f"runtime_core_facts.heavenly_generals[{index}]"
        row = _exact_keys(raw, required=("earth", "heaven", "general"), path=path)
        if row["earth"] != EARTH_PLATE_ORDER[index] or row["heaven"] != heaven_values[index]:
            raise LiurenRuntimeContractError(f"{path} must align with heaven_plate")
        _nonempty_string(row["general"], f"{path}.general")

    month_general = _exact_keys(
        contract["month_general"],
        required=("branch", "name"),
        path="runtime_core_facts.month_general",
    )
    _nonempty_string(month_general["branch"], "runtime_core_facts.month_general.branch")
    _nonempty_string(month_general["name"], "runtime_core_facts.month_general.name")

    noble_person = _exact_keys(
        contract["noble_person"],
        required=(
            "branch",
            "period",
            "earth_position",
            "direction",
            "profile",
            "day_night_profile",
            "source",
        ),
        path="runtime_core_facts.noble_person",
    )
    for field in noble_person:
        _nonempty_string(noble_person[field], f"runtime_core_facts.noble_person.{field}")

    method = _exact_keys(
        contract["lesson_method"],
        required=_LESSON_METHOD_FIELDS,
        path="runtime_core_facts.lesson_method",
    )
    for field in _LESSON_METHOD_FIELDS:
        if field == "direct_direction":
            _nullable_string(method[field], f"runtime_core_facts.lesson_method.{field}")
        else:
            _nonempty_string(method[field], f"runtime_core_facts.lesson_method.{field}")

    lessons = _sequence(contract["four_lessons"], "runtime_core_facts.four_lessons")
    if len(lessons) != 4:
        raise LiurenRuntimeContractError("runtime_core_facts.four_lessons must have 4 rows")
    for index, raw in enumerate(lessons):
        path = f"runtime_core_facts.four_lessons[{index}]"
        row = _exact_keys(
            raw,
            required=("lesson", "lower", "lower_lodge", "upper", "relation"),
            path=path,
        )
        if row["lesson"] != index + 1:
            raise LiurenRuntimeContractError(f"{path}.lesson is out of order")
        for field in ("lower", "lower_lodge", "upper", "relation"):
            _nonempty_string(row[field], f"{path}.{field}")

    transmissions = _sequence(
        contract["three_transmissions"], "runtime_core_facts.three_transmissions"
    )
    if len(transmissions) != 3:
        raise LiurenRuntimeContractError(
            "runtime_core_facts.three_transmissions must have 3 rows"
        )
    for index, raw in enumerate(transmissions):
        path = f"runtime_core_facts.three_transmissions[{index}]"
        row = _exact_keys(
            raw,
            required=("stage", "branch", "heavenly_general", "six_relative"),
            path=path,
        )
        if row["stage"] != TRANSMISSION_STAGES[index]:
            raise LiurenRuntimeContractError(f"{path}.stage is out of order")
        for field in ("branch", "heavenly_general", "six_relative"):
            _nonempty_string(row[field], f"{path}.{field}")

    offset = contract["plate_offset"]
    if not isinstance(offset, int) or isinstance(offset, bool) or not 0 <= offset < 12:
        raise LiurenRuntimeContractError(
            "runtime_core_facts.plate_offset must be an integer from 0 through 11"
        )
    xunkong = _exact_keys(
        contract["xunkong"],
        required=("xun", "branches"),
        path="runtime_core_facts.xunkong",
    )
    _nonempty_string(xunkong["xun"], "runtime_core_facts.xunkong.xun")
    if len(_string_array(xunkong["branches"], "runtime_core_facts.xunkong.branches")) != 2:
        raise LiurenRuntimeContractError(
            "runtime_core_facts.xunkong.branches must have 2 rows"
        )
    _string_array(
        contract["structural_patterns"], "runtime_core_facts.structural_patterns"
    )
    _validate_dimension_facts(
        contract["dimension_facts"], "runtime_core_facts.dimension_facts"
    )
    if "timing_candidates" in contract:
        rows = _sequence(
            contract["timing_candidates"], "runtime_core_facts.timing_candidates"
        )
        for index, row in enumerate(rows):
            _validate_timing_candidate(
                row, f"runtime_core_facts.timing_candidates[{index}]"
            )


def build_runtime_core_facts(
    output: Mapping[str, Any],
    dimension_facts: Mapping[str, Any],
    *,
    timing_candidates: Sequence[Mapping[str, Any]] | object = _MISSING,
) -> dict[str, Any]:
    """Build and self-validate the additive v1 public Runtime projection."""

    method = _mapping(output.get("transmission_method"), "output.transmission_method")
    contract: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "day_hour": copy.deepcopy(output.get("day_hour")),
        "earth_plate": copy.deepcopy(output.get("earth_plate")),
        "heaven_plate": copy.deepcopy(output.get("heaven_plate")),
        "heavenly_generals": copy.deepcopy(output.get("heavenly_generals")),
        "month_general": copy.deepcopy(output.get("month_general")),
        "noble_person": copy.deepcopy(output.get("noble_person")),
        "lesson_method": {
            field: copy.deepcopy(method.get(field)) for field in _LESSON_METHOD_FIELDS
        },
        "four_lessons": copy.deepcopy(output.get("four_lessons")),
        "three_transmissions": copy.deepcopy(output.get("three_transmissions")),
        "plate_offset": copy.deepcopy(output.get("plate_offset")),
        "xunkong": copy.deepcopy(output.get("xunkong")),
        "structural_patterns": copy.deepcopy(output.get("structural_patterns")),
        "dimension_facts": copy.deepcopy(dict(dimension_facts)),
    }
    if timing_candidates is not _MISSING:
        contract["timing_candidates"] = copy.deepcopy(timing_candidates)
    validate_runtime_core_facts(contract)
    return contract
