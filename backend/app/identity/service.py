"""Resolve an authenticated Supabase user to an internal user + merchant.

The frontend proves *who* the caller is (Supabase Auth); this service decides
*what merchant* they act for — server-side, never from a client header
(security-architecture.md #4).

For the buildathon demo, a first-time authenticated user is auto-provisioned as a
``MERCHANT_ADMIN`` of the demo merchant so sign-up "just works". In production
this would instead be an invite/onboarding flow.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domains.merchants.models import Merchant, MerchantUser, User
from app.integrations.supabase.auth import AuthenticatedUser


class NoMerchantForUser(Exception):
    """The authenticated user is not linked to any merchant and none could be assigned."""


@dataclass(frozen=True)
class MerchantIdentity:
    user_id: uuid.UUID
    provider_id: str
    email: str
    role: str
    merchant_id: uuid.UUID
    merchant_code: str
    business_name: str


class IdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(self, principal: AuthenticatedUser) -> MerchantIdentity:
        user = await self._get_or_create_user(principal)
        link = await self._session.scalar(
            select(MerchantUser).where(MerchantUser.user_id == user.id)
        )
        if link is None:
            link = await self._assign_demo_merchant(user)

        merchant = await self._session.get(Merchant, link.merchant_id)
        if merchant is None:
            raise NoMerchantForUser(str(user.id))

        return MerchantIdentity(
            user_id=user.id,
            provider_id=principal.provider_id,
            email=user.email,
            role=link.role,
            merchant_id=merchant.id,
            merchant_code=merchant.merchant_code,
            business_name=merchant.business_name,
        )

    async def _get_or_create_user(self, principal: AuthenticatedUser) -> User:
        user = await self._session.scalar(select(User).where(User.email == principal.email))
        if user is not None:
            if user.auth_provider_id is None:
                try:
                    user.auth_provider_id = uuid.UUID(principal.provider_id)
                except ValueError:
                    user.auth_provider_id = None
                await self._session.flush()
            return user

        provider_uuid: uuid.UUID | None
        try:
            provider_uuid = uuid.UUID(principal.provider_id)
        except ValueError:
            provider_uuid = None

        user = User(
            id=uuid.uuid4(),
            auth_provider_id=provider_uuid,
            email=principal.email,
            role="MERCHANT_ADMIN",
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def _assign_demo_merchant(self, user: User) -> MerchantUser:
        code = get_settings().demo_merchant_code
        merchant = await self._session.scalar(
            select(Merchant).where(Merchant.merchant_code == code)
        )
        if merchant is None:  # fall back to any active merchant
            merchant = await self._session.scalar(
                select(Merchant).where(Merchant.status == "active").order_by(Merchant.created_at)
            )
        if merchant is None:
            raise NoMerchantForUser(str(user.id))

        link = MerchantUser(
            id=uuid.uuid4(), merchant_id=merchant.id, user_id=user.id, role="MERCHANT_ADMIN"
        )
        self._session.add(link)
        await self._session.flush()
        return link
