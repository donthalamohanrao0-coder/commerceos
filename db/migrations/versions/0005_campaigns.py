"""campaigns: campaigns, campaign_rules, coupons

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-25
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE campaigns (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            external_campaign_code text NOT NULL,
            name text NOT NULL,
            status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','paused','archived')),
            discount_type text NOT NULL CHECK (discount_type IN ('percentage','fixed')),
            discount_percent numeric(5,2),
            discount_fixed_paise bigint,
            max_discount_paise bigint,
            requires_merchant_approval boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (merchant_id, external_campaign_code)
        );
    """)
    op.execute("CREATE INDEX idx_campaigns_merchant ON campaigns(merchant_id);")

    op.execute("""
        CREATE TABLE campaign_rules (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            campaign_id uuid NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            rule_type text NOT NULL CHECK (rule_type IN ('eligible_category','eligible_segment','min_order_value','min_category_purchase')),
            rule_value jsonb NOT NULL
        );
    """)

    op.execute("""
        CREATE TABLE coupons (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            merchant_id uuid NOT NULL REFERENCES merchants(id),
            campaign_id uuid REFERENCES campaigns(id),
            code text NOT NULL,
            max_redemptions int,
            redemptions_count int NOT NULL DEFAULT 0,
            expires_at timestamptz,
            UNIQUE (merchant_id, code)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS coupons;")
    op.execute("DROP TABLE IF EXISTS campaign_rules;")
    op.execute("DROP TABLE IF EXISTS campaigns;")
