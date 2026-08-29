"""Per-run context handed to every tool: the tenant-scoped DB session plus the
identity the graph is acting for. Tools never accept merchant_id from the model —
it comes from here, derived server-side (security-architecture.md #4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ToolContext:
    session: AsyncSession
    merchant_id: uuid.UUID
    agent_session_id: uuid.UUID
    customer_id: uuid.UUID | None = None
    customer_segment: str | None = None
    merchant_namespace: str = ""
    # mutated by cart tools so later tools in the same turn see the active cart
    cart_id: uuid.UUID | None = None
    # {name, phone, email, line1, line2, city, state, postal_code, country} —
    # set by save_shipping_details, read by order_create in the same turn
    shipping_address: dict[str, str] | None = None
    # set by a tool that needs the human before the backend will act
    pending_approval: dict[str, object] | None = field(default=None)
