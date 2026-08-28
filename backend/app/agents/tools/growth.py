"""Growth-agent tools. The agent reads revenue analytics and drafts a campaign;
the campaign is created in `draft` and can only go live through explicit merchant
approval (agent-guardrails.md #6). The agent never activates anything itself.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from app.agents.context import ToolContext
from app.agents.tools.base import ToolRegistry
from app.analytics.service import AnalyticsService
from app.approvals.service import ApprovalService
from app.domains.campaigns.service import CampaignService


class GetMerchantAnalyticsTool:
    name: ClassVar[str] = "get_merchant_analytics"
    description: ClassVar[str] = (
        "Revenue snapshot for the merchant: total revenue, order count, AOV, "
        "top products by revenue, and revenue by category."
    )

    class Args(BaseModel):
        pass

    async def run(self, ctx: ToolContext, args: Args) -> dict[str, Any]:
        snap = await AnalyticsService(ctx.session).merchant_snapshot(ctx.merchant_id)
        return {
            "revenue_paise": snap.revenue_paise,
            "order_count": snap.order_count,
            "paid_order_count": snap.paid_order_count,
            "aov_paise": snap.aov_paise,
            "top_products": [
                {
                    "external_code": p.external_code,
                    "name": p.name,
                    "category": p.category,
                    "units_sold": p.units_sold,
                    "revenue_paise": p.revenue_paise,
                }
                for p in snap.top_products
            ],
            "category_revenue": [
                {"category": c, "revenue_paise": r} for c, r in snap.category_revenue
            ],
        }


class AnalyzeCrossSellTool:
    name: ClassVar[str] = "analyze_cross_sell"
    description: ClassVar[str] = (
        "Products frequently bought together, with co-occurrence counts and attach "
        "rates — the raw signal for a cross-sell campaign."
    )

    class Args(BaseModel):
        pass

    async def run(self, ctx: ToolContext, args: Args) -> dict[str, Any]:
        snap = await AnalyticsService(ctx.session).merchant_snapshot(ctx.merchant_id)
        return {
            "pairs": [
                {
                    "a_code": p.a_code,
                    "a_name": p.a_name,
                    "b_code": p.b_code,
                    "b_name": p.b_name,
                    "co_occurrence": p.co_occurrence,
                    "attach_rate": p.attach_rate,
                }
                for p in snap.cross_sell_pairs
            ]
        }


class DraftCampaignTool:
    name: ClassVar[str] = "draft_campaign"
    description: ClassVar[str] = (
        "Create a DRAFT discount campaign (never active). The discount ceiling is "
        "capped by the merchant's auto-discount policy. Returns the campaign_id."
    )

    class Args(BaseModel):
        name: str = Field(min_length=3, max_length=120)
        discount_percent: float = Field(gt=0, le=50)
        max_discount_paise: int = Field(gt=0)
        eligible_category: str | None = Field(
            default=None, description="restrict the discount to one product category"
        )
        min_order_value_paise: int | None = Field(default=None, ge=0)

    async def run(self, ctx: ToolContext, args: Args) -> dict[str, Any]:
        rules: list[tuple[str, dict[str, Any]]] = []
        if args.eligible_category:
            rules.append(("eligible_category", {"category": args.eligible_category}))
        if args.min_order_value_paise is not None:
            rules.append(("min_order_value", {"min_order_value_paise": args.min_order_value_paise}))

        campaign = await CampaignService(ctx.session).create_draft(
            ctx.merchant_id,
            name=args.name,
            discount_type="percentage",
            discount_percent=args.discount_percent,
            max_discount_paise=args.max_discount_paise,
            rules=rules,
        )
        return {
            "campaign_id": str(campaign.id),
            "external_code": campaign.external_campaign_code,
            "status": campaign.status,
            "discount_percent": float(campaign.discount_percent or 0),
            "policy_capped_max_discount_paise": campaign.max_discount_paise,
            "rules": [r[0] for r in rules],
        }


class RequestCampaignApprovalTool:
    name: ClassVar[str] = "request_campaign_approval"
    description: ClassVar[str] = (
        "Send a drafted campaign to the merchant for approval. Stops this turn — "
        "the campaign only goes live if the merchant approves."
    )

    class Args(BaseModel):
        campaign_id: uuid.UUID
        rationale: str = Field(min_length=10, max_length=600)

    async def run(self, ctx: ToolContext, args: Args) -> dict[str, Any]:
        # confirm the campaign exists and belongs to this merchant before asking
        campaign = await CampaignService(ctx.session).get_campaign(
            ctx.merchant_id, args.campaign_id
        )
        approval = await ApprovalService(ctx.session).request(
            merchant_id=ctx.merchant_id,
            requested_action="campaign_activation",
            requested_by="agent",
            payload={"campaign_id": str(campaign.id), "rationale": args.rationale},
            session_id=ctx.agent_session_id,
        )
        ctx.pending_approval = {
            "approval_id": str(approval.id),
            "action": "campaign_activation",
            "campaign_id": str(campaign.id),
        }
        return {
            "status": "awaiting_merchant_approval",
            "approval_id": str(approval.id),
            "campaign_id": str(campaign.id),
        }


def build_growth_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            GetMerchantAnalyticsTool(),
            AnalyzeCrossSellTool(),
            DraftCampaignTool(),
            RequestCampaignApprovalTool(),
        ]
    )
