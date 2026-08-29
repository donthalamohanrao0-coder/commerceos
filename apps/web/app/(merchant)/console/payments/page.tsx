"use client";

import { useState } from "react";

import { Badge, Button, EmptyState } from "@/components/ui";
import { DataTable, PageHeader, QueryBoundary, type Column } from "@/features/console/Shared";
import { usePayments, useReconcilePayment } from "@/features/console/hooks";
import { relativeTime, rupees } from "@/lib/format";
import type { ConsolePayment } from "@/lib/types";

const statusTone: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  captured: "success",
  paid: "success",
  pending: "warning",
  created: "neutral",
  failed: "danger",
};

const SETTLED = new Set(["paid", "captured", "failed", "refunded"]);

export default function PaymentsPage() {
  const payments = usePayments();
  const reconcile = useReconcilePayment();
  const [note, setNote] = useState<Record<string, string>>({});

  const runReconcile = (id: string) => {
    reconcile.mutate(id, {
      onSuccess: (r) =>
        setNote((n) => ({
          ...n,
          [id]:
            r.action === "settled"
              ? "settled ✓"
              : r.action === "already_paid"
                ? "already paid"
                : `no change (${r.provider_status ?? "provider not paid"})`,
        })),
      onError: () => setNote((n) => ({ ...n, [id]: "reconcile failed" })),
    });
  };

  const columns: Column<ConsolePayment>[] = [
    {
      key: "id",
      header: "Payment",
      cell: (p) => (
        <div>
          <p className="font-mono text-xs">{p.provider_order_id ?? p.id.slice(0, 8)}</p>
          <p className="text-xs text-[var(--color-fg-muted)]">
            {p.order_number ? `${p.order_number} · ` : ""}
            {relativeTime(p.created_at)}
          </p>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      cell: (p) => (
        <div className="flex items-center gap-1.5">
          <Badge tone={statusTone[p.status] ?? "neutral"}>{p.status}</Badge>
          {p.signature_verified && <Badge tone="success">✓ signed</Badge>}
        </div>
      ),
    },
    {
      key: "reason",
      header: "Detail",
      cell: (p) => (
        <span className="text-xs text-[var(--color-fg-muted)]">
          {p.failure_reason ?? `${p.provider} · test mode`}
        </span>
      ),
    },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      cell: (p) => (
        <span className="font-medium">
          {rupees(p.amount_paise)} {p.currency !== "INR" ? p.currency : ""}
        </span>
      ),
    },
    {
      key: "reconcile",
      header: "",
      align: "right",
      cell: (p) =>
        SETTLED.has(p.status) ? null : (
          <div className="flex items-center justify-end gap-2">
            {note[p.id] && (
              <span className="text-xs text-[var(--color-fg-muted)]">{note[p.id]}</span>
            )}
            {p.payment_link_url && (
              <a
                href={p.payment_link_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-[var(--color-info)] underline"
              >
                pay link
              </a>
            )}
            <Button
              variant="secondary"
              className="!px-3 !py-1 text-xs"
              loading={reconcile.isPending && reconcile.variables === p.id}
              onClick={() => runReconcile(p.id)}
            >
              Reconcile
            </Button>
          </div>
        ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Payments"
        description="Razorpay test-mode payments. Every one was created by the backend after an explicit confirmation. Reconcile asks Razorpay directly and settles an order whose webhook was missed."
      />
      <QueryBoundary
        query={payments}
        isEmpty={(d) => d.payments.length === 0}
        emptyState={
          <EmptyState
            title="No payments yet"
            description="A payment is created only after a customer or AI buyer confirms a charge."
          />
        }
        skeletonRows={5}
      >
        {(d) => <DataTable columns={columns} rows={d.payments} rowKey={(p) => p.id} />}
      </QueryBoundary>
    </div>
  );
}
