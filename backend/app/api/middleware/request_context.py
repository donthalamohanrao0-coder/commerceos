import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import request_id_ctx, trace_id_ctx


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request_id (and reads/propagates trace_id) for correlation across
    logs, audit events, and Langfuse traces (plan.md #32)."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        trace_id = request.headers.get("x-trace-id", request_id)

        request_id_token = request_id_ctx.set(request_id)
        trace_id_token = trace_id_ctx.set(trace_id)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(request_id_token)
            trace_id_ctx.reset(trace_id_token)

        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(round((time.perf_counter() - start) * 1000, 2))
        return response
