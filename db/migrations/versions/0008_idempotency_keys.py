"""idempotency_keys + backfill FK from payment_attempts

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-25
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE idempotency_keys (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            operation text NOT NULL,
            idempotency_key text NOT NULL,
            request_hash text NOT NULL,
            response jsonb,
            status text NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress','completed','failed')),
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (merchant_id, operation, idempotency_key)
        );
    """)

    op.execute("""
        ALTER TABLE payment_attempts
        ADD CONSTRAINT fk_payment_attempts_idempotency_key
        FOREIGN KEY (idempotency_key_id) REFERENCES idempotency_keys(id);
    """)


def downgrade() -> None:
    op.execute(
        "ALTER TABLE payment_attempts DROP CONSTRAINT IF EXISTS fk_payment_attempts_idempotency_key;"
    )
    op.execute("DROP TABLE IF EXISTS idempotency_keys;")
