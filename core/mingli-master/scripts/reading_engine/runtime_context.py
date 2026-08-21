"""Generic runtime dependencies injected into the reading deep module.

The context carries a clock value, a default timezone name and a read-only
subject-fact store. Providers read their own default subject data from here;
no host environment variable and no gateway parameter is ever consulted by
generic code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class RuntimeContext:
    now_iso: str | None = None
    default_timezone_name: str | None = None
    subject_profiles: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        frozen = MappingProxyType(
            {
                str(subject_ref): MappingProxyType(dict(profile))
                for subject_ref, profile in dict(self.subject_profiles).items()
            }
        )
        object.__setattr__(self, "subject_profiles", frozen)

    def profile_for(self, subject_ref: str) -> Mapping[str, Any] | None:
        return self.subject_profiles.get(subject_ref)


def host_timezone_name() -> str | None:
    """Resolve the local zone once at assembly time; providers never guess."""

    candidates: list[str] = []
    environment_name = os.environ.get("TZ", "").strip().removeprefix(":")
    if environment_name:
        candidates.append(environment_name)
    try:
        localtime = Path("/etc/localtime").resolve(strict=True)
        parts = localtime.parts
        marker = parts.index("zoneinfo")
        candidates.append("/".join(parts[marker + 1 :]))
    except (OSError, ValueError):
        pass
    for candidate in candidates:
        try:
            ZoneInfo(candidate)
        except ZoneInfoNotFoundError:
            continue
        return candidate
    return None


def build_runtime_context(
    *,
    now_iso: str | None = None,
    default_timezone_name: str | None = None,
    subject_profiles: Mapping[str, Mapping[str, Any]] | None = None,
) -> RuntimeContext:
    return RuntimeContext(
        now_iso=now_iso,
        default_timezone_name=default_timezone_name or host_timezone_name(),
        subject_profiles=dict(subject_profiles or {}),
    )


__all__ = ["RuntimeContext", "build_runtime_context", "host_timezone_name"]
