from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import database_session
from app.config import Settings
from app.identity.cookies import GUEST_COOKIE, set_guest_cookies
from app.identity.repository import IdentityRepository
from app.identity.schemas import GuestSessionResponse
from app.identity.service import GuestSessionService

router = APIRouter(prefix="/guest-sessions", tags=["Identity"])


@router.post(
    "",
    operation_id="createGuestSession",
    response_model=GuestSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_guest_session(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(database_session),
    existing_token: str | None = Cookie(default=None, alias=GUEST_COOKIE),
) -> GuestSessionResponse:
    service = GuestSessionService(IdentityRepository(session))
    created = await service.create(existing_token)
    await session.commit()

    settings: Settings = request.app.state.settings
    set_guest_cookies(
        response,
        settings=settings,
        guest_token=created.token,
        csrf_token=created.csrf_token,
        expires_at=created.expires_at,
    )
    return GuestSessionResponse(
        expires_at=created.expires_at,
        csrf_token=created.csrf_token,
    )
