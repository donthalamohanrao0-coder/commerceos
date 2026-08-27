"""Deterministic catalog search — SQL filter, not Pinecone (data-architecture.md #3:
"transactional facts must never rely on RAG"). Pinecone is reserved for knowledge docs.
"""

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.exceptions import ProductNotFound
from app.domains.catalog.models import Product, ProductVariant


class CatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_products(
        self,
        merchant_id: uuid.UUID,
        *,
        query: str | None = None,
        category: str | None = None,
        max_price_paise: int | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[Product]:
        stmt = select(Product).where(Product.merchant_id == merchant_id, Product.status == "active")

        if category:
            stmt = stmt.where(Product.category.ilike(category))
        if max_price_paise is not None:
            stmt = stmt.where(Product.price_paise <= max_price_paise)
        if tags:
            stmt = stmt.where(Product.tags.overlap(tags))
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Product.name.ilike(like),
                    Product.description.ilike(like),
                    Product.brand.ilike(like),
                )
            )

        stmt = stmt.order_by(Product.rating.desc().nullslast()).limit(limit)
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def get_product(self, merchant_id: uuid.UUID, product_id: uuid.UUID) -> Product:
        product = await self._session.scalar(
            select(Product).where(
                and_(Product.id == product_id, Product.merchant_id == merchant_id)
            )
        )
        if product is None:
            raise ProductNotFound(str(product_id))
        return product

    async def get_default_variant(
        self, merchant_id: uuid.UUID, product_id: uuid.UUID
    ) -> ProductVariant:
        variant = await self._session.scalar(
            select(ProductVariant).where(
                ProductVariant.merchant_id == merchant_id,
                ProductVariant.product_id == product_id,
            )
        )
        if variant is None:
            raise ProductNotFound(str(product_id))
        return variant

    async def get_products_by_codes(
        self, merchant_id: uuid.UUID, codes: list[str]
    ) -> list[Product]:
        if not codes:
            return []
        result = await self._session.scalars(
            select(Product).where(
                Product.merchant_id == merchant_id, Product.external_product_code.in_(codes)
            )
        )
        return list(result.all())
