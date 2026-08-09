from app.api.errors import ApiProblem
from app.readings.rate_limit import RateLimitExceededError, WindowRateLimiter


def check_rate_limiter(
    *,
    limiter: WindowRateLimiter,
    key: str,
    title: str,
) -> None:
    """Check a per-owner write limiter and surface a Retry-After problem."""
    try:
        limiter.check(key)
    except RateLimitExceededError as error:
        raise ApiProblem(
            status=429,
            title=title,
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from error
