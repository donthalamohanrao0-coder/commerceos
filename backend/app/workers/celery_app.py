"""Celery application. Broker/backend come from settings (Redis by default).

Background work that must not block a request or a webhook: knowledge ingestion,
periodic growth-analytics refresh, and (later) payment reconciliation sweeps.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "commerceos",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_max_tasks_per_child=200,
    result_expires=3600,
)
