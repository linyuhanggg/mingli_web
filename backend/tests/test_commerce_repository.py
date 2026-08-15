import pytest
from app.commerce.repository import CommerceRepository
from app.identity.models import User


async def test_append_only_entitlement_repository_projects_events(database):  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        repository = CommerceRepository(session)

        await repository.append_entitlement_event(
            entitlement_id="ent-1",
            owner_user_id=user.id,
            kind="GRANT",
            quantity=1,
            source_type="payment",
            source_ref="payment-1",
            target_ref="reading-1",
        )
        await repository.append_entitlement_event(
            entitlement_id="ent-1",
            owner_user_id=user.id,
            kind="RESERVE",
            quantity=1,
            source_type="reading",
            source_ref="reading-1",
            target_ref="reading-1",
        )
        projection = await repository.project(
            entitlement_id="ent-1",
            owner_user_id=user.id,
        )
        assert projection.available == 0
        assert projection.reserved == 1


async def test_repository_rejects_event_replay_and_invalid_lifecycle(database):  # type: ignore[no-untyped-def]
    async with database.sessions() as session:
        user = User()
        session.add(user)
        await session.flush()
        repository = CommerceRepository(session)
        await repository.append_entitlement_event(
            entitlement_id="ent-1",
            owner_user_id=user.id,
            kind="GRANT",
            quantity=1,
            source_type="payment",
            source_ref="payment-1",
        )

        with pytest.raises(ValueError, match="requires reserved"):
            await repository.append_entitlement_event(
                entitlement_id="ent-1",
                owner_user_id=user.id,
                kind="CONSUME",
                quantity=1,
                source_type="reading",
                source_ref="reading-1",
            )

        with pytest.raises(ValueError, match="source_ref"):
            await repository.append_entitlement_event(
                entitlement_id="ent-1",
                owner_user_id=user.id,
                kind="GRANT",
                quantity=1,
                source_type="payment",
                source_ref="payment-1",
            )
