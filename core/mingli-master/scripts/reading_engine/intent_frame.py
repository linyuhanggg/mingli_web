"""Validated semantic intent supplied by the current caller model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class IntentFrameError(ValueError):
    """The caller supplied a malformed semantic intent frame."""


def _text(name: str, value: Any, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise IntentFrameError(f"intent.{name} must be non-empty text")
    return value.strip()


def _text_list(name: str, value: Any, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise IntentFrameError(f"intent.{name} must be a list of text values")
    normalized = tuple(_text(f"{name}[]", item) for item in value)
    if not allow_empty and not normalized:
        raise IntentFrameError(f"intent.{name} must not be empty")
    if len(set(normalized)) != len(normalized):
        raise IntentFrameError(f"intent.{name} contains duplicate values")
    return normalized  # type: ignore[return-value]


@dataclass(frozen=True)
class HorizonFrame:
    kind: str
    start: str | None = None
    end: str | None = None
    extensions: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: Any) -> "HorizonFrame":
        if not isinstance(payload, dict):
            raise IntentFrameError("intent.horizon must be an object")
        known = {"kind", "start", "end"}
        start = payload.get("start")
        end = payload.get("end")
        if start is not None and not isinstance(start, str):
            raise IntentFrameError("intent.horizon.start must be text or null")
        if end is not None and not isinstance(end, str):
            raise IntentFrameError("intent.horizon.end must be text or null")
        kind = str(_text("horizon.kind", payload.get("kind")))
        if kind == "instant" and (
            (start is None) != (end is None)
            or (start is not None and start != end)
        ):
            raise IntentFrameError(
                "intent.horizon instant boundaries must be absent or the same point"
            )
        return cls(
            kind=kind,
            start=start,
            end=end,
            extensions={key: value for key, value in payload.items() if key not in known},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "start": self.start,
            "end": self.end,
            **dict(self.extensions or {}),
        }


@dataclass(frozen=True)
class ContinuityFrame:
    reading_id: str | None
    same_subject: bool
    same_event: bool
    extensions: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: Any) -> "ContinuityFrame":
        if not isinstance(payload, dict):
            raise IntentFrameError("intent.continuity must be an object")
        reading_id = payload.get("reading_id")
        if reading_id is not None and not isinstance(reading_id, str):
            raise IntentFrameError("intent.continuity.reading_id must be text or null")
        for name in ("same_subject", "same_event"):
            if not isinstance(payload.get(name), bool):
                raise IntentFrameError(f"intent.continuity.{name} must be boolean")
        known = {"reading_id", "same_subject", "same_event"}
        return cls(
            reading_id=reading_id,
            same_subject=payload["same_subject"],
            same_event=payload["same_event"],
            extensions={key: value for key, value in payload.items() if key not in known},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reading_id": self.reading_id,
            "same_subject": self.same_subject,
            "same_event": self.same_event,
            **dict(self.extensions or {}),
        }


@dataclass(frozen=True)
class IntentFrame:
    subject_refs: tuple[str, ...]
    calculation_object: str
    question_dimensions: tuple[str, ...]
    horizon: HorizonFrame
    requested_method: str | None
    requested_granularity: str
    continuity: ContinuityFrame
    facts_present: tuple[str, ...]
    facts_corrected: tuple[str, ...]
    evidence_questions: tuple[str, ...]
    extensions: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: Any) -> "IntentFrame":
        if not isinstance(payload, dict) or not payload:
            raise IntentFrameError("intent must be a non-empty object")
        known = {
            "subject_refs",
            "calculation_object",
            "question_dimensions",
            "horizon",
            "requested_method",
            "requested_granularity",
            "continuity",
            "facts_present",
            "facts_corrected",
            "evidence_questions",
        }
        requested_method = _text(
            "requested_method",
            payload.get("requested_method"),
            optional=True,
        )
        return cls(
            subject_refs=_text_list("subject_refs", payload.get("subject_refs")),
            calculation_object=str(
                _text("calculation_object", payload.get("calculation_object"))
            ),
            question_dimensions=_text_list(
                "question_dimensions",
                payload.get("question_dimensions"),
                allow_empty=False,
            ),
            horizon=HorizonFrame.from_dict(payload.get("horizon")),
            requested_method=requested_method,
            requested_granularity=str(
                _text("requested_granularity", payload.get("requested_granularity"))
            ),
            continuity=ContinuityFrame.from_dict(payload.get("continuity")),
            facts_present=_text_list("facts_present", payload.get("facts_present")),
            facts_corrected=_text_list(
                "facts_corrected", payload.get("facts_corrected")
            ),
            evidence_questions=_text_list(
                "evidence_questions", payload.get("evidence_questions")
            ),
            extensions={key: value for key, value in payload.items() if key not in known},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_refs": list(self.subject_refs),
            "calculation_object": self.calculation_object,
            "question_dimensions": list(self.question_dimensions),
            "horizon": self.horizon.to_dict(),
            "requested_method": self.requested_method,
            "requested_granularity": self.requested_granularity,
            "continuity": self.continuity.to_dict(),
            "facts_present": list(self.facts_present),
            "facts_corrected": list(self.facts_corrected),
            "evidence_questions": list(self.evidence_questions),
            **dict(self.extensions or {}),
        }


def parse_intent_frame(payload: Any) -> IntentFrame:
    return IntentFrame.from_dict(payload)


__all__ = [
    "ContinuityFrame",
    "HorizonFrame",
    "IntentFrame",
    "IntentFrameError",
    "parse_intent_frame",
]
