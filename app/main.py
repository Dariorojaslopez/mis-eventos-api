from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestIdMiddleware

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        environment=settings.environment,
        version=settings.app_version,
    )
    yield
    await engine.dispose()
    logger.info("application_shutdown")


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API enterprise para gestión de eventos — Mis Eventos",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(RequestIdMiddleware)

    application.add_exception_handler(AppException, app_exception_handler)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)

    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.get("/health", tags=["Health"], include_in_schema=False)
    async def root_health() -> dict[str, str]:
        return {"status": "healthy", "service": settings.app_name}

    return application


app = create_app()
