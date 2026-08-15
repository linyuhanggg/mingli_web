from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commerce.models import Order, PaymentAttempt, ProductVersion
from app.commerce.service import CommerceService
from app.identity.models import User
from app.identity.policy import require_current_policy_version
from app.referrals.models import (
    ReferralAttribution,
    ReferralCampaignVersion,
    ReferralCode,
    ReferralParticipationRestriction,
    ReferralRefundConfirmation,
    ReferralRewardReservation,
    ReferralRewardSlot,
    ReferralTemporaryAttribution,
)
from app.referrals.policy import ReferralError, ReferralState

RewardSlotKey = Literal["inviter_reward", "invitee_reward"]
_REWARD_SLOT_KEYS = frozenset({"inviter_reward", "invitee_reward"})


def _visitor_hash(visitor_key: str) -> str:
    if not visitor_key.strip():
        raise ReferralError("visitor key is required")
    return hashlib.sha256(visitor_key.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class ReferralService:
    """Persistent referral state machine with first-purchase reward facts."""

    _ALLOWED_STATE_TRANSITIONS: dict[ReferralState, frozenset[ReferralState]] = {
        ReferralState.DRAFT: frozenset(
            {ReferralState.SCHEDULED, ReferralState.ACTIVE, ReferralState.ENDED}
        ),
        ReferralState.SCHEDULED: frozenset(
            {ReferralState.ACTIVE, ReferralState.PAUSED, ReferralState.ENDED}
        ),
        ReferralState.ACTIVE: frozenset({ReferralState.PAUSED, ReferralState.ENDED}),
        ReferralState.PAUSED: frozenset({ReferralState.ACTIVE, ReferralState.ENDED}),
        ReferralState.ENDED: frozenset(),
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.commerce = CommerceService(session)

    async def create_campaign(
        self,
        *,
        campaign_key: str,
        version: str,
        starts_at: datetime,
        ends_at: datetime | None,
        total_limit: int | None = None,
        per_inviter_limit: int = 10,
        reward_quantity: int = 1,
        reward_window_seconds: int = 90 * 86400,
    ) -> ReferralCampaignVersion:
        if not campaign_key.strip() or not version.strip() or per_inviter_limit < 1:
            raise ReferralError("campaign identity and limits are required")
        if total_limit is None or total_limit < 1:
            raise ReferralError("campaign total limit is required")
        if ends_at is not None and _as_utc(ends_at) <= _as_utc(starts_at):
            raise ReferralError("campaign window is invalid")
        if reward_quantity < 1 or reward_window_seconds < 1:
            raise ReferralError("reward values must be positive")
        existing = await self.session.scalar(
            select(ReferralCampaignVersion).where(
                ReferralCampaignVersion.campaign_key == campaign_key,
                ReferralCampaignVersion.version == version,
            )
        )
        if existing is not None:
            raise ReferralError("campaign version already exists")
        campaign = ReferralCampaignVersion(
            campaign_key=campaign_key,
            version=version,
            state=ReferralState.DRAFT,
            starts_at=starts_at,
            ends_at=ends_at,
            total_limit=total_limit,
            per_inviter_limit=per_inviter_limit,
            reward_quantity=reward_quantity,
            reward_window_seconds=reward_window_seconds,
        )
        self.session.add(campaign)
        await self.session.flush()
        return campaign

    async def configure_reward_slot(
        self,
        *,
        campaign_id: UUID,
        product_version_id: UUID,
        slot: RewardSlotKey,
        total_limit: int,
        quantity: int,
        enabled: bool = True,
    ) -> ReferralRewardSlot:
        """Add one product-specific reward rule before a campaign is scheduled."""
        if slot not in _REWARD_SLOT_KEYS:
            raise ReferralError("unsupported reward slot")
        if total_limit < 1 or quantity < 1:
            raise ReferralError("reward slot limits must be positive")
        campaign = await self.session.get(ReferralCampaignVersion, campaign_id)
        product = await self.session.get(ProductVersion, product_version_id)
        if campaign is None:
            raise ReferralError("campaign not found")
        if campaign.state != ReferralState.DRAFT:
            raise ReferralError("campaign reward rules are immutable")
        if product is None or product.status != "active":
            raise ReferralError("product version is not active")
        existing = await self.session.scalar(
            select(ReferralRewardSlot).where(
                ReferralRewardSlot.campaign_version_id == campaign.id,
                ReferralRewardSlot.product_version_id == product.id,
                ReferralRewardSlot.slot_key == slot,
            )
        )
        if existing is not None:
            raise ReferralError("reward slot already exists")
        reward_slot = ReferralRewardSlot(
            campaign_version_id=campaign.id,
            product_version_id=product.id,
            slot_key=slot,
            enabled=enabled,
            total_limit=total_limit,
            quantity=quantity,
        )
        self.session.add(reward_slot)
        await self.session.flush()
        return reward_slot

    async def set_campaign_state(
        self,
        campaign_id: UUID,
        state: ReferralState,
    ) -> ReferralCampaignVersion:
        campaign = await self.session.get(ReferralCampaignVersion, campaign_id)
        if campaign is None:
            raise ReferralError("campaign not found")
        current_state = ReferralState(campaign.state)
        if current_state == state:
            return campaign
        if state not in self._ALLOWED_STATE_TRANSITIONS[current_state]:
            raise ReferralError("invalid campaign state transition")
        if state is ReferralState.ACTIVE and campaign.starts_at >= (
            campaign.ends_at or datetime.max.replace(tzinfo=UTC)
        ):
            raise ReferralError("campaign window is invalid")
        campaign.state = state
        await self.session.flush()
        return campaign

    async def create_code(
        self,
        *,
        campaign_id: UUID,
        code: str,
        inviter_user_id: UUID,
    ) -> ReferralCode:
        campaign = await self.session.get(ReferralCampaignVersion, campaign_id)
        normalized_code = code.strip()
        if campaign is None:
            raise ReferralError("campaign not found")
        if not normalized_code:
            raise ReferralError("campaign and code are required")
        if campaign.state == ReferralState.ENDED:
            raise ReferralError("ended campaign cannot receive codes")
        inviter = await self.session.get(User, inviter_user_id)
        if inviter is None:
            raise ReferralError("inviter user not found")
        if inviter.status != "active":
            raise ReferralError("inviter user is not active")
        existing = await self.session.scalar(
            select(ReferralCode).where(ReferralCode.code == normalized_code)
        )
        if existing is not None:
            raise ReferralError("invitation code already exists")
        item = ReferralCode(
            campaign_version_id=campaign.id,
            code=normalized_code,
            inviter_user_id=inviter_user_id,
            status="active",
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def record_temporary_attribution(
        self,
        *,
        campaign_id: UUID,
        code: str,
        visitor_key: str,
        now: datetime | None = None,
    ) -> ReferralTemporaryAttribution:
        current = now or datetime.now(UTC)
        campaign, referral_code = await self._active_campaign_and_code(campaign_id, code, current)
        visitor_hash = _visitor_hash(visitor_key)
        existing = await self.session.scalar(
            select(ReferralTemporaryAttribution).where(
                ReferralTemporaryAttribution.campaign_version_id == campaign.id,
                ReferralTemporaryAttribution.visitor_key_hash == visitor_hash,
            )
        )
        expires_at = current + timedelta(days=30)
        if campaign.ends_at is not None:
            expires_at = min(expires_at, _as_utc(campaign.ends_at))
        if existing is None:
            existing = ReferralTemporaryAttribution(
                campaign_version_id=campaign.id,
                code_id=referral_code.id,
                visitor_key_hash=visitor_hash,
                inviter_user_id=referral_code.inviter_user_id,
                expires_at=expires_at,
                last_seen_at=current,
            )
            self.session.add(existing)
        else:
            existing.code_id = referral_code.id
            existing.inviter_user_id = referral_code.inviter_user_id
            existing.expires_at = expires_at
            existing.last_seen_at = current
        await self.session.flush()
        return existing

    async def lock_latest_attribution(
        self,
        *,
        visitor_key: str,
        referred_user_id: UUID,
        now: datetime | None = None,
    ) -> ReferralAttribution | None:
        """Lock the last still-valid invite observed for one guest session."""
        current = now or datetime.now(UTC)
        temporary = await self.session.scalar(
            select(ReferralTemporaryAttribution)
            .join(
                ReferralCampaignVersion,
                ReferralCampaignVersion.id
                == ReferralTemporaryAttribution.campaign_version_id,
            )
            .where(
                ReferralTemporaryAttribution.visitor_key_hash == _visitor_hash(visitor_key),
                ReferralTemporaryAttribution.expires_at > current,
                ReferralCampaignVersion.state == ReferralState.ACTIVE,
                ReferralCampaignVersion.starts_at <= current,
                (
                    ReferralCampaignVersion.ends_at.is_(None)
                    | (ReferralCampaignVersion.ends_at > current)
                ),
            )
            .order_by(
                desc(ReferralTemporaryAttribution.last_seen_at),
                desc(ReferralTemporaryAttribution.id),
            )
        )
        if temporary is None:
            return None
        code = await self.session.get(ReferralCode, temporary.code_id)
        if code is None or code.status != "active":
            return None
        return await self.lock_attribution(
            campaign_id=temporary.campaign_version_id,
            code=code.code,
            visitor_key=visitor_key,
            referred_user_id=referred_user_id,
            now=current,
        )

    async def clear_temporary_attributions(self, *, visitor_key: str) -> None:
        """Clear all uncommitted invite choices for one guest session."""
        await self.session.execute(
            delete(ReferralTemporaryAttribution).where(
                ReferralTemporaryAttribution.visitor_key_hash == _visitor_hash(visitor_key)
            )
        )
        await self.session.flush()

    async def lock_attribution(
        self,
        *,
        campaign_id: UUID,
        code: str,
        visitor_key: str,
        referred_user_id: UUID,
        now: datetime | None = None,
    ) -> ReferralAttribution:
        current = now or datetime.now(UTC)
        campaign, referral_code = await self._active_campaign_and_code(campaign_id, code, current)
        await self._ensure_participation_allowed(referred_user_id)
        await self._ensure_participation_allowed(referral_code.inviter_user_id)
        if referral_code.inviter_user_id == referred_user_id:
            raise ReferralError("self referral is not allowed")
        existing = await self.session.scalar(
            select(ReferralAttribution).where(
                ReferralAttribution.referred_user_id == referred_user_id
            )
        )
        if existing is not None:
            raise ReferralError("attribution already locked")
        temporary = await self.session.scalar(
            select(ReferralTemporaryAttribution).where(
                ReferralTemporaryAttribution.campaign_version_id == campaign.id,
                ReferralTemporaryAttribution.code_id == referral_code.id,
                ReferralTemporaryAttribution.visitor_key_hash == _visitor_hash(visitor_key),
                ReferralTemporaryAttribution.expires_at > current,
            )
        )
        if temporary is None:
            raise ReferralError("invitation attribution is not valid")
        attribution = ReferralAttribution(
            campaign_version_id=campaign.id,
            code_id=referral_code.id,
            referred_user_id=referred_user_id,
            inviter_user_id=referral_code.inviter_user_id,
            locked_at=current,
            status="locked",
        )
        self.session.add(attribution)
        await self.session.flush()
        return attribution

    async def reserve_reward(
        self,
        *,
        attribution_id: UUID,
        product_version_id: UUID,
        payment_attempt_id: UUID | None = None,
        now: datetime | None = None,
    ) -> ReferralRewardReservation:
        current = now or datetime.now(UTC)
        attribution = await self.session.get(ReferralAttribution, attribution_id)
        if attribution is None or attribution.status != "locked":
            raise ReferralError("locked attribution is required")
        await self._ensure_participation_allowed(attribution.referred_user_id)
        await self._ensure_participation_allowed(attribution.inviter_user_id)
        campaign = await self.session.scalar(
            select(ReferralCampaignVersion)
            .where(ReferralCampaignVersion.id == attribution.campaign_version_id)
            .with_for_update()
        )
        if campaign is None or not self._campaign_active(campaign, current):
            raise ReferralError("campaign is not active")
        existing = await self.session.scalar(
            select(ReferralRewardReservation).where(
                ReferralRewardReservation.campaign_version_id == campaign.id,
                ReferralRewardReservation.referred_user_id == attribution.referred_user_id,
            )
        )
        if existing is not None:
            if existing.product_version_id not in {None, product_version_id}:
                raise ReferralError("referred user already has a reward")
            if payment_attempt_id is not None and existing.payment_attempt_id not in {
                None,
                payment_attempt_id,
            }:
                raise ReferralError("reward is bound to another payment attempt")
            if existing.status in {"reserved", "committed"}:
                return existing
            if existing.status != "released":
                raise ReferralError("referred user already has a reward")
            if payment_attempt_id is not None:
                await self._validate_payment_attempt(
                    payment_attempt_id=payment_attempt_id,
                    referred_user_id=attribution.referred_user_id,
                    product_version_id=product_version_id,
                )
            existing.product_version_id = product_version_id
            existing.payment_attempt_id = payment_attempt_id
            existing.status = "reserved"
            existing.reserved_at = current
            existing.committed_at = None
            await self.session.flush()
            return existing
        reward_slot = await self.session.scalar(
            select(ReferralRewardSlot)
            .where(
                ReferralRewardSlot.campaign_version_id == campaign.id,
                ReferralRewardSlot.product_version_id == product_version_id,
                ReferralRewardSlot.slot_key == "inviter_reward",
                ReferralRewardSlot.enabled.is_(True),
            )
            .with_for_update()
        )
        if reward_slot is None:
            raise ReferralError("product is not eligible for referral reward")
        if payment_attempt_id is not None:
            await self._validate_payment_attempt(
                payment_attempt_id=payment_attempt_id,
                referred_user_id=attribution.referred_user_id,
                product_version_id=product_version_id,
            )
        count = await self.session.scalar(
            select(func.count()).select_from(ReferralRewardReservation).where(
                ReferralRewardReservation.campaign_version_id == campaign.id,
                ReferralRewardReservation.status.in_(["reserved", "committed"]),
            )
        )
        if campaign.total_limit is not None and int(count or 0) >= campaign.total_limit:
            raise ReferralError("campaign total limit reached")
        product_count = await self.session.scalar(
            select(func.count()).select_from(ReferralRewardReservation).where(
                ReferralRewardReservation.campaign_version_id == campaign.id,
                ReferralRewardReservation.product_version_id == product_version_id,
                ReferralRewardReservation.status.in_(
                    ["reserved", "committed"]
                ),
            )
        )
        if int(product_count or 0) >= reward_slot.total_limit:
            raise ReferralError("product reward limit reached")
        inviter_count = await self.session.scalar(
            select(func.count()).select_from(ReferralRewardReservation).where(
                ReferralRewardReservation.campaign_version_id == campaign.id,
                ReferralRewardReservation.inviter_user_id == attribution.inviter_user_id,
                ReferralRewardReservation.status.in_(["reserved", "committed"]),
            )
        )
        if int(inviter_count or 0) >= campaign.per_inviter_limit:
            raise ReferralError("inviter limit reached")
        reservation = ReferralRewardReservation(
            campaign_version_id=campaign.id,
            attribution_id=attribution.id,
            referred_user_id=attribution.referred_user_id,
            inviter_user_id=attribution.inviter_user_id,
            product_version_id=product_version_id,
            payment_attempt_id=payment_attempt_id,
            quantity=reward_slot.quantity,
            status="reserved",
            reserved_at=current,
        )
        self.session.add(reservation)
        await self.session.flush()
        return reservation

    async def restrict_future_participation(
        self,
        *,
        user_id: UUID,
        source_appeal_id: UUID,
        reason: str,
        created_by_staff_user_id: UUID,
    ) -> ReferralParticipationRestriction:
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ReferralError("participation restriction reason is required")
        existing = await self.session.scalar(
            select(ReferralParticipationRestriction).where(
                ReferralParticipationRestriction.user_id == user_id
            )
        )
        if existing is not None:
            if existing.source_appeal_id == source_appeal_id:
                return existing
            raise ReferralError("user already has a referral participation restriction")
        restriction = ReferralParticipationRestriction(
            user_id=user_id,
            source_appeal_id=source_appeal_id,
            reason=normalized_reason,
            created_by_staff_user_id=created_by_staff_user_id,
        )
        self.session.add(restriction)
        await self.session.flush()
        return restriction

    async def reserve_reward_for_payment(
        self,
        *,
        attribution_id: UUID,
        payment_attempt_id: UUID,
        now: datetime | None = None,
    ) -> ReferralRewardReservation:
        """Atomically occupy the matching product slot for a pending payment."""
        attempt = await self.session.get(PaymentAttempt, payment_attempt_id)
        if attempt is None:
            raise ReferralError("payment attempt not found")
        order = await self.session.get(Order, attempt.order_id)
        if order is None:
            raise ReferralError("payment order not found")
        return await self.reserve_reward(
            attribution_id=attribution_id,
            product_version_id=order.product_version_id,
            payment_attempt_id=payment_attempt_id,
            now=now,
        )

    async def release_reward(self, reservation_id: UUID) -> ReferralRewardReservation:
        reservation = await self._reservation(reservation_id)
        if reservation.status != "reserved":
            raise ReferralError("only a reserved reward can be released")
        reservation.status = "released"
        await self.session.flush()
        return reservation

    async def release_reward_for_payment(self, *, payment_attempt_id: UUID) -> int:
        """Release every still-open reward occupation for a failed payment attempt."""
        reservations = list(
            await self.session.scalars(
                select(ReferralRewardReservation).where(
                    ReferralRewardReservation.payment_attempt_id == payment_attempt_id,
                    ReferralRewardReservation.status == "reserved",
                )
            )
        )
        for reservation in reservations:
            reservation.status = "released"
        await self.session.flush()
        return len(reservations)

    async def confirm_refund(
        self,
        *,
        payment_id: UUID,
        user_id: UUID,
        policy_version: str,
        actor_session_id: UUID | None = None,
        now: datetime | None = None,
    ) -> tuple[ReferralRefundConfirmation, bool]:
        """Record the referred user's explicit, versioned refund confirmation."""
        normalized_policy_version = require_current_policy_version(policy_version)
        from app.commerce.models import Payment

        payment = await self.session.get(Payment, payment_id)
        order = None if payment is None else await self.session.get(Order, payment.order_id)
        if payment is None or order is None or payment.status != "confirmed":
            raise ReferralError("confirmed payment is required")
        if order.owner_user_id != user_id:
            raise ReferralError("refund confirmation belongs to another user")
        reservation = await self.session.scalar(
            select(ReferralRewardReservation).where(
                ReferralRewardReservation.payment_attempt_id == payment.attempt_id,
            )
        )
        if reservation is None or reservation.status not in {
            "committed",
            "expired",
            "reversed",
        }:
            raise ReferralError("committed referral reward is required")
        existing = await self.session.scalar(
            select(ReferralRefundConfirmation).where(
                ReferralRefundConfirmation.payment_id == payment.id,
            )
        )
        if existing is not None:
            if (
                existing.user_id != user_id
                or existing.policy_version != normalized_policy_version
                or existing.reservation_id != reservation.id
            ):
                raise ReferralError("refund confirmation is bound to another fact")
            return existing, False
        confirmation = ReferralRefundConfirmation(
            order_id=order.id,
            payment_id=payment.id,
            reservation_id=reservation.id,
            campaign_version_id=reservation.campaign_version_id,
            product_version_id=order.product_version_id,
            user_id=user_id,
            policy_version=normalized_policy_version,
            accepted_at=now or datetime.now(UTC),
            actor_session_id=actor_session_id,
        )
        self.session.add(confirmation)
        await self.session.flush()
        return confirmation, True

    async def reverse_reward_for_refund(
        self,
        *,
        payment_attempt_id: UUID,
        refund_id: UUID,
    ) -> ReferralRewardReservation | None:
        """Close a committed referral reward when its qualifying payment is refunded."""
        reservation = await self.session.scalar(
            select(ReferralRewardReservation).where(
                ReferralRewardReservation.payment_attempt_id == payment_attempt_id,
            )
        )
        if reservation is None:
            return None
        if reservation.status in {"released", "expired", "reversed"}:
            return reservation
        if reservation.status != "committed":
            raise ReferralError("only a committed reward can be reversed")

        entitlement_id = f"referral:{reservation.id}"
        projection = await self.commerce.ledger.project(
            entitlement_id=entitlement_id,
            owner_user_id=reservation.inviter_user_id,
        )
        if projection.granted == 0:
            raise ReferralError("committed reward grant is missing")
        if projection.reserved:
            await self.commerce.append_entitlement_event(
                owner_user_id=reservation.inviter_user_id,
                entitlement_id=entitlement_id,
                kind="RELEASE",
                quantity=projection.reserved,
                source_type="referral_refund",
                source_ref=f"{refund_id}:release",
            )
            projection = await self.commerce.ledger.project(
                entitlement_id=entitlement_id,
                owner_user_id=reservation.inviter_user_id,
            )

        expirable = projection.available
        if expirable > 0:
            await self.commerce.append_entitlement_event(
                owner_user_id=reservation.inviter_user_id,
                entitlement_id=entitlement_id,
                kind="EXPIRE",
                quantity=expirable,
                source_type="referral_refund",
                source_ref=f"{refund_id}:expire",
            )
            projection = await self.commerce.ledger.project(
                entitlement_id=entitlement_id,
                owner_user_id=reservation.inviter_user_id,
            )

        reversible = projection.consumed - projection.reversed
        if reversible > 0:
            await self.commerce.append_entitlement_event(
                owner_user_id=reservation.inviter_user_id,
                entitlement_id=entitlement_id,
                kind="REVERSE",
                quantity=reversible,
                source_type="referral_refund",
                source_ref=f"{refund_id}:reverse",
            )
        reservation.status = (
            "reversed"
            if reversible > 0 or projection.reversed > 0
            else "expired"
        )
        await self._notify_reward_state(reservation, "refunded")
        await self.session.flush()
        return reservation

    async def commit_reward(
        self,
        reservation_id: UUID,
        *,
        now: datetime | None = None,
    ) -> ReferralRewardReservation:
        reservation = await self._reservation(reservation_id)
        if reservation.status == "committed":
            return reservation
        if reservation.status != "reserved":
            raise ReferralError("only a reserved reward can be committed")
        campaign = await self.session.get(
            ReferralCampaignVersion,
            reservation.campaign_version_id,
        )
        current = _as_utc(now or datetime.now(UTC))
        if campaign is None or not self._campaign_active(campaign, current):
            reservation.status = "released"
            await self.session.flush()
            return reservation
        await self.session.flush()
        await self.commerce.append_entitlement_event(
            owner_user_id=reservation.inviter_user_id,
            entitlement_id=f"referral:{reservation.id}",
            kind="GRANT",
            quantity=reservation.quantity,
            source_type="referral",
            source_ref=str(reservation.id),
        )
        reservation.status = "committed"
        reservation.committed_at = now or datetime.now(UTC)
        await self._notify_reward_state(reservation, "committed")
        await self.session.flush()
        return reservation

    async def expire_rewards(self, *, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        rows = list(
            await self.session.scalars(
                select(ReferralRewardReservation).where(
                    ReferralRewardReservation.status == "committed",
                    ReferralRewardReservation.committed_at.is_not(None),
                )
            )
        )
        expired = 0
        for reservation in rows:
            campaign = await self.session.get(
                ReferralCampaignVersion, reservation.campaign_version_id
            )
            if campaign is None or reservation.committed_at is None:
                continue
            if _as_utc(reservation.committed_at) + timedelta(
                seconds=campaign.reward_window_seconds
            ) > current:
                continue
            projection = await self.commerce.ledger.project(
                entitlement_id=f"referral:{reservation.id}",
                owner_user_id=reservation.inviter_user_id,
            )
            if projection.reserved:
                continue
            expirable = projection.available
            if expirable < 1:
                continue
            await self.commerce.append_entitlement_event(
                owner_user_id=reservation.inviter_user_id,
                entitlement_id=f"referral:{reservation.id}",
                kind="EXPIRE",
                quantity=expirable,
                source_type="referral",
                source_ref=f"{reservation.id}:expire",
            )
            reservation.status = "expired"
            await self._notify_reward_state(reservation, "expired")
            expired += 1
        await self.session.flush()
        return expired

    async def _notify_reward_state(
        self,
        reservation: ReferralRewardReservation,
        state: Literal["committed", "expired", "refunded"],
    ) -> None:
        for audience, owner_user_id in (
            ("inviter", reservation.inviter_user_id),
            ("referred", reservation.referred_user_id),
        ):
            await self.commerce.enqueue_notification(
                owner_user_id=owner_user_id,
                kind=f"referral.reward.{state}",
                dedupe_key=f"referral.reward:{reservation.id}:{state}:{audience}",
                payload={"state": state},
            )

    async def _reservation(self, reservation_id: UUID) -> ReferralRewardReservation:
        reservation = await self.session.get(ReferralRewardReservation, reservation_id)
        if reservation is None:
            raise ReferralError("reward reservation not found")
        return reservation

    async def _ensure_participation_allowed(self, user_id: UUID) -> None:
        restriction = await self.session.scalar(
            select(ReferralParticipationRestriction).where(
                ReferralParticipationRestriction.user_id == user_id
            )
        )
        if restriction is not None:
            raise ReferralError("referral participation is restricted")

    async def _validate_payment_attempt(
        self,
        *,
        payment_attempt_id: UUID,
        referred_user_id: UUID,
        product_version_id: UUID,
    ) -> None:
        attempt = await self.session.get(PaymentAttempt, payment_attempt_id)
        order = None if attempt is None else await self.session.get(Order, attempt.order_id)
        if attempt is None or order is None:
            raise ReferralError("payment attempt not found")
        if attempt.status != "pending":
            raise ReferralError("payment attempt is not pending")
        if order.owner_user_id != referred_user_id:
            raise ReferralError("payment attempt belongs to another user")
        if order.product_version_id != product_version_id:
            raise ReferralError("payment product does not match reward")
        if order.status not in {"created", "payment_pending"}:
            raise ReferralError("payment order is not payable")

    async def _active_campaign_and_code(
        self,
        campaign_id: UUID,
        code: str,
        now: datetime,
    ) -> tuple[ReferralCampaignVersion, ReferralCode]:
        campaign = await self.session.get(ReferralCampaignVersion, campaign_id)
        referral_code = await self.session.scalar(
            select(ReferralCode).where(
                ReferralCode.campaign_version_id == campaign_id,
                ReferralCode.code == code,
                ReferralCode.status == "active",
            )
        )
        if campaign is None or referral_code is None or not self._campaign_active(campaign, now):
            raise ReferralError("campaign is not active")
        return campaign, referral_code

    @staticmethod
    def _campaign_active(campaign: ReferralCampaignVersion, now: datetime) -> bool:
        return (
            campaign.state == ReferralState.ACTIVE
            and _as_utc(campaign.starts_at) <= now
            and (campaign.ends_at is None or now < _as_utc(campaign.ends_at))
        )
