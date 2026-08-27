from functools import lru_cache

from app.core.config import get_settings
from app.integrations.razorpay.base import RazorpayClient
from app.integrations.razorpay.fake_client import FakeRazorpayClient


@lru_cache
def get_razorpay_client() -> RazorpayClient:
    settings = get_settings()
    if (
        settings.razorpay_key_id
        and settings.razorpay_key_secret
        and settings.razorpay_webhook_secret
    ):
        from app.integrations.razorpay.real_client import RealRazorpayClient

        return RealRazorpayClient(
            key_id=settings.razorpay_key_id,
            key_secret=settings.razorpay_key_secret,
            webhook_secret=settings.razorpay_webhook_secret,
        )
    return FakeRazorpayClient()
