from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import Owner, database_session, mark_private, require_owner_csrf
from app.api.errors import ApiProblem
from app.charts.api_schemas import (
    BaziChartSupplyInputRequest,
    BaziChartSyncRequest,
    BaziChartSyncResponse,
)
from app.charts.service import (
    ChartProfileNotFoundError,
    ChartService,
)
from app.charts.sessions import (
    ChartHandleGoneError,
    ChartHandleNotFoundError,
    ChartIdempotencyConflictError,
    ChartInputInvalidError,
    ChartPrepareStoppedError,
    ChartRuntimeUnavailableError,
    ChartSessionError,
)

router = APIRouter(prefix="/charts", tags=["Charts"])


def _service(request: Request, session: AsyncSession) -> ChartService:
    return ChartService(
        session,
        request.app.state.settings,
        request.app.state.chart_sessions,
    )


def _chart_problem(error: ChartSessionError) -> ApiProblem:
    if isinstance(error, ChartIdempotencyConflictError):
        return ApiProblem(status=409, title="Idempotency-Key conflict")
    if isinstance(error, ChartHandleNotFoundError):
        return ApiProblem(status=404, title="Chart handle not found")
    if isinstance(error, ChartHandleGoneError):
        return ApiProblem(status=410, title="Chart handle expired")
    if isinstance(error, ChartInputInvalidError):
        return ApiProblem(status=400, title="Invalid chart input")
    if isinstance(error, ChartPrepareStoppedError):
        status_code = 409 if error.reason == "conflict" else 400
        return ApiProblem(status=status_code, title="Chart calculation stopped")
    if isinstance(error, ChartRuntimeUnavailableError):
        return ApiProblem(status=503, title="Chart Runtime unavailable")
    return ApiProblem(status=500, title="Chart request failed")


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
    service = _service(request, session)
    try:
        result = await service.sync_bazi(
            owner,
            profile_version_id=payload.profile_version_id,
            idempotency_key=idempotency_key,
        )
    except ChartProfileNotFoundError as error:
        raise ApiProblem(status=404, title="Profile Version not found") from error
    except ChartSessionError as error:
        raise _chart_problem(error) from error
    await session.commit()
    mark_private(response)
    return result


@router.post(
    "/bazi/sync/{chart_handle}/input",
    operation_id="supplyBaziChartInput",
    response_model=BaziChartSyncResponse,
)
async def supply_bazi_chart_input(
    chart_handle: str,
    request: Request,
    response: Response,
    payload: BaziChartSupplyInputRequest,
    session: AsyncSession = Depends(database_session),
    owner: Owner = Depends(require_owner_csrf),
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=128,
    ),
) -> BaziChartSyncResponse:
    service = _service(request, session)
    try:
        result = await service.supply_input(
            owner,
            chart_handle=chart_handle,
            values=payload.values,
            idempotency_key=idempotency_key,
        )
    except ChartSessionError as error:
        raise _chart_problem(error) from error
    await session.commit()
    mark_private(response)
    return result
