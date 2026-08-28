"""Identity endpoint — who is the authenticated caller and which merchant do they
act for. The frontend calls this right after Supabase sign-in.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_merchant_identity
from app.api.envelope import ok
from app.identity.service import MerchantIdentity

router = APIRouter(prefix="/me", tags=["identity"])

_IDENTITY = Depends(get_merchant_identity)


@router.get("")
async def whoami(identity: MerchantIdentity = _IDENTITY) -> dict:
    return ok(
        {
            "user": {
                "id": str(identity.user_id),
                "email": identity.email,
                "role": identity.role,
            },
            "merchant": {
                "id": str(identity.merchant_id),
                "merchant_code": identity.merchant_code,
                "business_name": identity.business_name,
            },
        }
    )
