"use client";

import { useEffect } from "react";

import { Button, Spinner } from "@/components/ui";
import { rupees } from "@/lib/format";

import { ProductTile } from "./blocks/ProductTile";
import { useCart } from "./useCart";

export function CartDrawer({
  sessionId,
  turn,
  open,
  onClose,
  onCheckout,
}: {
  sessionId: string | null;
  turn: number;
  open: boolean;
  onClose: () => void;
  onCheckout: () => void;
}) {
  const cart = useCart(open ? sessionId : null, turn);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const items = cart.data?.items ?? [];
  const subtotal = cart.data?.subtotal_paise ?? 0;

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button
        type="button"
        aria-label="Close cart"
        onClick={onClose}
        className="absolute inset-0 bg-[var(--color-fg)]/20"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Your cart"
        className="relative flex h-full w-full max-w-sm flex-col border-l border-[var(--color-border)] bg-[var(--color-surface)] shadow-lg"
      >
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-3">
          <p className="text-sm font-semibold">Your cart</p>
          <button
            type="button"
            onClick={onClose}
            className="rounded-[var(--radius-control)] px-2 py-1 text-sm text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-muted)]"
          >
            Close
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {cart.isLoading && items.length === 0 ? (
            <div className="flex justify-center py-10">
              <Spinner className="size-5 text-[var(--color-fg-muted)]" />
            </div>
          ) : items.length === 0 ? (
            <p className="py-10 text-center text-sm text-[var(--color-fg-muted)]">
              Your cart is empty. Ask the assistant to add something.
            </p>
          ) : (
            <ul className="space-y-3">
              {items.map((it, i) => (
                <li key={i} className="flex gap-3">
                  <ProductTile
                    name={it.name}
                    category={it.category}
                    imageKey={it.image_key}
                    className="size-14 shrink-0 rounded-[var(--radius-control)]"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{it.name}</p>
                    <p className="text-xs text-[var(--color-fg-muted)]">
                      Qty {it.quantity} · {rupees(it.unit_price_paise)}
                    </p>
                  </div>
                  <p className="text-sm font-medium">{rupees(it.line_total_paise)}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="border-t border-[var(--color-border)] px-5 py-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[var(--color-fg-muted)]">Subtotal</span>
            <span className="font-semibold">{rupees(subtotal)}</span>
          </div>
          <p className="mt-1 text-xs text-[var(--color-fg-muted)]">
            Discounts, shipping and tax are calculated by the backend at checkout.
          </p>
          <Button
            className="mt-3 w-full"
            disabled={items.length === 0}
            onClick={onCheckout}
          >
            Checkout
          </Button>
        </div>
      </div>
    </div>
  );
}
