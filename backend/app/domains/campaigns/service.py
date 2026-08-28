"""Campaign eligibility + discount calculation — server-side, enforcing
max_discount_paise and campaign_rules (business_policies.md, campaign_playbook.md:
no fake urgency/social proof, discount never exceeds merchant policy)."""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.campaigns.exceptions import CampaignNotFound
from app.domains.campaigns.models import Campaign, CampaignRule
from app.domains.cart.models import CartItem
from app.domains.catalog.models import Product, ProductVariant
from app.policies.engine import PolicyEngine


@dataclass(frozen=True)
class CampaignEvaluation:
    campaign: Campaign | None
    discount_paise: int
    reason: str


class CampaignService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._policy_engine = PolicyEngine(session)

    async def create_draft(
        self,
        merchant_id: uuid.UUID,
        *,
        name: str,
        discount_type: str,
        discount_percent: float | None = None,
        discount_fixed_paise: int | None = None,
        max_discount_paise: int | None = None,
        rules: list[tuple[str, dict[str, Any]]] | None = None,
    ) -> Campaign:
        """Create a campaign in `draft` that always requires merchant approval.
        The discount ceiling is capped by the merchant's auto-discount policy so a
        draft can never be configured beyond what policy would allow at checkout."""
        policy = await self._policy_engine.check_discount(merchant_id, max_discount_paise or 0)
        capped_ceiling = (
            max_discount_paise
            if policy.allowed or max_discount_paise is None
            else (policy.capped_value or 0)
        )
        campaign = Campaign(
            id=uuid.uuid4(),
            merchant_id=merchant_id,
            external_campaign_code=f"cmp_{uuid.uuid4().hex[:10]}",
            name=name,
            status="draft",
            discount_type=discount_type,
            discount_percent=discount_percent,
            discount_fixed_paise=discount_fixed_paise,
            max_discount_paise=capped_ceiling,
            requires_merchant_approval=True,
        )
        self._session.add(campaign)
        await self._session.flush()
        for rule_type, rule_value in rules or []:
            self._session.add(
                CampaignRule(
                    id=uuid.uuid4(),
                    campaign_id=campaign.id,
                    rule_type=rule_type,
                    rule_value=rule_value,
                )
            )
        await self._session.flush()
        return campaign

    async def get_campaign(self, merchant_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign:
        campaign = await self._session.get(Campaign, campaign_id)
        if campaign is None or campaign.merchant_id != merchant_id:
            raise CampaignNotFound(str(campaign_id))
        return campaign

    async def activate(self, merchant_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign:
        campaign = await self.get_campaign(merchant_id, campaign_id)
        campaign.status = "active"
        await self._session.flush()
        return campaign

    async def _active_campaigns(self, merchant_id: uuid.UUID) -> list[Campaign]:
        result = await self._session.scalars(
            select(Campaign).where(Campaign.merchant_id == merchant_id, Campaign.status == "active")
        )
        return list(result.all())

    async def _rules_for(self, campaign_id: uuid.UUID) -> list[CampaignRule]:
        result = await self._session.scalars(
            select(CampaignRule).where(CampaignRule.campaign_id == campaign_id)
        )
        return list(result.all())

    async def _cart_categories_and_total(
        self, cart_items: list[CartItem]
    ) -> tuple[set[str], dict[str, int]]:
        categories: set[str] = set()
        category_totals: dict[str, int] = {}
        for item in cart_items:
            variant = await self._session.get(ProductVariant, item.product_variant_id)
            assert variant is not None, (
                f"cart item references missing variant {item.product_variant_id}"
            )
            product = await self._session.get(Product, variant.product_id)
            assert product is not None, f"variant references missing product {variant.product_id}"
            categories.add(product.category)
            category_totals[product.category] = (
                category_totals.get(product.category, 0) + item.unit_price_paise * item.quantity
            )
        return categories, category_totals

    async def _rules_satisfied(
        self,
        rules: list[CampaignRule],
        *,
        customer_segment: str | None,
        cart_categories: set[str],
        category_totals: dict[str, int],
    ) -> bool:
        for rule in rules:
            if rule.rule_type == "eligible_segment":
                if customer_segment not in rule.rule_value.get("segments", []):
                    return False
            elif rule.rule_type == "eligible_category":
                if not cart_categories.intersection(rule.rule_value.get("categories", [])):
                    return False
            elif rule.rule_type == "min_category_purchase":
                category = rule.rule_value["category"]
                if category_totals.get(category, 0) < rule.rule_value["min_paise"]:
                    return False
        return True

    async def near_miss_category_unlocks(
        self,
        merchant_id: uuid.UUID,
        *,
        cart_items: list[CartItem],
        customer_segment: str | None,
    ) -> list[tuple[Campaign, set[str]]]:
        """Active campaigns that would become eligible for this cart if one more
        product from a specific category were added — every rule already passes
        except a single ``eligible_category`` rule. Returns (campaign, the
        categories that would satisfy that rule). Used to nudge cross-sell.
        """
        if not cart_items:
            return []
        cart_categories, category_totals = await self._cart_categories_and_total(cart_items)
        out: list[tuple[Campaign, set[str]]] = []
        for campaign in await self._active_campaigns(merchant_id):
            missing: set[str] | None = None
            blocked = False
            for rule in await self._rules_for(campaign.id):
                if rule.rule_type == "eligible_segment":
                    if customer_segment not in rule.rule_value.get("segments", []):
                        blocked = True
                        break
                elif rule.rule_type == "min_category_purchase":
                    category = rule.rule_value["category"]
                    if category_totals.get(category, 0) < rule.rule_value["min_paise"]:
                        blocked = True
                        break
                elif rule.rule_type == "eligible_category":
                    cats = set(rule.rule_value.get("categories", []))
                    if not cart_categories.intersection(cats):
                        if missing is not None:
                            blocked = True
                            break
                        missing = cats
            if not blocked and missing:
                out.append((campaign, missing))
        return out

    async def evaluate_campaigns_for_cart(
        self,
        merchant_id: uuid.UUID,
        *,
        cart_items: list[CartItem],
        subtotal_paise: int,
        customer_segment: str | None,
    ) -> CampaignEvaluation:
        if not cart_items:
            return CampaignEvaluation(campaign=None, discount_paise=0, reason="empty_cart")

        cart_categories, category_totals = await self._cart_categories_and_total(cart_items)

        best: CampaignEvaluation = CampaignEvaluation(
            campaign=None, discount_paise=0, reason="no_eligible_campaign"
        )

        for campaign in await self._active_campaigns(merchant_id):
            rules = await self._rules_for(campaign.id)
            if not await self._rules_satisfied(
                rules,
                customer_segment=customer_segment,
                cart_categories=cart_categories,
                category_totals=category_totals,
            ):
                continue

            if campaign.discount_type == "percentage" and campaign.discount_percent is not None:
                raw_discount = round(subtotal_paise * float(campaign.discount_percent) / 100)
            else:
                raw_discount = campaign.discount_fixed_paise or 0

            if campaign.max_discount_paise is not None:
                raw_discount = min(raw_discount, campaign.max_discount_paise)

            # Defense in depth: even a well-configured campaign is re-capped by the
            # merchant's global auto-discount policy (agent-guardrails.md #5).
            policy_decision = await self._policy_engine.check_discount(merchant_id, raw_discount)
            discount = (
                raw_discount if policy_decision.allowed else (policy_decision.capped_value or 0)
            )

            if discount > best.discount_paise:
                best = CampaignEvaluation(
                    campaign=campaign, discount_paise=discount, reason="eligible"
                )

        return best
