"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui";
import { Markdown } from "@/components/ui/Markdown";
import { AgentActivity } from "./AgentActivity";
import { BlockRenderer } from "./blocks";
import { PaymentApprovalCard } from "./PaymentApprovalCard";
import { CartDrawer } from "./CartDrawer";
import { QuickReplies } from "./QuickReplies";
import { useCart } from "./useCart";
import type { ChatBlock } from "./deriveBlocks";
import { useChat, type AssistantEntry, type ChatEntry } from "./useChat";

const EXAMPLE_PROMPTS = [
  "Find a laptop for coding under ₹80,000",
  "What is your return policy?",
  "Recommend a wireless mouse",
  "What are today's best offers?",
];

const PLACEHOLDERS = [
  "Ask anything… e.g. “a lightweight laptop under ₹70k”",
  "Try “compare the top two”",
  "Try “what's your delivery time?”",
  "Type a message…",
];

function Welcome({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="co-fade-up mx-auto max-w-xl py-16 text-center">
      <div
        className="mx-auto flex size-11 items-center justify-center rounded-2xl bg-[var(--color-primary)] text-lg text-[var(--color-primary-fg)] shadow-[var(--shadow-md)]"
        aria-hidden="true"
      >
        ✦
      </div>
      <h1 className="mt-4 text-[1.7rem] font-semibold tracking-tight">
        What are you shopping for?
      </h1>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-[var(--color-fg-muted)]">
        Ask in plain language. The assistant proposes; the store&apos;s backend prices it, checks
        policy, and gates every payment behind your confirmation.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-2">
        {EXAMPLE_PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onPick(p)}
            className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2 text-sm text-[var(--color-fg-muted)] shadow-[var(--shadow-xs)] transition-all duration-150 hover:-translate-y-0.5 hover:text-[var(--color-fg)] hover:shadow-[var(--shadow-sm)]"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

function AssistantBubble({
  entry,
  busyApproval,
  paying,
  onAction,
  onPay,
  onResolve,
}: {
  entry: AssistantEntry;
  busyApproval: boolean;
  paying: boolean;
  onAction: (text: string) => void;
  onPay: (b: ChatBlock & { type: "checkout" }) => void;
  onResolve: (approved: boolean) => void;
}) {
  return (
    <div className="space-y-3">
      {entry.text &&
        (entry.failed ? (
          <p className="text-sm text-[var(--color-danger)]">{entry.text}</p>
        ) : (
          <Markdown>{entry.text}</Markdown>
        ))}

      {entry.blocks.map((block, i) => (
        <BlockRenderer key={i} block={block} onAction={onAction} onPay={onPay} paying={paying} />
      ))}

      {entry.pendingApproval && (
        <PaymentApprovalCard
          order={entry.approvalOrder}
          resolved={entry.approvalResolved}
          busy={busyApproval}
          onConfirm={() => onResolve(true)}
          onCancel={() => onResolve(false)}
        />
      )}
    </div>
  );
}

export function ChatShell() {
  const {
    entries,
    status,
    error,
    liveSteps,
    livePlanning,
    paying,
    sessionId,
    sendMessage,
    resolveApproval,
    payFor,
    reset,
  } = useChat();
  const [draft, setDraft] = useState("");
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const [cartOpen, setCartOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  const busy = status === "thinking";
  const resolving = status === "resolving";
  const inputDisabled = busy || resolving;

  const turnCount = entries.filter((e) => e.kind === "assistant").length;
  const cart = useCart(sessionId, turnCount);
  const cartCount = cart.data?.item_count ?? 0;

  const lastAssistantId = [...entries].reverse().find((e) => e.kind === "assistant")?.id ?? null;

  // Rotate the placeholder gently while the composer is empty and idle.
  useEffect(() => {
    if (draft || inputDisabled) return;
    const t = setInterval(() => setPlaceholderIdx((i) => (i + 1) % PLACEHOLDERS.length), 4500);
    return () => clearInterval(t);
  }, [draft, inputDisabled]);

  // Keep pinned to the latest message unless the user has scrolled up to read.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 200;
    if (nearBottom) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries, status]);

  // Auto-grow the textarea.
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "0px";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [draft]);

  function submit(text: string) {
    if (!text.trim() || inputDisabled) return;
    setDraft("");
    void sendMessage(text);
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-2 sm:px-6">
        <p className="text-sm font-medium">Shop with AI</p>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setCartOpen(true)}
            className="relative flex items-center gap-1.5 rounded-[var(--radius-control)] px-2.5 py-1.5 text-xs text-[var(--color-fg-muted)] transition-colors hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-fg)]"
            aria-label={`Cart, ${cartCount} item${cartCount === 1 ? "" : "s"}`}
          >
            <svg viewBox="0 0 24 24" className="size-4" fill="none" aria-hidden="true">
              <path
                d="M6 6h15l-1.5 9h-12L5 3H2M7 20a1 1 0 100-2 1 1 0 000 2zM18 20a1 1 0 100-2 1 1 0 000 2z"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Cart
            {cartCount > 0 && (
              <span className="ml-0.5 rounded-full bg-[var(--color-primary)] px-1.5 text-[10px] font-semibold text-[var(--color-primary-fg)]">
                {cartCount}
              </span>
            )}
          </button>
          {entries.length > 0 && (
            <Button variant="ghost" className="px-2 py-1 text-xs" onClick={reset}>
              New conversation
            </Button>
          )}
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
          {entries.length === 0 && !busy ? (
            <Welcome onPick={submit} />
          ) : (
            <div className="space-y-6">
              {entries.map((entry: ChatEntry) =>
                entry.kind === "user" ? (
                  <div key={entry.id} className="co-fade-up flex justify-end">
                    <p className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-[var(--color-primary)] px-4 py-2.5 text-sm leading-relaxed text-[var(--color-primary-fg)] shadow-[var(--shadow-sm)]">
                      {entry.text}
                    </p>
                  </div>
                ) : (
                  <div key={entry.id} className="co-fade-up space-y-2">
                    <AssistantBubble
                      entry={entry}
                      busyApproval={resolving}
                      paying={paying}
                      onAction={submit}
                      onPay={(b) =>
                        payFor({
                          paymentId: b.paymentId,
                          orderId: b.orderId,
                          amountPaise: b.amountPaise,
                        })
                      }
                      onResolve={(approved) =>
                        entry.pendingApproval &&
                        resolveApproval(entry.id, entry.pendingApproval.approval_id, approved)
                      }
                    />
                    {!entry.failed && entry.trace.length > 0 && (
                      <AgentActivity busy={false} trace={entry.trace} />
                    )}
                    {entry.id === lastAssistantId && !inputDisabled && (
                      <QuickReplies entry={entry} disabled={inputDisabled} onPick={submit} />
                    )}
                  </div>
                ),
              )}

              {busy && (
                <AgentActivity busy liveSteps={liveSteps} livePlanning={livePlanning} />
              )}
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t border-[var(--color-border)] bg-[var(--color-bg)]/80 px-4 py-3 backdrop-blur sm:px-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit(draft);
          }}
          className="mx-auto flex max-w-3xl items-end gap-2"
        >
          <textarea
            ref={taRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit(draft);
              }
            }}
            rows={1}
            placeholder={PLACEHOLDERS[placeholderIdx]}
            aria-label="Message the shopping assistant"
            className="max-h-40 flex-1 resize-none rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-sm shadow-[var(--shadow-xs)] transition-shadow duration-150 placeholder:text-[var(--color-fg-muted)] focus:border-[var(--color-info)] focus:shadow-[var(--shadow-focus)] focus:outline-none"
          />
          <button
            type="submit"
            disabled={!draft.trim() || inputDisabled}
            aria-label="Send message"
            className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary)] text-[var(--color-primary-fg)] shadow-[var(--shadow-sm)] transition-all duration-150 hover:shadow-[var(--shadow-md)] active:translate-y-px disabled:opacity-40 disabled:shadow-none"
          >
            {busy ? (
              <span className="co-pulse text-lg leading-none" aria-hidden="true">
                •
              </span>
            ) : (
              <svg viewBox="0 0 24 24" className="size-4" fill="none" aria-hidden="true">
                <path
                  d="M12 19V5M5 12l7-7 7 7"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </form>
        {error && (
          <p className="mx-auto mt-2 max-w-3xl text-xs text-[var(--color-danger)]">{error}</p>
        )}
        <p className="mx-auto mt-2 max-w-3xl text-[11px] text-[var(--color-fg-muted)]">
          Payments run on Razorpay test mode. The assistant can never charge a card without your
          explicit confirmation.
        </p>
      </div>

      <CartDrawer
        sessionId={sessionId}
        turn={turnCount}
        open={cartOpen}
        onClose={() => setCartOpen(false)}
        onCheckout={() => {
          setCartOpen(false);
          submit("Proceed to checkout and pay");
        }}
      />
    </div>
  );
}
