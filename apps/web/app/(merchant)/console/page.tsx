"use client";

import dynamic from "next/dynamic";
import Link from "next/link";

import { Badge, Card, Skeleton } from "@/components/ui";
import { PageHeader, QueryBoundary, StatCard } from "@/features/console/Shared";
import { useApprovals, useAudit, useMetrics } from "@/features/console/hooks";
import { clockTime, relativeTime, rupees } from "@/lib/format";

const Analytics = dynamic(
  () => import("@/features/console/Analytics").then((m) => m.Analytics),
  {
    ssr: false,
    loading: () => (
      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold">Analytics</h2>
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-60 w-full" />
          ))}
        </div>
      </section>
    ),
  },
);

export default function OverviewPage() {
  const metrics = useMetrics();
  const approvals = useApprovals();
  const audit = useAudit();

  const pendingCount = approvals.data?.approvals.length ?? 0;

  return (
    <div>
      <PageHeader
        title="Overview"
        description="Authoritative revenue figures and the agent audit trail for this merchant."
      />

      {pendingCount > 0 && (
        <Link
          href="/console/approvals"
          className="mb-6 flex items-center justify-between rounded-[var(--radius-card)] border border-[var(--color-warning)] bg-[var(--color-warning-bg)] px-4 py-3 text-sm"
        >
          <span className="font-medium text-[var(--color-warning)]">
            {pendingCount} action{pendingCount === 1 ? "" : "s"} waiting for your approval
          </span>
          <span aria-hidden="true">→</span>
        </Link>
      )}

      <QueryBoundary query={metrics} skeletonRows={1}>
        {(m) => (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatCard label="Revenue" value={rupees(m.revenue_paise)} hint="paid + fulfilled" />
              <StatCard label="Orders" value={String(m.order_count)} hint={`${m.paid_order_count} paid`} />
              <StatCard label="Avg order value" value={rupees(m.aov_paise)} />
              <StatCard
                label="Cross-sell pairs"
                value={String(m.cross_sell_pairs.length)}
                hint="from order history"
              />
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              <Card className="p-4">
                <h2 className="text-sm font-semibold">Top products</h2>
                <ul className="mt-3 space-y-2">
                  {m.top_products.length === 0 && (
                    <li className="text-sm text-[var(--color-fg-muted)]">No sales yet.</li>
                  )}
                  {m.top_products.map((p) => (
                    <li key={p.product_id} className="flex items-center justify-between text-sm">
                      <span className="min-w-0 truncate pr-2">{p.name}</span>
                      <span className="shrink-0 text-[var(--color-fg-muted)]">
                        {p.units_sold} sold · {rupees(p.revenue_paise)}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>

              <Card className="p-4">
                <h2 className="text-sm font-semibold">Frequently bought together</h2>
                <ul className="mt-3 space-y-2">
                  {m.cross_sell_pairs.length === 0 && (
                    <li className="text-sm text-[var(--color-fg-muted)]">
                      Not enough multi-item orders yet.
                    </li>
                  )}
                  {m.cross_sell_pairs.map((c, i) => (
                    <li key={i} className="flex items-center justify-between text-sm">
                      <span className="min-w-0 truncate pr-2">
                        {c.a_name} + {c.b_name}
                      </span>
                      <span className="shrink-0 text-[var(--color-fg-muted)]">
                        {(c.attach_rate * 100).toFixed(0)}% attach
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            </div>
          </>
        )}
      </QueryBoundary>

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Audit trail</h2>
          <span className="text-xs text-[var(--color-fg-muted)]">append-only</span>
        </div>
        <QueryBoundary
          query={audit}
          isEmpty={(d) => d.events.length === 0}
          emptyState={
            <p className="text-sm text-[var(--color-fg-muted)]">No audit events recorded yet.</p>
          }
          skeletonRows={4}
        >
          {(d) => (
            <Card className="divide-y divide-[var(--color-border)]">
              {d.events.map((e) => (
                <div key={e.id} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
                  <div className="flex min-w-0 items-center gap-2">
                    <Badge
                      tone={
                        e.action.includes("FAIL") || e.action.includes("DENIED")
                          ? "danger"
                          : e.action.includes("APPROVAL")
                            ? "warning"
                            : "neutral"
                      }
                    >
                      {e.action}
                    </Badge>
                    <span className="truncate text-[var(--color-fg-muted)]">{e.actor_type}</span>
                  </div>
                  <time
                    dateTime={e.created_at}
                    title={e.created_at}
                    className="shrink-0 font-mono text-xs text-[var(--color-fg-muted)]"
                  >
                    {relativeTime(e.created_at)} · {clockTime(e.created_at)}
                  </time>
                </div>
              ))}
            </Card>
          )}
        </QueryBoundary>
      </section>

      <Analytics />
    </div>
  );
}
