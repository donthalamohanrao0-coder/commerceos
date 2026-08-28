"""Issue, hash and verify external-agent API keys.

The raw key (``ack_live_<32 hex>``) is returned exactly once at creation. Only its
SHA-256 hash is persisted, so a database leak does not expose usable credentials
(secrets-and-data-protection.md).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_commerce.models import AGENT_API_SCOPES, AgentApiKey

_KEY_BYTES = 24  # -> 48 hex chars


class InvalidAgentKey(Exception):
    pass


class AgentKeyScopeDenied(Exception):
    def __init__(self, scope: str) -> None:
        self.scope = scope
        super().__init__(f"api key is not granted the required scope: {scope}")


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IssuedKey:
    id: uuid.UUID
    raw_key: str
    key_prefix: str
    scopes: list[str]
    rate_limit_per_minute: int


@dataclass(frozen=True)
class AgentPrincipal:
    key_id: uuid.UUID
    merchant_id: uuid.UUID
    name: str
    scopes: frozenset[str]
    rate_limit_per_minute: int

    def require(self, scope: str) -> None:
        if scope not in self.scopes:
            raise AgentKeyScopeDenied(scope)


class AgentApiKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def issue(
        self,
        *,
        merchant_id: uuid.UUID,
        name: str,
        scopes: list[str],
        rate_limit_per_minute: int = 60,
    ) -> IssuedKey:
        unknown = sorted(set(scopes) - set(AGENT_API_SCOPES))
        if unknown:
            raise ValueError(f"unknown scopes: {unknown}")

        raw_key = f"ack_live_{secrets.token_hex(_KEY_BYTES)}"
        prefix = raw_key[:16]
        row = AgentApiKey(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            name=name,
            key_prefix=prefix,
            key_hash=_hash(raw_key),
            scopes=sorted(set(scopes)),
            rate_limit_per_minute=rate_limit_per_minute,
            status="active",
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return IssuedKey(
            id=row.id,
            raw_key=raw_key,
            key_prefix=prefix,
            scopes=row.scopes,
            rate_limit_per_minute=row.rate_limit_per_minute,
        )

    async def authenticate(self, raw_key: str) -> AgentPrincipal:
        if not raw_key or not raw_key.startswith("ack_"):
            raise InvalidAgentKey("malformed key")
        row = await self._session.scalar(
            select(AgentApiKey).where(AgentApiKey.key_hash == _hash(raw_key))
        )
        if row is None or row.status != "active":
            raise InvalidAgentKey("unknown or revoked key")
        row.last_used_at = datetime.now(UTC)
        await self._session.flush()
        return AgentPrincipal(
            key_id=row.id,
            merchant_id=row.merchant_id,
            name=row.name,
            scopes=frozenset(row.scopes),
            rate_limit_per_minute=row.rate_limit_per_minute,
        )

    async def revoke(self, merchant_id: uuid.UUID, key_id: uuid.UUID) -> None:
        row = await self._session.get(AgentApiKey, key_id)
        if row is not None and row.merchant_id == merchant_id:
            row.status = "revoked"
            await self._session.flush()

    async def list_keys(self, merchant_id: uuid.UUID) -> list[AgentApiKey]:
        rows = await self._session.scalars(
            select(AgentApiKey)
            .where(AgentApiKey.merchant_id == merchant_id)
            .order_by(AgentApiKey.created_at.desc())
        )
        return list(rows)
