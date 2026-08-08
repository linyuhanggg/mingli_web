from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.adapters.otp import DisabledOtpDeliveryAdapter, FakeOtpDeliveryAdapter
from app.api.errors import ApiProblem
from app.api.health import ReadinessProbe
from app.api.problems import problem_response
from app.api.router import build_api_router
from app.config import Settings, get_settings
from app.database import Database
from app.identity.otp import InMemoryOtpChallengeStore
from app.observability import configure_logging, install_request_observability


def create_app(
    *,
    settings: Settings | None = None,
    readiness_probe: ReadinessProbe | None = None,
    database: Database | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_database = database or Database(resolved_settings.database_url)
    owns_database = database is None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if owns_database:
            await resolved_database.dispose()

    application = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.database = resolved_database
    application.state.session_factory = resolved_database.sessions
    identity_hash_key = resolved_settings.identity_hash_key.get_secret_value()
    application.state.otp_challenge_store = InMemoryOtpChallengeStore(
        secret=identity_hash_key,
        ttl_seconds=resolved_settings.otp_ttl_seconds,
        cooldown_seconds=resolved_settings.otp_cooldown_seconds,
        max_attempts=resolved_settings.otp_max_attempts,
    )
    application.state.otp_delivery = (
        FakeOtpDeliveryAdapter()
        if resolved_settings.otp_adapter == "fake"
        else DisabledOtpDeliveryAdapter()
    )

    @application.exception_handler(ApiProblem)
    async def api_problem_handler(request: Request, error: ApiProblem) -> JSONResponse:
        return problem_response(
            request,
            status=error.status,
            title=error.title,
            problem_type=error.problem_type,
            detail=error.detail,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_problem_handler(
        request: Request,
        _: RequestValidationError,
    ) -> JSONResponse:
        return problem_response(
            request,
            status=400,
            title="Invalid request",
            problem_type="urn:fateradar:problem:invalid-request",
        )

    configure_logging(resolved_settings.log_level)
    install_request_observability(application)
    application.include_router(build_api_router(readiness_probe or resolved_database.probe))
    return application


app = create_app()
