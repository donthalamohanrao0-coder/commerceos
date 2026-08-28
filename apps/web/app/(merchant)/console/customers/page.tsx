"use client";

import { Badge, EmptyState } from "@/components/ui";
import { DataTable, PageHeader, QueryBoundary, type Column } from "@/features/console/Shared";
import { useCustomers } from "@/features/console/hooks";
import { rupees } from "@/lib/format";
import type { ConsoleCustomer } from "@/lib/types";

const columns: Column<ConsoleCustomer>[] = [
  {
    key: "name",
    header: "Customer",
    cell: (c) => (
      <div className="min-w-0">
        <p className="truncate font-medium">{c.name}</p>
        <p className="truncate text-xs text-[var(--color-fg-muted)]">{c.email ?? "—"}</p>
      </div>
    ),
  },
  { key: "city", header: "City", cell: (c) => c.city ?? "—" },
  {
    key: "segment",
    header: "Segment",
    cell: (c) => (c.segment ? <Badge tone="info">{c.segment}</Badge> : "—"),
  },
  { key: "orders", header: "Orders", align: "right", cell: (c) => c.orders_count },
  {
    key: "ltv",
    header: "Lifetime value",
    align: "right",
    cell: (c) => rupees(c.lifetime_value_paise),
  },
];

export default function CustomersPage() {
  const customers = useCustomers();
  return (
    <div>
      <PageHeader
        title="Customers"
        description="Everyone who has bought from this merchant. Segment feeds campaign eligibility."
      />
      <QueryBoundary
        query={customers}
        isEmpty={(d) => d.customers.length === 0}
        emptyState={<EmptyState title="No customers yet" description="Customers appear after their first order." />}
        skeletonRows={5}
      >
        {(d) => <DataTable columns={columns} rows={d.customers} rowKey={(c) => c.id} />}
      </QueryBoundary>
    </div>
  );
}
