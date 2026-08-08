from fastapi import Request
from fastapi.responses import JSONResponse


def problem_response(
    request: Request,
    *,
    status: int,
    title: str,
    problem_type: str = "about:blank",
    detail: str | None = None,
) -> JSONResponse:
    body: dict[str, object] = {
        "type": problem_type,
        "title": title,
        "status": status,
        "request_id": request.state.request_id,
    }
    if detail is not None:
        body["detail"] = detail
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
    )
