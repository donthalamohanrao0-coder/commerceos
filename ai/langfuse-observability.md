# CommerceOS — Langfuse Observability

## 1. Role

Langfuse is the primary AI observability and evaluation platform.

Use it for:
- traces
- generations
- tool observations
- retrieval observations
- prompt versions
- datasets
- evaluations
- cost/latency analysis

## 2. Trace Hierarchy

```text
Trace: customer_session
├── Intent generation
├── Product retrieval
├── Recommendation generation
├── Tool: search_products
├── Tool: add_to_cart
├── RAG retrieval
├── Upsell decision
├── Campaign calculation
└── Payment request
```

## 3. Metadata

Useful metadata:
- merchant_id
- agent_type
- session_id
- order_id
- environment
- application_version

Do not include secrets.

## 4. Prompt Management

Prompts should have versions.

Development:
- experiment
- evaluate
- compare

Production:
- promote approved version
- monitor
- rollback if required

## 5. Cost

Track:
- model
- tokens
- latency
- estimated cost

## 6. Evaluations

Attach scores such as:
- task_success
- policy_compliance
- tool_accuracy
- groundedness
- recommendation_quality

## 7. Privacy

Sanitize sensitive inputs/outputs before sending them to Langfuse.

## 8. Correlation

Every AI trace should be correlatable with:
- request_id
- agent_session_id
- order_id where relevant

## 9. Production Monitoring

Monitor:
- error rate
- latency
- token usage
- cost
- tool failure rate
- evaluation scores

## 10. Complementary Tools

Langfuse is for AI/application-level observability.

Sentry is for application errors.

OpenTelemetry is for distributed infrastructure traces.

Do not duplicate every signal across all three systems.
