from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import SecretStr

from app.adapters.otp import (
    DisabledOtpDeliveryAdapter,
    FakeOtpDeliveryAdapter,
    OtpDeliveryAdapter,
    ProductionFailClosedOtpDeliveryAdapter,
    SmtpOtpDeliveryAdapter,
)
from app.adapters.runtime import FakeMingliRuntimeAdapter, MingliRuntime
from app.api.errors import ApiProblem
from app.api.health import ReadinessProbe
from app.api.problems import problem_response
from app.api.router import build_api_router
from app.config import Settings, get_settings
from app.database import Database
from app.identity.cookies import clear_device_cookies
from app.identity.otp import InMemoryOtpChallengeStore, InMemoryOtpRequestLimiter
from app.identity.service import random_six_digit_otp_code
from app.network import parse_trusted_proxy_cidrs
from app.observability import configure_logging, install_request_observability
from app.readings.rate_limit import WindowRateLimiter


def create_app(
    *,
    settings: Settings | None = None,
    readiness_probe: ReadinessProbe | None = None,
    database: Database | None = None,
    chart_runtime: MingliRuntime | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_database = database or Database(resolved_settings.database_url)
    owns_database = database is None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        application.state.reading_write_rate_limiter.clear()
        application.state.profile_write_rate_limiter.clear()
        application.state.dogfood_daily_reading_limiter.clear()
        application.state.dogfood_daily_paid_reading_limiter.clear()
        application.state.guest_session_create_rate_limiter.clear()
        application.state.admin_login_rate_limiter.clear()
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
    application.state.chart_runtime = chart_runtime or FakeMingliRuntimeAdapter()
    identity_hash_key = resolved_settings.identity_hash_key.get_secret_value()
    application.state.otp_challenge_store = InMemoryOtpChallengeStore(
        secret=identity_hash_key,
        ttl_seconds=resolved_settings.otp_ttl_seconds,
        cooldown_seconds=resolved_settings.otp_cooldown_seconds,
        max_attempts=resolved_settings.otp_max_attempts,
    )
    application.state.otp_request_limiter = InMemoryOtpRequestLimiter(
        window_seconds=resolved_settings.otp_rate_window_seconds,
        guest_limit=resolved_settings.otp_guest_window_limit,
        network_limit=resolved_settings.otp_network_window_limit,
        destination_limit=resolved_settings.otp_destination_window_limit,
    )
    application.state.guest_session_create_rate_limiter = WindowRateLimiter(
        limit=resolved_settings.guest_session_create_rate_limit,
        window_seconds=resolved_settings.guest_session_create_rate_window_seconds,
    )
    application.state.reading_write_rate_limiter = WindowRateLimiter(
        limit=resolved_settings.reading_write_rate_limit,
        window_seconds=resolved_settings.reading_write_rate_window_seconds,
    )
    application.state.profile_write_rate_limiter = WindowRateLimiter(
        limit=resolved_settings.profile_write_rate_limit,
        window_seconds=resolved_settings.profile_write_rate_window_seconds,
    )
    application.state.dogfood_daily_reading_limiter = WindowRateLimiter(
        limit=resolved_settings.dogfood_daily_reading_limit,
        window_seconds=resolved_settings.dogfood_daily_limit_window_seconds,
    )
    application.state.dogfood_daily_paid_reading_limiter = WindowRateLimiter(
        limit=resolved_settings.dogfood_daily_paid_reading_limit,
        window_seconds=resolved_settings.dogfood_daily_limit_window_seconds,
    )
    application.state.admin_login_rate_limiter = WindowRateLimiter(
        limit=resolved_settings.admin_login_rate_limit,
        window_seconds=resolved_settings.admin_login_rate_window_seconds,
    )
    application.state.trusted_proxy_networks = parse_trusted_proxy_cidrs(
        resolved_settings.trusted_proxy_cidrs
    )
    otp_delivery: OtpDeliveryAdapter
    if resolved_settings.environment == "production":
        otp_delivery = ProductionFailClosedOtpDeliveryAdapter()
    elif resolved_settings.otp_adapter == "fake":
        otp_delivery = FakeOtpDeliveryAdapter()
    elif resolved_settings.otp_adapter == "smtp":
        otp_delivery = SmtpOtpDeliveryAdapter(
            sender=resolved_settings.smtp_sender or "",
            host=resolved_settings.smtp_host or "",
            port=resolved_settings.smtp_port,
            username=resolved_settings.smtp_username or SecretStr(""),
            password=resolved_settings.smtp_password or SecretStr(""),
            security=resolved_settings.smtp_security,
        )
    else:
        otp_delivery = DisabledOtpDeliveryAdapter()
    application.state.otp_delivery = otp_delivery
    application.state.otp_code_factory = (
        (lambda: resolved_settings.fake_otp_code)
        if resolved_settings.otp_adapter == "fake"
        else random_six_digit_otp_code
    )

    @application.exception_handler(ApiProblem)
    async def api_problem_handler(request: Request, error: ApiProblem) -> JSONResponse:
        response = problem_response(
            request,
            status=error.status,
            title=error.title,
            problem_type=error.problem_type,
            detail=error.detail,
            headers=error.headers,
        )
        if error.clear_device_cookies:
            clear_device_cookies(response, settings=request.app.state.settings)
        return response

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

    base_openapi = application.openapi

    def openapi_without_validation_422() -> dict[str, Any]:
        document = base_openapi()
        for path in document.get("paths", {}).values():
            for operation in path.values():
                operation.get("responses", {}).pop("422", None)
        return document

    cast(Any, application).openapi = openapi_without_validation_422
    return application


app = create_app()
