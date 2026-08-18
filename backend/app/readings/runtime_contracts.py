from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | tuple[JsonValue, ...] | Mapping[str, JsonValue]
type JsonObject = Mapping[str, JsonValue]

SCHEMA_ROOT = Path(__file__).resolve().parents[3] / "contracts" / "schemas"
COMMAND_SCHEMA = "mingli-command-v2.schema.json"
RESULT_SCHEMA = "mingli-result-v2.schema.json"


class ContractValidationError(ValueError):
    """A public JSON payload does not match its frozen contract."""


@lru_cache(maxsize=8)
def _validator(schema_name: str) -> Draft202012Validator:
    with (SCHEMA_ROOT / schema_name).open(encoding="utf-8") as stream:
        schema: dict[str, Any] = json.load(stream)
    return Draft202012Validator(schema)


def _validate_schema(schema_name: str, payload: Mapping[str, object]) -> None:
    try:
        _validator(schema_name).validate(dict(payload))
    except ValidationError as error:
        path = "$" + "".join(f"[{part!r}]" for part in error.absolute_path)
        raise ContractValidationError(f"{schema_name} validation failed at {path}") from error


def _freeze_json(value: object) -> JsonValue:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


def _freeze_object(value: Mapping[str, object]) -> JsonObject:
    frozen = _freeze_json(value)
    if not isinstance(frozen, Mapping):
        raise TypeError("JSON object expected")
    return frozen


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _thaw_object(value: Mapping[str, object]) -> dict[str, Any]:
    thawed = _thaw_json(value)
    if not isinstance(thawed, dict):
        raise TypeError("JSON object expected")
    return cast(dict[str, Any], thawed)


class ReadingBrief(Mapping[str, JsonValue]):
    __slots__ = ("_data",)

    def __init__(self, payload: Mapping[str, object]) -> None:
        self._data = _freeze_object(payload)

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> ReadingBrief:
        _validate_schema(
            RESULT_SCHEMA,
            {
                "kind": "prepared",
                "state_token": "contract-validation-token",
                "brief": dict(payload),
            },
        )
        return cls(payload)

    def to_dict(self) -> dict[str, Any]:
        return _thaw_object(self._data)

    def __getitem__(self, key: str) -> JsonValue:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


@dataclass(frozen=True, slots=True)
class Describe:
    kind: Literal["describe"] = "describe"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind}


@dataclass(frozen=True, slots=True)
class Prepare:
    query: str
    intent: Mapping[str, object]
    facts: Mapping[str, object]
    state_token: str | None = None
    transition: Literal["correct", "restart"] | None = None
    kind: Literal["prepare"] = "prepare"

    def __post_init__(self) -> None:
        object.__setattr__(self, "intent", _freeze_object(self.intent))
        object.__setattr__(self, "facts", _freeze_object(self.facts))
        _validate_schema(COMMAND_SCHEMA, self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "query": self.query,
            "intent": _thaw_object(self.intent),
            "facts": _thaw_object(self.facts),
            "state_token": self.state_token,
            "transition": self.transition,
        }


@dataclass(frozen=True, slots=True)
class Complete:
    state_token: str
    public_copy: str
    kind: Literal["complete"] = "complete"

    def __post_init__(self) -> None:
        _validate_schema(COMMAND_SCHEMA, self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "state_token": self.state_token,
            "public_copy": self.public_copy,
        }


type MingliCommand = Describe | Prepare | Complete


@dataclass(frozen=True, slots=True)
class Described:
    protocol_version: str
    manifest_digest: str
    capabilities: tuple[Mapping[str, object], ...]
    transition_ids: tuple[Literal["correct", "restart"], ...] = ()
    kind: Literal["described"] = "described"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capabilities",
            tuple(_freeze_object(item) for item in self.capabilities),
        )
        _validate_schema(RESULT_SCHEMA, self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "protocol_version": self.protocol_version,
            "manifest_digest": self.manifest_digest,
            "capabilities": [_thaw_object(item) for item in self.capabilities],
            "transition_ids": list(self.transition_ids),
        }


@dataclass(frozen=True, slots=True)
class Prepared:
    state_token: str
    brief: ReadingBrief | Mapping[str, object]
    kind: Literal["prepared"] = "prepared"

    def __post_init__(self) -> None:
        if not isinstance(self.brief, ReadingBrief):
            object.__setattr__(self, "brief", ReadingBrief(self.brief))
        _validate_schema(RESULT_SCHEMA, self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        brief = cast(ReadingBrief, self.brief)
        return {
            "kind": self.kind,
            "state_token": self.state_token,
            "brief": brief.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class Accepted:
    state_token: str
    public_copy: str
    kind: Literal["accepted"] = "accepted"

    def __post_init__(self) -> None:
        _validate_schema(RESULT_SCHEMA, self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "state_token": self.state_token,
            "public_copy": self.public_copy,
        }


type StoppedReason = Literal["need_input", "unsupported", "conflict", "error"]


@dataclass(frozen=True, slots=True)
class Stopped:
    reason: StoppedReason
    public_copy: str
    state_token: str | None = None
    input_request: Mapping[str, object] | None = None
    kind: Literal["stopped"] = "stopped"

    def __post_init__(self) -> None:
        if self.input_request is not None:
            object.__setattr__(
                self,
                "input_request",
                _freeze_object(self.input_request),
            )
        _validate_schema(RESULT_SCHEMA, self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "reason": self.reason,
            "public_copy": self.public_copy,
            "state_token": self.state_token,
            "input_request": (
                None if self.input_request is None else _thaw_object(self.input_request)
            ),
        }


type MingliResult = Described | Prepared | Accepted | Stopped


def command_from_dict(payload: Mapping[str, object]) -> MingliCommand:
    _validate_schema(COMMAND_SCHEMA, payload)
    kind = payload["kind"]
    if kind == "describe":
        return Describe()
    if kind == "prepare":
        return Prepare(
            query=cast(str, payload["query"]),
            intent=cast(Mapping[str, object], payload["intent"]),
            facts=cast(Mapping[str, object], payload["facts"]),
            state_token=cast(str | None, payload["state_token"]),
            transition=cast(
                Literal["correct", "restart"] | None,
                payload["transition"],
            ),
        )
    return Complete(
        state_token=cast(str, payload["state_token"]),
        public_copy=cast(str, payload["public_copy"]),
    )


def result_from_dict(payload: Mapping[str, object]) -> MingliResult:
    _validate_schema(RESULT_SCHEMA, payload)
    kind = payload["kind"]
    if kind == "described":
        return Described(
            protocol_version=cast(str, payload["protocol_version"]),
            manifest_digest=cast(str, payload["manifest_digest"]),
            capabilities=tuple(
                cast(Mapping[str, object], item)
                for item in cast(list[object], payload["capabilities"])
            ),
            transition_ids=tuple(
                cast(Literal["correct", "restart"], item)
                for item in cast(list[object], payload.get("transition_ids", []))
            ),
        )
    if kind == "prepared":
        return Prepared(
            state_token=cast(str, payload["state_token"]),
            brief=ReadingBrief(cast(Mapping[str, object], payload["brief"])),
        )
    if kind == "accepted":
        return Accepted(
            state_token=cast(str, payload["state_token"]),
            public_copy=cast(str, payload["public_copy"]),
        )
    return Stopped(
        reason=cast(StoppedReason, payload["reason"]),
        public_copy=cast(str, payload["public_copy"]),
        state_token=cast(str | None, payload["state_token"]),
        input_request=cast(Mapping[str, object] | None, payload["input_request"]),
    )
