# CommerceOS — Git and CI/CD

## Branching

Use:
- `main`
- feature branches
- bugfix branches

Protect `main`.

## Pull Requests

Required:
- description
- tests
- screenshots for UI changes
- security impact assessment for sensitive changes
- migration notes where applicable

## CI Pipeline

```text
Push / PR
 ↓
Install dependencies
 ↓
Lint
 ↓
Type check
 ↓
Unit tests
 ↓
Integration tests
 ↓
Frontend build
 ↓
Security/dependency checks
```

## Deployment

Frontend:
- Vercel preview for PRs
- Vercel production after merge

Backend:
- Render deployment
- health check
- migration strategy
- rollback plan

## Database Migrations

Migrations are version-controlled.

Never manually alter production schema without a migration.

## Secrets

CI secrets come from the CI secret store.
Never commit them.

## Releases

Use semantic versioning for application releases when appropriate.

## Rollback

Every production deployment must have a rollback path.
