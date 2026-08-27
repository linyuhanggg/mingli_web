from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.entitlements.repository import EntitlementRepository
from app.profiles.service import OwnerProtocol

PAID_READING_CAPABILITIES = frozenset(
    {"today", "week", "liuyao", "bazi_deep", "qimen_deep", "liuyao_deep"}
)

_ACTION_TO_CAPABILITY = {
    "today": "today",
    "near_seven": "week",
    "wenshi_one_question": "liuyao",
    "bazi_deep": "bazi_deep",
    "qimen_deep": "qimen_deep",
    "liuyao_deep": "liuyao_deep",
}

OwnerKind = Literal["user", "guest"]

FORMAL_CAPABILITY_PREFIX = "capability:"


def formal_capability_entitlement_id(capability_id: str) -> str:
    return f"{FORMAL_CAPABILITY_PREFIX}{capability_id}"


def formal_grant_covers_capability(
    *,
    entitlement_id: str,
    target_refs: set[str],
    capability_id: str,
) -> bool:
    aliases = {capability_id, formal_capability_entitlement_id(capability_id)}
    return entitlement_id in aliases or bool(target_refs & aliases)


class EntitlementDeniedError(RuntimeError):
    """Caller may not start this paid reading action under dogfood gates."""

    def __init__(self, title: str, *, detail: str | None = None, code: str | None = None) -> None:
        super().__init__(title)
        self.title = title
        self.detail = detail
        self.code = code


def paid_capability_for_action(action: str) -> str | None:
    return _ACTION_TO_CAPABILITY.get(action)


class EntitlementService:
    """Enforces dogfood capability switches when enabled in settings."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repository = EntitlementRepository(session)

    @property
    def gates_enabled(self) -> bool:
        return self.settings.dogfood_entitlement_gates_enabled

    async def require_paid_action(self, owner: OwnerProtocol, *, action: str) -> None:
        capability_id = paid_capability_for_action(action)
        if capability_id is None:
            return
        kind: OwnerKind = owner.kind
        if kind == "user" and await self.has_available_formal_grant(
            owner_user_id=owner.id,
            capability_id=capability_id,
        ):
            # Formal ledger GRANT takes over; do not fall through to dogfood.
            return
        if not self.gates_enabled:
            return
        if kind != "user":
            raise EntitlementDeniedError(
                "Paid reading requires a signed-in account",
                detail="Sign in with email, then ask an operator to grant dogfood access.",
                code="paid_reading_requires_account",
            )
        grant = await self.repository.get_active_grant(
            owner_user_id=owner.id,
            capability_id=capability_id,
        )
        if grant is None:
            raise EntitlementDeniedError(
                "Paid reading not granted",
                detail=(
                    f"Capability {capability_id!r} is closed for this account. "
                    "Dogfood access is operator-granted only; there is no self-serve checkout."
                ),
                code="paid_reading_not_granted",
            )

    async def has_available_formal_grant(
        self,
        *,
        owner_user_id: UUID,
        capability_id: str,
    ) -> bool:
        """True when the commercial ledger still has an available GRANT for this capability."""
        from app.commerce.repository import CommerceRepository

        repository = CommerceRepository(self.session)
        events = await repository.list_events(owner_user_id=owner_user_id, limit=500)
        inspected: set[str] = set()
        for event in events:
            if event.entitlement_id in inspected:
                continue
            inspected.add(event.entitlement_id)
            projection = await repository.project(
                entitlement_id=event.entitlement_id,
                owner_user_id=owner_user_id,
            )
            if projection.available < 1:
                continue
            target_refs = {
                row.target_ref
                for row in events
                if row.entitlement_id == event.entitlement_id and row.target_ref
            }
            if formal_grant_covers_capability(
                entitlement_id=event.entitlement_id,
                target_refs=target_refs,
                capability_id=capability_id,
            ):
                return True
        return False

    async def grant_capabilities(
        self,
        *,
        owner_user_id: UUID,
        capability_ids: list[str],
        granted_by: str,
        note: str | None = None,
    ) -> list[str]:
        unknown = sorted(set(capability_ids) - PAID_READING_CAPABILITIES)
        if unknown:
            raise ValueError(f"unknown capabilities: {unknown}")
        now = datetime.now(UTC)
        granted: list[str] = []
        for capability_id in sorted(set(capability_ids)):
            await self.repository.upsert_grant(
                owner_user_id=owner_user_id,
                capability_id=capability_id,
                granted_by=granted_by,
                note=note,
                now=now,
            )
            granted.append(capability_id)
        return granted

    async def list_active(self, *, owner_user_id: UUID) -> list[str]:
        grants = await self.repository.list_active_grants(owner_user_id=owner_user_id)
        return sorted(grant.capability_id for grant in grants)
