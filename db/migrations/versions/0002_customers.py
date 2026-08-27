"""customers

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-25
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE customers (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            user_id uuid REFERENCES users(id),
            external_customer_code text,
            name text NOT NULL,
            email text,
            phone text,
            city text,
            segment text,
            lifetime_value_paise bigint NOT NULL DEFAULT 0,
            orders_count int NOT NULL DEFAULT 0,
            preferred_categories text[] NOT NULL DEFAULT '{}',
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (merchant_id, external_customer_code)
        );
    """)
    op.execute("CREATE INDEX idx_customers_merchant ON customers(merchant_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS customers;")
