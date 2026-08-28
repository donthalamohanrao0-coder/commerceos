"""Catalog search must be forgiving of how the LLM phrases a tool call — a
lowercase / singular `category` and a free-text `query` for a product type both
have to resolve, or the shopping agent falsely reports "no products"."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.service import CatalogService

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("category", ["Laptops", "laptops", "laptop"])
async def test_category_filter_tolerates_case_and_plural(
    db: AsyncSession, merchant, category: str
) -> None:
    results = await CatalogService(db).search_products(
        merchant.id, category=category, max_price_paise=8_000_000
    )
    assert results, f"category={category!r} returned nothing"
    assert all(r.category.lower().startswith("laptop") for r in results)
    assert all(r.price_paise <= 8_000_000 for r in results)


async def test_free_text_query_matches_on_category_too(db: AsyncSession, merchant) -> None:
    # NovaTech product names are brand names ("NovaBook…"), not "laptop" — the
    # query still has to find them via category/description.
    results = await CatalogService(db).search_products(merchant.id, query="laptop")
    assert any("NovaBook" in r.name for r in results)


async def test_use_case_word_in_query_matches_tags(db: AsyncSession, merchant) -> None:
    # The model routinely puts "coding" in `query`; it's a tag, not in the name.
    results = await CatalogService(db).search_products(
        merchant.id, query="coding", category="Laptops", max_price_paise=8_000_000
    )
    assert [r.name for r in results] == ["NovaBook Pro 14"]


async def test_multi_word_query_matches_any_word(db: AsyncSession, merchant) -> None:
    results = await CatalogService(db).search_products(
        merchant.id, query="laptop for coding", category="Laptops"
    )
    assert {r.name for r in results} >= {"NovaBook Pro 14", "NovaBook Air 13"}


async def test_no_match_returns_empty_not_error(db: AsyncSession, merchant) -> None:
    results = await CatalogService(db).search_products(
        merchant.id, category="Laptops", max_price_paise=1_000
    )
    assert results == []
