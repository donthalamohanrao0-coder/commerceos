import logging
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)
merchant_id_ctx: ContextVar[str | None] = ContextVar("merchant_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)
agent_session_id_ctx: ContextVar[str | None] = ContextVar("agent_session_id", default=None)
order_id_ctx: ContextVar[str | None] = ContextVar("order_id", default=None)

_REDACT_KEYS = {"authorization", "cookie", "api_key", "secret", "password", "token"}


class ContextFilter(logging.Filter):
    """Injects correlation ids into every log record (plan.md #32)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        record.trace_id = trace_id_ctx.get()
        record.merchant_id = merchant_id_ctx.get()
        record.user_id = user_id_ctx.get()
        record.agent_session_id = agent_session_id_ctx.get()
        record.order_id = order_id_ctx.get()
        return True


class RedactingJsonFormatter(JsonFormatter):
    """Never let secrets/credentials leak into logs (secrets-and-data-protection.md #3)."""

    def process_log_record(self, log_record: dict[str, object]) -> dict[str, object]:
        for key in list(log_record.keys()):
            if key.lower() in _REDACT_KEYS:
                log_record[key] = "[REDACTED]"
        result: dict[str, object] = super().process_log_record(log_record)
        return result


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(ContextFilter())
    handler.setFormatter(
        RedactingJsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s "
            "%(request_id)s %(trace_id)s %(merchant_id)s %(user_id)s "
            "%(agent_session_id)s %(order_id)s"
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
