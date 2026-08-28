"use client";

import { Badge, EmptyState } from "@/components/ui";
import { DataTable, PageHeader, QueryBoundary, type Column } from "@/features/console/Shared";
import { usePayments } from "@/features/console/hooks";
import { relativeTime, rupees } from "@/lib/format";
import type { ConsolePayment } from "@/lib/types";

const statusTone: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  captured: "success",
  paid: "success",
  pending: "warning",
  created: "neutral",
  failed: "danger",
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
];

export default function PaymentsPage() {
  const payments = usePayments();
  return (
    <div>
      <PageHeader
        title="Payments"
        description="Razorpay test-mode payment intents. Every one was created by the backend after an explicit confirmation."
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
