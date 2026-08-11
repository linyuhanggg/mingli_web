"""Staff authentication and admin overview services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.admin.passwords import hash_password, verify_password
from app.admin.repository import AdminRepository
from app.admin.schemas import AdminKpi, AdminOverviewResponse, AdminQueueSummary
from app.identity.security import hash_token, new_opaque_token


class AdminAuthError(Exception):
    """Invalid credentials or unavailable staff principal."""


class AdminBootstrapForbidden(Exception):
    """Bootstrap path is not allowed in this environment."""


@dataclass(frozen=True, slots=True)
class CreatedStaffSession:
    staff: StaffUser
    session_id: UUID
    token: str
    csrf_token: str
    expires_at: datetime


class AdminAuthService:
    def __init__(
        self,
        repository: AdminRepository,
        *,
        session_hours: int,
        bootstrap_email: str | None,
        bootstrap_password: str | None,
        allow_bootstrap: bool,
    ) -> None:
        self.repository = repository
        self.session_hours = session_hours
        self.bootstrap_email = (bootstrap_email or "").strip().lower() or None
        self.bootstrap_password = bootstrap_password
        self.allow_bootstrap = allow_bootstrap

    async def login(self, email: str, password: str) -> CreatedStaffSession:
        normalized = email.strip().lower()
        staff = await self.repository.get_staff_by_email(normalized)
        if staff is None:
            staff = await self._maybe_bootstrap(normalized, password)
        if staff is None or not verify_password(password, staff.password_hash):
            raise AdminAuthError("invalid credentials")
        if staff.status != "active":
            raise AdminAuthError("invalid credentials")

        now = datetime.now(UTC)
        session_id = uuid4()
        token = new_opaque_token()
        csrf_token = new_opaque_token()
        expires_at = now + timedelta(hours=self.session_hours)
        self.repository.add_session(
            StaffSession(
                id=session_id,
                staff_user_id=staff.id,
                token_hash=hash_token(token),
                csrf_token_hash=hash_token(csrf_token),
                expires_at=expires_at,
                last_seen_at=now,
            )
        )
        staff.last_login_at = now
        self.repository.add_audit(
            AdminAuditEvent(
                staff_user_id=staff.id,
                actor_session_id=session_id,
                action="admin.login",
                event_metadata={"role": staff.role},
            )
        )
        return CreatedStaffSession(
            staff=staff,
            session_id=session_id,
            token=token,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )

    async def logout(self, session: StaffSession) -> None:
        now = datetime.now(UTC)
        await self.repository.revoke_session(session, now)
        self.repository.add_audit(
            AdminAuditEvent(
                staff_user_id=session.staff_user_id,
                actor_session_id=session.id,
                action="admin.logout",
                event_metadata={},
            )
        )

    async def _maybe_bootstrap(self, email: str, password: str) -> StaffUser | None:
        if not self.allow_bootstrap:
            return None
        if not self.bootstrap_email or self.bootstrap_password is None:
            return None
        if email != self.bootstrap_email or password != self.bootstrap_password:
            return None
        if await self.repository.count_staff_users() > 0:
            return None
        staff = StaffUser(
            email=email,
            password_hash=hash_password(password),
            display_name="Bootstrap Superadmin",
            role="superadmin",
            status="active",
        )
        self.repository.add_staff(staff)
        await self.repository.session.flush()
        self.repository.add_audit(
            AdminAuditEvent(
                staff_user_id=staff.id,
                actor_session_id=None,
                action="admin.bootstrap_created",
                event_metadata={"email": email},
            )
        )
        return staff


def build_stub_overview() -> AdminOverviewResponse:
    now = datetime.now(UTC)
    return AdminOverviewResponse(
        generated_at=now,
        is_stub=True,
        kpis=[
            AdminKpi(id="refunds_pending", label="待审退款", value=0, is_stub=True),
            AdminKpi(id="readings_failed", label="失败解读", value=0, is_stub=True),
            AdminKpi(id="payments_abnormal", label="今日支付异常", value=0, is_stub=True),
            AdminKpi(id="reconcile_diff", label="对账差异", value=0, is_stub=True),
        ],
        queues=[
            AdminQueueSummary(id="refund_queue", label="退款审批队列", count=0, is_stub=True),
            AdminQueueSummary(id="reading_queue", label="解读失败队列", count=0, is_stub=True),
        ],
    )
