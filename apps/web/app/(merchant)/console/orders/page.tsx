"use client";

import { Badge, EmptyState } from "@/components/ui";
import { DataTable, PageHeader, QueryBoundary, type Column } from "@/features/console/Shared";
import { useOrders } from "@/features/console/hooks";
import { relativeTime, rupees } from "@/lib/format";
import type { ConsoleOrder } from "@/lib/types";

const statusTone: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  paid: "success",
  fulfilled: "success",
  created: "neutral",
  cancelled: "danger",
  payment_failed: "danger",
};

const sourceLabel: Record<string, string> = {
  customer: "Customer",
  ai_assisted: "AI-assisted",
  external_ai_buyer: "AI buyer",
};

const columns: Column<ConsoleOrder>[] = [
  {
    key: "order",
    header: "Order",
    cell: (o) => (
      <div>
        <p className="font-mono text-xs font-medium">{o.order_number}</p>
        <p className="text-xs text-[var(--color-fg-muted)]">
          {o.item_count} item{o.item_count === 1 ? "" : "s"} · {relativeTime(o.created_at)}
        </p>
      </div>
    ),
  },
  {
    key: "source",
    header: "Source",
    cell: (o) => <Badge tone="neutral">{sourceLabel[o.source] ?? o.source}</Badge>,
  },
  {
    key: "status",
    header: "Status",
    cell: (o) => <Badge tone={statusTone[o.status] ?? "neutral"}>{o.status}</Badge>,
  },
  {
    key: "discount",
    header: "Discount",
    align: "right",
    cell: (o) =>
      o.discount_paise > 0 ? (
        <span className="text-[var(--color-success)]">-{rupees(o.discount_paise)}</span>
      ) : (
        "—"
      ),
  },
  {
    key: "total",
    header: "Total",
    align: "right",
    cell: (o) => <span className="font-medium">{rupees(o.total_paise)}</span>,
  },
];

export default function OrdersPage() {
  const orders = useOrders();
  return (
    <div>
      <PageHeader
        title="Orders"
        description="Every order, however it was placed — a customer, the in-app agent, or an external AI buyer."
      />
      <QueryBoundary
        query={orders}
        isEmpty={(d) => d.orders.length === 0}
        emptyState={<EmptyState title="No orders yet" description="Orders show up here as they are created." />}
        skeletonRows={6}
      >
        {(d) => <DataTable columns={columns} rows={d.orders} rowKey={(o) => o.id} />}
      </QueryBoundary>
    </div>
  );
}
