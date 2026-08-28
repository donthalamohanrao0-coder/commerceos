"""Additive seed: laptop accessories + a few adjacent categories for merchant
NovaTech Store. Idempotent — skips any product whose external_product_code
already exists. Each product gets one default variant and an inventory row.

    uv run python -m db.seeds.add_accessories
"""

import asyncio
import os
import sys
import uuid
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
from app.domains.catalog.models import Inventory, Product, ProductVariant  # noqa: E402
from app.domains.merchants.models import Merchant  # noqa: E402

MERCHANT_CODE = "mrc_novatech_001"

# code, name, category, brand, price_inr, compare_at_inr, rating, reviews, tags, image_key, stock, desc
ACCESSORIES: list[tuple] = [
    ("NT-ACC-010", "NovaShell 14\" Laptop Sleeve", "Accessories", "NovaTech", 1299, 1599, 4.5, 74,
     ["laptop", "protection", "portable", "sleeve"], "sleeve_01", 120,
     "Slim water-resistant sleeve for 13-14 inch laptops with a soft microfibre lining."),
    ("NT-BAG-001", "NovaCarry Pro Backpack", "Bags", "NovaTech", 3499, 3999, 4.7, 158,
     ["laptop", "travel", "backpack", "work"], "backpack_01", 80,
     "20L commuter backpack with a padded 16-inch laptop compartment and USB pass-through."),
    ("NT-PWR-001", "NovaCharge 65W USB-C Charger", "Power", "NovaTech", 1999, 2499, 4.6, 203,
     ["laptop", "charger", "usb-c", "fast-charging"], "charger_01", 200,
     "Compact GaN 65W USB-C wall charger — fast-charges most laptops, tablets and phones."),
    ("NT-PWR-002", "NovaCell 20000mAh Power Bank", "Power", "NovaTech", 2499, 2999, 4.4, 96,
     ["portable", "charger", "travel", "usb-c"], "powerbank_01", 90,
     "20000mAh power bank with 65W USB-C PD output — one full laptop top-up on the go."),
    ("NT-STO-001", "NovaDrive 1TB Portable SSD", "Storage", "NovaTech", 6999, 7999, 4.8, 141,
     ["storage", "backup", "fast", "portable"], "ssd_01", 60,
     "Pocket 1TB NVMe SSD, up to 1050MB/s over USB-C, shock-resistant aluminium body."),
    ("NT-ACC-011", "NovaView 1080p Webcam", "Accessories", "NovaTech", 2799, 3299, 4.3, 88,
     ["video", "calls", "work", "streaming"], "webcam_01", 110,
     "Full-HD 1080p/60fps webcam with autofocus, dual mics and a privacy shutter."),
    ("NT-ACC-012", "NovaDock 12-in-1 Docking Station", "Accessories", "NovaTech", 8999, 9999, 4.6, 67,
     ["laptop", "usb-c", "hdmi", "productivity", "work"], "dock_01", 45,
     "12-in-1 USB-C dock: dual 4K HDMI, Gigabit Ethernet, SD, 100W power delivery."),
    ("NT-ACC-013", "NovaCool Laptop Cooling Pad", "Accessories", "NovaTech", 1799, 2199, 4.2, 54,
     ["laptop", "cooling", "gaming", "ergonomic"], "coolingpad_01", 75,
     "5-fan cooling pad with adjustable height and quiet 1200RPM fans for heavy workloads."),
    ("NT-DIS-001", "NovaVision 27\" 4K Monitor", "Displays", "NovaTech", 24999, 27999, 4.7, 112,
     ["display", "4k", "work", "creative"], "monitor_01", 30,
     "27-inch 4K IPS monitor, 99% sRGB, USB-C 90W, height-adjustable stand."),
    ("NT-ACC-014", "NovaTidy Cable Management Kit", "Accessories", "NovaTech", 699, 899, 4.4, 61,
     ["organization", "desk", "cables"], "cablekit_01", 160,
     "Desk cable kit: clips, sleeves and reusable ties to keep the workspace clean."),
    ("NT-ACC-015", "NovaGrip Ergonomic Wrist Rest", "Accessories", "NovaTech", 899, 1099, 4.5, 73,
     ["ergonomic", "keyboard", "comfort", "desk"], None, 140,
     "Memory-foam wrist rest with a non-slip base — pairs with the NovaType keyboard."),
    ("NT-AUD-003", "NovaMic USB Desk Microphone", "Audio", "NovaTech", 4499, 4999, 4.6, 129,
     ["audio", "streaming", "calls", "podcast"], "mic_01", 70,
     "Cardioid USB condenser mic with a desk stand, gain dial and zero-latency monitoring."),
]


def inr_to_paise(inr: float) -> int:
    return round(float(inr) * 100)


async def run() -> None:
    async with async_session_factory() as session, session.begin():
        merchant = await session.scalar(
            select(Merchant).where(Merchant.merchant_code == MERCHANT_CODE)
        )
        if merchant is None:
            raise SystemExit(f"merchant {MERCHANT_CODE} not found — run the base seed first")

        added = 0
        for (
            code, name, category, brand, price, compare_at, rating, reviews, tags, image_key,
            stock, desc,
        ) in ACCESSORIES:
            exists = await session.scalar(
                select(Product).where(
                    Product.merchant_id == merchant.id,
                    Product.external_product_code == code,
                )
            )
            if exists:
                continue

            product = Product(
                id=uuid.uuid4(),
                merchant_id=merchant.id,
                external_product_code=code,
                sku=code,
                name=name,
                category=category,
                brand=brand,
                description=desc,
                price_paise=inr_to_paise(price),
                compare_at_price_paise=inr_to_paise(compare_at),
                rating=rating,
                review_count=reviews,
                tags=tags,
                image_key=image_key,
                status="active",
            )
            session.add(product)
            await session.flush()

            variant = ProductVariant(
                id=uuid.uuid4(),
                product_id=product.id,
                merchant_id=merchant.id,
                sku=code,
                price_paise=product.price_paise,
            )
            session.add(variant)
            await session.flush()

            session.add(
                Inventory(
                    id=uuid.uuid4(),
                    merchant_id=merchant.id,
                    product_variant_id=variant.id,
                    quantity_available=stock,
                    quantity_reserved=0,
                )
            )
            added += 1

        print(f"add_accessories: inserted {added} product(s) for {MERCHANT_CODE}.")


if __name__ == "__main__":
    asyncio.run(run())
