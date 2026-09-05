"""payment_mandates — a buyer's standing, pre-authorised spending mandate.

The AP2 / ACP / UAP model on real rails: a human authorises a ceiling + expiry
once (Razorpay UPI AutoPay `as_presented` variable mandate / a card or e-mandate
token), and afterwards an external AI buyer's confirmed payment call charges
within that ceiling with no per-purchase checkout hand-off. The backend still
refuses any charge above the ceiling or past the expiry.

  * one row per authorised mandate, scoped to a merchant + a buyer customer
  * `provider_customer_id` / `provider_token_id` are the Razorpay handles
  * status: pending_authorization -> active -> (cancelled | expired)

Tenant-isolated like every merchant-owned table (RLS + FORCE, migrations 0012/0013).

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-05
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS payment_mandates (
            id                    uuid PRIMARY KEY,
            merchant_id           uuid NOT NULL REFERENCES merchants(id),
            customer_id           uuid NOT NULL REFERENCES customers(id),
            provider              text NOT NULL DEFAULT 'razorpay',
            provider_customer_id  text,
            provider_token_id     text,
            provider_order_id     text,
            method                text NOT NULL DEFAULT 'upi',
            max_amount_paise      bigint NOT NULL,
            currency              text NOT NULL DEFAULT 'INR',
            consent_reference     text NOT NULL,
            status                text NOT NULL DEFAULT 'pending_authorization',
            expires_at            timestamptz NOT NULL,
            authorized_at         timestamptz,
            cancelled_at          timestamptz,
            created_at            timestamptz NOT NULL DEFAULT now(),
            updated_at            timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_payment_mandates_status CHECK (
                status IN ('pending_authorization','active','cancelled','expired')
            ),
            CONSTRAINT ck_payment_mandates_amount_positive CHECK (max_amount_paise > 0)
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_payment_mandates_merchant_customer "
        "ON payment_mandates (merchant_id, customer_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_payment_mandates_provider_customer "
        "ON payment_mandates (provider_customer_id) "
        "WHERE provider_customer_id IS NOT NULL;"
    )

    # Tenant isolation — same shape as every other merchant-owned table.
    op.execute("ALTER TABLE payment_mandates ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE payment_mandates FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_payment_mandates ON payment_mandates
        USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);
    """)
    # 0013 granted app_request DML on all existing tables + default privileges for
    # future ones, but be explicit for a table added after that migration ran.
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON payment_mandates TO app_request;"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_payment_mandates ON payment_mandates;")
    op.execute("DROP TABLE IF EXISTS payment_mandates;")
