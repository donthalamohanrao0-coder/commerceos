"use client";

import { useState } from "react";

import { Badge, Button, Card } from "@/components/ui";
import { rupees } from "@/lib/format";
import type { CatalogProduct, KnowledgeResult } from "@/lib/types";

import type { ChatBlock } from "../deriveBlocks";
import { ProductTile } from "./ProductTile";

/** A tap on a card button sends a natural-language message to the agent — the
 *  agent still proposes and the backend still decides, but the customer never has
 *  to type the obvious next step (chat spec §7, §11, §14). */
type ActionFn = (text: string) => void;

/* ----------------------------------------------------------- Product carousel */

function Stars({ rating }: { rating: number | null }) {
  if (rating == null) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-[var(--color-fg-muted)]">
      <span aria-hidden="true" className="text-[var(--color-warning)]">
        ★
      </span>
      {rating.toFixed(1)}
    </span>
  );
}

function ProductCard({
  product,
  best,
  onAction,
}: {
  product: CatalogProduct;
  best: boolean;
  onAction?: ActionFn;
}) {
  return (
    <Card className="flex w-64 shrink-0 flex-col overflow-hidden">
      <ProductTile name={product.name} category={product.category} className="aspect-[4/3] w-full" />
      <div className="flex flex-1 flex-col gap-1 p-3">
        <div className="flex items-start justify-between gap-2">
          <p className="text-xs text-[var(--color-fg-muted)]">
            {product.brand ?? product.category}
          </p>
          {best && <Badge tone="info">Best match</Badge>}
        </div>
        <p className="line-clamp-2 text-sm font-medium">{product.name}</p>
        <div className="mt-1 flex items-center justify-between">
          <p className="text-sm font-semibold">{rupees(product.price_paise)}</p>
          <Stars rating={product.rating} />
        </div>
        {product.tags.length > 0 && (
          <p className="mt-1 line-clamp-1 text-xs text-[var(--color-fg-muted)]">
            {product.tags.slice(0, 3).join(" · ")}
          </p>
        )}
        <button
          type="button"
          onClick={() => onAction?.(`Tell me more about the ${product.name}`)}
          className="mt-2 self-start text-xs text-[var(--color-info)] hover:underline"
        >
          View details
        </button>
        <div className="mt-2 flex gap-2">
          <Button
            variant="secondary"
            className="flex-1 px-2 py-1.5 text-xs"
            onClick={() => onAction?.(`Add the ${product.name} to my cart`)}
          >
            Add to cart
          </Button>
          <Button
            className="flex-1 px-2 py-1.5 text-xs"
            onClick={() => onAction?.(`Buy the ${product.name} now`)}
          >
            Buy now
          </Button>
        </div>
      </div>
    </Card>
  );
}

function ProductCarousel({
  products,
  onAction,
}: {
  products: CatalogProduct[];
  onAction?: ActionFn;
}) {
  return (
    <div className="co-fade-up">
      <p className="mb-2 text-xs font-medium text-[var(--color-fg-muted)]">
        {products.length} match{products.length === 1 ? "" : "es"} from the catalogue
      </p>
      <div className="-mx-1 flex snap-x gap-3 overflow-x-auto px-1 pb-2">
        {products.map((p, i) => (
          <div key={p.product_id} className="snap-start">
            <ProductCard product={p} best={i === 0} onAction={onAction} />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------- Knowledge citation */

function KnowledgeCitation({ results }: { results: KnowledgeResult[] }) {
  const [open, setOpen] = useState(false);
  const top = results[0];
  return (
    <Card className="co-fade-up p-3">
      <p className="text-xs font-medium text-[var(--color-fg-muted)]">
        From the merchant&apos;s documents
      </p>
      <p className="mt-1 text-sm">{top.text.split("\n\n").slice(-1)[0]?.trim() || top.text}</p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="mt-2 text-xs text-[var(--color-info)] hover:underline"
        aria-expanded={open}
      >
        {open ? "Hide sources" : `Source: ${top.heading ?? top.document_type}`}
      </button>
      {open && (
        <ul className="mt-2 space-y-2 border-t border-[var(--color-border)] pt-2">
          {results.map((r, i) => (
            <li key={i} className="text-xs text-[var(--color-fg-muted)]">
              <span className="font-medium text-[var(--color-fg)]">
                {r.heading ?? r.document_type}
              </span>{" "}
              · match {(r.score * 100).toFixed(0)}%
              <p className="mt-0.5 line-clamp-3">{r.text}</p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/* ----------------------------------------------------------- Cart / campaign / order */

function CartPreview({
  itemCount,
  subtotalPaise,
  onAction,
}: {
  itemCount: number;
  subtotalPaise: number;
  onAction?: ActionFn;
}) {
  return (
    <Card className="co-fade-up p-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-[var(--color-fg-muted)]">Cart updated</p>
          <p className="text-sm">
            {itemCount} item{itemCount === 1 ? "" : "s"}
          </p>
        </div>
        <p className="text-sm font-semibold">{rupees(subtotalPaise)}</p>
      </div>
      {itemCount > 0 && (
        <div className="mt-3 flex gap-2">
          <Button
            variant="secondary"
            className="px-3 py-1.5 text-xs"
            onClick={() => onAction?.("Keep shopping — show me something to go with this")}
          >
            Keep shopping
          </Button>
          <Button
            className="px-3 py-1.5 text-xs"
            onClick={() => onAction?.("Proceed to checkout")}
          >
            Checkout
          </Button>
        </div>
      )}
    </Card>
  );
}

function CampaignCard({
  name,
  discountPaise,
  reason,
}: {
  name: string | null;
  discountPaise: number;
  reason: string;
}) {
  return (
    <Card className="co-fade-up p-3">
      <div className="flex items-center gap-2">
        <Badge tone="success">Offer</Badge>
        <p className="text-sm font-medium">{name ?? "Eligible discount"}</p>
      </div>
      <div className="mt-2 flex items-center justify-between text-sm">
        <span className="text-[var(--color-fg-muted)]">Campaign discount</span>
        <span className="font-semibold text-[var(--color-success)]">-{rupees(discountPaise)}</span>
      </div>
      {reason && reason !== "empty_cart" && (
        <p className="mt-1 text-xs text-[var(--color-fg-muted)]">Eligibility: {reason}</p>
      )}
      <p className="mt-2 text-xs text-[var(--color-fg-muted)]">
        The final total is re-checked and policy-capped by the backend at checkout.
      </p>
    </Card>
  );
}

function OrderPreview({ order }: { order: ChatBlock & { type: "order" } }) {
  const o = order.order;
  const rows: [string, number][] = [
    ["Subtotal", o.subtotal_paise],
    ["Discount", -o.discount_paise],
    ["Shipping", o.shipping_paise],
    ["Tax", o.tax_paise],
  ];
  return (
    <Card className="co-fade-up p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">Order prepared</p>
        <span className="font-mono text-xs text-[var(--color-fg-muted)]">{o.order_number}</span>
      </div>
      <dl className="mt-3 space-y-1.5 text-sm">
        {rows
          .filter(([, v]) => v !== 0)
          .map(([label, value]) => (
            <div key={label} className="flex justify-between">
              <dt className="text-[var(--color-fg-muted)]">{label}</dt>
              <dd className={value < 0 ? "text-[var(--color-success)]" : ""}>
                {value < 0 ? "-" : ""}
                {rupees(Math.abs(value))}
              </dd>
            </div>
          ))}
        <div className="flex justify-between border-t border-[var(--color-border)] pt-1.5 font-semibold">
          <dt>Total</dt>
          <dd>{rupees(o.total_paise)}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-[var(--color-fg-muted)]">
        No payment has been taken. Confirmation is required before any charge.
      </p>
    </Card>
  );
}

/* ----------------------------------------------------------- Payment status */

function PaymentStatusCard({
  block,
  onAction,
}: {
  block: ChatBlock & { type: "payment_status" };
  onAction?: ActionFn;
}) {
  if (block.state === "success") {
    return (
      <Card className="co-fade-up border-[var(--color-success)] bg-[var(--color-success-bg)] p-4">
        <Badge tone="success">Payment authorised</Badge>
        <p className="mt-2 text-sm">
          {block.amountPaise ? rupees(block.amountPaise, true) : "Payment"} authorised on Razorpay
          test mode.
        </p>
        {block.providerOrderId && (
          <p className="mt-1 font-mono text-xs text-[var(--color-fg-muted)]">
            {block.providerOrderId}
          </p>
        )}
        <div className="mt-3 flex gap-2">
          <Button
            variant="secondary"
            className="px-3 py-1.5 text-xs"
            onClick={() => onAction?.("What's the status of my order?")}
          >
            Track my order
          </Button>
          <Button
            variant="secondary"
            className="px-3 py-1.5 text-xs"
            onClick={() => onAction?.("I'd like to shop for something else")}
          >
            Shop for more
          </Button>
        </div>
      </Card>
    );
  }
  return (
    <Card className="co-fade-up border-[var(--color-danger)] bg-[var(--color-danger-bg)] p-4">
      <p className="text-sm font-semibold text-[var(--color-danger)]">
        Payment couldn&apos;t be completed
      </p>
      <p className="mt-1 text-sm">No charge was created and no duplicate attempt was made.</p>
      {block.reason && (
        <p className="mt-1 text-xs text-[var(--color-fg-muted)]">Reason: {block.reason}</p>
      )}
      <div className="mt-3 flex gap-2">
        <Button
          variant="secondary"
          className="px-3 py-1.5 text-xs"
          onClick={() => onAction?.("What's my payment status?")}
        >
          Check payment status
        </Button>
        <Button
          className="px-3 py-1.5 text-xs"
          onClick={() => onAction?.("Try the payment again")}
        >
          Try again
        </Button>
      </div>
    </Card>
  );
}

function PolicyBlockedCard({ reason }: { reason: string }) {
  return (
    <Card className="co-fade-up border-[var(--color-warning)] bg-[var(--color-warning-bg)] p-4">
      <p className="text-sm font-semibold text-[var(--color-warning)]">Action unavailable</p>
      <p className="mt-1 text-sm">
        I can&apos;t complete that automatically because it exceeds the merchant&apos;s transaction
        policy.
      </p>
      {reason && <p className="mt-1 text-xs text-[var(--color-fg-muted)]">{reason}</p>}
    </Card>
  );
}

function ErrorRecoveryCard({ tool, onAction }: { tool: string; onAction?: ActionFn }) {
  const label: Record<string, string> = {
    catalog_search: "The catalogue search",
    cart_add_item: "Adding that to your cart",
    order_create: "Preparing your order",
    payment_request: "The payment step",
  };
  return (
    <Card className="co-fade-up border-[var(--color-border)] p-3">
      <p className="text-sm">
        {label[tool] ?? "That step"} didn&apos;t go through. I haven&apos;t created an order or taken
        any payment.
      </p>
      <Button
        variant="secondary"
        className="mt-2 px-3 py-1.5 text-xs"
        onClick={() => onAction?.("Please try that again")}
      >
        Try again
      </Button>
    </Card>
  );
}

/* ----------------------------------------------------------- Upsell / cross-sell */

function UpsellCard({
  block,
  onAction,
}: {
  block: ChatBlock & { type: "upsell" };
  onAction?: ActionFn;
}) {
  return (
    <Card className="co-fade-up p-3">
      <div className="flex items-center gap-2">
        <Badge tone={block.basis === "history" ? "success" : "info"}>
          {block.basis === "history" ? "Frequently bought together" : "Goes well with this"}
        </Badge>
      </div>
      <p className="mt-1 text-xs text-[var(--color-fg-muted)]">{block.reason}</p>
      <ul className="mt-2 divide-y divide-[var(--color-border)]">
        {block.products.map((p) => (
          <li key={p.product_id} className="flex items-center gap-3 py-2">
            <ProductTile
              name={p.name}
              category={p.category}
              className="size-11 shrink-0 rounded-[var(--radius-control)]"
            />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{p.name}</p>
              <p className="text-xs text-[var(--color-fg-muted)]">{rupees(p.price_paise)}</p>
              {p.unlocks_campaign && (
                <p className="mt-0.5 flex items-center gap-1 text-xs font-medium text-[var(--color-success)]">
                  <svg viewBox="0 0 16 16" className="size-3 shrink-0" fill="currentColor" aria-hidden="true">
                    <path d="M11 6V5a3 3 0 0 0-6 0v1H3.5A1.5 1.5 0 0 0 2 7.5v5A1.5 1.5 0 0 0 3.5 14h9a1.5 1.5 0 0 0 1.5-1.5v-5A1.5 1.5 0 0 0 12.5 6H11ZM6.5 5a1.5 1.5 0 0 1 3 0v1h-3V5Z" />
                  </svg>
                  Unlocks {p.unlocks_campaign}
                </p>
              )}
            </div>
            <Button
              variant="secondary"
              className="px-3 py-1.5 text-xs"
              onClick={() => onAction?.(`Add the ${p.name} to my cart`)}
            >
              Add
            </Button>
          </li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => onAction?.("No thanks, that's all for now")}
        className="mt-1 text-xs text-[var(--color-fg-muted)] hover:underline"
      >
        Not now
      </button>
    </Card>
  );
}

/* ----------------------------------------------------------- Checkout */

function CheckoutCard({
  block,
  paying,
  onPay,
}: {
  block: ChatBlock & { type: "checkout" };
  paying: boolean;
  onPay?: (b: ChatBlock & { type: "checkout" }) => void;
}) {
  return (
    <Card className="co-fade-up border-[var(--color-fg)]/15 p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">Complete your payment</p>
        <Badge tone="info">Razorpay · test mode</Badge>
      </div>
      <p className="mt-1 text-sm text-[var(--color-fg-muted)]">
        Your order is reserved. Pay {rupees(block.amountPaise, true)} in the secure Razorpay window —
        we confirm the order the moment it clears.
      </p>
      <p className="mt-1 text-xs text-[var(--color-fg-muted)]">
        Test card 4111 1111 1111 1111, any future expiry, any CVV.
      </p>
      <Button className="mt-3" loading={paying} onClick={() => onPay?.(block)}>
        Pay {rupees(block.amountPaise)}
      </Button>
    </Card>
  );
}

/* ----------------------------------------------------------- Renderer */

export function BlockRenderer({
  block,
  onAction,
  onPay,
  paying = false,
}: {
  block: ChatBlock;
  onAction?: ActionFn;
  onPay?: (b: ChatBlock & { type: "checkout" }) => void;
  paying?: boolean;
}) {
  switch (block.type) {
    case "products":
      return <ProductCarousel products={block.products} onAction={onAction} />;
    case "knowledge":
      return <KnowledgeCitation results={block.results} />;
    case "cart":
      return (
        <CartPreview
          itemCount={block.itemCount}
          subtotalPaise={block.subtotalPaise}
          onAction={onAction}
        />
      );
    case "campaign":
      return (
        <CampaignCard name={block.name} discountPaise={block.discountPaise} reason={block.reason} />
      );
    case "upsell":
      return <UpsellCard block={block} onAction={onAction} />;
    case "order":
      return <OrderPreview order={block} />;
    case "checkout":
      return <CheckoutCard block={block} paying={paying} onPay={onPay} />;
    case "payment_status":
      return <PaymentStatusCard block={block} onAction={onAction} />;
    case "policy_blocked":
      return <PolicyBlockedCard reason={block.reason} />;
    case "error_recovery":
      return <ErrorRecoveryCard tool={block.tool} onAction={onAction} />;
    default:
      return null;
  }
}
