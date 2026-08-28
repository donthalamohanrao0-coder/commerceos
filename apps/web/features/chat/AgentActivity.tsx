"use client";

import { useState } from "react";

import type { ToolTraceRow } from "@/lib/types";

import type { LiveStep } from "./useChat";

const SAFE_LABELS: Record<string, string> = {
  catalog_search: "Searched the catalogue",
  catalog_get_product: "Looked up product details",
  knowledge_search: "Checked store policies",
  cart_add_item: "Updated your cart",
  cart_view: "Reviewed your cart",
  suggest_addons: "Found complementary items",
  campaign_preview: "Calculated eligible offers",
  order_create: "Prepared your order",
  payment_request: "Verified payment requirements",
};

const ACTIVE_LABELS: Record<string, string> = {
  catalog_search: "Searching the catalogue…",
  catalog_get_product: "Looking up product details…",
  knowledge_search: "Checking store policies…",
  cart_add_item: "Updating your cart…",
  cart_view: "Reviewing your cart…",
  suggest_addons: "Finding complementary items…",
  campaign_preview: "Calculating eligible offers…",
  order_create: "Preparing your order…",
  payment_request: "Verifying payment requirements…",
};

const label = (tool: string) => SAFE_LABELS[tool] ?? "Worked on your request";
const activeLabel = (tool: string) => ACTIVE_LABELS[tool] ?? "Working…";

function Dots() {
  return (
    <span className="flex gap-1" aria-hidden="true">
      <span className="co-pulse size-1.5 rounded-full bg-current" style={{ animationDelay: "0ms" }} />
      <span
        className="co-pulse size-1.5 rounded-full bg-current"
        style={{ animationDelay: "200ms" }}
      />
      <span
        className="co-pulse size-1.5 rounded-full bg-current"
        style={{ animationDelay: "400ms" }}
      />
    </span>
  );
}

/** Agent-activity panel (chat spec §6, ai-agent-experience §3). While a turn
 *  streams, shows the *real* steps as the backend reports them. After the turn,
 *  collapses to a summary. Never exposes args, prompts or reasoning. */
export function AgentActivity({
  busy,
  trace,
  liveSteps = [],
  livePlanning = [],
}: {
  busy: boolean;
  trace?: ToolTraceRow[];
  liveSteps?: LiveStep[];
  livePlanning?: string[];
}) {
  const [open, setOpen] = useState(false);

  if (busy) {
    const hasProgress = liveSteps.length > 0 || livePlanning.length > 0;
    if (!hasProgress) {
      return (
        <div
          className="flex items-center gap-2 text-sm text-[var(--color-fg-muted)]"
          role="status"
          aria-live="polite"
        >
          <Dots />
          <span>Thinking through your request</span>
        </div>
      );
    }
    return (
      <ol
        className="space-y-1 border-l border-[var(--color-border)] pl-3 text-xs"
        role="status"
        aria-live="polite"
      >
        {liveSteps.map((s, i) => (
          <li key={i} className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className={
                s.status === "failed" ? "text-[var(--color-danger)]" : "text-[var(--color-success)]"
              }
            >
              {s.status === "failed" ? "✕" : "✓"}
            </span>
            <span className="text-[var(--color-fg-muted)]">{label(s.tool)}</span>
          </li>
        ))}
        {livePlanning.map((tool) => (
          <li key={`p-${tool}`} className="flex items-center gap-2 text-[var(--color-fg-muted)]">
            <Dots />
            <span>{activeLabel(tool)}</span>
          </li>
        ))}
        {livePlanning.length === 0 && (
          <li className="flex items-center gap-2 text-[var(--color-fg-muted)]">
            <Dots />
            <span>Deciding what to do next…</span>
          </li>
        )}
      </ol>
    );
  }

  if (!trace || trace.length === 0) return null;

  const failed = trace.filter((r) => r.status === "failed").length;

  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]"
        aria-expanded={open}
      >
        <span aria-hidden="true">✦</span>
        {trace.length} step{trace.length === 1 ? "" : "s"}
        {failed > 0 ? ` · ${failed} needed attention` : " · all checks passed"}
        <span aria-hidden="true">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <ol className="mt-2 space-y-1 border-l border-[var(--color-border)] pl-3">
          {trace.map((row, i) => (
            <li key={i} className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={
                  row.status === "failed"
                    ? "text-[var(--color-danger)]"
                    : "text-[var(--color-success)]"
                }
              >
                {row.status === "failed" ? "✕" : "✓"}
              </span>
              <span className="text-[var(--color-fg-muted)]">{label(row.tool)}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
