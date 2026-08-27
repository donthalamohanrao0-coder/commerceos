"""AuditService — every domain service calls this at the point of state mutation,
not from API routes (coding-standards.md: "services own business workflows").

Events use the vocabulary from plan.md #18: USER_MESSAGE, PRODUCT_SEARCH,
PRODUCT_RECOMMENDED, CART_UPDATED, UPSELL_PROPOSED, DISCOUNT_CALCULATED,
DISCOUNT_APPLIED, ORDER_CREATED, APPROVAL_REQUESTED, APPROVAL_GRANTED,
PAYMENT_CREATED, PAYMENT_FAILED, PAYMENT_SUCCEEDED, REFUND_REQUESTED,
REFUND_COMPLETED, AGENT_ERROR.
"""

import uuid
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent

ActorType = Literal["customer", "agent", "merchant_user", "system", "external_agent"]


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        merchant_id: uuid.UUID,
        actor_type: ActorType,
        action: str,
        actor_id: str | None = None,
        session_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
        input: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        policy_decision: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            session_id=session_id,
            order_id=order_id,
            action=action,
            input=input,
            result=result,
            policy_decision=policy_decision,
        )
        self._session.add(event)
        await self._session.flush()
        return event
