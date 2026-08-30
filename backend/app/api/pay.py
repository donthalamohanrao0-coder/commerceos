"""Hosted checkout page for an external AI buyer.

An AI buyer has no browser to run Razorpay Checkout, and Razorpay test mode caps
an account at 30 payment links — so instead of a Payment Link we serve our own
one-page checkout. ``request_payment`` hands the buyer ``{base}/pay/{payment_id}``;
a human opens it, Razorpay Checkout runs in that page against the order we already
created, and the browser posts the signed result back to ``/pay/{id}/callback``,
which verifies the signature server-side and settles the order (the same code path
a webhook takes). No link quota, identical behaviour in production.

Both routes are intentionally unauthenticated: the payment id is an unguessable
UUID, the GET page exposes only the *publishable* key id, and the callback trusts
nothing it cannot cryptographically verify — the Razorpay signature is the auth.
"""

from __future__ import annotations

import html
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.envelope import ok
from app.core.config import get_settings
from app.domains.orders.models import Order
from app.domains.payments.exceptions import PaymentVerificationFailed
from app.domains.payments.models import Payment
from app.domains.payments.service import PaymentService

_log = logging.getLogger(__name__)
router = APIRouter(prefix="/pay", tags=["checkout"])

_SESSION = Depends(get_session)


class CheckoutCallbackIn(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


def _page(*, title: str, body: str) -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        "background:#0d0d0b;color:#f5f5f0;margin:0;display:flex;min-height:100vh;"
        "align-items:center;justify-content:center}"
        ".card{background:#17171400;border:1px solid #2a2a26;border-radius:16px;"
        "padding:40px;max-width:420px;width:calc(100% - 32px);text-align:center}"
        "h1{font-size:20px;margin:0 0 8px}p{color:#b8b8ae;font-size:14px;line-height:1.5}"
        ".amt{font-size:34px;font-weight:600;margin:16px 0}"
        "button{background:#3b82f6;color:#fff;border:0;border-radius:10px;padding:14px 24px;"
        "font-size:15px;font-weight:600;cursor:pointer;width:100%;margin-top:16px}"
        "button:disabled{opacity:.5;cursor:not-allowed}"
        ".ok{color:#4ade80}.err{color:#f87171}"
        ".muted{font-size:12px;color:#77776e;margin-top:20px}"
        "</style></head><body><div class='card'>" + body + "</div></body></html>"
    )


def render_checkout_page(payment: Payment, order: Order, *, key_id: str) -> str:
    """Pure: the HTML for an unpaid payment. Kept out of the handler so it is
    testable without an HTTP client."""
    addr = order.shipping_address or {}
    prefill_name = html.escape(str(addr.get("name", "")))
    prefill_email = html.escape(str(addr.get("email", "")))
    prefill_contact = html.escape(str(addr.get("phone", "")))
    rupees = f"₹{payment.amount_paise / 100:,.2f}"

    body = (
        f"<h1>Pay for {html.escape(order.order_number)}</h1>"
        "<p>CommerceOS secure checkout &middot; Razorpay test mode</p>"
        f"<div class='amt'>{rupees}</div>"
        "<button id='pay'>Pay now</button>"
        "<div id='status'></div>"
        "<div class='muted'>Test card 4111 1111 1111 1111 &middot; any future expiry "
        "&middot; any CVV</div>"
        "<script src='https://checkout.razorpay.com/v1/checkout.js'></script>"
        "<script>"
        f"var KEY={key_id!r};"
        f"var ORDER_ID={payment.provider_order_id!r};"
        f"var AMOUNT={payment.amount_paise};"
        f"var PAYMENT_ID={str(payment.id)!r};"
        f"var ORDER_NUMBER={order.order_number!r};"
        f"var NAME={prefill_name!r};var EMAIL={prefill_email!r};var CONTACT={prefill_contact!r};"
        "var s=document.getElementById('status');var btn=document.getElementById('pay');"
        "function done(cls,msg){s.className=cls;s.innerHTML=msg;btn.disabled=true;}"
        "btn.onclick=function(){"
        "var rzp=new Razorpay({key:KEY,order_id:ORDER_ID,amount:AMOUNT,currency:'INR',"
        "name:'CommerceOS',description:'Order '+ORDER_NUMBER,"
        "prefill:{name:NAME,email:EMAIL,contact:CONTACT},theme:{color:'#3b82f6'},"
        "handler:function(r){"
        "s.className='';s.innerHTML='Verifying\\u2026';"
        "fetch('/pay/'+PAYMENT_ID+'/callback',{method:'POST',"
        "headers:{'Content-Type':'application/json'},body:JSON.stringify({"
        "razorpay_payment_id:r.razorpay_payment_id,razorpay_order_id:r.razorpay_order_id,"
        "razorpay_signature:r.razorpay_signature})})"
        ".then(function(x){return x.json().then(function(b){return {ok:x.ok,b:b};});})"
        ".then(function(o){if(o.ok){"
        "done('ok','Payment successful \\u2014 you can close this page.');}"
        "else{done('err','Verification failed: '+(o.b.detail||'unknown error'));}})"
        ".catch(function(){done('err','Network error while verifying. "
        "Do not retry the card \\u2014 contact the merchant.');});"
        "},"
        "modal:{ondismiss:function(){s.className='';s.innerHTML='Checkout closed.';}}"
        "});rzp.on('payment.failed',function(){done('err','Payment failed. Try again.');});"
        "rzp.open();};"
        "</script>"
    )
    return _page(title=f"Pay for {order.order_number}", body=body)


async def _load(session: AsyncSession, payment_id: uuid.UUID) -> tuple[Payment, Order]:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")
    order = await session.get(Order, payment.order_id)
    if order is None:  # pragma: no cover - a payment always has an order
        raise HTTPException(status_code=404, detail="order not found")
    return payment, order


@router.get("/{payment_id}", response_class=HTMLResponse)
async def checkout_page(payment_id: uuid.UUID, session: AsyncSession = _SESSION) -> HTMLResponse:
    payment, order = await _load(session, payment_id)
    settings = get_settings()

    if payment.status == "paid":
        return HTMLResponse(
            _page(
                title=f"{order.order_number} paid",
                body=(
                    f"<h1>{html.escape(order.order_number)} is paid</h1>"
                    "<p class='ok'>This order has already been settled. Nothing more to do.</p>"
                ),
            )
        )
    if payment.status in ("failed", "refunded", "refund_processing", "refund_requested"):
        return HTMLResponse(
            _page(
                title=f"{order.order_number} unavailable",
                body=(
                    f"<h1>Cannot pay {html.escape(order.order_number)}</h1>"
                    f"<p class='err'>This payment is <b>{html.escape(payment.status)}</b>. "
                    "Ask the merchant for a fresh payment request.</p>"
                ),
            )
        )
    if not (settings.razorpay_key_id and payment.provider_order_id):
        raise HTTPException(status_code=503, detail="checkout is not configured")

    return HTMLResponse(render_checkout_page(payment, order, key_id=settings.razorpay_key_id))


async def settle_from_checkout(
    session: AsyncSession, payment_id: uuid.UUID, body: CheckoutCallbackIn
) -> dict:
    """Verify the browser's signed Checkout result and settle. Transaction-free so
    it is callable from a test with the rollback session fixture; the route wraps
    it in ``session.begin()``. Runs on an unscoped session (BYPASSRLS) keyed by
    the payment's own merchant id — the same thing the webhook handler does."""
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="payment not found")
    try:
        return await PaymentService(session).verify_and_capture(
            payment.merchant_id,
            payment_id,
            razorpay_payment_id=body.razorpay_payment_id,
            razorpay_order_id=body.razorpay_order_id,
            razorpay_signature=body.razorpay_signature,
        )
    except PaymentVerificationFailed as exc:
        _log.warning("hosted checkout: verification failed for %s: %s", payment_id, exc)
        raise HTTPException(status_code=400, detail=f"verification failed: {exc}") from exc


@router.post("/{payment_id}/callback")
async def checkout_callback(
    payment_id: uuid.UUID,
    body: CheckoutCallbackIn,
    session: AsyncSession = _SESSION,
) -> dict:
    """Browser posts the signed Razorpay Checkout result here."""
    async with session.begin():
        result = await settle_from_checkout(session, payment_id, body)
    _log.info("hosted checkout: settled payment %s (order %s)", payment_id, result["order_id"])
    return ok(result)
