"""agent_api_keys — credentials for external AI buyers hitting the Agent Commerce
API (ADR-006). Capability-scoped, per-key rate limited, revocable. The raw key is
shown once at creation; only a SHA-256 hash is stored.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-27
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

_ALLOWED_SCOPES = (
    "catalog:read",
    "catalog:search",
    "quote:create",
    "order:create",
    "payment:request",
)


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE agent_api_keys (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            name text NOT NULL,
            key_prefix text NOT NULL,
            key_hash text NOT NULL UNIQUE,
            scopes text[] NOT NULL DEFAULT '{{}}',
            rate_limit_per_minute integer NOT NULL DEFAULT 60,
            status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
            last_used_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            CHECK (scopes <@ ARRAY[{", ".join(f"'{s}'" for s in _ALLOWED_SCOPES)}]::text[])
        );
    """)
    op.execute("CREATE INDEX idx_agent_api_keys_merchant ON agent_api_keys (merchant_id);")

    op.execute("ALTER TABLE agent_api_keys ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE agent_api_keys FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_agent_api_keys ON agent_api_keys
        USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_api_keys;")
