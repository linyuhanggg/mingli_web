from datetime import UTC, datetime, timedelta

import pytest
from app.referrals.policy import (
    ReferralError,
    ReferralPolicy,
    ReferralState,
)


def policy() -> ReferralPolicy:
    now = datetime(2026, 8, 13, tzinfo=UTC)
    return ReferralPolicy(
        campaign_id="campaign-v1",
        state=ReferralState.ACTIVE,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1),
        total_limit=1,
        per_inviter_limit=1,
        now=now,
    )


def test_last_valid_temporary_attribution_locks_once_and_reserves_one_reward() -> None:
    referral = policy()
    referral.record_temporary_attribution(code="old", inviter_user_id="u1")
    referral.record_temporary_attribution(code="new", inviter_user_id="u2")
    locked = referral.lock_attribution(
        referred_user_id="u3",
        inviter_user_id="u2",
        code="new",
    )

    assert locked.code == "new"
    reservation = referral.reserve_reward(referred_user_id="u3", inviter_user_id="u2")
    assert reservation.status == "reserved"
    referral.commit_reward(reservation.reservation_id)
    assert referral.snapshot().committed == 1


def test_referral_rejects_self_referral_and_second_lock() -> None:
    referral = policy()
    referral.record_temporary_attribution(code="code", inviter_user_id="u1")

    with pytest.raises(ReferralError, match="self referral"):
        referral.lock_attribution(referred_user_id="u1", inviter_user_id="u1", code="code")

    referral.lock_attribution(referred_user_id="u2", inviter_user_id="u1", code="code")
    with pytest.raises(ReferralError, match="already locked"):
        referral.lock_attribution(referred_user_id="u2", inviter_user_id="u1", code="code")


def test_failed_reward_releases_reservation_and_limit_is_enforced() -> None:
    referral = policy()
    referral.record_temporary_attribution(code="a", inviter_user_id="u1")
    referral.lock_attribution(referred_user_id="u2", inviter_user_id="u1", code="a")
    first = referral.reserve_reward(referred_user_id="u2", inviter_user_id="u1")

    with pytest.raises(ReferralError, match="total limit"):
        referral.reserve_reward(referred_user_id="u2", inviter_user_id="u1")

    referral.release_reward(first.reservation_id)
    second = referral.reserve_reward(referred_user_id="u2", inviter_user_id="u1")
    assert second.status == "reserved"
