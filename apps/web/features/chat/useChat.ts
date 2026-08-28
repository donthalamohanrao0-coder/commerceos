"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError, apiStream } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CheckoutDismissed, openCheckout } from "@/lib/razorpay";
import { readSse } from "@/lib/sse";
import type {
  AgentTurn,
  OrderSummary,
  PendingApproval,
  StartSessionResponse,
  ToolTraceRow,
} from "@/lib/types";

import { deriveBlocks, orderFromTurn, type ChatBlock } from "./deriveBlocks";

interface CheckoutTarget {
  paymentId: string;
  orderId: string;
  amountPaise: number;
}

export interface LiveStep {
  tool: string;
  status: string;
}

export interface UserEntry {
  id: string;
  kind: "user";
  text: string;
}

export interface AssistantEntry {
  id: string;
  kind: "assistant";
  text: string;
  blocks: ChatBlock[];
  trace: ToolTraceRow[];
  pendingApproval: PendingApproval | null;
  approvalOrder: OrderSummary | null;
  approvalResolved: "approved" | "declined" | null;
  failed: boolean;
}

export type ChatEntry = UserEntry | AssistantEntry;

export type ChatStatus = "idle" | "thinking" | "awaiting_approval" | "resolving";

interface Persisted {
  sessionId: string | null;
  entries: ChatEntry[];
}

const uid = () => Math.random().toString(36).slice(2, 10);

function storageKey(merchantId: string) {
  return `commerceos.chat.${merchantId}`;
}

export function useChat() {
  const { identity } = useAuth();
  const merchantId = identity?.merchant.id ?? null;
  const queryClient = useQueryClient();

  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [status, setStatus] = useState<ChatStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [liveSteps, setLiveSteps] = useState<LiveStep[]>([]);
  const [livePlanning, setLivePlanning] = useState<string[]>([]);
  const [paying, setPaying] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const hydratedRef = useRef(false);

  const setSession = useCallback((id: string | null) => {
    sessionIdRef.current = id;
    setSessionId(id);
  }, []);

  // ---- persistence (survives refresh; spec 02 §21) ----
  useEffect(() => {
    if (!merchantId || hydratedRef.current) return;
    hydratedRef.current = true;
    try {
      const raw = localStorage.getItem(storageKey(merchantId));
      if (raw) {
        const parsed = JSON.parse(raw) as Persisted;
        setSession(parsed.sessionId);
        setEntries(parsed.entries ?? []);
        if (parsed.entries?.some((e) => e.kind === "assistant" && e.pendingApproval && !e.approvalResolved)) {
          setStatus("awaiting_approval");
        }
      }
    } catch {
      /* ignore corrupt cache */
    }
  }, [merchantId, setSession]);

  useEffect(() => {
    if (!merchantId || !hydratedRef.current) return;
    try {
      if (entries.length === 0 && !sessionIdRef.current) {
        localStorage.removeItem(storageKey(merchantId));
        return;
      }
      const data: Persisted = { sessionId: sessionIdRef.current, entries };
      localStorage.setItem(storageKey(merchantId), JSON.stringify(data));
    } catch {
      /* quota — non-fatal */
    }
  }, [merchantId, entries]);

  const ensureSession = useCallback(async (): Promise<string> => {
    if (sessionIdRef.current) return sessionIdRef.current;
    const res = await api<StartSessionResponse>("/agent/sessions", {
      method: "POST",
      body: { workflow: "shopping", channel: "web_chat" },
    });
    setSession(res.session_id);
    return res.session_id;
  }, [setSession]);

  const pushAssistantFromTurn = useCallback(
    (turn: AgentTurn, failed = false) => {
      setEntries((prev) => [
        ...prev,
        {
          id: uid(),
          kind: "assistant",
          text: turn.assistant,
          blocks: deriveBlocks(turn.tool_trace),
          trace: turn.tool_trace,
          pendingApproval: turn.pending_approval,
          approvalOrder: turn.pending_approval ? orderFromTurn(turn) : null,
          approvalResolved: null,
          failed,
        },
      ]);
      void queryClient.invalidateQueries({ queryKey: ["session-cart"] });
    },
    [queryClient],
  );

  const pushAssistantError = useCallback((text: string) => {
    setEntries((prev) => [
      ...prev,
      {
        id: uid(),
        kind: "assistant",
        text,
        blocks: [],
        trace: [],
        pendingApproval: null,
        approvalOrder: null,
        approvalResolved: null,
        failed: true,
      },
    ]);
  }, []);

  const pushAssistantBlocks = useCallback((text: string, blocks: ChatBlock[]) => {
    setEntries((prev) => [
      ...prev,
      {
        id: uid(),
        kind: "assistant",
        text,
        blocks,
        trace: [],
        pendingApproval: null,
        approvalOrder: null,
        approvalResolved: null,
        failed: false,
      },
    ]);
  }, []);

  /** Open Razorpay Checkout for a created payment intent, then verify + capture
   *  server-side. Called automatically after approval, and re-callable from the
   *  "Pay" button if the customer closes the window. */
  const payFor = useCallback(
    async (target: CheckoutTarget) => {
      if (paying) return;
      setPaying(true);
      setError(null);
      try {
        const cfg = await api<{ key_id: string; enabled: boolean }>("/payments/razorpay-config");
        if (!cfg.enabled) throw new ApiError(0, "CONFIG", "Payments are not configured.");

        const res = await openCheckout({
          keyId: cfg.key_id,
          orderId: target.orderId,
          amountPaise: target.amountPaise,
          name: identity?.merchant.business_name ?? "CommerceOS",
          description: "Order payment",
          prefill: { email: identity?.user.email },
        });

        const verified = await api<{ status: string; provider_payment_id?: string }>(
          `/payments/${target.paymentId}/verify`,
          {
            method: "POST",
            body: {
              razorpay_payment_id: res.razorpay_payment_id,
              razorpay_order_id: res.razorpay_order_id,
              razorpay_signature: res.razorpay_signature,
            },
          },
        );

        pushAssistantBlocks("Payment received — your order is confirmed.", [
          {
            type: "payment_status",
            state: "success",
            providerOrderId: target.orderId,
            amountPaise: target.amountPaise,
          },
        ]);
        void verified;
        void queryClient.invalidateQueries({ queryKey: ["session-cart"] });
      } catch (e) {
        if (e instanceof CheckoutDismissed) {
          setError("Payment window closed. Your order is still reserved — use Pay when ready.");
        } else {
          const msg = e instanceof ApiError ? e.friendlyMessage : "The payment could not be verified.";
          setError(msg);
          pushAssistantBlocks(
            `${msg} No charge was captured — you can try the payment again.`,
            [{ type: "payment_status", state: "failed", reason: undefined }],
          );
        }
      } finally {
        setPaying(false);
      }
    },
    [paying, identity, pushAssistantBlocks, queryClient],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || status === "thinking" || status === "resolving") return;

      setError(null);
      setEntries((prev) => [...prev, { id: uid(), kind: "user", text: trimmed }]);
      setStatus("thinking");
      setLiveSteps([]);
      setLivePlanning([]);

      try {
        const sessionId = await ensureSession();
        const res = await apiStream(`/agent/sessions/${sessionId}/messages/stream`, {
          text: trimmed,
        });

        let finalTurn: AgentTurn | null = null;
        for await (const ev of readSse(res.body as ReadableStream<Uint8Array>)) {
          if (ev.type === "planning") {
            setLivePlanning((ev.tools as string[] | undefined) ?? []);
          } else if (ev.type === "tool") {
            const step: LiveStep = { tool: String(ev.tool), status: String(ev.status) };
            setLiveSteps((s) => [...s, step]);
            setLivePlanning((p) => p.filter((t) => t !== step.tool));
          } else if (ev.type === "done") {
            finalTurn = {
              session_id: String(ev.session_id),
              session_status: String(ev.session_status),
              assistant: String(ev.assistant ?? ""),
              pending_approval: (ev.pending_approval as PendingApproval | null) ?? null,
              tool_trace: (ev.tool_trace as ToolTraceRow[] | undefined) ?? [],
            };
          } else if (ev.type === "error") {
            throw new ApiError(500, "STREAM", String(ev.message ?? "The assistant hit an error."));
          }
        }
        if (!finalTurn) throw new ApiError(0, "STREAM", "The response ended unexpectedly.");

        pushAssistantFromTurn(finalTurn);
        setStatus(finalTurn.pending_approval ? "awaiting_approval" : "idle");
      } catch (e) {
        const msg = e instanceof ApiError ? e.friendlyMessage : "The request failed.";
        setError(msg);
        pushAssistantError(`${msg} I haven't taken any action — you can try again.`);
        setStatus("idle");
      } finally {
        setLiveSteps([]);
        setLivePlanning([]);
      }
    },
    [status, ensureSession, pushAssistantFromTurn, pushAssistantError],
  );

  const resolveApproval = useCallback(
    async (entryId: string, approvalId: string, approved: boolean) => {
      const sid = sessionIdRef.current;
      if (!sid) return;
      setError(null);
      setStatus("resolving");
      try {
        const turn = await api<AgentTurn>(`/agent/sessions/${sid}/approvals/${approvalId}`, {
          method: "POST",
          body: { approved },
        });
        setEntries((prev) =>
          prev.map((e) =>
            e.id === entryId && e.kind === "assistant"
              ? { ...e, approvalResolved: approved ? "approved" : "declined" }
              : e,
          ),
        );
        pushAssistantFromTurn(turn);
        setStatus("idle");

        // If approval created a payment intent, open Razorpay Checkout now.
        const pending = turn.tool_trace.find(
          (r) =>
            r.tool === "payment_request" &&
            (r.output as Record<string, unknown> | null)?.stage === "checkout_pending",
        );
        const out = pending?.output as Record<string, unknown> | undefined;
        if (out?.payment_id && out?.provider_order_id) {
          void payFor({
            paymentId: String(out.payment_id),
            orderId: String(out.provider_order_id),
            amountPaise: typeof out.amount_paise === "number" ? out.amount_paise : 0,
          });
        }
      } catch (e) {
        const msg = e instanceof ApiError ? e.friendlyMessage : "Could not complete that.";
        setError(msg);
        pushAssistantError(
          `${msg} No payment was taken. You can check the payment status or try again.`,
        );
        setStatus("awaiting_approval");
      }
    },
    [pushAssistantFromTurn, pushAssistantError, payFor],
  );

  const reset = useCallback(() => {
    setSession(null);
    setEntries([]);
    setStatus("idle");
    setError(null);
    setLiveSteps([]);
    setLivePlanning([]);
    if (merchantId) {
      try {
        localStorage.removeItem(storageKey(merchantId));
      } catch {
        /* ignore */
      }
    }
  }, [merchantId, setSession]);

  return {
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
  };
}
