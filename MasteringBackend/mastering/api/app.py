try:
    from fastapi import FastAPI
except Exception:  # pragma: no cover
    FastAPI = None

if FastAPI is not None:
    from fastapi.middleware.cors import CORSMiddleware

    from mastering.api.routers.mastering import router as mastering_router

    app = FastAPI(title="MasteringBackend API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(mastering_router, prefix="/api/v1")
else:  # pragma: no cover
    app = None

