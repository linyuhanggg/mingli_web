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
    transition_ids: tuple[Literal["correct", "restart"], ...] | None = None
    kind: Literal["described"] = "described"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "capabilities",
            tuple(_freeze_object(item) for item in self.capabilities),
        )
        _validate_schema(RESULT_SCHEMA, self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind,
            "protocol_version": self.protocol_version,
            "manifest_digest": self.manifest_digest,
            "capabilities": [_thaw_object(item) for item in self.capabilities],
        }
        if self.transition_ids is not None:
            payload["transition_ids"] = list(self.transition_ids)
        return payload


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
type RuntimeFailureCategory = Literal[
    "bootstrap", "input_contract", "runtime_internal", "transient"
]
type RuntimeFailureCode = Literal[
    "bootstrap.unexpected_arguments",
    "bootstrap.guard_load_failed",
    "bootstrap.runtime_lock_failed",
    "bootstrap.runtime_identity_invalid",
    "bootstrap.state_root_invalid",
    "input_contract.malformed_json",
    "input_contract.invalid_command",
    "input_contract.invalid_payload",
    "input_contract.invalid_state_token",
    "runtime.internal_error",
    "transient.timeout",
    "transient.resource_unavailable",
]

RUNTIME_FAILURE_SCHEMA_VERSION: Literal["mingli-runtime-failure/v1"] = (
    "mingli-runtime-failure/v1"
)
RUNTIME_FAILURE_SCHEMA_VERSION_V2: Literal["mingli-runtime-failure/v2"] = (
    "mingli-runtime-failure/v2"
)
type RuntimeFailureSchemaVersion = Literal[
    "mingli-runtime-failure/v1",
    "mingli-runtime-failure/v2",
]
_RUNTIME_FAILURE_METADATA: Mapping[
    RuntimeFailureCode, tuple[RuntimeFailureCategory, bool]
] = MappingProxyType(
    {
        "bootstrap.unexpected_arguments": ("bootstrap", False),
        "bootstrap.guard_load_failed": ("bootstrap", False),
        "bootstrap.runtime_lock_failed": ("bootstrap", False),
        "bootstrap.runtime_identity_invalid": ("bootstrap", False),
        "bootstrap.state_root_invalid": ("bootstrap", False),
        "input_contract.malformed_json": ("input_contract", False),
        "input_contract.invalid_command": ("input_contract", False),
        "input_contract.invalid_payload": ("input_contract", False),
        "input_contract.invalid_state_token": ("input_contract", False),
        "runtime.internal_error": ("runtime_internal", False),
        "transient.timeout": ("transient", True),
        "transient.resource_unavailable": ("transient", True),
    }
)
SAFE_INTERNAL_FAILURE_CODES = frozenset(
    {
        "KeyError",
        "OSError",
        "RuntimeError",
        "TypeError",
        "ValueError",
        "action_requires_correct",
        "action_requires_correct_or_recast",
        "action_requires_recast",
        "descriptor_invalid",
        "descriptor_unbound",
        "empty_public_copy",
        "evidence_binding",
        "extension_digest_changed",
        "extension_missing",
        "invalid_preparation",
        "invalid_transition",
        "not_prepared",
        "subject_scope",
        "unknown_state_token",
        "wrong_system",
    }
)
_V1_FAILURE_FIELDS = frozenset({"schema_version", "code", "category", "retryable"})
_V2_FAILURE_FIELDS = frozenset(
    {"schema_version", "code", "category", "retryable", "internal_code"}
)


@dataclass(frozen=True, slots=True)
class RuntimeFailure:
    """Closed, non-PII Runtime failure classification for host audit only."""

    code: RuntimeFailureCode
    category: RuntimeFailureCategory
    retryable: bool
    schema_version: RuntimeFailureSchemaVersion = RUNTIME_FAILURE_SCHEMA_VERSION
    internal_code: str | None = None

    def __post_init__(self) -> None:
        expected = _RUNTIME_FAILURE_METADATA.get(self.code)
        if expected is None or expected != (self.category, self.retryable):
            raise ValueError("runtime failure must match the closed v1 code table")
        if self.schema_version == RUNTIME_FAILURE_SCHEMA_VERSION:
            if self.internal_code is not None:
                raise ValueError("runtime failure must match the closed v1 code table")
            return
        if self.schema_version != RUNTIME_FAILURE_SCHEMA_VERSION_V2:
            raise ValueError("runtime failure must match the closed v1 code table")
        if (
            self.code != "runtime.internal_error"
            or self.category != "runtime_internal"
            or self.retryable is not False
            or (
                self.internal_code is not None
                and self.internal_code not in SAFE_INTERNAL_FAILURE_CODES
            )
        ):
            raise ValueError("runtime failure must match the closed v2 code table")

    @classmethod
    def internal_error(cls) -> RuntimeFailure:
        return cls(
            code="runtime.internal_error",
            category="runtime_internal",
            retryable=False,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> RuntimeFailure:
        version = payload.get("schema_version")
        if version == RUNTIME_FAILURE_SCHEMA_VERSION:
            if set(payload) != _V1_FAILURE_FIELDS:
                raise ValueError("runtime failure fields are invalid")
            return cls(
                schema_version=RUNTIME_FAILURE_SCHEMA_VERSION,
                code=cast(RuntimeFailureCode, payload["code"]),
                category=cast(RuntimeFailureCategory, payload["category"]),
                retryable=cast(bool, payload["retryable"]),
            )
        if version == RUNTIME_FAILURE_SCHEMA_VERSION_V2:
            if set(payload) != _V2_FAILURE_FIELDS:
                raise ValueError("runtime failure fields are invalid")
            internal_code = payload["internal_code"]
            if internal_code is not None and (
                not isinstance(internal_code, str)
                or internal_code not in SAFE_INTERNAL_FAILURE_CODES
            ):
                raise ValueError("internal failure code is not in the safe code table")
            return cls(
                schema_version=RUNTIME_FAILURE_SCHEMA_VERSION_V2,
                code=cast(RuntimeFailureCode, payload["code"]),
                category=cast(RuntimeFailureCategory, payload["category"]),
                retryable=cast(bool, payload["retryable"]),
                internal_code=internal_code,
            )
        raise ValueError("runtime failure must match the closed v1 code table")

    def to_dict(self) -> dict[str, object]:
        """Public classification used by HTTP, DB, copy, and frozen result JSON."""

        return {
            "schema_version": RUNTIME_FAILURE_SCHEMA_VERSION,
            "code": self.code,
            "category": self.category,
            "retryable": self.retryable,
        }

    def to_audit_dict(self) -> dict[str, object]:
        """Typed turn-audit payload. v2 may include allowlisted internal_code."""

        if self.schema_version != RUNTIME_FAILURE_SCHEMA_VERSION_V2:
            return self.to_dict()
        return {
            "schema_version": RUNTIME_FAILURE_SCHEMA_VERSION_V2,
            "code": self.code,
            "category": self.category,
            "retryable": self.retryable,
            "internal_code": self.internal_code,
        }


@dataclass(frozen=True, slots=True)
class Stopped:
    reason: StoppedReason
    public_copy: str
    state_token: str | None = None
    input_request: Mapping[str, object] | None = None
    failure: RuntimeFailure | None = None
    kind: Literal["stopped"] = "stopped"

    def __post_init__(self) -> None:
        if self.input_request is not None:
            object.__setattr__(
                self,
                "input_request",
                _freeze_object(self.input_request),
            )
        if self.reason == "error":
            if self.failure is None:
                object.__setattr__(self, "failure", RuntimeFailure.internal_error())
        elif self.failure is not None:
            raise ValueError("only Stopped(error) can carry a runtime failure")
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
            "failure": None if self.failure is None else self.failure.to_dict(),
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


def _failure_from_stopped_payload(
    payload: Mapping[str, object],
) -> tuple[Mapping[str, object], RuntimeFailure | None]:
    raw_failure = payload.get("failure")
    if not isinstance(raw_failure, Mapping):
        return payload, None
    if raw_failure.get("schema_version") != RUNTIME_FAILURE_SCHEMA_VERSION_V2:
        return payload, None
    try:
        typed = RuntimeFailure.from_dict(raw_failure)
    except ValueError as error:
        raise ContractValidationError(str(error)) from error
    public = dict(payload)
    public["failure"] = typed.to_dict()
    return public, typed


def result_from_dict(payload: Mapping[str, object]) -> MingliResult:
    typed_v2_failure: RuntimeFailure | None = None
    if payload.get("kind") == "stopped":
        payload, typed_v2_failure = _failure_from_stopped_payload(payload)
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
            transition_ids=(
                None
                if payload.get("transition_ids") is None
                else tuple(
                    cast(Literal["correct", "restart"], item)
                    for item in cast(list[object], payload["transition_ids"])
                )
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
    if typed_v2_failure is not None:
        failure: RuntimeFailure | None = typed_v2_failure
    elif payload.get("failure") is None:
        failure = None
    else:
        failure = RuntimeFailure.from_dict(cast(Mapping[str, object], payload["failure"]))
    return Stopped(
        reason=cast(StoppedReason, payload["reason"]),
        public_copy=cast(str, payload["public_copy"]),
        state_token=cast(str | None, payload["state_token"]),
        input_request=cast(Mapping[str, object] | None, payload["input_request"]),
        failure=failure,
    )
