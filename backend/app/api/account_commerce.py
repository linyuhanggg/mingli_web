"""Private account projections for order and entitlement facts."""

from typing import cast

from fastapi import APIRouter, Depends, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import database_session, mark_private, require_device_session
from app.commerce.ledger import EntitlementLedger, LedgerEvent, LedgerEventKind
from app.commerce.models import (
    EntitlementEventRecord,
    FulfillmentRecord,
    Order,
    ProductFamily,
    ProductVersion,
)
from app.commerce.schemas import (
    AccountEntitlementEventResponse,
    AccountEntitlementResponse,
    AccountEntitlementsResponse,
    AccountOrderResponse,
    AccountOrdersResponse,
)
from app.identity.models import DeviceSession

router = APIRouter(tags=["Identity"])


@router.get(
    "/account/orders",
    operation_id="listAccountOrders",
    response_model=AccountOrdersResponse,
)
async def list_account_orders(
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
) -> AccountOrdersResponse:
    rows = (
        await session.execute(
            select(Order, ProductFamily.label, FulfillmentRecord.status)
            .join(ProductVersion, ProductVersion.id == Order.product_version_id)
            .join(ProductFamily, ProductFamily.id == ProductVersion.family_id)
            .outerjoin(FulfillmentRecord, FulfillmentRecord.order_id == Order.id)
            .where(Order.owner_user_id == device_session.user_id)
            .order_by(desc(Order.created_at), desc(Order.id))
        )
    ).all()
    mark_private(response)
    return AccountOrdersResponse(
        orders=[
            AccountOrderResponse(
                order_id=order.id,
                product_label=product_label,
                amount_minor=order.amount_minor,
                currency=order.currency,
                status=order.status,
                fulfillment_status=fulfillment_status,
                created_at=order.created_at,
                paid_at=order.paid_at,
            )
            for order, product_label, fulfillment_status in rows
        ]
    )


@router.get(
    "/account/entitlements",
    operation_id="listAccountEntitlements",
    response_model=AccountEntitlementsResponse,
)
async def list_account_entitlements(
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
) -> AccountEntitlementsResponse:
    events = list(
        await session.scalars(
            select(EntitlementEventRecord)
            .where(EntitlementEventRecord.owner_user_id == device_session.user_id)
            .order_by(
                desc(EntitlementEventRecord.created_at),
                desc(EntitlementEventRecord.id),
            )
        )
    )
    grouped: dict[str, list[EntitlementEventRecord]] = {}
    for event in events:
        grouped.setdefault(event.entitlement_id, []).append(event)

    projections: list[AccountEntitlementResponse] = []
    for index, entitlement_events in enumerate(grouped.values(), start=1):
        entitlement_events.sort(key=lambda item: (item.created_at, str(item.id)))
        entitlement_id = entitlement_events[0].entitlement_id
        ledger = EntitlementLedger()
        for event in entitlement_events:
            ledger.append(
                LedgerEvent(
                    event_id=event.id,
                    entitlement_id=event.entitlement_id,
                    kind=cast(LedgerEventKind, event.kind),
                    quantity=event.quantity,
                    source=event.source_type,
                    occurred_at=event.created_at,
                )
            )
        projection = ledger.project(entitlement_id)
        projections.append(
            AccountEntitlementResponse(
                label=f"权益 {index}",
                granted=projection.granted,
                reserved=projection.reserved,
                consumed=projection.consumed,
                released=projection.released,
                reversed=projection.reversed,
                expired=projection.expired,
                available=projection.available,
                events=[
                    AccountEntitlementEventResponse(
                        kind=cast(LedgerEventKind, event.kind),
                        quantity=event.quantity,
                        occurred_at=event.created_at,
                    )
                    for event in entitlement_events
                ],
            )
        )

    mark_private(response)
    return AccountEntitlementsResponse(entitlements=projections)
