"""Mechanical validation for caller-owned Mingli v4 requests."""

from __future__ import annotations

from typing import Any, Iterable

from .contracts import ReadingRequest
from .intent_frame import IntentFrameError, parse_intent_frame


ACTIONS = frozenset({"new", "continue", "recast", "correct", "resume"})


class RequestContractError(ValueError):
    """A caller supplied an invalid v4 request shape."""


def _is_private_id(value: str | None) -> bool:
    if not isinstance(value, str) or len(value) != 32:
        return False
    return all(character in "0123456789abcdef" for character in value)


def _require_object(name: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise RequestContractError(f"{name} must be an object")


def _validate_optional_text(name: str, value: Any) -> None:
    if value is not None and not isinstance(value, str):
        raise RequestContractError(f"{name} must be text or null")


def validate_request_contract(
    request: ReadingRequest,
    *,
    known_capability_ids: Iterable[str] | None = None,
) -> ReadingRequest:
    """Validate v4 structure without interpreting ``request.query``.

    Capability membership is validated against the loaded catalog when the
    caller injects ``known_capability_ids``; the contract itself carries no
    fixed provider set.
    """

    if not isinstance(request, ReadingRequest):
        raise RequestContractError("request must be a ReadingRequest")
    if not isinstance(request.query, str) or not request.query.strip():
        raise RequestContractError("query must be non-empty text")
    if request.action is None:
        raise RequestContractError("action is required for a production V4 request")
    if request.action not in ACTIONS:
        raise RequestContractError("unsupported reading action")
    if request.system_hint is not None:
        raise RequestContractError("system_hint is reserved for v3 import")

    for name in (
        "reference_datetime",
        "timezone",
        "location",
        "event_datetime",
        "transcribed_chart",
    ):
        _validate_optional_text(name, getattr(request, name))
    for name in ("birth_data", "chart_data", "goal", "intent", "metadata"):
        _require_object(name, getattr(request, name))
    try:
        parse_intent_frame(request.intent)
    except IntentFrameError as exc:
        raise RequestContractError(str(exc)) from exc
    if not isinstance(request.image_supplied, bool):
        raise RequestContractError("image_supplied must be boolean")

    if request.reading_id is not None and not _is_private_id(request.reading_id):
        raise RequestContractError("invalid reading_id")
    if request.intake_id is not None and not _is_private_id(request.intake_id):
        raise RequestContractError("invalid intake_id")

    action = request.action
    if action in {"new", "recast"}:
        if (
            request.system is not None
            and known_capability_ids is not None
            and request.system not in set(known_capability_ids)
        ):
            raise RequestContractError(f"{action} has an unsupported system")
        if request.intake_id is not None:
            raise RequestContractError(f"{action} cannot use intake_id")
        if action == "new" and request.reading_id is not None:
            raise RequestContractError("new cannot use reading_id")
        if action == "recast" and request.reading_id is None:
            raise RequestContractError("recast requires reading_id")
    elif action in {"continue", "correct"}:
        if request.reading_id is None:
            raise RequestContractError(f"{action} requires reading_id")
        if request.intake_id is not None:
            raise RequestContractError(f"{action} cannot use intake_id")
        if request.system is not None:
            raise RequestContractError(f"{action} inherits the prior system")
    elif action == "resume":
        if request.intake_id is None:
            raise RequestContractError("resume requires intake_id")
        if request.reading_id is not None:
            raise RequestContractError("resume cannot use reading_id")
        if request.system is not None:
            raise RequestContractError("resume inherits the pending system")

    return request


__all__ = [
    "ACTIONS",
    "RequestContractError",
    "validate_request_contract",
]
