from fastapi import APIRouter

from app.api.v1 import (
    agent,
    agent_commerce,
    agent_keys,
    carts,
    console,
    health,
    me,
    orders,
    payments,
)
from app.webhooks import razorpay_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(me.router)
api_router.include_router(console.router)
api_router.include_router(carts.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(agent.router)
api_router.include_router(agent_keys.router)
api_router.include_router(agent_commerce.router)
api_router.include_router(razorpay_router.router)
