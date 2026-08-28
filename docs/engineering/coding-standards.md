# CommerceOS — Coding Standards

## Python

- Python 3.12+
- Type hints required for public functions
- Pydantic for external data validation
- Ruff for linting/formatting
- MyPy for static typing
- Pytest for tests
- Prefer small pure functions
- Avoid hidden global state

## TypeScript

- Strict TypeScript
- ESLint
- Prettier
- Zod for runtime validation
- Avoid `any`
- Prefer typed API clients

## Naming

Use domain-specific names.

Bad:
- `data`
- `result`
- `doThing`

Good:
- `payment_attempt`
- `order_total`
- `agent_action`

## Error Handling

Use typed/domain exceptions.

Do not expose internal exception messages directly to clients.

## Routes

Routes should:
- authenticate
- validate
- call service
- serialize response

Routes should not contain large business logic.

## Services

Services own business workflows.

## Repositories

Repositories own persistence operations.

## Integrations

External providers are accessed through adapters.

## Comments

Comment why something is non-obvious, not what obvious code does.

## AI Code

Never trust LLM output without schema validation.

## Dependency Rules

Domain modules should not import API-layer code.

Infrastructure adapters should not leak into domain models.

## Definition of Done

Every feature includes:
- tests
- error handling
- authorization
- audit requirement assessment
- observability requirement assessment
