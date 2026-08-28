# CommerceOS — API Standards

## Versioning

All APIs begin with:

```text
/api/v1/
```

## Response Shape

Use predictable success/error structures.

Success:
```json
{
  "data": {},
  "request_id": "..."
}
```

Error:
```json
{
  "error": {
    "code": "ORDER_NOT_FOUND",
    "message": "The requested order could not be found."
  },
  "request_id": "..."
}
```

## Validation

Every request has a Pydantic schema.

Never accept arbitrary dictionaries for sensitive operations.

## Pagination

Use cursor pagination for large/continuously changing resources.

## Idempotency

Required for:
- payment creation
- refunds
- order creation where retries can duplicate state
- other financial mutations

## HTTP Semantics

Use appropriate:
- 200
- 201
- 202
- 204
- 400
- 401
- 403
- 404
- 409
- 422
- 429
- 500

## Security

Every endpoint declares:
- auth
- role/scope
- tenant scope
- rate limit

## OpenAPI

FastAPI-generated OpenAPI is the canonical API contract.

Keep schemas stable and version breaking changes.

## External Agent API

External agents receive explicit scopes and quotas.

Never expose internal service endpoints directly.
