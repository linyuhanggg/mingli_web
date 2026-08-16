"""Staff-only reconciliation runs over verified provider snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.api.admin import require_staff_csrf, require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.commerce.models import PaymentReconciliationItem, PaymentReconciliationRun
from app.commerce.reconciliation import ChannelPaymentSnapshot, ChannelRefundSnapshot
from app.commerce.schemas import (
    AdminReconciliationItemResponse,
    AdminReconciliationRunRequest,
    AdminReconciliationRunResponse,
    AdminReconciliationRunsResponse,
)
from app.commerce.service import CommerceError, CommerceService

router = APIRouter(prefix="/admin/reconciliation", tags=["Admin Reconciliation"])


def _require_reconciliation_operator(staff: StaffUser) -> None:
    if staff.role not in {"finance", "ops", "superadmin"}:
        raise ApiProblem(status=403, title="Reconciliation operator permission required")


def _reason(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ApiProblem(status=400, title="Reconciliation operation reason is required")
    return normalized


def _problem(error: CommerceError) -> ApiProblem:
    return ApiProblem(
        status=409,
        title="Invalid reconciliation snapshot",
        detail=str(error),
    )


def _item_response(item: PaymentReconciliationItem) -> AdminReconciliationItemResponse:
    return AdminReconciliationItemResponse(
        id=item.id,
        kind=item.kind,
        reference=item.reference,
        payment_id=item.payment_id,
        refund_id=item.refund_id,
        local_status=item.local_status,
        provider_status=item.provider_status,
        local_amount_minor=item.local_amount_minor,
        provider_amount_minor=item.provider_amount_minor,
        local_currency=item.local_currency,
        provider_currency=item.provider_currency,
        discrepancy=item.discrepancy,
        created_at=item.created_at,
    )


def _run_response(
    run: PaymentReconciliationRun,
    items: list[PaymentReconciliationItem],
) -> AdminReconciliationRunResponse:
    return AdminReconciliationRunResponse(
        id=run.id,
        channel=run.channel,
        run_at=run.run_at,
        status=run.status,
        item_count=run.item_count,
        matched_count=run.matched_count,
        difference_count=run.difference_count,
        created_at=run.created_at,
        items=[_item_response(item) for item in items],
    )


def _audit(
    session: AsyncSession,
    *,
    staff_session: StaffSession,
    staff: StaffUser,
    run: PaymentReconciliationRun,
    reason: str,
) -> None:
    event_metadata: dict[str, Any] = {
        "reason": _reason(reason),
        "run_id": str(run.id),
        "channel": run.channel,
        "status": run.status,
        "difference_count": run.difference_count,
    }
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action="payment.reconciliation.run",
            event_metadata=event_metadata,
        )
    )


async def _items_for_run(
    session: AsyncSession,
    run_id: UUID,
) -> list[PaymentReconciliationItem]:
    return list(
        await session.scalars(
            select(PaymentReconciliationItem)
            .where(PaymentReconciliationItem.run_id == run_id)
            .order_by(PaymentReconciliationItem.kind, PaymentReconciliationItem.reference)
        )
    )


@router.get(
    "",
    operation_id="listAdminReconciliationRuns",
    response_model=AdminReconciliationRunsResponse,
)
async def list_admin_reconciliation_runs(
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminReconciliationRunsResponse:
    _require_reconciliation_operator(principal[1])
    runs = list(
        await session.scalars(
            select(PaymentReconciliationRun)
            .order_by(desc(PaymentReconciliationRun.run_at))
            .limit(50)
        )
    )
    payload = AdminReconciliationRunsResponse(
        runs=[_run_response(run, await _items_for_run(session, run.id)) for run in runs]
    )
    mark_private(response)
    return payload


@router.get(
    "/runs/{run_id}",
    operation_id="getAdminReconciliationRun",
    response_model=AdminReconciliationRunResponse,
)
async def get_admin_reconciliation_run(
    run_id: UUID,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminReconciliationRunResponse:
    _require_reconciliation_operator(principal[1])
    run = await session.get(PaymentReconciliationRun, run_id)
    if run is None:
        raise ApiProblem(status=404, title="Reconciliation run not found")
    mark_private(response)
    return _run_response(run, await _items_for_run(session, run.id))


@router.post(
    "/runs",
    operation_id="createAdminReconciliationRun",
    response_model=AdminReconciliationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_reconciliation_run(
    payload: AdminReconciliationRunRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminReconciliationRunResponse:
    staff_session, staff = principal
    _require_reconciliation_operator(staff)
    payments = [
        ChannelPaymentSnapshot(
            transaction_id=item.transaction_id.strip(),
            status=item.status,
            amount_minor=item.amount_minor,
            currency=item.currency.strip().upper(),
        )
        for item in payload.payments
    ]
    refunds = [
        ChannelRefundSnapshot(
            refund_id=item.refund_id.strip(),
            payment_transaction_id=(
                item.payment_transaction_id.strip()
                if item.payment_transaction_id is not None
                else None
            ),
            status=item.status,
            amount_minor=item.amount_minor,
            currency=item.currency.strip().upper(),
        )
        for item in payload.refunds
    ]
    try:
        run, items = await CommerceService(session).reconcile_channel(
            channel=payload.channel,
            payments=payments,
            refunds=refunds,
            run_at=datetime.now(UTC),
        )
    except CommerceError as error:
        raise _problem(error) from error
    _audit(
        session,
        staff_session=staff_session,
        staff=staff,
        run=run,
        reason=payload.reason,
    )
    await session.commit()
    mark_private(response)
    return _run_response(run, items)
