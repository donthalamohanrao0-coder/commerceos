import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "./ChatShell";
import type { AssistantEntry, ChatEntry, UserEntry } from "./useChat";

const state = {
  entries: [] as ChatEntry[],
  status: "idle" as "idle" | "thinking" | "awaiting_approval" | "resolving",
  error: null as string | null,
  liveSteps: [] as { tool: string; status: string }[],
  livePlanning: [] as string[],
  sessionId: "sess1" as string | null,
  sendMessage: vi.fn(),
  resolveApproval: vi.fn(),
  reset: vi.fn(),
};

vi.mock("./useChat", () => ({
  useChat: () => state,
}));

vi.mock("./useCart", () => ({
  useCart: () => ({ data: { items: [], item_count: 0, subtotal_paise: 0 }, isLoading: false }),
}));

const user = (text: string): UserEntry => ({ id: `u-${text}`, kind: "user", text });
const assistant = (over: Partial<AssistantEntry> = {}): AssistantEntry => ({
  id: "a1",
  kind: "assistant",
  text: "Here are some options.",
  blocks: [],
  trace: [],
  pendingApproval: null,
  approvalOrder: null,
  approvalResolved: null,
  failed: false,
  ...over,
});

beforeEach(() => {
  state.entries = [];
  state.status = "idle";
  state.error = null;
  state.liveSteps = [];
  state.livePlanning = [];
  vi.clearAllMocks();
});

describe("ChatShell", () => {
  it("shows the welcome state and fires example prompts", async () => {
    render(<ChatShell />);
    expect(screen.getByRole("heading", { name: /what are you shopping for/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /find a laptop for coding under/i }));
    expect(state.sendMessage).toHaveBeenCalledWith("Find a laptop for coding under ₹80,000");
  });

  it("renders a conversation with product cards and contextual quick replies", () => {
    state.entries = [
      user("find a laptop"),
      assistant({
        blocks: [
          {
            type: "products",
            products: [
              { product_id: "p1", name: "NovaBook Pro 14", brand: "NovaTech", category: "Laptops", price_paise: 7499900, rating: 4.7, tags: [] },
            ],
          },
        ],
        trace: [{ tool: "catalog_search", status: "succeeded", output: {} }],
      }),
    ];
    render(<ChatShell />);
    expect(screen.getByText("find a laptop")).toBeInTheDocument();
    expect(screen.getByText("NovaBook Pro 14")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add to cart/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /compare the top two/i })).toBeInTheDocument();
    expect(screen.getByText(/all checks passed/i)).toBeInTheDocument(); // AgentActivity summary
  });

  it("shows an honest thinking indicator and disables send while a turn runs", () => {
    state.status = "thinking";
    render(<ChatShell />);
    expect(screen.getByRole("status")).toHaveTextContent(/thinking through your request/i);
    expect(screen.getByRole("button", { name: /send message/i })).toBeDisabled();
  });

  it("routes a payment approval click to resolveApproval", async () => {
    state.status = "awaiting_approval";
    state.entries = [
      user("buy it"),
      assistant({
        text: "Approve to pay.",
        pendingApproval: { approval_id: "ap1", action: "payment_initiation", order_id: "o1" },
        approvalOrder: {
          order_id: "o1",
          order_number: "ORD-1",
          status: "created",
          subtotal_paise: 500,
          discount_paise: 0,
          shipping_paise: 0,
          tax_paise: 0,
          total_paise: 500,
        },
      }),
    ];
    render(<ChatShell />);
    await userEvent.click(screen.getByRole("button", { name: /confirm & pay/i }));
    expect(state.resolveApproval).toHaveBeenCalledWith("a1", "ap1", true);
  });

  it("sends the composed message on Enter", async () => {
    render(<ChatShell />);
    const box = screen.getByRole("textbox", { name: /message the shopping assistant/i });
    await userEvent.type(box, "a wireless mouse{Enter}");
    expect(state.sendMessage).toHaveBeenCalledWith("a wireless mouse");
  });

  it("keeps the send button disabled with an empty composer", () => {
    render(<ChatShell />);
    expect(screen.getByRole("button", { name: /send message/i })).toBeDisabled();
  });

  it("surfaces a turn error inline", () => {
    state.error = "Something went wrong on our side. Please try again.";
    render(<ChatShell />);
    expect(screen.getByText(/something went wrong on our side/i)).toBeInTheDocument();
  });
});
