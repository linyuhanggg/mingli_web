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
_DAY_HOUR_FIELDS = ("day", "hour")
_HEAVEN_PLATE_ROW_FIELDS = ("earth", "heaven")
_HEAVENLY_GENERAL_ROW_FIELDS = ("earth", "heaven", "general")
_MONTH_GENERAL_FIELDS = ("branch", "name")
_NOBLE_PERSON_FIELDS = (
    "branch",
    "period",
    "earth_position",
    "direction",
    "profile",
    "day_night_profile",
    "source",
)
_LESSON_METHOD_FIELDS = (
    "primary",
    "use_method",
    "direct_direction",
    "selected_initial",
    "calculated_transmissions",
    "calculation_source",
    "source_anchor",
)
_FOUR_LESSON_ROW_FIELDS = ("lesson", "lower", "lower_lodge", "upper", "relation")
_THREE_TRANSMISSION_ROW_FIELDS = (
    "stage",
    "branch",
    "heavenly_general",
    "six_relative",
)
_XUNKONG_FIELDS = ("xun", "branches")
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
_RELATION_FIELDS = (
    "subject",
    "subject_value",
    "subject_element",
    "object",
    "object_value",
    "object_element",
    "relation",
)
_TRANSMISSION_RELATION_ROW_FIELDS = ("stage", *_RELATION_FIELDS)
_STAGE_FLOW_ROW_FIELDS = ("from_stage", "to_stage", *_RELATION_FIELDS)
_SIX_RELATIVE_STAGE_ROW_FIELDS = ("stage", "branch", "six_relative")
_STAGE_STATUS_ROW_FIELDS = (
    "stage",
    "branch",
    "six_relative",
    "heavenly_general",
    "season_strength",
    "is_xunkong",
)
_GENERAL_LANDING_ROW_REQUIRED = (
    "stage",
    "heavenly_general",
    "landing_branch",
    "source_pack",
    "source_rule",
    "role",
    "status",
)
_GENERAL_LANDING_ROW_OPTIONAL = ("source_text", "source_anchor")
_STAGE_BRANCH_DIRECTION_ROW_FIELDS = (
    "stage",
    "branch",
    "direction",
    "direction_chinese",
    "declared_source_anchor",
    "source_binding_status",
    "scope",
)
_TIMING_CANDIDATE_BRANCH_FIELDS = (
    "branch",
    "anchor_earth_branch",
    "source_rule",
)
_TARGET_STRENGTH_ROW_FIELDS = (
    "stage",
    "branch",
    "six_relative",
    "season_strength",
    "is_xunkong",
)
_WEALTH_STAGE_STRENGTH_ROW_FIELDS = (
    "stage",
    "branch",
    "six_relative",
    "season_strength",
)
_WEALTH_VOID_STATUS_ROW_FIELDS = (
    "stage",
    "branch",
    "six_relative",
    "is_xunkong",
)
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
_DIMENSION_OBJECT_FIELDS = {
    "subject_object_relation": _RELATION_FIELDS,
    "initial_final_relation": _RELATION_FIELDS,
    "candidate_branch": _TIMING_CANDIDATE_BRANCH_FIELDS,
    "candidate_date": _TIMING_CANDIDATE_FIELDS,
}
_DIMENSION_ROW_FIELDS = {
    "transmissions_to_day": _TRANSMISSION_RELATION_ROW_FIELDS,
    "stage_flow": _STAGE_FLOW_ROW_FIELDS,
    "six_relative_stages": _SIX_RELATIVE_STAGE_ROW_FIELDS,
    "stage_status": _STAGE_STATUS_ROW_FIELDS,
    "general_landing_correspondences": (
        *_GENERAL_LANDING_ROW_REQUIRED,
        *_GENERAL_LANDING_ROW_OPTIONAL,
    ),
    "stage_branch_directions": _STAGE_BRANCH_DIRECTION_ROW_FIELDS,
    "target_strength": _TARGET_STRENGTH_ROW_FIELDS,
    "target_general_modifier": (
        *_GENERAL_LANDING_ROW_REQUIRED,
        *_GENERAL_LANDING_ROW_OPTIONAL,
        "six_relative",
    ),
    "wealth_stage_strength": _WEALTH_STAGE_STRENGTH_ROW_FIELDS,
    "wealth_void_status": _WEALTH_VOID_STATUS_ROW_FIELDS,
    "wealth_general_modifier": (
        *_GENERAL_LANDING_ROW_REQUIRED,
        *_GENERAL_LANDING_ROW_OPTIONAL,
        "six_relative",
    ),
}
_NULLABLE_DIMENSION_OBJECTS = {"candidate_branch", "candidate_date"}

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


def _project_mapping(
    value: Any,
    *,
    fields: Sequence[str],
    path: str,
) -> dict[str, Any]:
    """Copy only fields declared by the stable public contract."""

    item = _mapping(value, path)
    return {field: copy.deepcopy(item[field]) for field in fields if field in item}


def _project_mapping_rows(
    value: Any,
    *,
    fields: Sequence[str],
    path: str,
) -> list[dict[str, Any]]:
    rows = _sequence(value, path)
    return [
        _project_mapping(row, fields=fields, path=f"{path}[{index}]")
        for index, row in enumerate(rows)
    ]


def _project_source_refs(value: Any, path: str) -> list[dict[str, Any]]:
    return _project_mapping_rows(
        value,
        fields=(*_SOURCE_REF_REQUIRED, *_SOURCE_REF_OPTIONAL),
        path=path,
    )


def _project_evidence_record(value: Any, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    projected: dict[str, Any] = {}
    for field in (*_EVIDENCE_RECORD_REQUIRED, *_EVIDENCE_RECORD_OPTIONAL):
        if field not in item:
            continue
        if field == "source_refs":
            projected[field] = _project_source_refs(
                item[field],
                f"{path}.source_refs",
            )
        elif field == "observation":
            projected[field] = copy.deepcopy(
                _mapping(item[field], f"{path}.observation")
            )
        else:
            projected[field] = copy.deepcopy(item[field])
    return projected


def _project_not_evaluated_record(value: Any, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    projected: dict[str, Any] = {}
    for field in _NOT_EVALUATED_FIELDS:
        if field not in item:
            continue
        if field == "source_refs":
            projected[field] = _project_source_refs(
                item[field],
                f"{path}.source_refs",
            )
        else:
            projected[field] = copy.deepcopy(item[field])
    return projected


def _project_rule_evidence(value: Any, path: str) -> dict[str, Any]:
    item = _mapping(value, path)
    projected: dict[str, Any] = {}
    for field in _EVIDENCE_FIELDS:
        if field not in item:
            continue
        field_path = f"{path}.{field}"
        if field in {"matched", "scope_boundaries"}:
            rows = _sequence(item[field], field_path)
            projected[field] = [
                _project_evidence_record(row, f"{field_path}[{index}]")
                for index, row in enumerate(rows)
            ]
        elif field == "not_evaluated":
            rows = _sequence(item[field], field_path)
            projected[field] = [
                _project_not_evaluated_record(row, f"{field_path}[{index}]")
                for index, row in enumerate(rows)
            ]
        else:
            projected[field] = copy.deepcopy(item[field])
    return projected


def _project_dimension_payload(value: Any, *, field: str, path: str) -> Any:
    object_fields = _DIMENSION_OBJECT_FIELDS.get(field)
    if object_fields is not None:
        if value is None and field in _NULLABLE_DIMENSION_OBJECTS:
            return None
        return _project_mapping(value, fields=object_fields, path=path)
    row_fields = _DIMENSION_ROW_FIELDS.get(field)
    if row_fields is not None:
        return _project_mapping_rows(value, fields=row_fields, path=path)
    return copy.deepcopy(value)


def _project_dimension_facts(value: Any, path: str) -> dict[str, Any]:
    dimensions = _mapping(value, path)
    projected: dict[str, Any] = {}
    for requested, raw in dimensions.items():
        dimension_path = f"{path}.{requested}"
        expected_canonical = _REQUESTED_CANONICAL.get(str(requested))
        if expected_canonical is None:
            raise LiurenRuntimeContractError(
                f"{path} contains unsupported requested dimension: {requested}"
            )
        item = _mapping(raw, dimension_path)
        dimension_fields = _DIMENSION_FIELDS[expected_canonical]
        row: dict[str, Any] = {}
        for field in (*_DIMENSION_ENVELOPE, *dimension_fields):
            if field not in item:
                continue
            if field in dimension_fields:
                row[field] = _project_dimension_payload(
                    item[field],
                    field=field,
                    path=f"{dimension_path}.{field}",
                )
            elif field == "rule_evidence":
                row[field] = _project_rule_evidence(
                    item[field],
                    f"{dimension_path}.rule_evidence",
                )
            else:
                row[field] = copy.deepcopy(item[field])
        projected[requested] = row
    return projected


def _nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LiurenRuntimeContractError(f"{path} must be a non-empty string")
    return value


def _nullable_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _nonempty_string(value, path)


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise LiurenRuntimeContractError(f"{path} must be a boolean")
    return value


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


def _validate_fixed_dimension_object(
    value: Any,
    *,
    required: Sequence[str],
    path: str,
) -> None:
    row = _exact_keys(value, required=required, path=path)
    for field in required:
        _nonempty_string(row[field], f"{path}.{field}")


def _validate_fixed_dimension_rows(
    value: Any,
    *,
    required: Sequence[str],
    path: str,
) -> None:
    rows = _sequence(value, path)
    for index, raw in enumerate(rows):
        row_path = f"{path}[{index}]"
        row = _exact_keys(raw, required=required, path=row_path)
        for field in required:
            if field == "is_xunkong":
                _boolean(row[field], f"{row_path}.{field}")
            elif field == "season_strength":
                _nullable_string(row[field], f"{row_path}.{field}")
            else:
                _nonempty_string(row[field], f"{row_path}.{field}")


def _validate_general_landing_rows(
    value: Any,
    *,
    path: str,
    include_six_relative: bool = False,
) -> None:
    rows = _sequence(value, path)
    for index, raw in enumerate(rows):
        row_path = f"{path}[{index}]"
        base_required = (
            *_GENERAL_LANDING_ROW_REQUIRED,
            *(("six_relative",) if include_six_relative else ()),
        )
        item = _mapping(raw, row_path)
        if item.get("status") == "source_correspondence_matched":
            required = (*base_required, *_GENERAL_LANDING_ROW_OPTIONAL)
        elif item.get("status") == "no_exact_source_correspondence":
            required = base_required
        else:
            raise LiurenRuntimeContractError(f"{row_path}.status is unsupported")
        row = _exact_keys(item, required=required, path=row_path)
        for field in required:
            _nonempty_string(row[field], f"{row_path}.{field}")


def _validate_dimension_payloads(
    row: Mapping[str, Any],
    *,
    canonical: str,
    path: str,
) -> None:
    for field in _DIMENSION_FIELDS[canonical]:
        field_path = f"{path}.{field}"
        value = row[field]
        if field in _NULLABLE_DIMENSION_OBJECTS and value is None:
            continue
        if field == "candidate_date":
            _validate_timing_candidate(value, field_path)
        elif field == "candidate_branch":
            branch = _exact_keys(
                value,
                required=_TIMING_CANDIDATE_BRANCH_FIELDS,
                path=field_path,
            )
            for branch_field in _TIMING_CANDIDATE_BRANCH_FIELDS:
                _nonempty_string(branch[branch_field], f"{field_path}.{branch_field}")
        elif field in {"subject_object_relation", "initial_final_relation"}:
            _validate_fixed_dimension_object(
                value,
                required=_DIMENSION_OBJECT_FIELDS[field],
                path=field_path,
            )
        elif field in {
            "general_landing_correspondences",
            "target_general_modifier",
            "wealth_general_modifier",
        }:
            _validate_general_landing_rows(
                value,
                path=field_path,
                include_six_relative=field != "general_landing_correspondences",
            )
        elif field in _DIMENSION_ROW_FIELDS:
            _validate_fixed_dimension_rows(
                value,
                required=_DIMENSION_ROW_FIELDS[field],
                path=field_path,
            )
        elif field in {"relative_speed", "target_relative"}:
            _nullable_string(value, field_path)
        elif field in {"target_presence", "wealth_presence"}:
            _boolean(value, field_path)
        else:
            _nonempty_string(value, field_path)


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
        _validate_dimension_payloads(
            row,
            canonical=expected_canonical,
            path=dimension_path,
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
        contract["day_hour"],
        required=_DAY_HOUR_FIELDS,
        path="runtime_core_facts.day_hour",
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
        row = _exact_keys(raw, required=_HEAVEN_PLATE_ROW_FIELDS, path=path)
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
        row = _exact_keys(raw, required=_HEAVENLY_GENERAL_ROW_FIELDS, path=path)
        if row["earth"] != EARTH_PLATE_ORDER[index] or row["heaven"] != heaven_values[index]:
            raise LiurenRuntimeContractError(f"{path} must align with heaven_plate")
        _nonempty_string(row["general"], f"{path}.general")

    month_general = _exact_keys(
        contract["month_general"],
        required=_MONTH_GENERAL_FIELDS,
        path="runtime_core_facts.month_general",
    )
    _nonempty_string(month_general["branch"], "runtime_core_facts.month_general.branch")
    _nonempty_string(month_general["name"], "runtime_core_facts.month_general.name")

    noble_person = _exact_keys(
        contract["noble_person"],
        required=_NOBLE_PERSON_FIELDS,
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
            required=_FOUR_LESSON_ROW_FIELDS,
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
            required=_THREE_TRANSMISSION_ROW_FIELDS,
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
        required=_XUNKONG_FIELDS,
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

    contract: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "day_hour": _project_mapping(
            output.get("day_hour"),
            fields=_DAY_HOUR_FIELDS,
            path="output.day_hour",
        ),
        "earth_plate": copy.deepcopy(output.get("earth_plate")),
        "heaven_plate": _project_mapping_rows(
            output.get("heaven_plate"),
            fields=_HEAVEN_PLATE_ROW_FIELDS,
            path="output.heaven_plate",
        ),
        "heavenly_generals": _project_mapping_rows(
            output.get("heavenly_generals"),
            fields=_HEAVENLY_GENERAL_ROW_FIELDS,
            path="output.heavenly_generals",
        ),
        "month_general": _project_mapping(
            output.get("month_general"),
            fields=_MONTH_GENERAL_FIELDS,
            path="output.month_general",
        ),
        "noble_person": _project_mapping(
            output.get("noble_person"),
            fields=_NOBLE_PERSON_FIELDS,
            path="output.noble_person",
        ),
        "lesson_method": _project_mapping(
            output.get("transmission_method"),
            fields=_LESSON_METHOD_FIELDS,
            path="output.transmission_method",
        ),
        "four_lessons": _project_mapping_rows(
            output.get("four_lessons"),
            fields=_FOUR_LESSON_ROW_FIELDS,
            path="output.four_lessons",
        ),
        "three_transmissions": _project_mapping_rows(
            output.get("three_transmissions"),
            fields=_THREE_TRANSMISSION_ROW_FIELDS,
            path="output.three_transmissions",
        ),
        "plate_offset": copy.deepcopy(output.get("plate_offset")),
        "xunkong": _project_mapping(
            output.get("xunkong"),
            fields=_XUNKONG_FIELDS,
            path="output.xunkong",
        ),
        "structural_patterns": copy.deepcopy(output.get("structural_patterns")),
        "dimension_facts": _project_dimension_facts(
            dimension_facts,
            "dimension_facts",
        ),
    }
    if timing_candidates is not _MISSING:
        contract["timing_candidates"] = _project_mapping_rows(
            timing_candidates,
            fields=_TIMING_CANDIDATE_FIELDS,
            path="timing_candidates",
        )
    validate_runtime_core_facts(contract)
    return contract
