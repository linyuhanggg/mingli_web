from app.api.errors import ApiProblem
from app.readings.rate_limit import RateLimitExceededError, WindowRateLimiter

_PROBLEM_TYPE_PREFIX = "urn:mingli:problem:"


def check_rate_limiter(
    *,
    limiter: WindowRateLimiter,
    key: str,
    title: str,
    code: str | None = None,
    owner_kind: str | None = None,
    limit_scope: str | None = None,
) -> None:
    """Check a per-owner write limiter and surface a Retry-After problem."""
    try:
        limiter.check(key)
    except RateLimitExceededError as error:
        problem_code = code or "rate_limit_exceeded"
        extensions: dict[str, object] = {
            "limit": limiter.limit,
            "remaining": 0,
        }
        if owner_kind is not None:
            extensions["owner_kind"] = owner_kind
        if limit_scope is not None:
            extensions["limit_scope"] = limit_scope
        raise ApiProblem(
            status=429,
            title=title,
            problem_type=f"{_PROBLEM_TYPE_PREFIX}{problem_code}",
            detail=title,
            code=problem_code,
            headers={"Retry-After": str(error.retry_after_seconds)},
            extensions=extensions,
        ) from error
