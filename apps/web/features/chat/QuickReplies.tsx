"use client";

import type { AssistantEntry } from "./useChat";

/** Contextual one-tap follow-ups, derived from what the last turn actually did.
 *  Keeps the conversation moving without making the customer think of the next
 *  sentence (chat spec §3 "example prompt chips", §6). */
function suggestionsFor(entry: AssistantEntry): string[] {
  if (entry.pendingApproval) return []; // the approval card owns the next action
  const kinds = new Set(entry.blocks.map((b) => b.type));

  if (kinds.has("payment_status")) {
    const paid = entry.blocks.some((b) => b.type === "payment_status" && b.state === "success");
    return paid
      ? ["Track my order", "What's your return policy?", "Start a new order"]
      : ["Check payment status", "Try the payment again"];
  }
  if (kinds.has("order")) return ["Add something else first", "Go ahead and pay"];
  if (kinds.has("cart")) return ["Proceed to checkout", "Show me a matching accessory"];
  if (kinds.has("products"))
    return ["Compare the top two", "Show cheaper options", "What offers apply?"];
  if (kinds.has("knowledge")) return ["Got it — show me products", "How long is delivery?"];
  if (kinds.has("error_recovery") || kinds.has("policy_blocked"))
    return ["Show me other options"];
  return ["Find a laptop under ₹80,000", "What are today's offers?"];
}

export function QuickReplies({
  entry,
  disabled,
  onPick,
}: {
  entry: AssistantEntry;
  disabled: boolean;
  onPick: (text: string) => void;
}) {
  const suggestions = suggestionsFor(entry);
  if (suggestions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 pt-1">
      {suggestions.map((s) => (
        <button
          key={s}
          type="button"
          disabled={disabled}
          onClick={() => onPick(s)}
          className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs text-[var(--color-fg-muted)] transition-colors hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-fg)] disabled:opacity-50"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
