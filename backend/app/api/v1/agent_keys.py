"""Internal API for a merchant to issue / list / revoke Agent Commerce API keys
for external AI buyers. Tenant-scoped via X-Merchant-Id (internal auth)."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_commerce.keys import AgentApiKeyService
from app.agent_commerce.models import AGENT_API_SCOPES
from app.api.deps import get_current_merchant_id, get_tenant_session
from app.api.envelope import ok

router = APIRouter(prefix="/agent-keys", tags=["agent-keys"])


class IssueKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(min_length=1)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=6000)


@router.post("")
async def issue_key(
    body: IssueKeyRequest,
    session: AsyncSession = Depends(get_tenant_session),
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
) -> dict:
    async with session.begin():
        issued = await AgentApiKeyService(session).issue(
            merchant_id=merchant_id,
            name=body.name,
            scopes=body.scopes,
            rate_limit_per_minute=body.rate_limit_per_minute,
        )
    return ok(
        {
            "key_id": str(issued.id),
            "api_key": issued.raw_key,  # shown once
            "key_prefix": issued.key_prefix,
            "scopes": issued.scopes,
            "rate_limit_per_minute": issued.rate_limit_per_minute,
            "grantable_scopes": list(AGENT_API_SCOPES),
        }
    )


@router.get("")
async def list_keys(
    session: AsyncSession = Depends(get_tenant_session),
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
) -> dict:
    async with session.begin():
        keys = await AgentApiKeyService(session).list_keys(merchant_id)
    return ok(
        {
            "keys": [
                {
                    "key_id": str(k.id),
                    "name": k.name,
                    "key_prefix": k.key_prefix,
                    "scopes": list(k.scopes),
                    "status": k.status,
                    "rate_limit_per_minute": k.rate_limit_per_minute,
                    "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                }
                for k in keys
            ]
        }
    )


@router.delete("/{key_id}")
async def revoke_key(
    key_id: uuid.UUID,
    session: AsyncSession = Depends(get_tenant_session),
    merchant_id: uuid.UUID = Depends(get_current_merchant_id),
) -> dict:
    async with session.begin():
        await AgentApiKeyService(session).revoke(merchant_id, key_id)
    return ok({"key_id": str(key_id), "status": "revoked"})
