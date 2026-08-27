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


TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION: Literal["time-layer-entitlement/v1"] = (
    "time-layer-entitlement/v1"
)
type TimeLayerEntitlementCapabilityId = Literal["bazi", "ziwei"]
type TimeLayerEntitlementResolution = Literal[
    "granted",
    "denied",
    "unknown",
    "unauthenticated",
    "request_failed",
]
type TimeLayerEntitlementAccess = Literal[
    "readable",
    "locked_paywall",
    "fail_closed_unknown",
    "unavailable",
]
type TimeLayerEntitlementTier = Literal["free", "paid"]
type TimeLayerUpgradeCta = Literal["professional_info"]
type TimeLayerEntitlementLayerId = Literal[
    "life",
    "luck_cycles",
    "major_limits",
    "year",
    "month",
    "day",
    "hour",
]

PAID_TIME_LAYER_IDS: tuple[TimeLayerEntitlementLayerId, ...] = ("month", "day", "hour")
FREE_BOUNDARY_LAYER_ID: Literal["year"] = "year"
_TIME_LAYER_CAPABILITY_KEYS = frozenset(
    {"layer_id", "label", "available", "unavailable_reason"}
)
_ENTITLEMENT_LAYER_KEYS = frozenset(
    {"layer_id", "tier", "access", "upgrade_cta"}
)
_ENTITLEMENT_OBJECT_KEYS = frozenset(
    {
        "schema_version",
        "capability_id",
        "resolution",
        "free_boundary_layer_id",
        "paid_layer_ids",
        "free_year_set",
        "capability",
        "layers",
    }
)
_CAPABILITY_OBJECT_KEYS = frozenset({"time_layers"})
_RESOLUTION_VALUES = frozenset(
    {"granted", "denied", "unknown", "unauthenticated", "request_failed"}
)
_ACCESS_VALUES = frozenset(
    {"readable", "locked_paywall", "fail_closed_unknown", "unavailable"}
)
_LOCKED_PAID_ACCESS = frozenset({"locked_paywall", "fail_closed_unknown"})
_PAID_ACCESS_BY_RESOLUTION: Mapping[
    TimeLayerEntitlementResolution, frozenset[TimeLayerEntitlementAccess]
] = MappingProxyType(
    {
        "granted": frozenset({"readable", "unavailable"}),
        "denied": frozenset({"locked_paywall", "unavailable"}),
        "unknown": frozenset({"fail_closed_unknown", "unavailable"}),
        "unauthenticated": frozenset({"fail_closed_unknown", "unavailable"}),
        "request_failed": frozenset({"fail_closed_unknown", "unavailable"}),
    }
)
_LAYER_IDS_BY_CAPABILITY: Mapping[
    TimeLayerEntitlementCapabilityId, tuple[TimeLayerEntitlementLayerId, ...]
] = MappingProxyType(
    {
        "bazi": ("life", "luck_cycles", "year", "month", "day", "hour"),
        "ziwei": ("life", "major_limits", "year", "month", "day", "hour"),
    }
)
_CAPABILITY_LAYER_IDS_BY_CAPABILITY: Mapping[
    TimeLayerEntitlementCapabilityId, frozenset[str]
] = MappingProxyType(
    {
        "bazi": frozenset({"life", "year", "month", "day", "hour"}),
        "ziwei": frozenset({"life", "year", "month", "day", "hour"}),
    }
)
_FREE_LAYER_IDS_BY_CAPABILITY: Mapping[
    TimeLayerEntitlementCapabilityId, frozenset[TimeLayerEntitlementLayerId]
] = MappingProxyType(
    {
        "bazi": frozenset({"life", "luck_cycles", "year"}),
        "ziwei": frozenset({"life", "major_limits", "year"}),
    }
)
_YEAR_FACT_KEY_BY_CAPABILITY: Mapping[TimeLayerEntitlementCapabilityId, str] = (
    MappingProxyType({"bazi": "year_layers", "ziwei": "annual_layers"})
)
_MONTH_FACT_KEY_BY_CAPABILITY: Mapping[TimeLayerEntitlementCapabilityId, str] = (
    MappingProxyType({"bazi": "month_layers", "ziwei": "monthly_layers"})
)
_DAY_FACT_KEY_BY_CAPABILITY: Mapping[TimeLayerEntitlementCapabilityId, str] = (
    MappingProxyType({"bazi": "day_layers", "ziwei": "daily_layers"})
)
_SCHEMA_TO_CAPABILITY: Mapping[str, TimeLayerEntitlementCapabilityId] = MappingProxyType(
    {"bazi-chart/v1": "bazi", "ziwei-chart/v1": "ziwei"}
)


def _require_exact_keys(
    payload: Mapping[str, object],
    allowed: frozenset[str],
    *,
    label: str,
) -> None:
    keys = frozenset(payload)
    extra = keys - allowed
    missing = allowed - keys
    if extra or missing:
        raise ContractValidationError(
            f"{label} must use closed keys; extra={sorted(extra)} missing={sorted(missing)}"
        )


def _text_layer_id(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ContractValidationError("time layer id must be a non-empty string")
    return value


def resolve_time_layer_entitlement_resolution(
    *,
    owner_kind: Literal["user", "guest"] | None,
    request_failed: bool = False,
    paid_grant: bool | None = None,
) -> TimeLayerEntitlementResolution:
    """Map host session/grant state to entitlement without touching capability."""

    if request_failed:
        return "request_failed"
    if owner_kind != "user":
        return "unauthenticated"
    if paid_grant is None:
        return "unknown"
    return "granted" if paid_grant else "denied"


def _access_for_layer(
    *,
    tier: TimeLayerEntitlementTier,
    available: bool,
    facts_present: bool,
    resolution: TimeLayerEntitlementResolution,
) -> TimeLayerEntitlementAccess:
    if tier == "free":
        if facts_present or available:
            return "readable"
        return "unavailable"
    if not available and not facts_present:
        return "unavailable"
    if resolution == "granted":
        return "readable"
    if resolution == "denied":
        return "locked_paywall"
    return "fail_closed_unknown"


def _upgrade_cta_for_access(
    access: TimeLayerEntitlementAccess,
    *,
    tier: TimeLayerEntitlementTier,
) -> TimeLayerUpgradeCta | None:
    if tier == "free" or access not in _LOCKED_PAID_ACCESS:
        return None
    return "professional_info"


@dataclass(frozen=True, slots=True)
class TimeLayerCapabilitySnapshot:
    layer_id: str
    label: str
    available: bool
    unavailable_reason: str | None

    def __post_init__(self) -> None:
        if not self.layer_id or not self.label:
            raise ContractValidationError("capability time layer requires layer_id and label")
        if self.available == (self.unavailable_reason is not None):
            raise ContractValidationError(
                "capability unavailable_reason is required iff available is false"
            )
        if self.unavailable_reason is not None and not self.unavailable_reason:
            raise ContractValidationError("capability unavailable_reason must be non-empty")

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> TimeLayerCapabilitySnapshot:
        _require_exact_keys(payload, _TIME_LAYER_CAPABILITY_KEYS, label="capability time_layers[]")
        available = payload["available"]
        if not isinstance(available, bool):
            raise ContractValidationError("capability available must be a boolean")
        reason = payload["unavailable_reason"]
        if reason is not None and not isinstance(reason, str):
            raise ContractValidationError("capability unavailable_reason must be string or null")
        return cls(
            layer_id=_text_layer_id(payload["layer_id"]),
            label=_text_layer_id(payload["label"]),
            available=available,
            unavailable_reason=reason,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "label": self.label,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
        }


@dataclass(frozen=True, slots=True)
class TimeLayerEntitlementEntry:
    layer_id: TimeLayerEntitlementLayerId
    tier: TimeLayerEntitlementTier
    access: TimeLayerEntitlementAccess
    upgrade_cta: TimeLayerUpgradeCta | None

    def __post_init__(self) -> None:
        expected_cta = _upgrade_cta_for_access(self.access, tier=self.tier)
        if self.upgrade_cta != expected_cta:
            raise ContractValidationError(
                "upgrade_cta is only professional_info for locked paid layers"
            )
        if self.tier == "free" and self.access in _LOCKED_PAID_ACCESS:
            raise ContractValidationError("free layers cannot use paid lock access")
        if self.tier == "paid" and self.layer_id not in PAID_TIME_LAYER_IDS:
            raise ContractValidationError("paid tier is fixed to month/day/hour")
        if self.tier == "free" and self.layer_id in PAID_TIME_LAYER_IDS:
            raise ContractValidationError("month/day/hour cannot be free")

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> TimeLayerEntitlementEntry:
        _require_exact_keys(payload, _ENTITLEMENT_LAYER_KEYS, label="entitlement layers[]")
        layer_id = payload["layer_id"]
        tier = payload["tier"]
        access = payload["access"]
        upgrade_cta = payload["upgrade_cta"]
        if layer_id not in {
            "life",
            "luck_cycles",
            "major_limits",
            "year",
            "month",
            "day",
            "hour",
        }:
            raise ContractValidationError(f"unsupported entitlement layer_id: {layer_id!r}")
        if tier not in {"free", "paid"}:
            raise ContractValidationError(f"unsupported entitlement tier: {tier!r}")
        if access not in _ACCESS_VALUES:
            raise ContractValidationError(f"unsupported entitlement access: {access!r}")
        if upgrade_cta not in {None, "professional_info"}:
            raise ContractValidationError(f"unsupported upgrade_cta: {upgrade_cta!r}")
        return cls(
            layer_id=cast(TimeLayerEntitlementLayerId, layer_id),
            tier=cast(TimeLayerEntitlementTier, tier),
            access=cast(TimeLayerEntitlementAccess, access),
            upgrade_cta=cast(TimeLayerUpgradeCta | None, upgrade_cta),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "tier": self.tier,
            "access": self.access,
            "upgrade_cta": self.upgrade_cta,
        }


@dataclass(frozen=True, slots=True)
class TimeLayerEntitlementV1:
    """Versioned G1/G3 time-layer entitlement, separate from capability availability."""

    capability_id: TimeLayerEntitlementCapabilityId
    resolution: TimeLayerEntitlementResolution
    free_year_set: tuple[int, ...]
    capability: tuple[TimeLayerCapabilitySnapshot, ...]
    layers: tuple[TimeLayerEntitlementEntry, ...]
    schema_version: Literal["time-layer-entitlement/v1"] = (
        TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION
    )
    free_boundary_layer_id: Literal["year"] = FREE_BOUNDARY_LAYER_ID
    paid_layer_ids: tuple[TimeLayerEntitlementLayerId, ...] = PAID_TIME_LAYER_IDS

    def __post_init__(self) -> None:
        if self.schema_version != TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION:
            raise ContractValidationError("time-layer-entitlement schema_version is frozen at v1")
        if self.free_boundary_layer_id != FREE_BOUNDARY_LAYER_ID:
            raise ContractValidationError("free boundary is frozen at year")
        if self.paid_layer_ids != PAID_TIME_LAYER_IDS:
            raise ContractValidationError("paid layers are frozen as month/day/hour")
        if self.resolution not in _PAID_ACCESS_BY_RESOLUTION:
            raise ContractValidationError(
                f"unsupported entitlement resolution: {self.resolution!r}"
            )
        expected_ids = _LAYER_IDS_BY_CAPABILITY[self.capability_id]
        actual_ids = tuple(item.layer_id for item in self.layers)
        if actual_ids != expected_ids:
            raise ContractValidationError("entitlement layers must match the closed per-art table")
        free_ids = _FREE_LAYER_IDS_BY_CAPABILITY[self.capability_id]
        for item in self.layers:
            expected_tier: TimeLayerEntitlementTier = (
                "free" if item.layer_id in free_ids else "paid"
            )
            if item.tier != expected_tier:
                raise ContractValidationError(
                    f"{item.layer_id} tier must be {expected_tier} for {self.capability_id}"
                )
        allowed_paid_access = _PAID_ACCESS_BY_RESOLUTION[self.resolution]
        for item in self.layers:
            if item.tier != "paid":
                continue
            if item.access not in allowed_paid_access:
                raise ContractValidationError(
                    f"paid layer {item.layer_id} access {item.access!r} is incompatible "
                    f"with resolution {self.resolution}"
                )
        allowed_capability_ids = _CAPABILITY_LAYER_IDS_BY_CAPABILITY[self.capability_id]
        seen_capability: set[str] = set()
        for snapshot in self.capability:
            if snapshot.layer_id in seen_capability:
                raise ContractValidationError("capability time_layers layer_id must be unique")
            seen_capability.add(snapshot.layer_id)
            if snapshot.layer_id in {"luck_cycles", "major_limits"}:
                raise ContractValidationError(
                    "capability time_layers cannot carry structural fact keys"
                )
            if snapshot.layer_id not in allowed_capability_ids:
                raise ContractValidationError(
                    f"capability time_layers layer_id {snapshot.layer_id!r} is outside "
                    f"the closed {self.capability_id} table"
                )
        years = self.free_year_set
        if any(
            not isinstance(year, int) or isinstance(year, bool) or year < 1800 or year > 2199
            for year in years
        ):
            raise ContractValidationError("free_year_set must be server civil years")
        if len(set(years)) != len(years):
            raise ContractValidationError("free_year_set cannot contain duplicate years")

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> TimeLayerEntitlementV1:
        _require_exact_keys(payload, _ENTITLEMENT_OBJECT_KEYS, label="time-layer-entitlement/v1")
        if payload["schema_version"] != TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION:
            raise ContractValidationError("unsupported time-layer-entitlement schema_version")
        capability_id = payload["capability_id"]
        resolution = payload["resolution"]
        if capability_id not in {"bazi", "ziwei"}:
            raise ContractValidationError(f"unsupported capability_id: {capability_id!r}")
        if resolution not in _RESOLUTION_VALUES:
            raise ContractValidationError(f"unsupported entitlement resolution: {resolution!r}")
        if payload["free_boundary_layer_id"] != FREE_BOUNDARY_LAYER_ID:
            raise ContractValidationError("free_boundary_layer_id must be year")
        paid_layer_ids = payload["paid_layer_ids"]
        if not isinstance(paid_layer_ids, (list, tuple)) or tuple(paid_layer_ids) != (
            "month",
            "day",
            "hour",
        ):
            raise ContractValidationError("paid_layer_ids must be exactly [month, day, hour]")
        free_year_set = payload["free_year_set"]
        if not isinstance(free_year_set, (list, tuple)) or any(
            isinstance(year, bool) or not isinstance(year, int) for year in free_year_set
        ):
            raise ContractValidationError("free_year_set must be an array of integers")
        capability_payload = payload["capability"]
        if not isinstance(capability_payload, Mapping):
            raise ContractValidationError("capability must be an object")
        _require_exact_keys(
            capability_payload,
            _CAPABILITY_OBJECT_KEYS,
            label="time-layer-entitlement capability",
        )
        time_layers = capability_payload["time_layers"]
        if not isinstance(time_layers, (list, tuple)):
            raise ContractValidationError("capability.time_layers must be an array")
        layers = payload["layers"]
        if not isinstance(layers, (list, tuple)):
            raise ContractValidationError("layers must be an array")
        return cls(
            schema_version=TIME_LAYER_ENTITLEMENT_SCHEMA_VERSION,
            capability_id=cast(TimeLayerEntitlementCapabilityId, capability_id),
            resolution=cast(TimeLayerEntitlementResolution, resolution),
            free_boundary_layer_id=FREE_BOUNDARY_LAYER_ID,
            paid_layer_ids=PAID_TIME_LAYER_IDS,
            free_year_set=tuple(cast(int, year) for year in free_year_set),
            capability=tuple(
                TimeLayerCapabilitySnapshot.from_dict(cast(Mapping[str, object], item))
                for item in time_layers
            ),
            layers=tuple(
                TimeLayerEntitlementEntry.from_dict(cast(Mapping[str, object], item))
                for item in layers
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "resolution": self.resolution,
            "free_boundary_layer_id": self.free_boundary_layer_id,
            "paid_layer_ids": list(self.paid_layer_ids),
            "free_year_set": list(self.free_year_set),
            "capability": {"time_layers": [item.to_dict() for item in self.capability]},
            "layers": [item.to_dict() for item in self.layers],
        }


def _view_model_mapping(view_model: object) -> Mapping[str, object] | None:
    if isinstance(view_model, Mapping):
        return view_model
    dump = getattr(view_model, "model_dump", None)
    if callable(dump):
        payload = dump(mode="python")
        if isinstance(payload, Mapping):
            return cast(Mapping[str, object], payload)
    return None


def _core_facts_mapping(view_model: Mapping[str, object]) -> Mapping[str, object]:
    raw = view_model.get("core_facts")
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return raw
    dump = getattr(raw, "model_dump", None)
    if callable(dump):
        payload = dump(mode="python")
        if isinstance(payload, Mapping):
            return cast(Mapping[str, object], payload)
    raise ContractValidationError("core_facts must be an object or null")


def _capability_snapshots(
    view_model: Mapping[str, object],
) -> tuple[TimeLayerCapabilitySnapshot, ...]:
    raw_layers = view_model.get("time_layers")
    if raw_layers is None:
        return ()
    if not isinstance(raw_layers, (list, tuple)):
        raise ContractValidationError("time_layers must be an array")
    snapshots: list[TimeLayerCapabilitySnapshot] = []
    for item in raw_layers:
        if isinstance(item, Mapping):
            snapshots.append(TimeLayerCapabilitySnapshot.from_dict(item))
            continue
        dump = getattr(item, "model_dump", None)
        if not callable(dump):
            raise ContractValidationError("time_layers[] must be objects")
        payload = dump(mode="python")
        if not isinstance(payload, Mapping):
            raise ContractValidationError("time_layers[] must be objects")
        snapshots.append(TimeLayerCapabilitySnapshot.from_dict(payload))
    return tuple(snapshots)


def _fact_rows(core_facts: Mapping[str, object], key: str) -> tuple[object, ...] | None:
    raw = core_facts.get(key)
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)):
        raise ContractValidationError(f"{key} must be an array or null")
    return tuple(raw)


def _facts_present(rows: tuple[object, ...] | None) -> bool:
    return rows is not None and len(rows) > 0


def _free_year_set(rows: tuple[object, ...] | None) -> tuple[int, ...]:
    if rows is None:
        return ()
    years: list[int] = []
    seen: set[int] = set()
    for item in rows:
        if not isinstance(item, Mapping):
            dump = getattr(item, "model_dump", None)
            if not callable(dump):
                raise ContractValidationError("free year facts must be objects")
            payload = dump(mode="python")
            if not isinstance(payload, Mapping):
                raise ContractValidationError("free year facts must be objects")
            item = payload
        year = item.get("year")
        if isinstance(year, bool) or not isinstance(year, int) or year < 1800 or year > 2199:
            raise ContractValidationError("free year facts must carry a civil year")
        if year in seen:
            raise ContractValidationError("free_year_set cannot contain duplicate years")
        seen.add(year)
        years.append(year)
    return tuple(years)


def _layer_available(
    layer_id: TimeLayerEntitlementLayerId,
    snapshots: tuple[TimeLayerCapabilitySnapshot, ...],
    *,
    structural_present: bool,
) -> bool:
    if layer_id in {"luck_cycles", "major_limits"}:
        return structural_present
    for snapshot in snapshots:
        if snapshot.layer_id == layer_id:
            return snapshot.available
    return False


def project_time_layer_entitlement(
    view_model: object,
    *,
    resolution: TimeLayerEntitlementResolution,
) -> TimeLayerEntitlementV1 | None:
    """Project G1/G3 entitlement from a v1 chart ViewModel without mutating it."""

    if resolution not in _RESOLUTION_VALUES:
        raise ContractValidationError(f"unsupported entitlement resolution: {resolution!r}")
    payload = _view_model_mapping(view_model)
    if payload is None:
        return None
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or schema_version not in _SCHEMA_TO_CAPABILITY:
        return None
    capability_id = _SCHEMA_TO_CAPABILITY[schema_version]
    snapshots = _capability_snapshots(payload)
    core_facts = _core_facts_mapping(payload)
    year_rows = _fact_rows(core_facts, _YEAR_FACT_KEY_BY_CAPABILITY[capability_id])
    month_rows = _fact_rows(core_facts, _MONTH_FACT_KEY_BY_CAPABILITY[capability_id])
    day_rows = _fact_rows(core_facts, _DAY_FACT_KEY_BY_CAPABILITY[capability_id])
    hour_rows = _fact_rows(core_facts, "hour_layers")
    structural_key = "luck_cycles" if capability_id == "bazi" else "major_limits"
    structural_value = core_facts.get(structural_key)
    structural_present = structural_value is not None and structural_value != ()
    facts_by_layer: dict[TimeLayerEntitlementLayerId, bool] = {
        "life": True,
        "luck_cycles": structural_present if capability_id == "bazi" else False,
        "major_limits": structural_present if capability_id == "ziwei" else False,
        "year": _facts_present(year_rows),
        "month": _facts_present(month_rows),
        "day": _facts_present(day_rows),
        "hour": _facts_present(hour_rows),
    }
    free_ids = _FREE_LAYER_IDS_BY_CAPABILITY[capability_id]
    entries: list[TimeLayerEntitlementEntry] = []
    for layer_id in _LAYER_IDS_BY_CAPABILITY[capability_id]:
        tier: TimeLayerEntitlementTier = "free" if layer_id in free_ids else "paid"
        available = _layer_available(
            layer_id,
            snapshots,
            structural_present=structural_present,
        )
        access = _access_for_layer(
            tier=tier,
            available=available,
            facts_present=facts_by_layer[layer_id],
            resolution=resolution,
        )
        entries.append(
            TimeLayerEntitlementEntry(
                layer_id=layer_id,
                tier=tier,
                access=access,
                upgrade_cta=_upgrade_cta_for_access(access, tier=tier),
            )
        )
    return TimeLayerEntitlementV1(
        capability_id=capability_id,
        resolution=resolution,
        free_year_set=_free_year_set(year_rows),
        capability=snapshots,
        layers=tuple(entries),
    )
