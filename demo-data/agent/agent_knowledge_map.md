# Agent Knowledge Map

## Authoritative structured sources
- Product price → PostgreSQL catalog
- Inventory → inventory service/database
- Order state → PostgreSQL
- Payment state → verified payment service/webhooks
- Campaign eligibility → campaign service
- Customer permissions → authorization service

## RAG knowledge
- shipping policy
- returns policy
- warranty policy
- support FAQ
- recommendation guide
- merchant brand guidelines

## Never use RAG as authority for
- current price
- stock
- payment state
- order state
- refund amount
- customer authorization

## Retrieval metadata
Every vector should contain:
- merchant_id
- document_id
- document_version
- document_type
- chunk_id
