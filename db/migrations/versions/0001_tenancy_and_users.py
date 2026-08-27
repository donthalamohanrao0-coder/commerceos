"""tenancy and users: organizations, merchants, users, merchant_users

Revision ID: 0001
Revises:
Create Date: 2026-08-25
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE organizations (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE TABLE merchants (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id uuid NOT NULL REFERENCES organizations(id),
            merchant_code text NOT NULL UNIQUE,
            business_name text NOT NULL,
            legal_name text,
            currency text NOT NULL DEFAULT 'INR',
            country text NOT NULL DEFAULT 'IN',
            timezone text NOT NULL DEFAULT 'Asia/Kolkata',
            gst_percent numeric(5,2) NOT NULL DEFAULT 18.00,
            prices_tax_inclusive boolean NOT NULL DEFAULT true,
            pinecone_namespace text NOT NULL,
            status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended')),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE TABLE users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            auth_provider_id uuid,
            email text NOT NULL UNIQUE,
            role text NOT NULL CHECK (role IN ('CUSTOMER','MERCHANT_OPERATOR','MERCHANT_ADMIN','PLATFORM_ADMIN','EXTERNAL_AGENT')),
            created_at timestamptz NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
        CREATE TABLE merchant_users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            user_id uuid NOT NULL REFERENCES users(id),
            role text NOT NULL CHECK (role IN ('MERCHANT_OPERATOR','MERCHANT_ADMIN')),
            UNIQUE (merchant_id, user_id)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS merchant_users;")
    op.execute("DROP TABLE IF EXISTS users;")
    op.execute("DROP TABLE IF EXISTS merchants;")
    op.execute("DROP TABLE IF EXISTS organizations;")
