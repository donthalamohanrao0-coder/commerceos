"""Seeds the CommerceOS demo dataset for merchant NovaTech Store (mrc_novatech_001).

Import order follows demo-data/DATA_DICTIONARY.md:
merchant profile -> categories (informational only, not a DB table) -> products ->
inventory -> customers -> campaigns -> policies/knowledge -> agent configuration ->
historical orders/analytics.

Run with:
    uv run python -m db.seeds.seed_novatech_demo
"""

import asyncio
import csv
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import select  # noqa: E402

# Import every model package so the mapper registry is complete: seeded tables
# (carts, orders) carry FKs into agent_sessions / documents / etc., and SQLAlchemy
# must resolve all of them before it can flush.
from app.agents import models as _agent_models  # noqa: E402,F401
from app.approvals import models as _approval_models  # noqa: E402,F401
from app.audit import models as _audit_models  # noqa: E402,F401
from app.core import idempotency_models as _idempotency_models  # noqa: E402,F401
from app.core.db import async_session_factory  # noqa: E402
from app.domains.campaigns.models import Campaign, CampaignRule  # noqa: E402
from app.domains.cart.models import Cart  # noqa: E402
from app.domains.catalog.models import Inventory, Product, ProductVariant  # noqa: E402
from app.domains.customers.models import Customer  # noqa: E402
from app.domains.merchants.models import Merchant, Organization  # noqa: E402
from app.domains.orders.models import Order, OrderItem  # noqa: E402
from app.knowledge import models as _knowledge_models  # noqa: E402,F401
from app.policies.models import Policy  # noqa: E402
from app.webhooks import models as _webhook_models  # noqa: E402,F401

DATA_ROOT = Path(__file__).resolve().parents[2] / "demo-data"
MERCHANT_CODE = "mrc_novatech_001"


def inr_to_paise(inr: float) -> int:
    return round(float(inr) * 100)


async def seed() -> None:
    async with async_session_factory() as session, session.begin():
        merchant = await seed_merchant(session)
        product_variant_by_code = await seed_catalog(session, merchant)
        await seed_inventory(session, product_variant_by_code)
        customer_by_code = await seed_customers(session, merchant)
        campaign_by_code = await seed_campaigns(session, merchant)
        await seed_policies(session, merchant)
        await seed_orders(
            session, merchant, customer_by_code, product_variant_by_code, campaign_by_code
        )

    print(f"Seed complete for merchant {MERCHANT_CODE}.")


async def seed_merchant(session) -> Merchant:
    profile = json.loads(
        (DATA_ROOT / "business" / "merchant_profile.json").read_text(encoding="utf-8")
    )

    existing = await session.scalar(select(Merchant).where(Merchant.merchant_code == MERCHANT_CODE))
    if existing:
        print("Merchant already seeded, skipping merchant/org creation.")
        return existing

    org = Organization(id=uuid.uuid4(), name=profile["legal_name"])
    session.add(org)
    await session.flush()

    merchant = Merchant(
        id=uuid.uuid4(),
        organization_id=org.id,
        merchant_code=profile["merchant_id"],
        business_name=profile["business_name"],
        legal_name=profile["legal_name"],
        currency=profile["currency"],
        country=profile["country"],
        timezone=profile["timezone"],
        gst_percent=profile["tax"]["default_gst_percent"],
        prices_tax_inclusive=profile["tax"]["prices_are_tax_inclusive"],
        pinecone_namespace=f"merchant_{profile['merchant_id']}",
    )
    session.add(merchant)
    await session.flush()
    return merchant


async def seed_catalog(session, merchant: Merchant) -> dict[str, ProductVariant]:
    variants_by_code: dict[str, ProductVariant] = {}

    existing_count = await session.scalar(
        select(Product).where(Product.merchant_id == merchant.id).limit(1)
    )
    if existing_count:
        result = await session.scalars(
            select(ProductVariant).where(ProductVariant.merchant_id == merchant.id)
        )
        for variant in result:
            product = await session.get(Product, variant.product_id)
            variants_by_code[product.external_product_code] = variant
        print("Catalog already seeded, skipping.")
        return variants_by_code

    with (DATA_ROOT / "catalog" / "products.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            product = Product(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                external_product_code=row["product_id"],
                sku=row["sku"],
                name=row["name"],
                category=row["category"],
                brand=row["brand"],
                description=row["description"],
                price_paise=inr_to_paise(row["price_inr"]),
                compare_at_price_paise=inr_to_paise(row["compare_at_price_inr"]),
                rating=float(row["rating"]),
                review_count=int(row["review_count"]),
                tags=row["tags"].split("|") if row["tags"] else [],
                image_key=row["image_key"],
            )
            session.add(product)
            await session.flush()

            variant = ProductVariant(
                id=uuid.uuid4(),
                product_id=product.id,
                merchant_id=merchant.id,
                sku=row["sku"],
                price_paise=product.price_paise,
            )
            session.add(variant)
            await session.flush()
            variants_by_code[row["product_id"]] = variant

    return variants_by_code


async def seed_inventory(session, product_variant_by_code: dict[str, ProductVariant]) -> None:
    existing = await session.scalar(select(Inventory).limit(1))
    if existing:
        print("Inventory already seeded, skipping.")
        return

    with (DATA_ROOT / "catalog" / "inventory.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            variant = product_variant_by_code[row["product_id"]]
            session.add(
                Inventory(
                    id=uuid.uuid4(),
                    merchant_id=variant.merchant_id,
                    product_variant_id=variant.id,
                    quantity_available=int(row["available_qty"]),
                    quantity_reserved=int(row["reserved_qty"]),
                )
            )


async def seed_customers(session, merchant: Merchant) -> dict[str, Customer]:
    customers_by_code: dict[str, Customer] = {}

    result = await session.scalars(select(Customer).where(Customer.merchant_id == merchant.id))
    for c in result:
        customers_by_code[c.external_customer_code] = c
    if customers_by_code:
        print("Customers already seeded, skipping.")
        return customers_by_code

    with (DATA_ROOT / "customers" / "customers.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            customer = Customer(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                external_customer_code=row["customer_id"],
                name=row["name"],
                email=row["email"],
                city=row["city"],
                segment=row["segment"],
                lifetime_value_paise=inr_to_paise(row["lifetime_value_inr"]),
                orders_count=int(row["orders_count"]),
                preferred_categories=row["preferred_categories"].split("|"),
            )
            session.add(customer)
            await session.flush()
            customers_by_code[row["customer_id"]] = customer

    return customers_by_code


async def seed_campaigns(session, merchant: Merchant) -> dict[str, Campaign]:
    campaigns_by_code: dict[str, Campaign] = {}

    result = await session.scalars(select(Campaign).where(Campaign.merchant_id == merchant.id))
    for c in result:
        campaigns_by_code[c.external_campaign_code] = c
    if campaigns_by_code:
        print("Campaigns already seeded, skipping.")
        return campaigns_by_code

    with (DATA_ROOT / "campaigns" / "campaigns.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            discount_type = "percentage" if row["type"] == "percentage" else "fixed"
            campaign = Campaign(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                external_campaign_code=row["campaign_id"],
                name=row["name"],
                status=row["status"],
                discount_type=discount_type,
                discount_percent=float(row["discount_percent"])
                if row["discount_percent"]
                else None,
                discount_fixed_paise=inr_to_paise(row["discount_inr"])
                if row["discount_inr"]
                else None,
                max_discount_paise=inr_to_paise(row["max_discount_inr"])
                if row["max_discount_inr"]
                else None,
                requires_merchant_approval=row["requires_merchant_approval"].strip().lower()
                == "true",
            )
            session.add(campaign)
            await session.flush()
            campaigns_by_code[row["campaign_id"]] = campaign

            if row["eligible_segments"]:
                session.add(
                    CampaignRule(
                        id=uuid.uuid4(),
                        campaign_id=campaign.id,
                        rule_type="eligible_segment",
                        rule_value={"segments": row["eligible_segments"].split("|")},
                    )
                )
            if row["eligible_categories"]:
                session.add(
                    CampaignRule(
                        id=uuid.uuid4(),
                        campaign_id=campaign.id,
                        rule_type="eligible_category",
                        rule_value={"categories": row["eligible_categories"].split("|")},
                    )
                )
            if row["min_laptop_purchase_inr"]:
                session.add(
                    CampaignRule(
                        id=uuid.uuid4(),
                        campaign_id=campaign.id,
                        rule_type="min_category_purchase",
                        rule_value={
                            "category": "Laptops",
                            "min_paise": inr_to_paise(row["min_laptop_purchase_inr"]),
                        },
                    )
                )

    return campaigns_by_code


async def seed_policies(session, merchant: Merchant) -> None:
    existing = await session.scalar(
        select(Policy).where(Policy.merchant_id == merchant.id).limit(1)
    )
    if existing:
        print("Policies already seeded, skipping.")
        return

    agent_config = json.loads(
        (DATA_ROOT / "agent" / "agent_config.json").read_text(encoding="utf-8")
    )
    financial_policy = agent_config["financial_policy"]

    values = {
        "max_auto_discount_paise": inr_to_paise(financial_policy["max_auto_discount_inr"]),
        "max_auto_refund_paise": inr_to_paise(financial_policy["max_auto_refund_inr"]),
        "payment_requires_customer_confirmation": financial_policy[
            "customer_confirmation_required"
        ],
        "max_transaction_amount_paise": inr_to_paise(
            100_000
        ),  # platform-wide cap, plan.md #16 example
        "max_graph_steps": agent_config["limits"]["max_graph_steps"],
        "max_tool_calls": agent_config["limits"]["max_tool_calls"],
        "max_execution_seconds": agent_config["limits"]["max_execution_seconds"],
        "max_retries": agent_config["limits"]["max_retries"],
    }
    for key, value in values.items():
        session.add(Policy(id=uuid.uuid4(), merchant_id=merchant.id, key=key, value=value))


async def seed_orders(
    session,
    merchant: Merchant,
    customer_by_code: dict[str, Customer],
    product_variant_by_code: dict[str, ProductVariant],
    campaign_by_code: dict[str, Campaign],
) -> None:
    existing = await session.scalar(select(Order).where(Order.merchant_id == merchant.id).limit(1))
    if existing:
        print("Orders already seeded, skipping.")
        return

    orders_data = json.loads((DATA_ROOT / "orders" / "orders.json").read_text(encoding="utf-8"))

    status_map = {
        "paid": "paid",
        "payment_pending": "payment_pending",
    }

    for row in orders_data:
        customer = customer_by_code[row["customer_id"]]

        cart = Cart(
            id=uuid.uuid4(), merchant_id=merchant.id, customer_id=customer.id, status="converted"
        )
        session.add(cart)
        await session.flush()

        order = Order(
            id=uuid.uuid4(),
            merchant_id=merchant.id,
            customer_id=customer.id,
            cart_id=cart.id,
            order_number=row["order_id"].upper().replace("ORD_", "ORD-"),
            status=status_map.get(row["status"], row["status"]),
            subtotal_paise=inr_to_paise(row["subtotal_inr"]),
            discount_paise=inr_to_paise(row["discount_inr"]),
            shipping_paise=inr_to_paise(row["shipping_inr"]),
            tax_paise=0,
            total_paise=inr_to_paise(row["total_inr"]),
            source=row["source"],
        )
        session.add(order)
        await session.flush()

        for item in row["items"]:
            variant = product_variant_by_code[item["product_id"]]
            product = await session.get(Product, variant.product_id)
            session.add(
                OrderItem(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    product_variant_id=variant.id,
                    product_name_snapshot=product.name,
                    quantity=item["qty"],
                    unit_price_paise=inr_to_paise(item["unit_price_inr"]),
                    line_total_paise=inr_to_paise(item["unit_price_inr"]) * item["qty"],
                )
            )


if __name__ == "__main__":
    asyncio.run(seed())
