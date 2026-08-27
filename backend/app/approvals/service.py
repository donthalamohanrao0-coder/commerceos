"""Generic approval lifecycle (ADR-005 'explicit customer confirmation'). A
customer's 'Confirm & Pay' click is modeled the same way a merchant-side refund
approval will later be — one mechanism, reused across actor types."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.models import ApprovalRequest
from app.audit.service import AuditService

RequestedBy = Literal["customer", "agent", "merchant_operator"]

DEFAULT_EXPIRY_MINUTES = 15


class ApprovalNotFound(Exception):
    pass


class ApprovalNotPending(Exception):
    pass


class ApprovalService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._audit = AuditService(session)

    async def request(
        self,
        *,
        merchant_id: uuid.UUID,
        requested_action: str,
        requested_by: RequestedBy,
        payload: dict[str, Any],
        session_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
    ) -> ApprovalRequest:
        approval = ApprovalRequest(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            session_id=session_id,
            order_id=order_id,
            requested_action=requested_action,
            requested_by=requested_by,
            payload=payload,
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(minutes=DEFAULT_EXPIRY_MINUTES),
        )
        self._session.add(approval)
        await self._session.flush()

        await self._audit.record(
            merchant_id=merchant_id,
            actor_type="agent" if requested_by == "agent" else "customer",
            session_id=session_id,
            order_id=order_id,
            action="APPROVAL_REQUESTED",
            input={"requested_action": requested_action, **payload},
        )
        return approval

    async def _get_pending(self, merchant_id: uuid.UUID, approval_id: uuid.UUID) -> ApprovalRequest:
        approval = await self._session.get(ApprovalRequest, approval_id)
        if approval is None or approval.merchant_id != merchant_id:
            raise ApprovalNotFound(str(approval_id))
        if approval.status != "pending":
            raise ApprovalNotPending(approval.status)
        if approval.expires_at is not None and approval.expires_at < datetime.now(UTC):
            approval.status = "expired"
            await self._session.flush()
            raise ApprovalNotPending("expired")
        return approval

    async def approve(
        self, merchant_id: uuid.UUID, approval_id: uuid.UUID, *, decided_by: uuid.UUID | None
    ) -> ApprovalRequest:
        approval = await self._get_pending(merchant_id, approval_id)
        approval.status = "approved"
        approval.decided_by = decided_by
        approval.decided_at = datetime.now(UTC)
        await self._session.flush()

        await self._audit.record(
            merchant_id=merchant_id,
            actor_type="customer",
            session_id=approval.session_id,
            order_id=approval.order_id,
            action="APPROVAL_GRANTED",
            result={"approval_id": str(approval.id)},
        )
        return approval

    async def reject(
        self, merchant_id: uuid.UUID, approval_id: uuid.UUID, *, decided_by: uuid.UUID | None
    ) -> ApprovalRequest:
        approval = await self._get_pending(merchant_id, approval_id)
        approval.status = "rejected"
        approval.decided_by = decided_by
        approval.decided_at = datetime.now(UTC)
        await self._session.flush()
        return approval
