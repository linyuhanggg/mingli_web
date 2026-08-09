from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class WindowRateLimiter:
    """Small per-owner sliding-window limiter for in-process API writes."""

    limit: int
    window_seconds: float
    _hits: dict[str, deque[float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("rate limit must be positive")
        if self.window_seconds <= 0:
            raise ValueError("rate window must be positive")

    def check(self, key: str) -> None:
        if not key:
            raise ValueError("rate limit key must be non-empty")
        now = time.monotonic()
        self._prune(key, now)
        hits = self._hits.setdefault(key, deque())
        if len(hits) >= self.limit:
            retry_after = self.retry_after(key)
            raise RateLimitExceededError(retry_after_seconds=retry_after)
        hits.append(now)

    def _prune(self, key: str, now: float) -> None:
        window_start = now - self.window_seconds
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] < window_start:
            hits.popleft()

    def retry_after(self, key: str) -> int:
        """Whole seconds until the oldest hit leaves the window."""
        now = time.monotonic()
        self._prune(key, now)
        hits = self._hits.get(key)
        if not hits or len(hits) < self.limit:
            return 0
        oldest = hits[0]
        remaining = self.window_seconds - (now - oldest)
        return max(1, math.ceil(remaining))

    def clear(self) -> None:
        self._hits.clear()


class RateLimitExceededError(RuntimeError):
    """The owner exceeded the configured write window."""

    def __init__(self, *, retry_after_seconds: int = 1) -> None:
        super().__init__("rate limit exceeded")
        self.retry_after_seconds = max(1, retry_after_seconds)
