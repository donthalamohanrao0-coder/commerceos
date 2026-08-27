"""Sentry wiring — initialized from day one; no-ops safely if SENTRY_DSN is unset (local dev)."""

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.core.config import get_settings


def init_sentry() -> None:
    settings = get_settings()
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[FastApiIntegration(), CeleryIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,  # never send unnecessary PII (secrets-and-data-protection.md #7)
    )
