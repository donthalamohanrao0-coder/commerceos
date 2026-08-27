# CommerceOS — Repository Structure

```text
commerceos/
├── apps/
│   └── web/
├── backend/
│   └── app/
│       ├── api/
│       ├── core/
│       ├── domains/
│       ├── agents/
│       ├── knowledge/
│       ├── policies/
│       ├── approvals/
│       ├── audit/
│       ├── workers/
│       └── integrations/
├── db/
│   ├── migrations/
│   └── seeds/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── agent-evals/
├── docs/
├── infra/
├── .github/
├── Dockerfile
└── README.md
```

## Backend Domain Structure

```text
payments/
├── models.py
├── schemas.py
├── repository.py
├── service.py
├── state_machine.py
├── exceptions.py
└── tests/
```

## Agent Structure

```text
agents/
├── graphs/
├── nodes/
├── tools/
├── prompts/
├── state/
└── policies/
```

## Integration Structure

```text
integrations/
├── razorpay/
├── openai/
├── pinecone/
├── langfuse/
└── supabase/
```

## Rule

Dependencies flow inward toward domain logic. Domain logic should not depend on HTTP route implementations.
