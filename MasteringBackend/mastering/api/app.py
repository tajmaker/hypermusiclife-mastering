import logging
import time
import uuid

try:
    from fastapi import FastAPI
except Exception:  # pragma: no cover
    FastAPI = None

if FastAPI is not None:
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.middleware.cors import CORSMiddleware
    from starlette.exceptions import HTTPException as StarletteHTTPException

    from mastering.api.errors import (
        http_exception_handler,
        unexpected_exception_handler,
        validation_exception_handler,
    )
    from mastering.api.routers.mastering import router as mastering_router

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger = logging.getLogger(__name__)

    app = FastAPI(title="MasteringBackend API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        started_at = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
            },
        )
        return response

    app.include_router(mastering_router, prefix="/api/v1")
else:  # pragma: no cover
    app = None

