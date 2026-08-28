"""Maps domain exceptions to the predictable success/error envelope from
api-standards.md. Never expose internal exception messages to clients
(coding-standards.md #Error Handling)."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.agent_commerce.keys import AgentKeyScopeDenied, InvalidAgentKey
from app.agent_commerce.service import AgentOrderNotFound
from app.agents.service import AgentSessionNotFound, ApprovalMismatch
from app.approvals.service import ApprovalNotFound, ApprovalNotPending
from app.core.idempotency import IdempotencyConflict
from app.core.logging import request_id_ctx
from app.core.rate_limit import RateLimitExceeded
from app.domains.campaigns.exceptions import CampaignNotFound
from app.domains.cart.exceptions import CartItemNotFound, CartNotFound
from app.domains.catalog.exceptions import ProductNotFound
from app.domains.catalog.inventory_service import InsufficientStock
from app.domains.orders.exceptions import EmptyCart, OrderNotFound
from app.domains.payments.exceptions import (
    PaymentNotFound,
    PaymentPolicyDenied,
    PaymentVerificationFailed,
)


def _error_body(code: str, message: str) -> dict:
    return {
        "error": {"code": code, "message": message},
        "request_id": request_id_ctx.get() or str(uuid.uuid4()),
    }


_EXCEPTION_MAP: list[tuple[type[Exception], int, str]] = [
    (AgentSessionNotFound, 404, "AGENT_SESSION_NOT_FOUND"),
    (ApprovalMismatch, 404, "APPROVAL_NOT_FOUND"),
    (AgentOrderNotFound, 404, "ORDER_NOT_FOUND"),
    (CampaignNotFound, 404, "CAMPAIGN_NOT_FOUND"),
    (InvalidAgentKey, 401, "INVALID_AGENT_KEY"),
    (AgentKeyScopeDenied, 403, "AGENT_SCOPE_DENIED"),
    (ProductNotFound, 404, "PRODUCT_NOT_FOUND"),
    (CartNotFound, 404, "CART_NOT_FOUND"),
    (CartItemNotFound, 404, "CART_ITEM_NOT_FOUND"),
    (OrderNotFound, 404, "ORDER_NOT_FOUND"),
    (PaymentNotFound, 404, "PAYMENT_NOT_FOUND"),
    (ApprovalNotFound, 404, "APPROVAL_NOT_FOUND"),
    (EmptyCart, 422, "CART_EMPTY"),
    (InsufficientStock, 409, "INSUFFICIENT_STOCK"),
    (ApprovalNotPending, 409, "APPROVAL_NOT_PENDING"),
    (IdempotencyConflict, 409, "IDEMPOTENCY_KEY_CONFLICT"),
    (PaymentPolicyDenied, 403, "PAYMENT_POLICY_DENIED"),
    (PaymentVerificationFailed, 402, "PAYMENT_VERIFICATION_FAILED"),
    (RateLimitExceeded, 429, "RATE_LIMIT_EXCEEDED"),
]


def register_exception_handlers(app: FastAPI) -> None:
    for exc_type, status_code, code in _EXCEPTION_MAP:

        def make_handler(
            status_code: int = status_code, code: str = code
        ) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
            async def handler(request: Request, exc: Exception) -> JSONResponse:
                return JSONResponse(status_code=status_code, content=_error_body(code, str(exc)))

            return handler

        app.add_exception_handler(exc_type, make_handler())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "An unexpected error occurred."),
        )
