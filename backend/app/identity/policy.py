from typing import Final

CURRENT_POLICY_VERSION: Final = "development-preview-v0.1"
CURRENT_POLICY_KEYS: Final = frozenset({"privacy", "terms"})


class InvalidPolicyVersion(ValueError):
    """The client submitted a policy version that is not currently published."""


class InvalidPolicyKey(ValueError):
    """The client submitted a policy document outside the supported policy set."""


def require_current_policy_version(policy_version: str) -> str:
    normalized = policy_version.strip()
    if normalized != CURRENT_POLICY_VERSION:
        raise InvalidPolicyVersion("policy version is not current")
    return normalized


def require_policy_key(policy_key: str) -> str:
    normalized = policy_key.strip()
    if normalized not in CURRENT_POLICY_KEYS:
        raise InvalidPolicyKey("policy key is not supported")
    return normalized
