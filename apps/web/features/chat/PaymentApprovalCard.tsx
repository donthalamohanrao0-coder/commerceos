"use client";

import { Badge, Button, Card } from "@/components/ui";
import { rupees } from "@/lib/format";
import type { OrderSummary } from "@/lib/types";

/**
 * High-trust component (chat spec §15). The AI has *proposed* a payment; nothing
 * moves until the customer clicks Confirm & Pay. The order total shown here is
 * the backend's authoritative figure, carried in the same turn's tool trace.
 */
export function PaymentApprovalCard({
  order,
  resolved,
  busy,
  onConfirm,
  onCancel,
}: {
  order: OrderSummary | null;
  resolved: "approved" | "declined" | null;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Card className="co-fade-up border-[var(--color-fg)]/15 p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">Review your purchase</p>
        <Badge tone="warning">Requires your confirmation</Badge>
      </div>

      {order ? (
        <dl className="mt-3 space-y-1.5 text-sm">
          <div className="flex justify-between">
            <dt className="text-[var(--color-fg-muted)]">Order</dt>
            <dd className="font-mono text-xs">{order.order_number}</dd>
          </div>
          {order.discount_paise > 0 && (
            <div className="flex justify-between">
              <dt className="text-[var(--color-fg-muted)]">Discount</dt>
              <dd className="text-[var(--color-success)]">-{rupees(order.discount_paise)}</dd>
            </div>
          )}
          <div className="flex justify-between border-t border-[var(--color-border)] pt-1.5 text-base font-semibold">
            <dt>Total</dt>
            <dd>{rupees(order.total_paise)}</dd>
          </div>
        </dl>
      ) : (
        <p className="mt-3 text-sm text-[var(--color-fg-muted)]">
          The backend has prepared an order and is waiting for your approval to charge the card.
        </p>
      )}

      <ul className="mt-3 space-y-1 text-xs text-[var(--color-fg-muted)]">
        <li>✓ Product availability verified</li>
        <li>✓ Price re-computed by the backend</li>
        <li>✓ Campaign eligibility verified</li>
        <li>✓ Payment policy checked</li>
      </ul>

      {resolved === null ? (
        <div className="mt-4 flex gap-2">
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={onConfirm} loading={busy}>
            Confirm &amp; Pay
          </Button>
        </div>
      ) : (
        <p className="mt-4 text-xs font-medium text-[var(--color-fg-muted)]">
          {resolved === "approved"
            ? "You confirmed this payment."
            : "You declined. No charge was made."}
        </p>
      )}
    </Card>
  );
}
