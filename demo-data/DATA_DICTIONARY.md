# CommerceOS Demo Business Data Dictionary

## Authoritative data
PostgreSQL/commerce services are authoritative for:
- price
- inventory
- order state
- payment state
- campaign eligibility
- customer authorization

## RAG data
Documents under `knowledge/` are intended for semantic retrieval.

## Synthetic data
Customers, orders, analytics, campaigns and products in this package are fictional demo data.

## Images
Stock image references are for the demo UI. Production should use merchant-owned/licensed product photography.

## Import order
1. merchant profile
2. categories
3. products
4. inventory
5. customers
6. campaigns
7. policies/knowledge
8. agent configuration
9. historical orders/analytics
