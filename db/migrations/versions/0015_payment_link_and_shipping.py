"""payment-link settlement + full shipping address.

  1. payments.payment_link_id / payment_link_url — a headless AI buyer settles via
     a Razorpay Payment Link (it has no browser for Checkout). The link runs its
     own internal Razorpay order, so we keep the link id to reconcile against the
     provider if the webhook is missed.
  2. orders.shipping_address (JSONB) — structured delivery address captured before
     payment (name, phone, email, line1, line2, city, state, postal_code, country).

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-29
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_link_id text;")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_link_url text;")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_payments_payment_link_id "
        "ON payments (payment_link_id) WHERE payment_link_id IS NOT NULL;"
    )
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_address jsonb;")


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS shipping_address;")
    op.execute("DROP INDEX IF EXISTS idx_payments_payment_link_id;")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS payment_link_url;")
    op.execute("ALTER TABLE payments DROP COLUMN IF EXISTS payment_link_id;")
