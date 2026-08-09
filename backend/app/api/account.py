from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import database_session, mark_private, require_device_session
from app.api.errors import ApiProblem
from app.identity.models import DeviceSession
from app.identity.repository import IdentityRepository
from app.identity.schemas import AccountResponse, LoginIdentitySummary

router = APIRouter(tags=["Identity"])


@router.get("/account", operation_id="getAccount", response_model=AccountResponse)
async def get_account(
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
) -> AccountResponse:
    repository = IdentityRepository(session)
    user = await repository.get_user(device_session.user_id)
    if user is None or user.status != "active":
        raise ApiProblem(status=401, title="Authentication required")
    identities = await repository.list_identities(user.id)
    mark_private(response)
    return AccountResponse(
        user_id=user.id,
        identities=[LoginIdentitySummary.model_validate(identity) for identity in identities],
    )
