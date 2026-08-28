import { describe, expect, it } from "vitest";

import type { AgentTurn, ToolTraceRow } from "@/lib/types";

import { deriveBlocks, orderFromTurn } from "./deriveBlocks";

const row = (tool: string, status: string, output: Record<string, unknown> | null): ToolTraceRow => ({
  tool,
  status,
  output,
});

describe("deriveBlocks", () => {
  it("turns catalog_search results into a products block", () => {
    const blocks = deriveBlocks([
      row("catalog_search", "succeeded", {
        products: [{ product_id: "p1", name: "NovaBook Pro 14", price_paise: 7499900, tags: [] }],
      }),
    ]);
    expect(blocks).toHaveLength(1);
    expect(blocks[0]).toMatchObject({ type: "products" });
  });

  it("emits nothing for an empty catalog_search", () => {
    expect(deriveBlocks([row("catalog_search", "succeeded", { products: [] })])).toEqual([]);
  });

  it("turns knowledge_search hits into a knowledge block", () => {
    const blocks = deriveBlocks([
      row("knowledge_search", "succeeded", {
        results: [{ text: "Q\n\n7 days.", heading: "Returns", document_type: "policy", score: 0.9 }],
      }),
    ]);
    expect(blocks[0]).toMatchObject({ type: "knowledge" });
  });

  it("maps a cart add to a cart block, and a cart error to recovery", () => {
    expect(
      deriveBlocks([row("cart_add_item", "succeeded", { cart_id: "c1", item_count: 2, subtotal_paise: 500 })])[0],
    ).toMatchObject({ type: "cart", itemCount: 2, subtotalPaise: 500 });

    expect(
      deriveBlocks([row("cart_add_item", "failed", { error: "insufficient_stock" })])[0],
    ).toMatchObject({ type: "error_recovery", tool: "cart_add_item" });
  });

  it("only shows a campaign block when there is an actual discount or named campaign", () => {
    expect(deriveBlocks([row("campaign_preview", "succeeded", { discount_paise: 0, campaign: null })])).toEqual(
      [],
    );
    expect(
      deriveBlocks([row("campaign_preview", "succeeded", { discount_paise: 1000, campaign: "Bundle" })])[0],
    ).toMatchObject({ type: "campaign", discountPaise: 1000, name: "Bundle" });
  });

  it("maps suggest_addons to an upsell block, and an empty one to nothing", () => {
    expect(deriveBlocks([row("suggest_addons", "succeeded", { suggestions: [] })])).toEqual([]);
    const b = deriveBlocks([
      row("suggest_addons", "succeeded", {
        basis: "history",
        reason: "Frequently bought with the NovaBook Pro 14",
        suggestions: [
          { product_id: "p2", name: "NovaGlide Wireless Mouse", category: "Mice", price_paise: 129900 },
        ],
      }),
    ])[0];
    expect(b).toMatchObject({ type: "upsell", basis: "history" });
    expect(b.type === "upsell" && b.products[0].name).toBe("NovaGlide Wireless Mouse");
  });

  it("maps order_create to an order block", () => {
    const blocks = deriveBlocks([
      row("order_create", "succeeded", { order_id: "o1", order_number: "ORD-1", total_paise: 7499900 }),
    ]);
    expect(blocks[0]).toMatchObject({ type: "order" });
  });

  describe("payment_request", () => {
    it("policy_denied -> policy_blocked", () => {
      expect(
        deriveBlocks([row("payment_request", "succeeded", { status: "policy_denied", reason: "exceeds_max" })])[0],
      ).toMatchObject({ type: "policy_blocked", reason: "exceeds_max" });
    });

    it("payment_created -> payment_status success", () => {
      expect(
        deriveBlocks([
          row("payment_request", "succeeded", {
            status: "payment_created",
            provider_order_id: "order_X",
            amount_paise: 7499900,
          }),
        ])[0],
      ).toMatchObject({ type: "payment_status", state: "success", providerOrderId: "order_X" });
    });

    it("checkout_pending stage (approval granted) -> a checkout block", () => {
      expect(
        deriveBlocks([
          row("payment_request", "succeeded", {
            stage: "checkout_pending",
            payment_id: "pmt_1",
            provider_order_id: "order_Y",
            amount_paise: 100,
          }),
        ])[0],
      ).toMatchObject({ type: "checkout", paymentId: "pmt_1", orderId: "order_Y", amountPaise: 100 });
    });

    it("captured / paid status -> payment_status success", () => {
      expect(
        deriveBlocks([row("payment_request", "succeeded", { status: "captured", provider_order_id: "order_Z" })])[0],
      ).toMatchObject({ type: "payment_status", state: "success", providerOrderId: "order_Z" });
    });

    it("failed row -> payment_status failed with reason", () => {
      expect(
        deriveBlocks([row("payment_request", "failed", { reason: "exceeds_max_transaction_amount" })])[0],
      ).toMatchObject({ type: "payment_status", state: "failed", reason: "exceeds_max_transaction_amount" });
    });

    it("awaiting_customer_confirmation -> no block (the approval card owns it)", () => {
      expect(
        deriveBlocks([row("payment_request", "succeeded", { status: "awaiting_customer_confirmation" })]),
      ).toEqual([]);
    });
  });

  it("preserves order and covers a full buy sequence", () => {
    const blocks = deriveBlocks([
      row("cart_add_item", "succeeded", { cart_id: "c1", item_count: 1, subtotal_paise: 7499900 }),
      row("order_create", "succeeded", { order_id: "o1", order_number: "ORD-1", total_paise: 7499900 }),
      row("payment_request", "succeeded", { status: "awaiting_customer_confirmation" }),
    ]);
    expect(blocks.map((b) => b.type)).toEqual(["cart", "order"]);
  });

  it("maps an unknown failed tool to a generic recovery block", () => {
    expect(deriveBlocks([row("mystery_tool", "failed", null)])[0]).toMatchObject({
      type: "error_recovery",
      tool: "mystery_tool",
    });
  });
});

describe("orderFromTurn", () => {
  const base: AgentTurn = {
    session_id: "s1",
    session_status: "waiting_for_approval",
    assistant: "Approve?",
    pending_approval: { approval_id: "a1", action: "payment_initiation" },
    tool_trace: [],
  };

  it("returns the order_create output for the approval card", () => {
    const turn = {
      ...base,
      tool_trace: [row("order_create", "succeeded", { order_id: "o1", order_number: "ORD-9", total_paise: 500 })],
    };
    expect(orderFromTurn(turn)).toMatchObject({ order_number: "ORD-9", total_paise: 500 });
  });

  it("ignores an errored order_create row", () => {
    const turn = { ...base, tool_trace: [row("order_create", "failed", { error: "empty_cart" })] };
    expect(orderFromTurn(turn)).toBeNull();
  });
});
