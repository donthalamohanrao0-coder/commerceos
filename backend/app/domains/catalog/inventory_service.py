"""Inventory checks/reservations, tied to the cart -> order lifecycle."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.catalog.exceptions import ProductNotFound
from app.domains.catalog.models import Inventory


class InsufficientStock(Exception):
    pass


class InventoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get(self, merchant_id: uuid.UUID, product_variant_id: uuid.UUID) -> Inventory:
        row = await self._session.scalar(
            select(Inventory).where(
                Inventory.merchant_id == merchant_id,
                Inventory.product_variant_id == product_variant_id,
            )
        )
        if row is None:
            raise ProductNotFound(str(product_variant_id))
        return row

    async def check_available(
        self, merchant_id: uuid.UUID, product_variant_id: uuid.UUID, quantity: int
    ) -> bool:
        inv = await self._get(merchant_id, product_variant_id)
        return (inv.quantity_available - inv.quantity_reserved) >= quantity

    async def reserve(
        self, merchant_id: uuid.UUID, product_variant_id: uuid.UUID, quantity: int
    ) -> None:
        inv = await self._get(merchant_id, product_variant_id)
        if (inv.quantity_available - inv.quantity_reserved) < quantity:
            raise InsufficientStock(str(product_variant_id))
        inv.quantity_reserved += quantity
        await self._session.flush()

    async def release(
        self, merchant_id: uuid.UUID, product_variant_id: uuid.UUID, quantity: int
    ) -> None:
        inv = await self._get(merchant_id, product_variant_id)
        inv.quantity_reserved = max(0, inv.quantity_reserved - quantity)
        await self._session.flush()

    async def commit_reserved(
        self, merchant_id: uuid.UUID, product_variant_id: uuid.UUID, quantity: int
    ) -> None:
        """Order confirmed: convert a reservation into a permanent stock deduction."""
        inv = await self._get(merchant_id, product_variant_id)
        inv.quantity_reserved = max(0, inv.quantity_reserved - quantity)
        inv.quantity_available = max(0, inv.quantity_available - quantity)
        await self._session.flush()
