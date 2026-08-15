from __future__ import annotations

import pytest
from app.commerce import CatalogError, CatalogService


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
        await catalog.create_offer(
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
