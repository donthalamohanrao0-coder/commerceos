"""Predictable success envelope from api-standards.md: {"data": {...}, "request_id": "..."}."""

import uuid
from typing import Any

from app.core.logging import request_id_ctx


def ok(data: Any) -> dict:
    return {"data": data, "request_id": request_id_ctx.get() or str(uuid.uuid4())}
