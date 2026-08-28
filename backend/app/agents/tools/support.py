"""Support-agent tools: read-only order lookup, shipping status, and knowledge
search. No money actions — the support flow cannot mutate commerce state.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from pydantic import BaseModel
from sqlalchemy import select

from app.agents.context import ToolContext
from app.agents.tools.base import ToolRegistry
from app.agents.tools.shopping import KnowledgeSearchTool
from app.domains.orders.models import Order

_SHIPPING_BY_STATUS = {
    "created": "Order placed. Payment not yet completed.",
    "payment_pending": "Awaiting payment. Nothing has shipped.",
    "payment_processing": "Payment is being confirmed.",
    "paid": "Payment received. The order is being prepared for dispatch.",
    "fulfilled": "Shipped. Tracking is available from the carrier.",
    "cancelled": "This order was cancelled.",
    "refund_requested": "A refund has been requested for this order.",
    "refund_processing": "The refund is being processed.",
    "refunded": "This order was refunded.",
    "failed": "The order could not be completed.",
}


async def _find_order(ctx: ToolContext, ref: str) -> Order | None:
    try:
        order = await ctx.session.get(Order, uuid.UUID(ref))
        if order is not None and order.merchant_id == ctx.merchant_id:
            return order
    except ValueError:
        pass
    stmt = select(Order).where(
        Order.merchant_id == ctx.merchant_id, Order.order_number == ref.upper()
    )
    if ctx.customer_id is not None:
        stmt = stmt.where(Order.customer_id == ctx.customer_id)
    found: Order | None = await ctx.session.scalar(stmt)
    return found


class OrderLookupTool:
    name: ClassVar[str] = "order_lookup"
    description: ClassVar[str] = (
        "Look up an order by its order number (e.g. ORD-1002) or id. Returns status and totals."
    )

    class Args(BaseModel):
        order_ref: str

    async def run(self, ctx: ToolContext, args: Args) -> dict[str, Any]:
        order = await _find_order(ctx, args.order_ref.strip())
        if order is None:
            return {"error": "order_not_found", "order_ref": args.order_ref}
        return {
            "order_number": order.order_number,
            "status": order.status,
            "subtotal_paise": order.subtotal_paise,
            "discount_paise": order.discount_paise,
            "shipping_paise": order.shipping_paise,
            "total_paise": order.total_paise,
            "placed_at": order.created_at.isoformat(),
        }


class ShippingStatusTool:
    name: ClassVar[str] = "shipping_status"
    description: ClassVar[str] = "Plain-language delivery status for an order."

    class Args(BaseModel):
        order_ref: str

    async def run(self, ctx: ToolContext, args: Args) -> dict[str, Any]:
        order = await _find_order(ctx, args.order_ref.strip())
        if order is None:
            return {"error": "order_not_found", "order_ref": args.order_ref}
        return {
            "order_number": order.order_number,
            "status": order.status,
            "shipping_status": _SHIPPING_BY_STATUS.get(order.status, "Status unavailable."),
        }


def build_support_registry() -> ToolRegistry:
    return ToolRegistry([OrderLookupTool(), ShippingStatusTool(), KnowledgeSearchTool()])
