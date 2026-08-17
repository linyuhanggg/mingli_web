from __future__ import annotations

from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.payment import FakePaymentGateway, PaymentGateway
from app.api.dependencies import (
    database_session,
    mark_private,
    require_device_csrf,
    require_device_session,
)
from app.api.errors import ApiProblem
from app.commerce.models import Payment
from app.commerce.public_schemas import (
    PublicBaziCheckoutRequest,
    PublicCheckoutAttempt,
    PublicCheckoutOrder,
    PublicCheckoutResponse,
)
from app.commerce.public_service import (
    PublicCheckoutConflict,
    PublicCheckoutGatewayError,
    PublicCheckoutNotFound,
    PublicCheckoutResult,
    PublicCheckoutService,
)
from app.identity.models import DeviceSession

router = APIRouter(prefix="/commerce", tags=["Commerce"])


def get_payment_gateway(request: Request) -> PaymentGateway:
    """Resolve the injected gateway, defaulting to the fail-closed fake."""

    configured = getattr(request.app.state, "payment_gateway", None)
    return cast(PaymentGateway, configured if configured is not None else FakePaymentGateway())


def _project(result: PublicCheckoutResult) -> PublicCheckoutResponse:
    payment: Payment | None = result.payment
    return PublicCheckoutResponse(
        order=PublicCheckoutOrder(
            order_id=result.order.id,
            reading_version_id=result.reading_version_id,
            product_id="bazi-deep",
            product_version=result.product.version,
            amount_minor=result.order.amount_minor,
            currency=result.order.currency,
            status=result.order.status,
            created_at=result.order.created_at,
            paid_at=result.order.paid_at,
        ),
        attempt=PublicCheckoutAttempt(
            attempt_id=result.attempt.id,
            channel=result.attempt.channel,
            status=result.attempt.status,
            created_at=result.attempt.created_at,
        ),
        gateway_status=result.gateway_status,
        redirect_url=result.redirect_url,
        payment_id=payment.id if payment is not None else None,
        created=result.created,
    )


def _problem(error: Exception) -> ApiProblem:
    if isinstance(error, PublicCheckoutNotFound):
        return ApiProblem(status=404, title="Checkout not found")
    if isinstance(error, PublicCheckoutConflict):
        return ApiProblem(status=409, title="Checkout is not available")
    if isinstance(error, PublicCheckoutGatewayError):
        return ApiProblem(status=503, title="Payment gateway unavailable")
    return ApiProblem(status=500, title="Checkout failed")


@router.post(
    "/checkout",
    operation_id="createBaziDeepCheckout",
    response_model=PublicCheckoutResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_bazi_deep_checkout(
    response: Response,
    payload: PublicBaziCheckoutRequest,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_csrf),
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
    gateway: PaymentGateway = Depends(get_payment_gateway),
) -> PublicCheckoutResponse:
    try:
        result = await PublicCheckoutService(session, gateway).create_checkout(
            owner_user_id=device_session.user_id,
            reading_version_id=payload.reading_version_id,
            idempotency_key=idempotency_key,
        )
    except (PublicCheckoutNotFound, PublicCheckoutConflict, PublicCheckoutGatewayError) as error:
        raise _problem(error) from error
    await session.commit()
    mark_private(response)
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return _project(result)


@router.get(
    "/checkout/{order_id}",
    operation_id="getBaziDeepCheckout",
    response_model=PublicCheckoutResponse,
    response_model_exclude_none=True,
)
async def get_bazi_deep_checkout(
    response: Response,
    order_id: UUID,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
    gateway: PaymentGateway = Depends(get_payment_gateway),
) -> PublicCheckoutResponse:
    try:
        result = await PublicCheckoutService(session, gateway).get_checkout(
            owner_user_id=device_session.user_id,
            order_id=order_id,
        )
    except (PublicCheckoutNotFound, PublicCheckoutConflict, PublicCheckoutGatewayError) as error:
        raise _problem(error) from error
    await session.commit()
    mark_private(response)
    return _project(result)
