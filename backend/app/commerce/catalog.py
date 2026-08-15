from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commerce.models import ProductFamily, ProductOffer, ProductVersion


class CatalogError(ValueError):
    """The product catalog cannot accept the requested state transition."""


class CatalogService:
    """Create immutable product semantics and publish sellable offers.

    ProductVersion fields that affect delivery are supplied only at creation.
    Publishing changes availability, not the version's price or contract.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_family(self, *, key: str, label: str) -> ProductFamily:
        normalized_key = key.strip()
        normalized_label = label.strip()
        if not normalized_key or not normalized_label:
            raise CatalogError("product family key and label are required")
        existing = await self.session.scalar(
            select(ProductFamily).where(ProductFamily.key == normalized_key)
        )
        if existing is not None:
            raise CatalogError("product family key already exists")
        family = ProductFamily(key=normalized_key, label=normalized_label, status="active")
        self.session.add(family)
        await self.session.flush()
        return family

    async def create_version(
        self,
        *,
        family_id: UUID,
        version: str,
        price_minor: int,
        currency: str,
        contract_version: str,
        follow_up_count: int = 0,
        follow_up_window_seconds: int = 0,
    ) -> ProductVersion:
        family = await self.session.get(ProductFamily, family_id)
        if family is None:
            raise CatalogError("product family not found")
        if not version.strip() or not contract_version.strip():
            raise CatalogError("product version and contract version are required")
        if price_minor < 0:
            raise CatalogError("product price cannot be negative")
        if follow_up_count < 0 or follow_up_window_seconds < 0:
            raise CatalogError("follow-up values cannot be negative")
        normalized_currency = _currency(currency)
        existing = await self.session.scalar(
            select(ProductVersion).where(
                ProductVersion.family_id == family.id,
                ProductVersion.version == version.strip(),
            )
        )
        if existing is not None:
            raise CatalogError("product version already exists")
        product = ProductVersion(
            family_id=family.id,
            version=version.strip(),
            price_minor=price_minor,
            currency=normalized_currency,
            follow_up_count=follow_up_count,
            follow_up_window_seconds=follow_up_window_seconds,
            contract_version=contract_version.strip(),
            status="draft",
        )
        self.session.add(product)
        await self.session.flush()
        return product

    async def create_offer(
        self,
        *,
        product_version_id: UUID,
        channel: str,
        channel_sku: str,
        price_minor: int,
        currency: str,
        enabled: bool = False,
    ) -> ProductOffer:
        product = await self.session.get(ProductVersion, product_version_id)
        if product is None:
            raise CatalogError("product version not found")
        if product.status == "retired":
            raise CatalogError("retired product version cannot receive an offer")
        normalized_channel = channel.strip()
        normalized_sku = channel_sku.strip()
        if not normalized_channel or not normalized_sku:
            raise CatalogError("offer channel and SKU are required")
        if price_minor < 0:
            raise CatalogError("offer price cannot be negative")
        normalized_currency = _currency(currency)
        existing = await self.session.scalar(
            select(ProductOffer).where(
                ProductOffer.channel == normalized_channel,
                ProductOffer.channel_sku == normalized_sku,
            )
        )
        if existing is not None:
            raise CatalogError("channel SKU already exists")
        offer = ProductOffer(
            product_version_id=product.id,
            channel=normalized_channel,
            channel_sku=normalized_sku,
            price_minor=price_minor,
            currency=normalized_currency,
            enabled=enabled,
        )
        self.session.add(offer)
        await self.session.flush()
        return offer

    async def publish_version(self, product_version_id: UUID) -> ProductVersion:
        product = await self.session.get(ProductVersion, product_version_id)
        if product is None:
            raise CatalogError("product version not found")
        if product.status == "active":
            return product
        if product.status != "draft":
            raise CatalogError("product version cannot be published")
        enabled_offer = await self.session.scalar(
            select(ProductOffer.id).where(
                ProductOffer.product_version_id == product.id,
                ProductOffer.enabled.is_(True),
            )
        )
        if enabled_offer is None:
            raise CatalogError("an enabled offer is required before publishing")
        product.status = "active"
        await self.session.flush()
        return product

    async def retire_version(self, product_version_id: UUID) -> ProductVersion:
        product = await self.session.get(ProductVersion, product_version_id)
        if product is None:
            raise CatalogError("product version not found")
        if product.status == "retired":
            return product
        if product.status != "active":
            raise CatalogError("only an active product version can be retired")
        product.status = "retired"
        await self.session.flush()
        return product

    async def set_offer_enabled(
        self,
        offer_id: UUID,
        *,
        enabled: bool,
    ) -> ProductOffer:
        offer = await self.session.get(ProductOffer, offer_id)
        if offer is None:
            raise CatalogError("product offer not found")
        product = await self.session.get(ProductVersion, offer.product_version_id)
        if product is None:
            raise CatalogError("product version not found")
        if enabled and product.status == "retired":
            raise CatalogError("retired product version cannot be enabled")
        offer.enabled = enabled
        await self.session.flush()
        return offer


def _currency(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise CatalogError("currency must be a three-letter code")
    return normalized
