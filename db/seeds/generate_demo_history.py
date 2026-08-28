"""Generate ~90 days-spread historical orders (+ customers, + captured payments)
for NovaTech Store so the analytics dashboards have something real to show, and
populate cross-sell links used by the shopping agent's upsell tool.

Idempotent: skips if history orders (ORD-H*) already exist.

    uv run python db/seeds/generate_demo_history.py
"""

import asyncio
import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(_BACKEND))


def _load_backend_env() -> None:
    env_path = _BACKEND / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_backend_env()

from sqlalchemy import select  # noqa: E402

from app.agents import models as _agent_models  # noqa: E402,F401
from app.core.db import async_session_factory  # noqa: E402
from app.domains.cart.models import Cart  # noqa: E402
from app.domains.catalog.models import Product, ProductVariant  # noqa: E402
from app.domains.customers.models import Customer  # noqa: E402
from app.domains.merchants.models import Merchant  # noqa: E402
from app.domains.orders.models import Order, OrderItem  # noqa: E402
from app.domains.payments.models import Payment  # noqa: E402

MERCHANT_CODE = "mrc_novatech_001"
DAYS = 60
TARGET_ORDERS = 95
rng = random.Random(42)

NEW_CUSTOMERS = [
    ("Aarav Menon", "aarav.menon@example.test", "Kochi", "returning"),
    ("Diya Kulkarni", "diya.k@example.test", "Pune", "new"),
    ("Kabir Shah", "kabir.shah@example.test", "Ahmedabad", "vip"),
    ("Meera Iyer", "meera.iyer@example.test", "Chennai", "returning"),
    ("Rohan Gupta", "rohan.g@example.test", "Delhi", "new"),
    ("Sara Thomas", "sara.thomas@example.test", "Bengaluru", "returning"),
    ("Vivaan Reddy", "vivaan.reddy@example.test", "Hyderabad", "vip"),
    ("Ananya Bose", "ananya.bose@example.test", "Kolkata", "new"),
    ("Ishaan Nair", "ishaan.nair@example.test", "Thiruvananthapuram", "returning"),
    ("Priya Sharma", "priya.sharma2@example.test", "Jaipur", "new"),
    ("Arjun Rao", "arjun.rao@example.test", "Mysuru", "returning"),
    ("Nisha Verma", "nisha.verma@example.test", "Lucknow", "new"),
    ("Dev Patel", "dev.patel@example.test", "Surat", "vip"),
    ("Tara Singh", "tara.singh@example.test", "Chandigarh", "returning"),
    ("Farhan Ali", "farhan.ali@example.test", "Nagpur", "new"),
]

# anchor product code -> complementary product codes (for the upsell tool)
CROSS_SELL = {
    "prod_lap_001": ["NT-ACC-010", "NT-BAG-001", "prod_mouse_001", "NT-PWR-001", "NT-ACC-012"],
    "prod_lap_002": ["NT-ACC-010", "NT-BAG-001", "prod_mouse_001", "NT-PWR-001"],
    "prod_lap_003": ["NT-DIS-001", "NT-ACC-012", "NT-STO-001", "prod_keyboard_001"],
    "prod_phone_001": ["prod_audio_002", "NT-PWR-002", "prod_watch_001"],
    "prod_phone_002": ["prod_audio_002", "NT-PWR-002"],
    "prod_keyboard_001": ["prod_mouse_001", "NT-ACC-015"],
    "prod_mouse_001": ["prod_keyboard_001", "NT-ACC-015"],
    "prod_audio_001": ["NT-ACC-013"],
    "NT-DIS-001": ["prod_keyboard_001", "prod_mouse_001", "NT-ACC-014"],
}


def _weighted_day_offset() -> int:
    # more orders recently: sample two and take the smaller
    return min(rng.randint(0, DAYS - 1), rng.randint(0, DAYS - 1))


async def run() -> None:
    async with async_session_factory() as session, session.begin():
        merchant = await session.scalar(
            select(Merchant).where(Merchant.merchant_code == MERCHANT_CODE)
        )
        if merchant is None:
            raise SystemExit("run the base seed first")

        already = await session.scalar(
            select(Order).where(
                Order.merchant_id == merchant.id, Order.order_number.like("ORD-H%")
            )
        )
        if already is not None:
            print("generate_demo_history: history already present, skipping.")
            return

        # --- cross-sell links -------------------------------------------------
        products = list(
            await session.scalars(select(Product).where(Product.merchant_id == merchant.id))
        )
        by_code = {p.external_product_code: p for p in products}
        cs_set = 0
        for code, links in CROSS_SELL.items():
            p = by_code.get(code)
            if p is None:
                continue
            valid = [c for c in links if c in by_code]
            if valid:
                p.cross_sell_product_codes = valid
                cs_set += 1

        # --- extra customers -----------------------------------------------
        customers = list(
            await session.scalars(select(Customer).where(Customer.merchant_id == merchant.id))
        )
        for i, (name, email, city, segment) in enumerate(NEW_CUSTOMERS):
            if any(c.email == email for c in customers):
                continue
            c = Customer(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                external_customer_code=f"cus_h{i:03d}",
                name=name,
                email=email,
                city=city,
                segment=segment,
                preferred_categories=[],
            )
            session.add(c)
            customers.append(c)
        await session.flush()

        variants = {
            v.product_id: v
            for v in await session.scalars(
                select(ProductVariant).where(ProductVariant.merchant_id == merchant.id)
            )
        }
        active = [p for p in products if p.status == "active" and p.id in variants]
        anchors = [p for p in active if p.external_product_code in CROSS_SELL]

        sources = ["ai_assisted"] * 11 + ["customer"] * 6 + ["external_ai_buyer"] * 3
        statuses = ["paid"] * 74 + ["fulfilled"] * 14 + ["created"] * 6 + ["failed"] * 4 + [
            "cancelled"
        ] * 2

        made = 0
        for n in range(TARGET_ORDERS):
            created = datetime.now(UTC) - timedelta(
                days=_weighted_day_offset(),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )
            customer = rng.choice(customers)
            anchor = rng.choice(anchors) if rng.random() < 0.55 else rng.choice(active)
            basket = [anchor]
            for _ in range(rng.choice([0, 0, 1, 1, 2])):
                extra_codes = CROSS_SELL.get(anchor.external_product_code, [])
                pick = (
                    by_code.get(rng.choice(extra_codes))
                    if extra_codes and rng.random() < 0.7
                    else rng.choice(active)
                )
                if pick is not None and pick.id not in {b.id for b in basket}:
                    basket.append(pick)

            subtotal = 0
            lines = []
            for prod in basket:
                qty = 1 if prod.category != "Accessories" else rng.choice([1, 1, 2])
                line = prod.price_paise * qty
                subtotal += line
                lines.append((prod, qty, line))

            discount = 0
            if rng.random() < 0.22:
                discount = min(int(subtotal * rng.choice([0.05, 0.08, 0.1])), 300000)
            shipping = 0 if subtotal >= 200000 else 9900
            total = subtotal - discount + shipping
            status = rng.choice(statuses)

            cart = Cart(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                customer_id=customer.id,
                status="converted",
            )
            session.add(cart)
            await session.flush()

            order = Order(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                customer_id=customer.id,
                cart_id=cart.id,
                order_number=f"ORD-H{n:04d}",
                status=status,
                subtotal_paise=subtotal,
                discount_paise=discount,
                shipping_paise=shipping,
                tax_paise=0,
                total_paise=total,
                source=rng.choice(sources),
                created_at=created,
            )
            session.add(order)
            await session.flush()

            for prod, qty, line in lines:
                session.add(
                    OrderItem(
                        id=uuid.uuid4(),
                        order_id=order.id,
                        product_variant_id=variants[prod.id].id,
                        product_name_snapshot=prod.name,
                        quantity=qty,
                        unit_price_paise=prod.price_paise,
                        line_total_paise=line,
                    )
                )

            if status in ("paid", "fulfilled"):
                session.add(
                    Payment(
                        id=uuid.uuid4(),
                        merchant_id=merchant.id,
                        order_id=order.id,
                        status="paid",
                        amount_paise=total,
                        provider="razorpay",
                        provider_order_id=f"order_hist_{uuid.uuid4().hex[:12]}",
                        provider_payment_id=f"pay_hist_{uuid.uuid4().hex[:12]}",
                        razorpay_signature_verified=True,
                        created_at=created,
                    )
                )
            made += 1

        print(
            f"generate_demo_history: {made} orders over {DAYS} days, "
            f"{len(NEW_CUSTOMERS)} customers, cross-sell on {cs_set} products."
        )


if __name__ == "__main__":
    asyncio.run(run())
