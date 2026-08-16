"""Staff-only product catalog management."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AdminAuditEvent, StaffSession, StaffUser
from app.api.admin import require_staff_csrf, require_staff_session
from app.api.dependencies import database_session, mark_private
from app.api.errors import ApiProblem
from app.commerce.catalog import CatalogError, CatalogService
from app.commerce.models import ProductFamily, ProductOffer, ProductVersion
from app.commerce.schemas import (
    AdminCatalogFamilyCreateRequest,
    AdminCatalogFamilyResponse,
    AdminCatalogOfferCreateRequest,
    AdminCatalogOfferEnabledRequest,
    AdminCatalogOfferResponse,
    AdminCatalogReasonRequest,
    AdminCatalogResponse,
    AdminCatalogVersionCreateRequest,
    AdminCatalogVersionResponse,
)

router = APIRouter(prefix="/admin/catalog", tags=["Admin Catalog"])


def _require_catalog_operator(staff: StaffUser) -> None:
    if staff.role not in {"ops", "superadmin"}:
        raise ApiProblem(status=403, title="Catalog operator permission required")


def _reason(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ApiProblem(status=400, title="Catalog operation reason is required")
    return normalized


def _catalog_problem(error: CatalogError) -> ApiProblem:
    detail = str(error)
    not_found = detail.endswith("not found")
    return ApiProblem(
        status=404 if not_found else 409,
        title="Catalog object not found" if not_found else "Invalid catalog transition",
        detail=detail,
    )


def _audit(
    session: AsyncSession,
    *,
    staff_session: StaffSession,
    staff: StaffUser,
    action: str,
    reason: str,
    target_id: UUID,
    metadata: dict[str, Any] | None = None,
) -> None:
    event_metadata: dict[str, Any] = {
        "reason": _reason(reason),
        "target_id": str(target_id),
    }
    if metadata:
        event_metadata.update(metadata)
    session.add(
        AdminAuditEvent(
            staff_user_id=staff.id,
            actor_session_id=staff_session.id,
            action=action,
            event_metadata=event_metadata,
        )
    )


def _offer_response(offer: ProductOffer) -> AdminCatalogOfferResponse:
    return AdminCatalogOfferResponse(
        id=offer.id,
        product_version_id=offer.product_version_id,
        channel=offer.channel,
        channel_sku=offer.channel_sku,
        price_minor=offer.price_minor,
        currency=offer.currency,
        enabled=offer.enabled,
        created_at=offer.created_at,
    )


def _version_response(
    version: ProductVersion,
    offers: list[ProductOffer],
) -> AdminCatalogVersionResponse:
    return AdminCatalogVersionResponse(
        id=version.id,
        family_id=version.family_id,
        version=version.version,
        price_minor=version.price_minor,
        currency=version.currency,
        contract_version=version.contract_version,
        follow_up_count=version.follow_up_count,
        follow_up_window_seconds=version.follow_up_window_seconds,
        status=version.status,
        created_at=version.created_at,
        offers=[_offer_response(offer) for offer in offers],
    )


async def _offers_for_version(
    session: AsyncSession,
    version_id: UUID,
) -> list[ProductOffer]:
    return list(
        await session.scalars(
            select(ProductOffer)
            .where(ProductOffer.product_version_id == version_id)
            .order_by(ProductOffer.channel, ProductOffer.channel_sku)
        )
    )


async def _catalog_response(session: AsyncSession) -> AdminCatalogResponse:
    families = list(
        await session.scalars(select(ProductFamily).order_by(ProductFamily.key))
    )
    versions = list(
        await session.scalars(
            select(ProductVersion).order_by(ProductVersion.family_id, ProductVersion.version)
        )
    )
    offers = list(
        await session.scalars(
            select(ProductOffer).order_by(
                ProductOffer.product_version_id,
                ProductOffer.channel,
                ProductOffer.channel_sku,
            )
        )
    )
    offers_by_version: dict[UUID, list[ProductOffer]] = {}
    for offer in offers:
        offers_by_version.setdefault(offer.product_version_id, []).append(offer)
    versions_by_family: dict[UUID, list[ProductVersion]] = {}
    for version in versions:
        versions_by_family.setdefault(version.family_id, []).append(version)
    return AdminCatalogResponse(
        families=[
            AdminCatalogFamilyResponse(
                id=family.id,
                key=family.key,
                label=family.label,
                status=family.status,
                created_at=family.created_at,
                versions=[
                    _version_response(
                        version,
                        offers_by_version.get(version.id, []),
                    )
                    for version in versions_by_family.get(family.id, [])
                ],
            )
            for family in families
        ]
    )


@router.get(
    "",
    operation_id="listAdminCatalog",
    response_model=AdminCatalogResponse,
)
async def list_admin_catalog(
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_session),
) -> AdminCatalogResponse:
    _require_catalog_operator(principal[1])
    payload = await _catalog_response(session)
    mark_private(response)
    return payload


@router.post(
    "/families",
    operation_id="createAdminCatalogFamily",
    response_model=AdminCatalogFamilyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_catalog_family(
    payload: AdminCatalogFamilyCreateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminCatalogFamilyResponse:
    staff_session, staff = principal
    _require_catalog_operator(staff)
    try:
        family = await CatalogService(session).create_family(
            key=payload.key,
            label=payload.label,
        )
    except CatalogError as error:
        raise _catalog_problem(error) from error
    _audit(
        session,
        staff_session=staff_session,
        staff=staff,
        action="catalog.family.created",
        reason=payload.reason,
        target_id=family.id,
        metadata={"key": family.key},
    )
    await session.commit()
    mark_private(response)
    return AdminCatalogFamilyResponse(
        id=family.id,
        key=family.key,
        label=family.label,
        status=family.status,
        created_at=family.created_at,
        versions=[],
    )


@router.post(
    "/versions",
    operation_id="createAdminCatalogVersion",
    response_model=AdminCatalogVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_catalog_version(
    payload: AdminCatalogVersionCreateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminCatalogVersionResponse:
    staff_session, staff = principal
    _require_catalog_operator(staff)
    try:
        version = await CatalogService(session).create_version(
            family_id=payload.family_id,
            version=payload.version,
            price_minor=payload.price_minor,
            currency=payload.currency,
            contract_version=payload.contract_version,
            follow_up_count=payload.follow_up_count,
            follow_up_window_seconds=payload.follow_up_window_seconds,
        )
    except CatalogError as error:
        raise _catalog_problem(error) from error
    _audit(
        session,
        staff_session=staff_session,
        staff=staff,
        action="catalog.version.created",
        reason=payload.reason,
        target_id=version.id,
        metadata={"family_id": str(version.family_id), "version": version.version},
    )
    await session.commit()
    mark_private(response)
    return _version_response(version, [])


@router.post(
    "/offers",
    operation_id="createAdminCatalogOffer",
    response_model=AdminCatalogOfferResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_catalog_offer(
    payload: AdminCatalogOfferCreateRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminCatalogOfferResponse:
    staff_session, staff = principal
    _require_catalog_operator(staff)
    try:
        offer = await CatalogService(session).create_offer(
            product_version_id=payload.product_version_id,
            channel=payload.channel,
            channel_sku=payload.channel_sku,
            price_minor=payload.price_minor,
            currency=payload.currency,
            enabled=payload.enabled,
        )
    except CatalogError as error:
        raise _catalog_problem(error) from error
    _audit(
        session,
        staff_session=staff_session,
        staff=staff,
        action="catalog.offer.created",
        reason=payload.reason,
        target_id=offer.id,
        metadata={
            "product_version_id": str(offer.product_version_id),
            "enabled": offer.enabled,
        },
    )
    await session.commit()
    mark_private(response)
    return _offer_response(offer)


@router.post(
    "/versions/{version_id}/publish",
    operation_id="publishAdminCatalogVersion",
    response_model=AdminCatalogVersionResponse,
)
async def publish_admin_catalog_version(
    version_id: UUID,
    payload: AdminCatalogReasonRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminCatalogVersionResponse:
    staff_session, staff = principal
    _require_catalog_operator(staff)
    try:
        version = await CatalogService(session).publish_version(version_id)
    except CatalogError as error:
        raise _catalog_problem(error) from error
    _audit(
        session,
        staff_session=staff_session,
        staff=staff,
        action="catalog.version.published",
        reason=payload.reason,
        target_id=version.id,
        metadata={"status": version.status},
    )
    offers = await _offers_for_version(session, version.id)
    await session.commit()
    mark_private(response)
    return _version_response(version, offers)


@router.post(
    "/versions/{version_id}/retire",
    operation_id="retireAdminCatalogVersion",
    response_model=AdminCatalogVersionResponse,
)
async def retire_admin_catalog_version(
    version_id: UUID,
    payload: AdminCatalogReasonRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminCatalogVersionResponse:
    staff_session, staff = principal
    _require_catalog_operator(staff)
    try:
        version = await CatalogService(session).retire_version(version_id)
    except CatalogError as error:
        raise _catalog_problem(error) from error
    _audit(
        session,
        staff_session=staff_session,
        staff=staff,
        action="catalog.version.retired",
        reason=payload.reason,
        target_id=version.id,
        metadata={"status": version.status},
    )
    offers = await _offers_for_version(session, version.id)
    await session.commit()
    mark_private(response)
    return _version_response(version, offers)


@router.post(
    "/offers/{offer_id}/enabled",
    operation_id="setAdminCatalogOfferEnabled",
    response_model=AdminCatalogOfferResponse,
)
async def set_admin_catalog_offer_enabled(
    offer_id: UUID,
    payload: AdminCatalogOfferEnabledRequest,
    response: Response,
    session: AsyncSession = Depends(database_session),
    principal: tuple[StaffSession, StaffUser] = Depends(require_staff_csrf),
) -> AdminCatalogOfferResponse:
    staff_session, staff = principal
    _require_catalog_operator(staff)
    try:
        offer = await CatalogService(session).set_offer_enabled(
            offer_id,
            enabled=payload.enabled,
        )
    except CatalogError as error:
        raise _catalog_problem(error) from error
    _audit(
        session,
        staff_session=staff_session,
        staff=staff,
        action="catalog.offer.enabled_changed",
        reason=payload.reason,
        target_id=offer.id,
        metadata={"enabled": offer.enabled},
    )
    await session.commit()
    mark_private(response)
    return _offer_response(offer)
