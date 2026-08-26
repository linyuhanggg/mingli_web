from fastapi import Request
from fastapi.responses import JSONResponse


def problem_response(
    request: Request,
    *,
    status: int,
    title: str,
    problem_type: str = "about:blank",
    detail: str | None = None,
    code: str | None = None,
    headers: dict[str, str] | None = None,
    extensions: dict[str, object] | None = None,
) -> JSONResponse:
    body: dict[str, object] = {
        "type": problem_type,
        "title": title,
        "status": status,
        "request_id": request.state.request_id,
    }
    if detail is not None:
        body["detail"] = detail
    if code is not None:
        body["code"] = code
    if extensions:
        for key, value in extensions.items():
            if key not in body:
                body[key] = value
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
        headers=headers,
    )
