"""Public discovery manifest for the Agent Commerce API.

  * the manifest renders with no authentication and no principal;
  * its advertised scopes are exactly the grantable scopes — nothing more;
  * refunds / discount-overrides are advertised as non-grantable;
  * endpoint URLs are absolute and under the configured public base;
  * it still answers when the demo merchant row is absent (never depends on state).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_commerce.models import AGENT_API_SCOPES
from app.api.well_known import agent_commerce_manifest
from app.core.config import get_settings

pytestmark = pytest.mark.asyncio


async def test_manifest_is_public_and_self_describing(db: AsyncSession) -> None:
    manifest = await agent_commerce_manifest(session=db)

    assert manifest["protocol"] == "agent-commerce"
    assert set(manifest["scopes"]) == set(AGENT_API_SCOPES)
    assert "refund" in manifest["non_grantable"]
    assert "discount-override" in manifest["non_grantable"]

    base = get_settings().public_base_url.rstrip("/")
    for url in manifest["endpoints"].values():
        assert url.startswith(base + "/api/v1/agent-commerce")

    assert [s["step"] for s in manifest["flow"]] == [1, 2, 3, 4, 5, 6, 7]
    assert set(manifest["mandate_schema"]) == {
        "consent_reference",
        "max_amount_paise",
        "expires_at",
    }
    assert manifest["idempotency"]["header"] == "Idempotency-Key"
    assert manifest["limits"]["rate_limit_per_minute_default"] == 60


async def test_manifest_never_raises_without_demo_merchant(db: AsyncSession) -> None:
    # The `db` fixture's merchant (if any) does not use the demo merchant_code,
    # so the advisory-limits and merchant-block lookups fall through their
    # best-effort paths — the manifest must still return a complete document.
    manifest = await agent_commerce_manifest(session=db)
    assert manifest["merchant"]["code"] == get_settings().demo_merchant_code
    assert "guarantees" in manifest and len(manifest["guarantees"]) >= 4
