# CommerceOS — Secrets and Data Protection

## 1. Secret Storage

Secrets live only in:
- Vercel environment variables for frontend-safe public configuration
- Render secret/environment configuration for backend secrets
- CI secret store for GitHub Actions

## 2. Never Client-Side

Never expose:
- OpenAI secret
- Pinecone secret
- Razorpay secret
- Supabase service-role key
- Langfuse secret
- Redis credentials

## 3. Logging

Redact:
- authorization headers
- bearer tokens
- API keys
- cookies
- passwords
- payment credentials
- unnecessary PII

## 4. Langfuse

Do not send secrets or unnecessary sensitive customer data into traces.

Use redaction/sanitization middleware before capturing observations.

## 5. OpenAI

Only send the minimum data required for the model to complete the task.

Do not include unrelated customer records.

## 6. Browser Storage

Do not store sensitive credentials in localStorage.

Use secure authentication mechanisms.

## 7. Data Minimization

Collect only data required for:
- commerce
- support
- analytics
- security

## 8. Backups

Production database backup and recovery procedures must be defined before real-money launch.

## 9. Incident Response

Document:
- secret rotation
- compromised API key response
- suspicious agent activity
- payment incident handling
- data access incident handling
