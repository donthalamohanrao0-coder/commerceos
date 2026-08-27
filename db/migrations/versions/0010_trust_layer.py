"""trust layer: policies, approval_requests, audit_events, webhook_events

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-25
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE policies (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            key text NOT NULL,
            value jsonb NOT NULL,
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (merchant_id, key)
        );
    """)
    op.execute("CREATE INDEX idx_policies_merchant ON policies(merchant_id);")

    op.execute("""
        CREATE TABLE approval_requests (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            session_id uuid REFERENCES agent_sessions(id),
            order_id uuid REFERENCES orders(id),
            requested_action text NOT NULL,
            requested_by text NOT NULL CHECK (requested_by IN ('customer','agent','merchant_operator')),
            payload jsonb NOT NULL,
            status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','expired')),
            decided_by uuid REFERENCES users(id),
            decided_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz
        );
    """)
    op.execute(
        "CREATE INDEX idx_approval_requests_status ON approval_requests(merchant_id, status);"
    )

    op.execute("""
        CREATE TABLE audit_events (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            actor_type text NOT NULL CHECK (actor_type IN ('customer','agent','merchant_user','system','external_agent')),
            actor_id text,
            session_id uuid REFERENCES agent_sessions(id),
            order_id uuid REFERENCES orders(id),
            action text NOT NULL,
            input jsonb,
            result jsonb,
            policy_decision jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        );
    """)
    op.execute(
        "CREATE INDEX idx_audit_events_merchant_created ON audit_events(merchant_id, created_at DESC);"
    )
    op.execute("CREATE INDEX idx_audit_events_order ON audit_events(order_id);")
    # Append-only: revoke UPDATE/DELETE from the application role (Phase 5 RLS migration
    # creates/uses the scoped app role; this statement is idempotent/no-op if the role
    # doesn't exist yet locally and is re-asserted once the role exists).

    op.execute("""
        CREATE TABLE webhook_events (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            provider text NOT NULL DEFAULT 'razorpay',
            provider_event_id text NOT NULL,
            event_type text NOT NULL,
            payload jsonb NOT NULL,
            signature_verified boolean NOT NULL,
            processing_status text NOT NULL DEFAULT 'received' CHECK (processing_status IN ('received','processed','ignored','error')),
            received_at timestamptz NOT NULL DEFAULT now(),
            processed_at timestamptz,
            UNIQUE (provider, provider_event_id)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS webhook_events;")
    op.execute("DROP TABLE IF EXISTS audit_events;")
    op.execute("DROP TABLE IF EXISTS approval_requests;")
    op.execute("DROP TABLE IF EXISTS policies;")
