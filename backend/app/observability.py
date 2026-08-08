import json
import logging
import re
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
logger = logging.getLogger("mingli.api")


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(message)s")


def _request_id(request: Request) -> str:
    candidate = request.headers.get("x-request-id", "")
    if REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return uuid4().hex


def install_request_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_observability(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = _request_id(request)
        request.state.request_id = request_id
        started = time.perf_counter()

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return response
