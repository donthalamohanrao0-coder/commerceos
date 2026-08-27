# CommerceOS — Harness Engineering Patterns (reference)

Patterns adapted from deepseek-ai/deepseek-harness's architecture (a general-purpose
TypeScript coding-agent harness — not vendored here, just studied for transferable
design). Mapped onto our LangGraph/FastAPI shopping-agent build.

## 1. Append-only log is the only source of model-visible context

Harness rule: "model-visible means logged" — `deriveMessages()` reconstructs
everything the model sees purely by replaying the session event log; a runtime
invariant asserts nothing reaches a model request that isn't reconstructable from it.

**Applies to us via `agent_messages`.** Build `derive_messages(session_id)` in
`agents/state/` as the *only* function that assembles LLM-visible history. No node
should carry its own parallel in-memory conversation state — this keeps our
explainability/audit story (agent-architecture.md, 04-ai-agent-experience.md) airtight:
if it influenced the model, it's in the table, full stop.

## 2. Tool pipeline as three explicit stages

Harness shape: `tools/pre-execute -> tools/execute -> tools/post-execute`, each a
waterfall any listener can veto or rewrite.

**This is our `tool-security.md` contract, formalized.** Implement the LangGraph tool
wrapper (`agents/tools/_pipeline.py`) as three explicit stages rather than one flat
function:
- pre-execute: schema validation, re-check authz/tenant ownership, policy engine check
- execute: call the domain service
- post-execute: validate/typed result, `audit.record(...)`

Keeps the mapping table in plan.md Phase 6 (node -> tool -> service -> policy ->
audit) mechanically enforced instead of hand-wired per tool.

## 3. Capability seams (Service Definition / Provider / Consumer)

Harness rule: a seam is swappable because it has three separated roles; one provider
swap (e.g. local sandbox -> remote sandbox) changes the whole product with zero
consumer forks.

**Confirms what we already planned**: `integrations/{razorpay,openai,pinecone}/client.py`
as adapters behind an interface, with `FakeOpenAIClient`/`FakeRazorpayClient`
implementations so Phase 6/7 can be built and tested before real credentials arrive.
No change needed — just keep tool code depending on the interface, never the concrete
client.

## 4. `agent/pre-step` as an explicit gate

Harness rule: before every model step, a dedicated hook can reject or rewrite the
claimed input; a rejected/empty step still closes the turn and is logged.

**Adopt for our shopping graph**: give `classify_intent` (the graph's entry node) an
explicit pre-step gate that runs before any LLM call — this is the formal home for:
- prompt-injection-defense.md's requirement that retrieved RAG content is evidence,
  not instructions (sanitize/delimit here, not ad hoc inside prompt templates)
- rate-limit / bounded-execution checks (max_graph_steps, max_tool_calls) from
  agent_config.json

A rejection here should still write an `agent_actions` row (status=denied_by_policy)
so the failure is visible in the merchant Agent Activity trace, matching how a
rejected harness step still records the attempt.

## Not adopted

The plugin-tree/profile/bundle composition system (Cordis), the web/headless runtime,
and the subagent-team coordination layer are solving a different problem (a general
extensible coding-agent product) and have no counterpart need in CommerceOS's single
LangGraph shopping/support/growth graph — not brought in.
