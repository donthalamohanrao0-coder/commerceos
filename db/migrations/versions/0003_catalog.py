"""catalog: products, product_variants, inventory

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-25
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE products (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            external_product_code text NOT NULL,
            sku text NOT NULL,
            name text NOT NULL,
            category text NOT NULL,
            brand text,
            description text,
            price_paise bigint NOT NULL CHECK (price_paise >= 0),
            compare_at_price_paise bigint,
            rating numeric(2,1),
            review_count int NOT NULL DEFAULT 0,
            attributes jsonb NOT NULL DEFAULT '{}',
            tags text[] NOT NULL DEFAULT '{}',
            cross_sell_product_codes text[] NOT NULL DEFAULT '{}',
            image_key text,
            status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (merchant_id, external_product_code),
            UNIQUE (merchant_id, sku)
        );
    """)
    op.execute("CREATE INDEX idx_products_merchant_category ON products(merchant_id, category);")

    op.execute("""
        CREATE TABLE product_variants (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id uuid NOT NULL REFERENCES products(id),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            sku text NOT NULL,
            variant_attributes jsonb NOT NULL DEFAULT '{}',
            price_paise bigint NOT NULL,
            status text NOT NULL DEFAULT 'active',
            UNIQUE (merchant_id, sku)
        );
    """)
    op.execute("CREATE INDEX idx_product_variants_merchant ON product_variants(merchant_id);")

    op.execute("""
        CREATE TABLE inventory (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            product_variant_id uuid NOT NULL REFERENCES product_variants(id),
            quantity_available int NOT NULL CHECK (quantity_available >= 0),
            quantity_reserved int NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (product_variant_id)
        );
    """)
    op.execute("CREATE INDEX idx_inventory_merchant ON inventory(merchant_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS inventory;")
    op.execute("DROP TABLE IF EXISTS product_variants;")
    op.execute("DROP TABLE IF EXISTS products;")
