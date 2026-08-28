import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.middleware.request_context import RequestContextMiddleware
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.otel import init_otel
from app.core.sentry import init_sentry

_log = logging.getLogger(__name__)


def _assert_production_ready(settings: Settings) -> None:
    """Fail fast rather than boot a production instance that silently accepts any
    bearer token (FakeTokenVerifier) or fakes payments (FakeRazorpayClient).
    Non-production keeps the credential-gated fakes for local dev / tests."""
    if not settings.is_production:
        return

    # Hard fail: these make a production instance actively unsafe or non-functional.
    fatal: list[str] = []
    if not (settings.supabase_url and settings.supabase_anon_key):
        fatal.append("SUPABASE_URL + SUPABASE_ANON_KEY (auth would accept ANY bearer token)")
    if "@localhost" in settings.database_url or "commerceos:commerceos" in settings.database_url:
        fatal.append("DATABASE_URL (still points at the local dev database)")
    if fatal:
        raise RuntimeError(
            "ENVIRONMENT=production but these are unset/insecure: " + "; ".join(fatal)
        )

    # Loud warning: the app boots but a capability is running on its Fake.
    for cond, msg in (
        (
            not (settings.razorpay_key_id and settings.razorpay_key_secret),
            "RAZORPAY keys unset — payments run on FakeRazorpayClient.",
        ),
        (not settings.openai_api_key, "OPENAI_API_KEY unset — the agent runs on canned replies."),
        (not settings.pinecone_api_key, "PINECONE_API_KEY unset — knowledge retrieval disabled."),
    ):
        if cond:
            _log.warning("production: %s", msg)


def create_app() -> FastAPI:
    settings = get_settings()

    configure_logging()
    _assert_production_ready(settings)
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
