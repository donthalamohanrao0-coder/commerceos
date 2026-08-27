from fastapi import APIRouter

from app.api.v1 import carts, health, orders, payments
from app.webhooks import razorpay_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(carts.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(razorpay_router.router)
