"""payments: payments, payment_attempts

idempotency_key_id FK on payment_attempts is added in 0008 once idempotency_keys exists.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-25
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

PAYMENT_STATUSES = (
    "created",
    "pending",
    "processing",
    "paid",
    "failed",
    "refund_requested",
    "refund_processing",
    "refunded",
)


def upgrade() -> None:
    statuses_sql = ",".join(f"'{s}'" for s in PAYMENT_STATUSES)
    op.execute(f"""
        CREATE TABLE payments (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            order_id uuid NOT NULL REFERENCES orders(id),
            status text NOT NULL DEFAULT 'created' CHECK (status IN ({statuses_sql})),
            amount_paise bigint NOT NULL CHECK (amount_paise > 0),
            currency text NOT NULL DEFAULT 'INR',
            provider text NOT NULL DEFAULT 'razorpay',
            provider_order_id text,
            provider_payment_id text,
            razorpay_signature_verified boolean NOT NULL DEFAULT false,
            failure_reason text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (order_id)
        );
    """)
    op.execute("CREATE INDEX idx_payments_merchant_status ON payments(merchant_id, status);")
    op.execute(
        "CREATE UNIQUE INDEX uq_payments_provider_order ON payments(provider_order_id) "
        "WHERE provider_order_id IS NOT NULL;"
    )

    op.execute("""
        CREATE TABLE payment_attempts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            payment_id uuid NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
            attempt_number int NOT NULL,
            status text NOT NULL CHECK (status IN ('initiated','pending','succeeded','failed','timed_out')),
            provider_payment_id text,
            provider_error_code text,
            provider_error_description text,
            idempotency_key_id uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (payment_id, attempt_number)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payment_attempts;")
    op.execute("DROP TABLE IF EXISTS payments;")
