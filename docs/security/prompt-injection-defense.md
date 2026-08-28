# CommerceOS — Prompt Injection Defense

## 1. Threat Model

Potential injection sources:
- customer messages
- product descriptions
- merchant documents
- retrieved RAG chunks
- external AI requests
- tool outputs

## 2. Core Rule

Retrieved content is data, not instructions.

A document saying "ignore previous instructions" must never override system policy.

## 3. Prompt Separation

Separate:
- system policy
- developer instructions
- user content
- retrieved data
- tool output

Use clear delimiters and structured message construction.

## 4. Tool Boundary

Even a successful prompt injection must not bypass:
- authorization
- tenant isolation
- policy engine
- tool allowlist
- payment gating

## 5. Output Validation

Validate structured model outputs.

Reject:
- unknown tool names
- malformed arguments
- unexpected capabilities
- out-of-range financial values

## 6. RAG Safety

Retrieved documents may contain malicious instructions.

The model should be explicitly instructed to use them only as evidence.

## 7. External Agent Safety

External AI agents must use capability-scoped APIs and cannot access internal prompts or services.

## 8. Testing

Maintain adversarial prompts covering:
- refund manipulation
- tenant escape
- secret extraction
- tool escalation
- instruction injection
- malicious product descriptions
- malicious PDFs
