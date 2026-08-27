"""Row-level security: tenant isolation on every merchant-owned table.

FastAPI sets `SELECT set_config('app.current_merchant_id', :merchant_id, true)` per
request transaction (app/core/db.py::db_session_with_tenant), derived server-side from
the authenticated identity — never from client input (security-architecture.md #4).

This is defense-in-depth *underneath* service-layer authorization, testable locally
via manually-set session GUCs even before Supabase Auth is wired
(tests/integration/test_rls_tenant_isolation.py).

Once on Supabase, the backend connects with the service-role key for privileged
operations (which bypasses RLS by design) while any direct client-side Supabase calls
use the anon/authenticated key and remain subject to these policies.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-25
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

# Tables that carry merchant_id directly.
DIRECT_TENANT_TABLES = [
    "merchants",  # gated on id, see below (self-referential)
    "customers",
    "products",
    "product_variants",
    "inventory",
    "carts",
    "campaigns",
    "coupons",
    "orders",
    "payments",
    "policies",
    "approval_requests",
    "audit_events",
    "agent_sessions",
    "agent_actions",
    "documents",
]

# Child tables scoped via a parent table's merchant_id (no merchant_id column of their own).
CHILD_TABLE_POLICIES = {
    "cart_items": ("carts", "cart_id"),
    "order_items": ("orders", "order_id"),
    "payment_attempts": ("payments", "payment_id"),
    "campaign_rules": ("campaigns", "campaign_id"),
    "agent_messages": ("agent_sessions", "session_id"),
    "document_versions": ("documents", "document_id"),
}


def upgrade() -> None:
    for table in DIRECT_TENANT_TABLES:
        merchant_col = "id" if table == "merchants" else "merchant_id"
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            USING ({merchant_col} = current_setting('app.current_merchant_id', true)::uuid);
        """)

    for table, (parent_table, fk_col) in CHILD_TABLE_POLICIES.items():
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            USING (
                {fk_col} IN (
                    SELECT id FROM {parent_table}
                    WHERE merchant_id = current_setting('app.current_merchant_id', true)::uuid
                )
            );
        """)

    # audit_events is append-only: no role (other than a privileged/service role, which
    # bypasses RLS and grants entirely) may UPDATE or DELETE rows once written.
    op.execute("REVOKE UPDATE, DELETE ON audit_events FROM PUBLIC;")


def downgrade() -> None:
    op.execute("GRANT UPDATE, DELETE ON audit_events TO PUBLIC;")

    for table in CHILD_TABLE_POLICIES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    for table in DIRECT_TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
