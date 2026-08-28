"""Each workflow's tool registry is an explicit allowlist (agent-guardrails.md #2):
a flow can only ever call the tools it is meant to."""

from app.agents.tools.growth import build_growth_registry
from app.agents.tools.shopping import build_shopping_registry
from app.agents.tools.support import build_support_registry


def test_support_has_no_money_or_mutation_tools() -> None:
    names = set(build_support_registry().names())
    assert names.isdisjoint(
        {"cart_add_item", "order_create", "payment_request", "draft_campaign", "activate_campaign"}
    )
    assert names == {"order_lookup", "shipping_status", "knowledge_search"}


def test_growth_cannot_take_payments_or_touch_carts() -> None:
    names = set(build_growth_registry().names())
    assert names.isdisjoint({"payment_request", "order_create", "cart_add_item"})
    assert "request_campaign_approval" in names  # activation is approval-gated
    assert "activate_campaign" not in names  # the agent never activates directly


def test_shopping_cannot_draft_or_activate_campaigns() -> None:
    names = set(build_shopping_registry().names())
    assert names.isdisjoint({"draft_campaign", "activate_campaign", "get_merchant_analytics"})
