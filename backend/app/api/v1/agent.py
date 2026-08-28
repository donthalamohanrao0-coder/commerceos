"""Agent API — drive any agent workflow (shopping / support / growth) over HTTP.

POST /agent/sessions                              -> start a session (explicit or auto-routed)
POST /agent/sessions/{id}/messages               -> send a turn
POST /agent/sessions/{id}/approvals/{approval_id} -> approve / decline a gated action
"""

import json
import uuid
from collections.abc import AsyncIterator
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_service import AgentSessionNotFound, BaseAgentService
from app.agents.growth_service import GrowthAgentService
from app.agents.models import AgentSession
from app.agents.service import ShoppingAgentService
from app.agents.supervisor import classify_workflow
from app.agents.support_service import SupportAgentService
from app.api.deps import get_current_merchant_id, get_tenant_session
from app.api.envelope import ok
from app.domains.cart.models import CartItem
from app.domains.catalog.models import Product, ProductVariant
from app.integrations.openai.chat import get_chat_client

router = APIRouter(prefix="/agent", tags=["agent"])

_SESSION = Depends(get_tenant_session)
_MERCHANT = Depends(get_current_merchant_id)

_SERVICES: dict[str, type[BaseAgentService]] = {
    "shopping": ShoppingAgentService,
    "support": SupportAgentService,
    "growth": GrowthAgentService,
}


class StartSessionRequest(BaseModel):
    workflow: Literal["shopping", "support", "growth", "auto"] = "shopping"
    first_message: str | None = None  # used only when workflow == "auto"
    customer_id: uuid.UUID | None = None
    channel: str = "web_chat"


class MessageRequest(BaseModel):
    text: str


class ApprovalDecisionRequest(BaseModel):
    approved: bool


async def _service_for_session(session: AsyncSession, session_id: uuid.UUID) -> BaseAgentService:
    row = await session.get(AgentSession, session_id)
    workflow = row.workflow if row else "shopping"
    return _SERVICES.get(workflow, ShoppingAgentService)(session)


@router.post("/sessions")
async def start_session(
    body: StartSessionRequest,
    session: AsyncSession = _SESSION,
    merchant_id: uuid.UUID = _MERCHANT,
) -> dict:
    workflow = body.workflow
    if workflow == "auto":
        workflow = await classify_workflow(
            body.first_message or "", chat_client=get_chat_client()
        )
    service_cls = _SERVICES[workflow]
    async with session.begin():
        agent_session = await service_cls(session).start_session(
            merchant_id=merchant_id, customer_id=body.customer_id, channel=body.channel
        )
    return ok(
        {"session_id": str(agent_session.id), "workflow": workflow, "status": agent_session.status}
    )


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    body: MessageRequest,
    session: AsyncSession = _SESSION,
    merchant_id: uuid.UUID = _MERCHANT,
) -> dict:
    async with session.begin():
        service = await _service_for_session(session, session_id)
        result = await service.send_message(
            merchant_id=merchant_id, session_id=session_id, text=body.text
        )
    return ok(
        {
            "session_id": str(result.session_id),
            "session_status": result.session_status,
            "assistant": result.assistant_text,
            "pending_approval": result.pending_approval,
            "tool_trace": result.tool_trace,
        }
    )


@router.get("/sessions/{session_id}/cart")
async def get_session_cart(
    session_id: uuid.UUID,
    session: AsyncSession = _SESSION,
    merchant_id: uuid.UUID = _MERCHANT,
) -> dict:
    """The current cart for a chat session (the agent stores its id on the
    session). Read-only — the agent still owns all cart mutations."""
    async with session.begin():
        agent_session = await session.get(AgentSession, session_id)
        if agent_session is None or agent_session.merchant_id != merchant_id:
            raise AgentSessionNotFound(str(session_id))

        raw = agent_session.session_metadata.get("cart_id")
        if not raw:
            return ok({"cart_id": None, "items": [], "item_count": 0, "subtotal_paise": 0})

        cart_id = uuid.UUID(str(raw))
        rows = (
            await session.execute(
                select(
                    CartItem.quantity,
                    CartItem.unit_price_paise,
                    Product.name,
                    Product.category,
                    Product.image_key,
                )
                .join(ProductVariant, ProductVariant.id == CartItem.product_variant_id)
                .join(Product, Product.id == ProductVariant.product_id)
                .where(CartItem.cart_id == cart_id)
                .order_by(Product.name)
            )
        ).all()

    items = [
        {
            "name": name,
            "category": category,
            "image_key": image_key,
            "quantity": qty,
            "unit_price_paise": unit,
            "line_total_paise": qty * unit,
        }
        for qty, unit, name, category, image_key in rows
    ]
    return ok(
        {
            "cart_id": str(cart_id),
            "items": items,
            "item_count": sum(i["quantity"] for i in items),
            "subtotal_paise": sum(i["line_total_paise"] for i in items),
        }
    )


@router.post("/sessions/{session_id}/messages/stream")
async def stream_message(
    session_id: uuid.UUID,
    body: MessageRequest,
    session: AsyncSession = _SESSION,
    merchant_id: uuid.UUID = _MERCHANT,
) -> StreamingResponse:
    """Same turn as ``/messages`` but Server-Sent Events: one ``data:`` frame per
    progress event, terminal frame is ``{"type": "done", ...}`` with the full turn
    result (or ``{"type": "error"}``)."""

    def _frame(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    async def frames() -> AsyncIterator[str]:
        try:
            async with session.begin():
                service = await _service_for_session(session, session_id)
                async for event in service.stream_message(
                    merchant_id=merchant_id, session_id=session_id, text=body.text
                ):
                    yield _frame(event)
        except AgentSessionNotFound:
            yield _frame({"type": "error", "message": "Session not found."})
        except Exception:  # noqa: BLE001 - the stream has started; report cleanly
            yield _frame({"type": "error", "message": "The assistant hit an error."})

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/sessions/{session_id}/approvals/{approval_id}")
async def resolve_approval(
    session_id: uuid.UUID,
    approval_id: uuid.UUID,
    body: ApprovalDecisionRequest,
    session: AsyncSession = _SESSION,
    merchant_id: uuid.UUID = _MERCHANT,
) -> dict:
    async with session.begin():
        service = await _service_for_session(session, session_id)
        result = await service.resolve_approval(
            merchant_id=merchant_id,
            session_id=session_id,
            approval_id=approval_id,
            approved=body.approved,
        )
    return ok(
        {
            "session_id": str(result.session_id),
            "session_status": result.session_status,
            "assistant": result.assistant_text,
            "tool_trace": result.tool_trace,
        }
    )
