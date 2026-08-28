"""AnalyticsService — read-only merchant revenue analytics that feed the growth
agent. Everything is computed from authoritative order data; the agent may reason
over these numbers but can never redefine them (agent-guardrails.md #8).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from itertools import combinations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.models import Product, ProductVariant
from app.domains.orders.models import Order, OrderItem

_REVENUE_STATUSES = ("paid", "fulfilled")


@dataclass(frozen=True)
class ProductStat:
    product_id: uuid.UUID
    external_code: str
    name: str
    category: str
    units_sold: int
    revenue_paise: int


@dataclass(frozen=True)
class CrossSellPair:
    a_code: str
    a_name: str
    b_code: str
    b_name: str
    co_occurrence: int
    attach_rate: float  # co_occurrence / orders containing A


@dataclass(frozen=True)
class MerchantSnapshot:
    revenue_paise: int
    order_count: int
    paid_order_count: int
    aov_paise: int
    top_products: list[ProductStat]
    cross_sell_pairs: list[CrossSellPair]
    category_revenue: list[tuple[str, int]]


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def merchant_snapshot(
        self, merchant_id: uuid.UUID, *, top_n: int = 5
    ) -> MerchantSnapshot:
        totals = (
            await self._session.execute(
                select(func.count(Order.id), func.coalesce(func.sum(Order.total_paise), 0)).where(
                    Order.merchant_id == merchant_id, Order.status.in_(_REVENUE_STATUSES)
                )
            )
        ).one()
        paid_count, revenue = int(totals[0]), int(totals[1])
        order_count = int(
            (
                await self._session.execute(
                    select(func.count(Order.id)).where(Order.merchant_id == merchant_id)
                )
            ).scalar_one()
        )
        aov = revenue // paid_count if paid_count else 0

        # per-product units + revenue over revenue-generating orders
        rows = (
            await self._session.execute(
                select(
                    Product.id,
                    Product.external_product_code,
                    Product.name,
                    Product.category,
                    func.sum(OrderItem.quantity),
                    func.sum(OrderItem.line_total_paise),
                )
                .select_from(OrderItem)
                .join(Order, Order.id == OrderItem.order_id)
                .join(ProductVariant, ProductVariant.id == OrderItem.product_variant_id)
                .join(Product, Product.id == ProductVariant.product_id)
                .where(Order.merchant_id == merchant_id, Order.status.in_(_REVENUE_STATUSES))
                .group_by(Product.id, Product.external_product_code, Product.name, Product.category)
            )
        ).all()
        product_stats = sorted(
            (
                ProductStat(
                    product_id=r[0],
                    external_code=r[1],
                    name=r[2],
                    category=r[3],
                    units_sold=int(r[4]),
                    revenue_paise=int(r[5]),
                )
                for r in rows
            ),
            key=lambda s: s.revenue_paise,
            reverse=True,
        )

        category_revenue: dict[str, int] = {}
        for s in product_stats:
            category_revenue[s.category] = category_revenue.get(s.category, 0) + s.revenue_paise

        cross_sell = await self._cross_sell_pairs(merchant_id)

        return MerchantSnapshot(
            revenue_paise=revenue,
            order_count=order_count,
            paid_order_count=paid_count,
            aov_paise=aov,
            top_products=product_stats[:top_n],
            cross_sell_pairs=cross_sell,
            category_revenue=sorted(category_revenue.items(), key=lambda kv: kv[1], reverse=True),
        )

    async def _cross_sell_pairs(
        self, merchant_id: uuid.UUID, *, min_co_occurrence: int = 1
    ) -> list[CrossSellPair]:
        # A single co-purchase is still signal for a small merchant; production can
        # raise the threshold as order volume grows.
        rows = (
            await self._session.execute(
                select(OrderItem.order_id, Product.external_product_code, Product.name)
                .select_from(OrderItem)
                .join(Order, Order.id == OrderItem.order_id)
                .join(ProductVariant, ProductVariant.id == OrderItem.product_variant_id)
                .join(Product, Product.id == ProductVariant.product_id)
                .where(Order.merchant_id == merchant_id, Order.status.in_(_REVENUE_STATUSES))
            )
        ).all()

        by_order: dict[uuid.UUID, set[str]] = {}
        names: dict[str, str] = {}
        for order_id, code, name in rows:
            by_order.setdefault(order_id, set()).add(code)
            names[code] = name

        solo_count: dict[str, int] = {}
        pair_count: dict[tuple[str, str], int] = {}
        for codes in by_order.values():
            for code in codes:
                solo_count[code] = solo_count.get(code, 0) + 1
            for a, b in combinations(sorted(codes), 2):
                pair_count[(a, b)] = pair_count.get((a, b), 0) + 1

        pairs = [
            CrossSellPair(
                a_code=a,
                a_name=names[a],
                b_code=b,
                b_name=names[b],
                co_occurrence=n,
                attach_rate=round(n / solo_count[a], 3) if solo_count.get(a) else 0.0,
            )
            for (a, b), n in pair_count.items()
            if n >= min_co_occurrence
        ]
        return sorted(pairs, key=lambda p: (p.co_occurrence, p.attach_rate), reverse=True)
