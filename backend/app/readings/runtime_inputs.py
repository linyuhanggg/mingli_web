from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast


class InvalidRuntimeInputError(ValueError):
    """Supplied values do not satisfy a product-approved Runtime input request."""


@dataclass(frozen=True, slots=True)
class InputFieldPolicy:
    target: str
    type_ids: frozenset[str]
    minimum: int | float | None = None
    maximum: int | float | None = None


_INPUT_FIELD_POLICIES: dict[str, InputFieldPolicy] = {
    **{
        f"cast_{index}": InputFieldPolicy(
            target="cast",
            type_ids=frozenset({"integer"}),
            minimum=6,
            maximum=9,
        )
        for index in range(1, 7)
    },
    "zi_policy": InputFieldPolicy(
        target="zi_hour_policy",
        type_ids=frozenset({"choice"}),
    ),
    "fixture_input": InputFieldPolicy(
        target="fixture_input",
        type_ids=frozenset({"text", "textarea"}),
    ),
}


def validate_runtime_input_values(
    input_request: Mapping[str, Any],
    values: Mapping[str, Any],
) -> dict[str, object]:
    requirements = input_request.get("requirements")
    if not isinstance(requirements, (list, tuple)) or not requirements:
        raise InvalidRuntimeInputError("runtime input request is malformed")
    fields_by_id: dict[str, Mapping[str, object]] = {}
    selected_ids: list[str] = []
    for requirement in requirements:
        if not isinstance(requirement, Mapping):
            raise InvalidRuntimeInputError("runtime input request is malformed")
        any_of = requirement.get("any_of")
        if not isinstance(any_of, (list, tuple)) or not any_of:
            raise InvalidRuntimeInputError("runtime input request is malformed")
        fields = [field for field in any_of if isinstance(field, Mapping)]
        field_ids = {str(field.get("id")) for field in fields if field.get("id")}
        if len(field_ids) != len(fields):
            raise InvalidRuntimeInputError("runtime input request is malformed")
        for field in fields:
            fields_by_id[str(field["id"])] = cast(Mapping[str, object], field)
        selected = sorted(field_ids.intersection(values))
        if len(selected) != 1:
            raise InvalidRuntimeInputError(
                "exactly one field from each input alternative is required"
            )
        selected_ids.extend(selected)

    if set(values) - set(fields_by_id):
        raise InvalidRuntimeInputError("unknown input fields are forbidden")

    mapped: dict[str, object] = {}
    cast_values: dict[int, int] = {}
    for field_id in selected_ids:
        policy = _INPUT_FIELD_POLICIES.get(field_id)
        if policy is None:
            raise InvalidRuntimeInputError("runtime input field is not product-approved")
        field = fields_by_id[field_id]
        type_id = field.get("type_id")
        if not isinstance(type_id, str) or type_id not in policy.type_ids:
            raise InvalidRuntimeInputError("runtime input field type is not approved")
        value = values[field_id]
        _validate_input_value(field, policy, value)
        if policy.target == "cast":
            cast_values[int(field_id.removeprefix("cast_"))] = cast(int, value)
        else:
            mapped[policy.target] = cast(object, value)

    if cast_values:
        if set(cast_values) != set(range(1, 7)):
            raise InvalidRuntimeInputError("all six cast values are required")
        mapped["cast"] = [cast_values[index] for index in range(1, 7)]
    return mapped


def apply_runtime_inputs(
    facts: Mapping[str, object],
    values: Mapping[str, Any],
) -> dict[str, object]:
    merged: dict[str, object] = {}
    for ref, subject_facts in facts.items():
        if isinstance(subject_facts, Mapping):
            merged[str(ref)] = {**dict(subject_facts), **dict(values)}
        else:
            merged[str(ref)] = subject_facts
    return merged


def _validate_input_value(
    field: Mapping[str, object],
    policy: InputFieldPolicy,
    value: object,
) -> None:
    type_id = cast(str, field["type_id"])
    if type_id == "integer":
        if type(value) is not int:
            raise InvalidRuntimeInputError("integer input must be an integer")
    elif type_id in {"text", "textarea"}:
        if not isinstance(value, str) or not value.strip():
            raise InvalidRuntimeInputError("text input must be non-empty")
    elif type_id == "choice":
        if not isinstance(value, str):
            raise InvalidRuntimeInputError("choice input must be a string")
    else:
        raise InvalidRuntimeInputError("unsupported runtime input type")

    if isinstance(value, (int, float)) and type(value) is not bool:
        if policy.minimum is not None and value < policy.minimum:
            raise InvalidRuntimeInputError("numeric input is below the allowed range")
        if policy.maximum is not None and value > policy.maximum:
            raise InvalidRuntimeInputError("numeric input is above the allowed range")

    raw_choices = field.get("choices")
    if raw_choices:
        if not isinstance(raw_choices, (list, tuple)):
            raise InvalidRuntimeInputError("runtime input choices are malformed")
        choice_ids = {
            str(choice.get("id"))
            for choice in raw_choices
            if isinstance(choice, Mapping) and choice.get("id")
        }
        if value not in choice_ids:
            raise InvalidRuntimeInputError("input value is outside the allowed choices")
