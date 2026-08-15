"""Private account projection for Reading Root and version history."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import database_session, mark_private, require_device_session
from app.identity.models import DeviceSession
from app.readings.api_schemas import AccountHistoryResponse
from app.readings.service import ReadingService

router = APIRouter(tags=["Identity"])


@router.get(
    "/account/history",
    operation_id="listAccountHistory",
    response_model=AccountHistoryResponse,
)
async def list_account_history(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    device_session: DeviceSession = Depends(require_device_session),
) -> AccountHistoryResponse:
    history = await ReadingService(
        session,
        request.app.state.settings,
    ).list_account_history(device_session.user_id)
    mark_private(response)
    return history
