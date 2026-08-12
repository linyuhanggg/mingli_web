from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import Owner, database_session, mark_private, require_owner_csrf
from app.api.errors import ApiProblem
from app.charts.api_schemas import BaziChartSyncRequest, BaziChartSyncResponse
from app.charts.service import (
    ChartPrepareStoppedError,
    ChartProfileNotFoundError,
    ChartService,
)

router = APIRouter(prefix="/charts", tags=["Charts"])


@router.post(
    "/bazi/sync",
    operation_id="syncBaziChart",
    response_model=BaziChartSyncResponse,
)
async def sync_bazi_chart(
    request: Request,
    response: Response,
    payload: BaziChartSyncRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> BaziChartSyncResponse:
    del idempotency_key
    service = ChartService(
        session,
        request.app.state.settings,
        request.app.state.chart_runtime,
    )
    try:
        result = await service.sync_bazi(
            owner,
            profile_version_id=payload.profile_version_id,
        )
    except ChartProfileNotFoundError as error:
        raise ApiProblem(status=404, title="Profile Version not found") from error
    except ChartPrepareStoppedError as error:
        raise ApiProblem(status=409, title="Chart calculation stopped") from error
    await session.commit()
    mark_private(response)
    return result
