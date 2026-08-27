"""orders: orders, order_items

agent_session_id FK on orders is added in 0009 once agent_sessions exists.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-25
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

ORDER_STATUSES = (
    "created",
    "payment_pending",
    "payment_processing",
    "paid",
    "fulfilled",
    "failed",
    "cancelled",
    "refund_requested",
    "refund_processing",
    "refunded",
)


def upgrade() -> None:
    statuses_sql = ",".join(f"'{s}'" for s in ORDER_STATUSES)
    op.execute(f"""
        CREATE TABLE orders (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            customer_id uuid REFERENCES customers(id),
            cart_id uuid REFERENCES carts(id),
            order_number text NOT NULL,
            status text NOT NULL DEFAULT 'created' CHECK (status IN ({statuses_sql})),
            subtotal_paise bigint NOT NULL,
            discount_paise bigint NOT NULL DEFAULT 0,
            shipping_paise bigint NOT NULL DEFAULT 0,
            tax_paise bigint NOT NULL DEFAULT 0,
            total_paise bigint NOT NULL,
            campaign_id uuid REFERENCES campaigns(id),
            source text NOT NULL DEFAULT 'customer' CHECK (source IN ('customer','ai_assisted','external_ai_buyer')),
            agent_session_id uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (merchant_id, order_number)
        );
    """)
    op.execute("CREATE INDEX idx_orders_merchant_status ON orders(merchant_id, status);")
    op.execute("CREATE INDEX idx_orders_customer ON orders(customer_id);")

    op.execute("""
        CREATE TABLE order_items (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id uuid NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            product_variant_id uuid NOT NULL REFERENCES product_variants(id),
            product_name_snapshot text NOT NULL,
            quantity int NOT NULL CHECK (quantity > 0),
            unit_price_paise bigint NOT NULL,
            line_total_paise bigint NOT NULL
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS order_items;")
    op.execute("DROP TABLE IF EXISTS orders;")
