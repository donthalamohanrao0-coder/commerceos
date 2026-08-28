import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, apiStream } from "@/lib/api";
import { openCheckout } from "@/lib/razorpay";
import { readSse, type SseEvent } from "@/lib/sse";

import { useChat } from "./useChat";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const renderChat = () => renderHook(() => useChat(), { wrapper });

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, api: vi.fn(), apiStream: vi.fn() };
});
vi.mock("@/lib/sse", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/sse")>();
  return { ...actual, readSse: vi.fn() };
});
vi.mock("@/lib/razorpay", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/razorpay")>();
  return { ...actual, openCheckout: vi.fn() };
});
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    identity: { merchant: { id: "m1", business_name: "NovaTech", merchant_code: "x" }, user: {} },
    session: { access_token: "t" },
    loading: false,
    error: null,
  }),
}));

const apiMock = vi.mocked(api);
const apiStreamMock = vi.mocked(apiStream);
const readSseMock = vi.mocked(readSse);
const openCheckoutMock = vi.mocked(openCheckout);

const START = { session_id: "sess1", workflow: "shopping", status: "active" };

/** Script the SSE stream for the next turn. */
function stream(events: SseEvent[]) {
  apiStreamMock.mockResolvedValueOnce({ body: {} } as unknown as Response);
  readSseMock.mockImplementationOnce(async function* () {
    for (const e of events) yield e;
  });
}

function doneEvent(over: Partial<SseEvent> = {}): SseEvent {
  return {
    type: "done",
    session_id: "sess1",
    session_status: "active",
    assistant: "Here you go.",
    pending_approval: null,
    tool_trace: [],
    ...over,
  };
}

beforeEach(() => {
  localStorage.clear();
  apiMock.mockReset();
  apiStreamMock.mockReset();
  readSseMock.mockReset();
});
afterEach(() => vi.clearAllMocks());

describe("useChat turn lifecycle (SSE)", () => {
  it("starts a session once, streams the turn, then reuses the session", async () => {
    apiMock.mockResolvedValueOnce(START);
    stream([
      { type: "start" },
      { type: "planning", tools: ["catalog_search"] },
      { type: "tool", tool: "catalog_search", status: "succeeded" },
      doneEvent({
        tool_trace: [
          {
            tool: "catalog_search",
            status: "succeeded",
            output: { products: [{ product_id: "p1", name: "NovaBook", price_paise: 1, tags: [] }] },
          },
        ],
      }),
    ]);

    const { result } = renderChat();
    await act(async () => {
      await result.current.sendMessage("find a laptop");
    });

    expect(result.current.entries.map((e) => e.kind)).toEqual(["user", "assistant"]);
    expect(result.current.status).toBe("idle");
    const assistant = result.current.entries[1];
    expect(assistant.kind === "assistant" && assistant.blocks[0].type).toBe("products");
    expect(result.current.liveSteps).toEqual([]); // cleared after the turn

    apiMock.mockResolvedValueOnce(START); // would start a 2nd session if called
    stream([doneEvent({ assistant: "Second." })]);
    await act(async () => {
      await result.current.sendMessage("second question");
    });

    const startCalls = apiMock.mock.calls.filter(([path]) => path === "/agent/sessions");
    expect(startCalls).toHaveLength(1);
    expect(result.current.entries).toHaveLength(4);
  });

  it("parks on a pending approval and carries the order total", async () => {
    apiMock.mockResolvedValueOnce(START);
    stream([
      { type: "tool", tool: "order_create", status: "succeeded" },
      doneEvent({
        session_status: "waiting_for_approval",
        assistant: "Approve to pay.",
        pending_approval: { approval_id: "a1", action: "payment_initiation", order_id: "o1" },
        tool_trace: [
          {
            tool: "order_create",
            status: "succeeded",
            output: { order_id: "o1", order_number: "ORD-1", total_paise: 500 },
          },
          {
            tool: "payment_request",
            status: "succeeded",
            output: { status: "awaiting_customer_confirmation" },
          },
        ],
      }),
    ]);

    const { result } = renderChat();
    await act(async () => {
      await result.current.sendMessage("buy it");
    });

    expect(result.current.status).toBe("awaiting_approval");
    const a = result.current.entries[1];
    expect(a.kind === "assistant" && a.pendingApproval?.approval_id).toBe("a1");
    expect(a.kind === "assistant" && a.approvalOrder?.total_paise).toBe(500);
  });

  it("approval -> checkout block -> Razorpay Checkout -> verified success", async () => {
    apiMock.mockResolvedValueOnce(START);
    stream([
      doneEvent({
        session_status: "waiting_for_approval",
        pending_approval: { approval_id: "a1", action: "payment_initiation" },
        tool_trace: [
          {
            tool: "order_create",
            status: "succeeded",
            output: { order_id: "o1", order_number: "ORD-1", total_paise: 500 },
          },
        ],
      }),
    ]);

    const { result } = renderChat();
    await act(async () => {
      await result.current.sendMessage("buy it");
    });
    const approvalEntry = result.current.entries[1];

    // approve -> backend returns a created payment intent (checkout_pending)
    apiMock.mockResolvedValueOnce({
      session_id: "sess1",
      session_status: "active",
      assistant: "Complete it in the Razorpay window.",
      pending_approval: null,
      tool_trace: [
        {
          tool: "payment_request",
          status: "succeeded",
          output: {
            stage: "checkout_pending",
            payment_id: "pmt_1",
            provider_order_id: "order_X",
            amount_paise: 500,
          },
        },
      ],
    });
    // payFor: razorpay-config, then verify
    apiMock.mockResolvedValueOnce({ key_id: "rzp_test_x", enabled: true });
    apiMock.mockResolvedValueOnce({ status: "paid", provider_payment_id: "pay_1" });
    openCheckoutMock.mockResolvedValueOnce({
      razorpay_payment_id: "pay_1",
      razorpay_order_id: "order_X",
      razorpay_signature: "sig",
    });

    await act(async () => {
      await result.current.resolveApproval(approvalEntry.id, "a1", true);
    });

    const updated = result.current.entries.find((e) => e.id === approvalEntry.id);
    expect(updated?.kind === "assistant" && updated.approvalResolved).toBe("approved");

    // the approval turn's entry carries a checkout block
    const approvalTurnEntry = result.current.entries.at(-2);
    expect(approvalTurnEntry?.kind === "assistant" && approvalTurnEntry.blocks[0].type).toBe(
      "checkout",
    );

    // Checkout opened with the Razorpay order id
    expect(openCheckoutMock).toHaveBeenCalledWith(
      expect.objectContaining({ orderId: "order_X", amountPaise: 500 }),
    );

    // server-side verify was called, then a success message appended
    expect(apiMock).toHaveBeenCalledWith(
      "/payments/pmt_1/verify",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({ razorpay_signature: "sig" }),
      }),
    );
    const last = result.current.entries.at(-1);
    expect(last?.kind === "assistant" && last.blocks[0]).toMatchObject({
      type: "payment_status",
      state: "success",
    });
    expect(result.current.status).toBe("idle");
  });

  it("a closed Checkout window is recoverable, not a failure", async () => {
    apiMock.mockResolvedValueOnce(START);
    stream([
      doneEvent({
        session_status: "waiting_for_approval",
        pending_approval: { approval_id: "a1", action: "payment_initiation" },
        tool_trace: [],
      }),
    ]);
    const { result } = renderChat();
    await act(async () => {
      await result.current.sendMessage("buy it");
    });

    apiMock.mockResolvedValueOnce({
      session_id: "sess1",
      session_status: "active",
      assistant: "Complete payment.",
      pending_approval: null,
      tool_trace: [
        {
          tool: "payment_request",
          status: "succeeded",
          output: {
            stage: "checkout_pending",
            payment_id: "pmt_9",
            provider_order_id: "order_9",
            amount_paise: 999,
          },
        },
      ],
    });
    apiMock.mockResolvedValueOnce({ key_id: "k", enabled: true });
    const { CheckoutDismissed } = await import("@/lib/razorpay");
    openCheckoutMock.mockRejectedValueOnce(new CheckoutDismissed());

    await act(async () => {
      await result.current.resolveApproval(result.current.entries[1].id, "a1", true);
    });

    expect(result.current.error).toMatch(/still reserved/i);
    // no failure message pushed — the checkout block stays for a retry
    const last = result.current.entries.at(-1);
    expect(last?.kind === "assistant" && last.blocks[0]?.type).toBe("checkout");
  });

  it("surfaces a stream error as a safe assistant message without taking action", async () => {
    apiMock.mockResolvedValueOnce(START);
    stream([
      { type: "start" },
      { type: "error", message: "The assistant hit an error." },
    ]);

    const { result } = renderChat();
    await act(async () => {
      await result.current.sendMessage("break it");
    });

    const last = result.current.entries.at(-1);
    expect(last?.kind === "assistant" && last.failed).toBe(true);
    expect(last?.kind === "assistant" && last.text).toMatch(/haven't taken any action/i);
    expect(result.current.error).toMatch(/something went wrong/i);
    expect(result.current.status).toBe("idle");
    expect(result.current.liveSteps).toEqual([]);
  });

  it("treats a premature stream end as a failure, not a hang", async () => {
    apiMock.mockResolvedValueOnce(START);
    stream([{ type: "start" }, { type: "tool", tool: "catalog_search", status: "succeeded" }]); // no done

    const { result } = renderChat();
    await act(async () => {
      await result.current.sendMessage("hello");
    });

    expect(result.current.status).toBe("idle");
    expect(result.current.entries.at(-1)?.kind === "assistant").toBe(true);
    expect(
      result.current.entries.at(-1)?.kind === "assistant" &&
        (result.current.entries.at(-1) as { failed: boolean }).failed,
    ).toBe(true);
  });

  it("persists the transcript to localStorage and restores it", async () => {
    apiMock.mockResolvedValueOnce(START);
    stream([doneEvent({ assistant: "Saved." })]);

    const first = renderChat();
    await act(async () => {
      await first.result.current.sendMessage("hello");
    });
    await waitFor(() => expect(localStorage.getItem("commerceos.chat.m1")).toBeTruthy());

    const second = renderChat();
    await waitFor(() => expect(second.result.current.entries).toHaveLength(2));
    expect(second.result.current.entries[0].text).toBe("hello");
  });

  it("reset clears the conversation and its stored copy", async () => {
    apiMock.mockResolvedValueOnce(START);
    stream([doneEvent({})]);
    const { result } = renderChat();
    await act(async () => {
      await result.current.sendMessage("hi");
    });
    act(() => result.current.reset());
    expect(result.current.entries).toEqual([]);
    expect(localStorage.getItem("commerceos.chat.m1")).toBeNull();
  });
});
