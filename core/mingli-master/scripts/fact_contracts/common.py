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

from typing import Any


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
