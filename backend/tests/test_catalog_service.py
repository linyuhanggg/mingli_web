from __future__ import annotations

from uuid import uuid4

import pytest
from app.commerce import CatalogError, CatalogService
from app.commerce.models import ProductOffer, ProductVersion
from sqlalchemy import select


async def test_catalog_version_requires_an_enabled_offer_before_publish(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        catalog = CatalogService(session)
        family = await catalog.create_family(
            key="bazi-deep-reading",
            label="八字深度解读",
        )
        version = await catalog.create_version(
            family_id=family.id,
            version="v1",
            price_minor=9900,
            currency="CNY",
            contract_version="reading-document-v1",
            follow_up_count=2,
            follow_up_window_seconds=90 * 86400,
        )

        with pytest.raises(CatalogError, match="enabled offer"):
            await catalog.publish_version(version.id)

        await catalog.create_offer(
            product_version_id=version.id,
            channel="closed",
            channel_sku="bazi-deep-reading-v1",
            price_minor=9900,
            currency="CNY",
            enabled=True,
        )
        published = await catalog.publish_version(version.id)

        assert published.id == version.id
        assert published.status == "active"


async def test_catalog_retired_version_keeps_snapshot_and_rejects_new_offers(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        catalog = CatalogService(session)
        family = await catalog.create_family(
            key="ziwei-deep-reading",
            label="紫微深度解读",
        )
        version = await catalog.create_version(
            family_id=family.id,
            version="v1",
            price_minor=12900,
            currency="cny",
            contract_version="reading-document-v1",
        )
        offer = await catalog.create_offer(
            product_version_id=version.id,
            channel="closed",
            channel_sku="ziwei-deep-reading-v1",
            price_minor=12900,
            currency="CNY",
            enabled=True,
        )
        await catalog.publish_version(version.id)

        retired = await catalog.retire_version(version.id)

        assert retired.status == "retired"
        assert retired.price_minor == 12900
        assert retired.currency == "CNY"
        assert retired.contract_version == "reading-document-v1"
        refreshed_offer = await session.get(ProductOffer, offer.id)
        assert refreshed_offer is not None
        assert refreshed_offer.enabled is False
        with pytest.raises(CatalogError, match="retired"):
            await catalog.create_offer(
                product_version_id=version.id,
                channel="another",
                channel_sku="ziwei-deep-reading-v1-another",
                price_minor=12900,
                currency="CNY",
            )


async def test_catalog_can_disable_an_existing_offer_without_changing_version(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        catalog = CatalogService(session)
        family = await catalog.create_family(
            key="qimen-deep-reading",
            label="奇门深度解读",
        )
        version = await catalog.create_version(
            family_id=family.id,
            version="v1",
            price_minor=15900,
            currency="CNY",
            contract_version="reading-document-v1",
        )
        offer = await catalog.create_offer(
            product_version_id=version.id,
            channel="closed",
            channel_sku="qimen-deep-reading-v1",
            price_minor=15900,
            currency="CNY",
            enabled=True,
        )
        await catalog.publish_version(version.id)

        disabled = await catalog.set_offer_enabled(offer.id, enabled=False)

        assert disabled.id == offer.id
        assert disabled.enabled is False
        assert version.status == "active"
        assert version.price_minor == 15900


async def test_catalog_can_append_immutable_versions_on_the_same_family(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        catalog = CatalogService(session)
        family = await catalog.create_family(
            key="liuyao-deep-reading",
            label="六爻深度解读",
        )
        first = await catalog.create_version(
            family_id=family.id,
            version="v1",
            price_minor=7900,
            currency="cny",
            contract_version="reading-document-v1",
            follow_up_count=1,
            follow_up_window_seconds=30 * 86400,
        )
        await catalog.create_offer(
            product_version_id=first.id,
            channel="closed",
            channel_sku="liuyao-deep-reading-v1",
            price_minor=7900,
            currency="CNY",
            enabled=True,
        )
        await catalog.publish_version(first.id)

        second = await catalog.create_version(
            family_id=family.id,
            version="v2",
            price_minor=8900,
            currency="CNY",
            contract_version="reading-document-v1",
            follow_up_count=3,
            follow_up_window_seconds=60 * 86400,
        )

        refreshed_first = await session.get(ProductVersion, first.id)
        assert refreshed_first is not None
        assert refreshed_first.status == "active"
        assert refreshed_first.price_minor == 7900
        assert refreshed_first.currency == "CNY"
        assert refreshed_first.follow_up_count == 1
        assert refreshed_first.follow_up_window_seconds == 30 * 86400
        assert second.status == "draft"
        assert second.price_minor == 8900
        assert second.follow_up_count == 3
        versions = list(
            await session.scalars(
                select(ProductVersion)
                .where(ProductVersion.family_id == family.id)
                .order_by(ProductVersion.version)
            )
        )
        assert [item.version for item in versions] == ["v1", "v2"]


async def test_catalog_rejects_duplicate_family_version_and_channel_sku(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        catalog = CatalogService(session)
        family = await catalog.create_family(
            key="taiyi-deep-reading",
            label="太乙深度解读",
        )
        with pytest.raises(CatalogError, match="already exists"):
            await catalog.create_family(
                key="taiyi-deep-reading",
                label="重复商品族",
            )

        version = await catalog.create_version(
            family_id=family.id,
            version="v1",
            price_minor=9900,
            currency="CNY",
            contract_version="reading-document-v1",
        )
        with pytest.raises(CatalogError, match="already exists"):
            await catalog.create_version(
                family_id=family.id,
                version="v1",
                price_minor=10900,
                currency="CNY",
                contract_version="reading-document-v1",
            )

        await catalog.create_offer(
            product_version_id=version.id,
            channel="closed",
            channel_sku="taiyi-deep-reading-v1",
            price_minor=9900,
            currency="CNY",
        )
        with pytest.raises(CatalogError, match="already exists"):
            await catalog.create_offer(
                product_version_id=version.id,
                channel="closed",
                channel_sku="taiyi-deep-reading-v1",
                price_minor=10900,
                currency="CNY",
            )


async def test_catalog_rejects_invalid_family_version_and_offer_inputs(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        catalog = CatalogService(session)
        with pytest.raises(CatalogError, match="key and label are required"):
            await catalog.create_family(key="  ", label="空白")
        with pytest.raises(CatalogError, match="product family not found"):
            await catalog.create_version(
                family_id=uuid4(),
                version="v1",
                price_minor=100,
                currency="CNY",
                contract_version="reading-document-v1",
            )

        family = await catalog.create_family(
            key="meihua-deep-reading",
            label="梅花深度解读",
        )
        with pytest.raises(CatalogError, match="cannot be negative"):
            await catalog.create_version(
                family_id=family.id,
                version="v1",
                price_minor=-1,
                currency="CNY",
                contract_version="reading-document-v1",
            )
        with pytest.raises(CatalogError, match="three-letter code"):
            await catalog.create_version(
                family_id=family.id,
                version="v1",
                price_minor=100,
                currency="CN",
                contract_version="reading-document-v1",
            )
        with pytest.raises(CatalogError, match="product version and contract version"):
            await catalog.create_version(
                family_id=family.id,
                version="  ",
                price_minor=100,
                currency="CNY",
                contract_version="reading-document-v1",
            )

        version = await catalog.create_version(
            family_id=family.id,
            version="v1",
            price_minor=100,
            currency="CNY",
            contract_version="reading-document-v1",
        )
        with pytest.raises(CatalogError, match="channel and SKU are required"):
            await catalog.create_offer(
                product_version_id=version.id,
                channel=" ",
                channel_sku="meihua-v1",
                price_minor=100,
                currency="CNY",
            )
        with pytest.raises(CatalogError, match="offer price cannot be negative"):
            await catalog.create_offer(
                product_version_id=version.id,
                channel="closed",
                channel_sku="meihua-v1",
                price_minor=-10,
                currency="CNY",
            )


async def test_catalog_cannot_retire_draft_or_republish_retired_and_blocks_reenable(
    database,
) -> None:  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        catalog = CatalogService(session)
        family = await catalog.create_family(
            key="hecan-deep-reading",
            label="合参深度解读",
        )
        version = await catalog.create_version(
            family_id=family.id,
            version="v1",
            price_minor=19900,
            currency="CNY",
            contract_version="reading-document-v1",
        )
        with pytest.raises(CatalogError, match="only an active product version"):
            await catalog.retire_version(version.id)

        offer = await catalog.create_offer(
            product_version_id=version.id,
            channel="closed",
            channel_sku="hecan-deep-reading-v1",
            price_minor=19900,
            currency="CNY",
            enabled=True,
        )
        published = await catalog.publish_version(version.id)
        again = await catalog.publish_version(version.id)
        assert published.status == "active"
        assert again.status == "active"
        assert again.price_minor == 19900
        assert again.contract_version == "reading-document-v1"

        retired = await catalog.retire_version(version.id)
        retired_again = await catalog.retire_version(version.id)
        assert retired.status == "retired"
        assert retired_again.status == "retired"
        stored_offer = await session.get(ProductOffer, offer.id)
        assert stored_offer is not None
        assert stored_offer.enabled is False

        with pytest.raises(CatalogError, match="cannot be published"):
            await catalog.publish_version(version.id)
        with pytest.raises(CatalogError, match="retired product version cannot be enabled"):
            await catalog.set_offer_enabled(offer.id, enabled=True)
