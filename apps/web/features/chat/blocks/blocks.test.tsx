import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CatalogProduct, OrderSummary } from "@/lib/types";

import type { ChatBlock } from "../deriveBlocks";
import { PaymentApprovalCard } from "../PaymentApprovalCard";
import { BlockRenderer } from "./index";

const product: CatalogProduct = {
  product_id: "p1",
  name: "NovaBook Pro 14",
  brand: "NovaTech",
  category: "Laptops",
  price_paise: 7499900,
  rating: 4.7,
  tags: ["dev", "16GB"],
};

const order: OrderSummary = {
  order_id: "o1",
  order_number: "ORD-10428",
  status: "created",
  subtotal_paise: 7499900,
  discount_paise: 100000,
  shipping_paise: 0,
  tax_paise: 0,
  total_paise: 7399900,
};

describe("BlockRenderer — product carousel", () => {
  it("shows product details and a Best match badge on the first card", () => {
    render(<BlockRenderer block={{ type: "products", products: [product] }} onAction={vi.fn()} />);
    expect(screen.getByText("NovaBook Pro 14")).toBeInTheDocument();
    expect(screen.getByText("₹74,999")).toBeInTheDocument();
    expect(screen.getByText(/best match/i)).toBeInTheDocument();
  });

  it("Add to cart sends a natural-language instruction to the agent", async () => {
    const onAction = vi.fn();
    render(<BlockRenderer block={{ type: "products", products: [product] }} onAction={onAction} />);
    await userEvent.click(screen.getByRole("button", { name: /add to cart/i }));
    expect(onAction).toHaveBeenCalledWith("Add the NovaBook Pro 14 to my cart");
  });

  it("Buy now kicks off the purchase flow through the agent", async () => {
    const onAction = vi.fn();
    render(<BlockRenderer block={{ type: "products", products: [product] }} onAction={onAction} />);
    await userEvent.click(screen.getByRole("button", { name: /buy now/i }));
    expect(onAction).toHaveBeenCalledWith("Buy the NovaBook Pro 14 now");
  });

  it("View details asks the agent about the product", async () => {
    const onAction = vi.fn();
    render(<BlockRenderer block={{ type: "products", products: [product] }} onAction={onAction} />);
    await userEvent.click(screen.getByRole("button", { name: /view details/i }));
    expect(onAction).toHaveBeenCalledWith("Tell me more about the NovaBook Pro 14");
  });
});

describe("BlockRenderer — cart / offers / recovery", () => {
  it("cart preview offers a Checkout button", async () => {
    const onAction = vi.fn();
    const block: ChatBlock = { type: "cart", cartId: "c1", itemCount: 2, subtotalPaise: 500 };
    render(<BlockRenderer block={block} onAction={onAction} />);
    await userEvent.click(screen.getByRole("button", { name: /checkout/i }));
    expect(onAction).toHaveBeenCalledWith("Proceed to checkout");
  });

  it("policy_blocked explains without leaking internals", () => {
    render(<BlockRenderer block={{ type: "policy_blocked", reason: "exceeds_max" }} />);
    expect(screen.getByText(/exceeds the merchant's transaction policy/i)).toBeInTheDocument();
  });

  it("payment failure states clearly that no charge was created", () => {
    render(<BlockRenderer block={{ type: "payment_status", state: "failed", reason: "timeout" }} onAction={vi.fn()} />);
    expect(screen.getByText(/no charge was created/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /check payment status/i })).toBeInTheDocument();
  });
});

describe("PaymentApprovalCard", () => {
  it("shows the backend total and gates on an explicit click", async () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <PaymentApprovalCard
        order={order}
        resolved={null}
        busy={false}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    expect(screen.getByText("₹73,999")).toBeInTheDocument(); // total_paise, not subtotal
    expect(screen.getByText("ORD-10428")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /confirm & pay/i }));
    expect(onConfirm).toHaveBeenCalledOnce();

    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("hides the actions once resolved and confirms no charge on decline", () => {
    render(
      <PaymentApprovalCard order={order} resolved="declined" busy={false} onConfirm={vi.fn()} onCancel={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: /confirm & pay/i })).not.toBeInTheDocument();
    expect(screen.getByText(/no charge was made/i)).toBeInTheDocument();
  });

  it("still renders a safe fallback when the order details are missing", () => {
    render(
      <PaymentApprovalCard order={null} resolved={null} busy={false} onConfirm={vi.fn()} onCancel={vi.fn()} />,
    );
    expect(screen.getByText(/waiting for your approval/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /confirm & pay/i })).toBeInTheDocument();
  });
});
