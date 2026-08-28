from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.otel import init_otel
from app.core.sentry import init_sentry


def create_app() -> FastAPI:
    settings = get_settings()

    configure_logging()
    init_sentry()  # no-op until SENTRY_DSN is set

    app = FastAPI(title=settings.app_name)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    init_otel(app)  # exports to console until OTEL_EXPORTER_OTLP_ENDPOINT is set

    return app


app = create_app()
