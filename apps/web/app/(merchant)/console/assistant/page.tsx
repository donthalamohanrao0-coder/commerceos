"use client";

import { useRef, useState } from "react";

import { Badge, Button, Card } from "@/components/ui";
import { Markdown } from "@/components/ui/Markdown";
import { PageHeader } from "@/features/console/Shared";
import { api, ApiError } from "@/lib/api";
import type { AgentTurn, StartSessionResponse } from "@/lib/types";

type Msg =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; tools: { tool: string; status: string }[] };

const SUGGESTIONS = [
  "Where can I grow revenue this month?",
  "What products are frequently bought together?",
  "Draft a cross-sell campaign for laptop buyers",
];

export default function AssistantPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<{ approval_id: string; action: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sessionId = useRef<string | null>(null);

  async function ensureSession(): Promise<string> {
    if (sessionId.current) return sessionId.current;
    const res = await api<StartSessionResponse>("/agent/sessions", {
      method: "POST",
      body: { workflow: "growth", channel: "web_console" },
    });
    sessionId.current = res.session_id;
    return res.session_id;
  }

  function applyTurn(turn: AgentTurn) {
    setMsgs((m) => [
      ...m,
      {
        role: "assistant",
        text: turn.assistant || "…",
        tools: turn.tool_trace.map((t) => ({ tool: t.tool, status: t.status })),
      },
    ]);
    setPending(
      turn.pending_approval
        ? {
            approval_id: turn.pending_approval.approval_id,
            action: turn.pending_approval.action,
          }
        : null,
    );
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setError(null);
    setInput("");
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const sid = await ensureSession();
      const turn = await api<AgentTurn>(`/agent/sessions/${sid}/messages`, {
        method: "POST",
        body: { text: q },
      });
      applyTurn(turn);
    } catch (e) {
      setError(e instanceof ApiError ? e.friendlyMessage : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function decide(approved: boolean) {
    if (!pending || !sessionId.current || busy) return;
    setBusy(true);
    setError(null);
    try {
      const turn = await api<AgentTurn>(
        `/agent/sessions/${sessionId.current}/approvals/${pending.approval_id}`,
        { method: "POST", body: { approved } },
      );
      applyTurn(turn);
    } catch (e) {
      setError(e instanceof ApiError ? e.friendlyMessage : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Growth assistant"
        description="Ask the growth agent to analyse revenue and propose a campaign. It can only draft — every campaign stays inactive until you approve it here."
      />

      <div className="mx-auto max-w-2xl">
        {msgs.length === 0 && (
          <Card className="mb-4">
            <p className="mb-3 text-sm text-[var(--color-fg-muted)]">Try asking:</p>
            <div className="flex flex-col gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  disabled={busy}
                  className="rounded-[var(--radius-control)] border border-[var(--color-border)] px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--color-surface-muted)] disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </Card>
        )}

        <div className="flex flex-col gap-3">
          {msgs.map((m, i) => (
            <div key={i} className={m.role === "user" ? "self-end" : "self-start"}>
              <div
                className={
                  m.role === "user"
                    ? "rounded-[var(--radius-card)] bg-[var(--color-primary)] px-4 py-2 text-sm text-[var(--color-primary-fg)]"
                    : "rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm"
                }
              >
                {m.role === "assistant" ? <Markdown>{m.text}</Markdown> : m.text}
                {m.role === "assistant" && m.tools.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {m.tools.map((t, j) => (
                      <Badge key={j} tone={t.status === "failed" ? "danger" : "neutral"}>
                        {t.tool}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && <p className="self-start text-xs text-[var(--color-fg-muted)]">Thinking…</p>}
        </div>

        {pending && (
          <Card className="mt-3 border-[var(--color-warning)]">
            <p className="text-sm font-medium">
              The assistant is asking to {pending.action.replace(/_/g, " ")}.
            </p>
            <p className="mb-3 mt-1 text-xs text-[var(--color-fg-muted)]">
              Nothing goes live until you approve. The policy is re-checked at activation.
            </p>
            <div className="flex gap-2">
              <Button variant="primary" loading={busy} onClick={() => decide(true)}>
                Approve
              </Button>
              <Button variant="secondary" disabled={busy} onClick={() => decide(false)}>
                Decline
              </Button>
            </div>
          </Card>
        )}

        {error && <p className="mt-3 text-sm text-[var(--color-danger)]">{error}</p>}

        <form
          className="mt-4 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about revenue, cross-sell, campaigns…"
            className="flex-1 rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm outline-none focus:border-[var(--color-primary)]"
            disabled={busy}
          />
          <Button variant="primary" loading={busy} disabled={!input.trim()}>
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}
