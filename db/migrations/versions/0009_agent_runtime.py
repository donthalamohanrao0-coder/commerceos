"""agent runtime: agent_sessions, agent_messages, agent_actions
+ backfill agent_session_id FKs on carts and orders

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-25
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE agent_sessions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            customer_id uuid REFERENCES customers(id),
            workflow text NOT NULL CHECK (workflow IN ('shopping','support','growth','external_ai_buyer')),
            status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','waiting_for_user','waiting_for_approval','failed','cancelled')),
            channel text NOT NULL DEFAULT 'web_chat',
            started_at timestamptz NOT NULL DEFAULT now(),
            ended_at timestamptz,
            metadata jsonb NOT NULL DEFAULT '{}'
        );
    """)
    op.execute("CREATE INDEX idx_agent_sessions_merchant ON agent_sessions(merchant_id);")

    op.execute("""
        ALTER TABLE carts ADD CONSTRAINT fk_carts_session
        FOREIGN KEY (agent_session_id) REFERENCES agent_sessions(id);
    """)
    op.execute("""
        ALTER TABLE orders ADD CONSTRAINT fk_orders_session
        FOREIGN KEY (agent_session_id) REFERENCES agent_sessions(id);
    """)

    op.execute("""
        CREATE TABLE agent_messages (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id uuid NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
            role text NOT NULL CHECK (role IN ('user','assistant','system','tool')),
            content_type text NOT NULL DEFAULT 'text',
            content jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX idx_agent_messages_session ON agent_messages(session_id, created_at);")

    op.execute("""
        CREATE TABLE agent_actions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id uuid NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            node_name text NOT NULL,
            tool_name text,
            input jsonb NOT NULL DEFAULT '{}',
            output jsonb,
            status text NOT NULL CHECK (status IN ('started','succeeded','failed','denied_by_policy')),
            policy_decision jsonb,
            duration_ms int,
            created_at timestamptz NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX idx_agent_actions_session ON agent_actions(session_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_actions;")
    op.execute("DROP TABLE IF EXISTS agent_messages;")
    op.execute("ALTER TABLE orders DROP CONSTRAINT IF EXISTS fk_orders_session;")
    op.execute("ALTER TABLE carts DROP CONSTRAINT IF EXISTS fk_carts_session;")
    op.execute("DROP TABLE IF EXISTS agent_sessions;")
