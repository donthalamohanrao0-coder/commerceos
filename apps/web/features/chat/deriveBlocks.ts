import type {
  AgentTurn,
  CatalogProduct,
  KnowledgeResult,
  OrderSummary,
  ToolTraceRow,
} from "@/lib/types";

/**
 * The backend returns a plain assistant string plus a `tool_trace` of the real
 * tool calls it made (frontend-architecture.md §8: typed blocks, never rendered
 * HTML from the model). We reconstruct rich, deterministic UI blocks from that
 * trace — every block corresponds to a real backend event (ai-agent-experience.md
 * §13 "No fake AI").
 */
export type ChatBlock =
  | { type: "products"; products: CatalogProduct[] }
  | { type: "knowledge"; results: KnowledgeResult[] }
  | { type: "cart"; cartId: string | null; itemCount: number; subtotalPaise: number }
  | { type: "campaign"; name: string | null; discountPaise: number; reason: string }
  | {
      type: "upsell";
      products: (Pick<
        CatalogProduct,
        "product_id" | "name" | "brand" | "category" | "price_paise" | "rating"
      > & { unlocks_campaign?: string | null })[];
      reason: string;
      basis: "history" | "complement" | string;
    }
  | { type: "order"; order: OrderSummary }
  | {
      type: "checkout";
      paymentId: string;
      orderId: string;
      amountPaise: number;
    }
  | { type: "payment_status"; state: "success" | "failed"; reason?: string; providerOrderId?: string; amountPaise?: number }
  | { type: "policy_blocked"; reason: string }
  | { type: "error_recovery"; tool: string };

function num(v: unknown): number {
  return typeof v === "number" ? v : 0;
}

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

export function deriveBlocks(trace: ToolTraceRow[]): ChatBlock[] {
  const blocks: ChatBlock[] = [];

  for (const row of trace) {
    const out = (row.output ?? {}) as Record<string, unknown>;

    switch (row.tool) {
      case "catalog_search": {
        const products = (out.products as CatalogProduct[] | undefined) ?? [];
        if (products.length) blocks.push({ type: "products", products });
        break;
      }
      case "knowledge_search": {
        const results = (out.results as KnowledgeResult[] | undefined) ?? [];
        if (results.length) blocks.push({ type: "knowledge", results });
        break;
      }
      case "cart_add_item":
      case "cart_view": {
        if (out.error) {
          blocks.push({ type: "error_recovery", tool: row.tool });
          break;
        }
        blocks.push({
          type: "cart",
          cartId: str(out.cart_id) ?? null,
          itemCount: num(out.item_count),
          subtotalPaise: num(out.subtotal_paise),
        });
        break;
      }
      case "suggest_addons": {
        const suggestions =
          (out.suggestions as (ChatBlock & { type: "upsell" })["products"] | undefined) ?? [];
        if (suggestions.length) {
          blocks.push({
            type: "upsell",
            products: suggestions,
            reason: str(out.reason) ?? "You might also like",
            basis: str(out.basis) ?? "complement",
          });
        }
        break;
      }
      case "campaign_preview": {
        const discount = num(out.discount_paise);
        const name = str(out.campaign) ?? null;
        if (discount > 0 || name) {
          blocks.push({
            type: "campaign",
            name,
            discountPaise: discount,
            reason: str(out.reason) ?? "",
          });
        }
        break;
      }
      case "order_create": {
        if (out.error) {
          blocks.push({ type: "error_recovery", tool: row.tool });
          break;
        }
        if (out.order_id) blocks.push({ type: "order", order: out as unknown as OrderSummary });
        break;
      }
      case "payment_request": {
        const status = str(out.status);
        // The turn is parked for confirmation — the approval card owns the UI here.
        if (status === "awaiting_customer_confirmation") break;
        if (status === "policy_denied") {
          blocks.push({ type: "policy_blocked", reason: str(out.reason) ?? "" });
        } else if (out.stage === "checkout_pending" && out.payment_id && out.provider_order_id) {
          // Approval granted -> a Razorpay order exists; the customer still has to
          // pay in Checkout. The frontend drives that and captures on success.
          blocks.push({
            type: "checkout",
            paymentId: str(out.payment_id) ?? "",
            orderId: str(out.provider_order_id) ?? "",
            amountPaise: num(out.amount_paise),
          });
        } else if (status === "payment_created" || status === "captured" || status === "paid") {
          blocks.push({
            type: "payment_status",
            state: "success",
            providerOrderId: str(out.provider_order_id),
            amountPaise: num(out.amount_paise),
          });
        } else if (row.status === "failed") {
          blocks.push({ type: "payment_status", state: "failed", reason: str(out.reason) });
        }
        break;
      }
      default: {
        if (row.status === "failed") blocks.push({ type: "error_recovery", tool: row.tool });
      }
    }
  }

  return blocks;
}

/** Order totals for the approval card, pulled from the same turn's trace. */
export function orderFromTurn(turn: AgentTurn): OrderSummary | null {
  const row = turn.tool_trace.find(
    (r) => r.tool === "order_create" && r.output && !("error" in (r.output as object)),
  );
  return row ? (row.output as unknown as OrderSummary) : null;
}
