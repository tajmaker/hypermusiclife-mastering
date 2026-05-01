import logging

try:
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException
except Exception:  # pragma: no cover
    Request = None
    RequestValidationError = None
    JSONResponse = None
    StarletteHTTPException = None

logger = logging.getLogger(__name__)

STATUS_ERROR_CODES = {
    400: "bad_request",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "too_many_requests",
    500: "internal_error",
}


def error_detail(message: str, code: str | None = None) -> dict:
    return {"error": {"code": code or "bad_request", "message": message}}


if Request is not None:

    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        detail = exc.detail
        status_code = exc.status_code

        if isinstance(detail, dict) and "error" in detail:
            payload = detail
        else:
            message = str(detail) if detail else "Request failed"
            code = STATUS_ERROR_CODES.get(status_code, "http_error")
            payload = error_detail(message, code)

        if request_id:
            payload["error"]["request_id"] = request_id

        return JSONResponse(status_code=status_code, content=payload)

    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        payload = error_detail("Invalid request payload", "validation_error")
        payload["error"]["details"] = exc.errors()
        if request_id:
            payload["error"]["request_id"] = request_id
        return JSONResponse(status_code=422, content=payload)

    async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Unhandled API error", extra={"request_id": request_id})
        payload = error_detail("Internal server error", "internal_error")
        if request_id:
            payload["error"]["request_id"] = request_id
        return JSONResponse(status_code=500, content=payload)
