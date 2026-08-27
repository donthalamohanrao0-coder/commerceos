"""cart: carts, cart_items

agent_session_id FK on carts is added in 0009 once agent_sessions exists.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-25
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE carts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            customer_id uuid REFERENCES customers(id),
            agent_session_id uuid,
            status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','converted','abandoned')),
            currency text NOT NULL DEFAULT 'INR',
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX idx_carts_merchant_customer ON carts(merchant_id, customer_id);")

    op.execute("""
        CREATE TABLE cart_items (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cart_id uuid NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
            product_variant_id uuid NOT NULL REFERENCES product_variants(id),
            quantity int NOT NULL CHECK (quantity > 0),
            unit_price_paise bigint NOT NULL,
            added_reason text,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (cart_id, product_variant_id)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cart_items;")
    op.execute("DROP TABLE IF EXISTS carts;")
