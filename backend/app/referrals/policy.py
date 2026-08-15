from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4


class ReferralState(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


ReferralStateValue = Literal["draft", "scheduled", "active", "paused", "ended"]


class ReferralError(ValueError):
    """The referral campaign state or attribution is invalid."""


@dataclass(frozen=True, slots=True)
class TemporaryAttribution:
    code: str
    inviter_user_id: str
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class LockedAttribution:
    referred_user_id: str
    inviter_user_id: str
    code: str
    locked_at: datetime


@dataclass(frozen=True, slots=True)
class RewardReservation:
    reservation_id: str
    referred_user_id: str
    inviter_user_id: str
    status: Literal["reserved", "released", "committed"]


@dataclass(frozen=True, slots=True)
class ReferralSnapshot:
    reserved: int
    committed: int


class ReferralPolicy:
    """Deterministic campaign rules; persistence is supplied by the API layer."""

    def __init__(
        self,
        *,
        campaign_id: str,
        state: ReferralState | ReferralStateValue,
        starts_at: datetime,
        ends_at: datetime,
        total_limit: int,
        per_inviter_limit: int,
        now: datetime,
    ) -> None:
        if total_limit <= 0 or per_inviter_limit <= 0:
            raise ReferralError("limits must be positive")
        self.campaign_id = campaign_id
        self.state = state
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.total_limit = total_limit
        self.per_inviter_limit = per_inviter_limit
        self.now = now
        self._temporary: dict[str, TemporaryAttribution] = {}
        self._latest_code: str | None = None
        self._locked: dict[str, LockedAttribution] = {}
        self._reservations: dict[str, RewardReservation] = {}

    def _ensure_active(self) -> None:
        if self.state != ReferralState.ACTIVE or not self.starts_at <= self.now < self.ends_at:
            raise ReferralError("campaign is not active")

    def record_temporary_attribution(
        self,
        *,
        code: str,
        inviter_user_id: str,
    ) -> TemporaryAttribution:
        self._ensure_active()
        if not code or not inviter_user_id:
            raise ReferralError("invitation code and inviter are required")
        attribution = TemporaryAttribution(code, inviter_user_id, self.now)
        self._temporary[code] = attribution
        self._latest_code = code
        return attribution

    def lock_attribution(
        self,
        *,
        referred_user_id: str,
        inviter_user_id: str,
        code: str,
    ) -> LockedAttribution:
        self._ensure_active()
        if referred_user_id == inviter_user_id:
            raise ReferralError("self referral is not allowed")
        if referred_user_id in self._locked:
            raise ReferralError("attribution already locked")
        temporary = self._temporary.get(code)
        if (
            temporary is None
            or code != self._latest_code
            or temporary.inviter_user_id != inviter_user_id
        ):
            raise ReferralError("invitation attribution is not valid")
        locked = LockedAttribution(referred_user_id, inviter_user_id, code, self.now)
        self._locked[referred_user_id] = locked
        return locked

    def reserve_reward(self, *, referred_user_id: str, inviter_user_id: str) -> RewardReservation:
        self._ensure_active()
        locked = self._locked.get(referred_user_id)
        if locked is None or locked.inviter_user_id != inviter_user_id:
            raise ReferralError("locked attribution is required")
        snapshot = self.snapshot()
        if snapshot.reserved + snapshot.committed >= self.total_limit:
            raise ReferralError("campaign total limit reached")
        inviter_count = sum(
            1
            for reservation in self._reservations.values()
            if reservation.inviter_user_id == inviter_user_id
            and reservation.status in {"reserved", "committed"}
        )
        if inviter_count >= self.per_inviter_limit:
            raise ReferralError("inviter limit reached")
        if any(
            reservation.referred_user_id == referred_user_id
            and reservation.status in {"reserved", "committed"}
            for reservation in self._reservations.values()
        ):
            raise ReferralError("referred user already has a reward")
        reservation = RewardReservation(uuid4().hex, referred_user_id, inviter_user_id, "reserved")
        self._reservations[reservation.reservation_id] = reservation
        return reservation

    def release_reward(self, reservation_id: str) -> None:
        reservation = self._reservations.get(reservation_id)
        if reservation is None or reservation.status != "reserved":
            raise ReferralError("only a reserved reward can be released")
        self._reservations[reservation_id] = RewardReservation(
            reservation.reservation_id,
            reservation.referred_user_id,
            reservation.inviter_user_id,
            "released",
        )

    def commit_reward(self, reservation_id: str) -> None:
        reservation = self._reservations.get(reservation_id)
        if reservation is None or reservation.status != "reserved":
            raise ReferralError("only a reserved reward can be committed")
        self._reservations[reservation_id] = RewardReservation(
            reservation.reservation_id,
            reservation.referred_user_id,
            reservation.inviter_user_id,
            "committed",
        )

    def snapshot(self) -> ReferralSnapshot:
        return ReferralSnapshot(
            reserved=sum(r.status == "reserved" for r in self._reservations.values()),
            committed=sum(r.status == "committed" for r in self._reservations.values()),
        )
