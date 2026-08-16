"""Read-only Admin views over local order, payment and refund facts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import StaffSession, StaffUser
from app.api.admin import require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.commerce.models import FulfillmentRecord, Order, Payment, Refund
from app.commerce.schemas import (
    AdminOrderResponse,
    AdminOrdersResponse,
    AdminPaymentResponse,
    AdminPaymentsResponse,
    AdminRefundResponse,
    AdminRefundsResponse,
)
from app.referrals.models import ReferralRefundConfirmation

router = APIRouter(prefix="/admin/commerce", tags=["Admin Commerce"])


def _require_commerce_reader(staff: StaffUser) -> None:
    if staff.role not in {"finance", "ops", "superadmin"}:
        raise ApiProblem(status=403, title="Commerce reader permission required")


@router.get(
    "/orders",
    operation_id="listAdminOrders",
    response_model=AdminOrdersResponse,
)
async def list_admin_orders(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminOrdersResponse:
    _require_commerce_reader(principal[1])
    rows = (
        await session.execute(
            select(Order, FulfillmentRecord.status)
            .outerjoin(FulfillmentRecord, FulfillmentRecord.order_id == Order.id)
            .order_by(desc(Order.created_at), desc(Order.id))
            .limit(limit)
        )
    ).all()
    mark_private(response)
    return AdminOrdersResponse(
        orders=[
            AdminOrderResponse(
                id=order.id,
                owner_user_id=order.owner_user_id,
                product_version_id=order.product_version_id,
                purchase_target_ref=order.purchase_target_ref,
                amount_minor=order.amount_minor,
                currency=order.currency,
                status=order.status,
                fulfillment_status=fulfillment_status,
                created_at=order.created_at,
                paid_at=order.paid_at,
            )
            for order, fulfillment_status in rows
        ]
    )


@router.get(
    "/payments",
    operation_id="listAdminPayments",
    response_model=AdminPaymentsResponse,
)
async def list_admin_payments(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminPaymentsResponse:
    _require_commerce_reader(principal[1])
    payments = list(
        await session.scalars(
            select(Payment)
            .order_by(desc(Payment.confirmed_at), desc(Payment.id))
            .limit(limit)
        )
    )
    mark_private(response)
    return AdminPaymentsResponse(
        payments=[
            AdminPaymentResponse(
                id=item.id,
                order_id=item.order_id,
                channel=item.channel,
                channel_transaction_id=item.channel_transaction_id,
                amount_minor=item.amount_minor,
                currency=item.currency,
                status=item.status,
                confirmed_at=item.confirmed_at,
            )
            for item in payments
        ]
    )


@router.get(
    "/refunds",
    operation_id="listAdminRefunds",
    response_model=AdminRefundsResponse,
)
async def list_admin_refunds(
    response: Response,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminRefundsResponse:
    _require_commerce_reader(principal[1])
    rows = (
        await session.execute(
            select(Refund, Payment.order_id, ReferralRefundConfirmation)
            .join(Payment, Payment.id == Refund.payment_id)
            .outerjoin(
                ReferralRefundConfirmation,
                ReferralRefundConfirmation.payment_id == Refund.payment_id,
            )
            .order_by(desc(Refund.created_at), desc(Refund.id))
            .limit(limit)
        )
    ).all()
    mark_private(response)
    return AdminRefundsResponse(
        refunds=[
            AdminRefundResponse(
                id=item.id,
                payment_id=item.payment_id,
                order_id=order_id,
                channel=item.channel,
                channel_refund_id=item.channel_refund_id,
                amount_minor=item.amount_minor,
                currency=item.currency,
                reason=item.reason,
                status=item.status,
                created_at=item.created_at,
                confirmed_at=item.confirmed_at,
                referral_confirmation_id=None if confirmation is None else confirmation.id,
                referral_confirmation_policy_version=(
                    None if confirmation is None else confirmation.policy_version
                ),
                referral_confirmation_at=(
                    None if confirmation is None else confirmation.accepted_at
                ),
            )
            for item, order_id, confirmation in rows
        ]
    )
