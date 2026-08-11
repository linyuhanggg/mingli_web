from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

logger = logging.getLogger("mingli.alerts")

AlertKind = str


class AlertSink(Protocol):
    def emit(self, event: AlertEvent) -> None: ...


@dataclass(frozen=True, slots=True)
class AlertEvent:
    kind: AlertKind
    at: datetime
    job_id: str | None = None
    reading_version_id: str | None = None
    details: Mapping[str, Any] | None = None

    def to_log_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event": "ops_alert",
            "kind": self.kind,
            "at": self.at.isoformat(),
        }
        if self.job_id is not None:
            payload["job_id"] = self.job_id
        if self.reading_version_id is not None:
            payload["reading_version_id"] = self.reading_version_id
        if self.details:
            payload["details"] = dict(self.details)
        return payload


class NoopAlertSink:
    def emit(self, event: AlertEvent) -> None:
        del event


class LoggingAlertSink:
    """Local/staging sink: structured logs only, no secret values."""

    def emit(self, event: AlertEvent) -> None:
        logger.warning(
            json.dumps(
                event.to_log_payload(),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )


class RecordingAlertSink:
    """Test sink that records emitted events in memory."""

    def __init__(self) -> None:
        self.events: list[AlertEvent] = []

    def emit(self, event: AlertEvent) -> None:
        self.events.append(event)


def build_alert_sink(*, enabled: bool) -> AlertSink:
    if enabled:
        return LoggingAlertSink()
    return NoopAlertSink()


def as_optional_id(value: UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value)
