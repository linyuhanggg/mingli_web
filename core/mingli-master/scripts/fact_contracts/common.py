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


_FORBIDDEN_THIRD_PARTY_RAW_KEYS = frozenset(
    {
        "candidate_oss_output",
        "engine_raw",
        "engine_raw_json",
        "iztro_raw",
        "oss_raw",
        "raw_engine_output",
        "third_party_raw",
        "third_party_raw_object",
        "third_party_runtime_object",
    }
)


class CanonicalFactsError(ValueError):
    """An art-specific fact snapshot is not safe or provenance-complete."""


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


def canonical_json_snapshot(payload: Any) -> dict[str, Any]:
    """Return a detached JSON object or fail closed on private/raw values.

    Canonical Facts cross the Provider boundary, so only exact JSON runtime
    types are admitted.  In particular, engine classes, Mapping subclasses,
    exception objects and explicitly raw third-party containers cannot be
    smuggled into a public calculation record.
    """

    def clone(value: Any, path: str) -> Any:
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
            return [clone(item, f"{path}/{index}") for index, item in enumerate(value)]
        if value_type is dict:
            result: dict[str, Any] = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise CanonicalFactsError(
                        f"canonical facts contain a non-text key at {path}"
                    )
                if key in _FORBIDDEN_THIRD_PARTY_RAW_KEYS:
                    raise CanonicalFactsError(
                        "third-party raw output cannot enter Canonical Facts"
                    )
                result[key] = clone(item, f"{path}/{key}")
            return result
        raise CanonicalFactsError(
            f"canonical facts contain a private runtime value at {path}"
        )

    snapshot = clone(payload, "")
    if type(snapshot) is not dict:
        raise CanonicalFactsError("canonical facts must be a JSON object")
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
