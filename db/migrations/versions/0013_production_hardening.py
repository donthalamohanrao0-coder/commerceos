"""production hardening: least-privilege request role, real RLS enforcement,
FK indexes, append-only audit, updated_at triggers, Data-API lockdown.

Closes the gaps found in the 2026-08-27 schema audit:

  1. RLS was inert on the app path. The backend connects as `postgres`, which has
     rolbypassrls -> every tenant_isolation_* policy from 0013's predecessor (0012)
     was skipped. Fix: a dedicated NOLOGIN role `app_request` (no bypass, not table
     owner) that request-scoped transactions SET LOCAL ROLE into
     (app/core/db.py, app/api/deps.py::get_tenant_session), plus FORCE ROW LEVEL
     SECURITY so the policy applies even to a table owner.
  2. idempotency_keys carries merchant_id but had no policy -> add one.
  3. Hot FK columns had no index (order_items.order_id, product_variants.product_id,
     campaign_rules.campaign_id, ...) -> full scans + slow cascades. Add 23 indexes.
  4. "Append-only" audit_events was only a comment; anon/authenticated/service_role
     kept UPDATE/DELETE and the owner could always mutate -> BEFORE UPDATE/DELETE
     trigger that hard-rejects, for everyone.
  5. updated_at was maintained only by the ORM -> a raw UPDATE left it stale.
     Add a BEFORE UPDATE trigger on the 8 tables that have the column.
  6. This is a server-only database (data-architecture.md #9) but Supabase's default
     GRANTs left anon/authenticated with full DML on every table -> REVOKE, and set
     default privileges so future tables stay locked. users + webhook_events get RLS
     enabled with no permissive policy (deny-all for every non-bypass role).

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-27
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

# FK columns with no leading-column index (write amplification + slow ON DELETE).
# Exactly the 23 flagged by the 2026-08-27 audit.
FK_INDEXES = [
    ("agent_actions", "merchant_id"),
    ("agent_sessions", "customer_id"),
    ("approval_requests", "decided_by"),
    ("approval_requests", "order_id"),
    ("approval_requests", "session_id"),
    ("audit_events", "session_id"),
    ("campaign_rules", "campaign_id"),
    ("cart_items", "product_variant_id"),
    ("carts", "agent_session_id"),
    ("carts", "customer_id"),
    ("coupons", "campaign_id"),
    ("customers", "user_id"),
    ("documents", "current_version_id"),
    ("documents", "merchant_id"),
    ("merchant_users", "user_id"),
    ("merchants", "organization_id"),
    ("order_items", "order_id"),
    ("order_items", "product_variant_id"),
    ("orders", "agent_session_id"),
    ("orders", "campaign_id"),
    ("orders", "cart_id"),
    ("payment_attempts", "idempotency_key_id"),
    ("product_variants", "product_id"),
]

# Tables carrying updated_at (UpdatedAtMixin) — DB-side safety net for raw UPDATEs.
UPDATED_AT_TABLES = [
    "merchants",
    "customers",
    "products",
    "inventory",
    "carts",
    "orders",
    "payments",
    "policies",
]

# Every tenant table that already has a tenant_isolation_* policy from 0012,
# plus idempotency_keys (added here). FORCE so the policy binds even for an owner.
FORCE_RLS_TABLES = [
    "merchants",
    "customers",
    "products",
    "product_variants",
    "inventory",
    "carts",
    "cart_items",
    "campaigns",
    "campaign_rules",
    "coupons",
    "orders",
    "order_items",
    "payments",
    "payment_attempts",
    "policies",
    "approval_requests",
    "audit_events",
    "agent_sessions",
    "agent_messages",
    "agent_actions",
    "documents",
    "document_versions",
    "idempotency_keys",
]


def upgrade() -> None:
    # ------------------------------------------------------------------ 1. indexes
    for table, col in FK_INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table} ({col});")

    # ------------------------------------------------- 2. idempotency_keys tenancy
    op.execute("ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_idempotency_keys ON idempotency_keys
        USING (merchant_id = current_setting('app.current_merchant_id', true)::uuid);
    """)

    # ----------------------------------------------- 3. least-privilege app role
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_request') THEN
                CREATE ROLE app_request NOLOGIN;
            END IF;
        END
        $$;
    """)
    # backend logs in as postgres, then SET LOCAL ROLE app_request per tenant txn
    op.execute("GRANT app_request TO postgres;")
    op.execute("GRANT USAGE ON SCHEMA public TO app_request;")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_request;"
    )
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_request;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_request;"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app_request;"
    )

    # ------------------------------------------------------- 4. FORCE RLS binding
    for table in FORCE_RLS_TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")

    # -------------------------------------------- 5. Data-API lockdown (server-only)
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;"
    )
    # global tables with no merchant_id: deny-all for every non-bypass role
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE merchant_users ENABLE ROW LEVEL SECURITY;")

    # --------------------------------------------------- 6. append-only audit_events
    op.execute("""
        CREATE OR REPLACE FUNCTION reject_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'append-only table: % on % is not permitted', TG_OP, TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END
        $$;
    """)
    op.execute(
        "CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events "
        "FOR EACH ROW EXECUTE FUNCTION reject_mutation();"
    )
    op.execute(
        "CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events "
        "FOR EACH ROW EXECUTE FUNCTION reject_mutation();"
    )

    # ------------------------------------------------------ 7. updated_at safety net
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END
        $$;
    """)
    for table in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_set_updated_at BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
        )


def downgrade() -> None:
    for table in UPDATED_AT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_set_updated_at ON {table};")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")

    op.execute("DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events;")
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_delete ON audit_events;")
    op.execute("DROP FUNCTION IF EXISTS reject_mutation();")

    op.execute("ALTER TABLE merchant_users DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE webhook_events DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated;"
    )

    for table in FORCE_RLS_TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_idempotency_keys ON idempotency_keys;")
    op.execute("ALTER TABLE idempotency_keys DISABLE ROW LEVEL SECURITY;")

    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_request;"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM app_request;"
    )
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM app_request;")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM app_request;")
    op.execute("REVOKE USAGE ON SCHEMA public FROM app_request;")
    op.execute("REVOKE app_request FROM postgres;")
    op.execute("DROP ROLE IF EXISTS app_request;")

    for table, col in FK_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS idx_{table}_{col};")
