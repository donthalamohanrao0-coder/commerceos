"use client";

import { useEffect } from "react";

import { Badge, Spinner } from "@/components/ui";
import { clockTime } from "@/lib/format";
import type { ActivityAction, ActivityMessage } from "@/lib/types";

import { useActivityDetail } from "./hooks";

function summarise(value: Record<string, unknown> | null): string {
  if (!value) return "—";
  const keys = Object.keys(value);
  if (keys.length === 0) return "{}";
  return keys
    .slice(0, 4)
    .map((k) => {
      const v = value[k];
      const rendered =
        typeof v === "object" && v !== null
          ? Array.isArray(v)
            ? `[${v.length}]`
            : "{…}"
          : String(v);
      return `${k}: ${rendered.length > 40 ? rendered.slice(0, 40) + "…" : rendered}`;
    })
    .join("  ·  ");
}

function ActionRow({ action }: { action: ActivityAction }) {
  const failed = action.status === "failed" || action.status === "denied_by_policy";
  return (
    <li className="border-l-2 border-[var(--color-border)] pl-3">
      <div className="flex items-center gap-2">
        <span aria-hidden="true" className={failed ? "text-[var(--color-danger)]" : "text-[var(--color-success)]"}>
          {failed ? "✕" : "✓"}
        </span>
        <span className="font-mono text-xs font-medium">{action.tool_name ?? action.node_name}</span>
        <Badge tone={failed ? "danger" : "neutral"}>{action.status}</Badge>
        {action.duration_ms != null && (
          <span className="text-xs text-[var(--color-fg-muted)]">{action.duration_ms} ms</span>
        )}
        <time className="ml-auto font-mono text-xs text-[var(--color-fg-muted)]">
          {clockTime(action.created_at)}
        </time>
      </div>
      <p className="mt-1 text-xs text-[var(--color-fg-muted)]">
        <span className="font-medium text-[var(--color-fg)]">in</span> {summarise(action.input)}
      </p>
      <p className="mt-0.5 text-xs text-[var(--color-fg-muted)]">
        <span className="font-medium text-[var(--color-fg)]">out</span> {summarise(action.output)}
      </p>
      {action.policy_decision && (
        <p className="mt-0.5 text-xs">
          <span className="font-medium">policy</span>{" "}
          <span className="text-[var(--color-fg-muted)]">{summarise(action.policy_decision)}</span>
        </p>
      )}
    </li>
  );
}

function MessageRow({ message }: { message: ActivityMessage }) {
  const text =
    typeof message.content?.text === "string" && message.content.text
      ? message.content.text
      : message.content_type === "tool_calls"
        ? "(proposed tool calls)"
        : JSON.stringify(message.content).slice(0, 160);
  return (
    <li className="flex gap-2 text-xs">
      <span className="w-16 shrink-0 font-mono text-[var(--color-fg-muted)]">{message.role}</span>
      <span className="min-w-0 flex-1 whitespace-pre-wrap">{text}</span>
    </li>
  );
}

export function SessionTrace({
  sessionId,
  onClose,
}: {
  sessionId: string;
  onClose: () => void;
}) {
  const detail = useActivityDetail(sessionId);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button
        type="button"
        aria-label="Close trace"
        onClick={onClose}
        className="absolute inset-0 bg-[var(--color-fg)]/20"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Agent session trace"
        className="relative flex h-full w-full max-w-lg flex-col overflow-y-auto border-l border-[var(--color-border)] bg-[var(--color-surface)] shadow-lg"
      >
        <div className="sticky top-0 flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-3">
          <div>
            <p className="text-sm font-semibold">Session trace</p>
            <p className="font-mono text-xs text-[var(--color-fg-muted)]">{sessionId}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-[var(--radius-control)] px-2 py-1 text-sm text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-muted)]"
          >
            Close
          </button>
        </div>

        <div className="flex-1 px-5 py-4">
          {detail.isLoading && (
            <div className="flex justify-center py-10">
              <Spinner className="size-5 text-[var(--color-fg-muted)]" />
            </div>
          )}
          {detail.isError && (
            <p className="text-sm text-[var(--color-danger)]">Could not load this trace.</p>
          )}
          {detail.data?.session && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="info">{detail.data.session.workflow}</Badge>
                <Badge tone="neutral">{detail.data.session.status}</Badge>
                <span className="text-xs text-[var(--color-fg-muted)]">
                  {detail.data.session.channel}
                </span>
              </div>

              <h3 className="mt-5 text-xs font-semibold uppercase tracking-wide text-[var(--color-fg-muted)]">
                Tool trace ({detail.data.actions.length})
              </h3>
              <ol className="mt-2 space-y-3">
                {detail.data.actions.map((a, i) => (
                  <ActionRow key={i} action={a} />
                ))}
                {detail.data.actions.length === 0 && (
                  <li className="text-xs text-[var(--color-fg-muted)]">No tool calls in this session.</li>
                )}
              </ol>

              <h3 className="mt-6 text-xs font-semibold uppercase tracking-wide text-[var(--color-fg-muted)]">
                Transcript ({detail.data.messages.length})
              </h3>
              <ol className="mt-2 space-y-1.5">
                {detail.data.messages.map((m, i) => (
                  <MessageRow key={i} message={m} />
                ))}
              </ol>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
