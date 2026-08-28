"use client";

import type { ReactNode } from "react";

import { Card, ErrorState, Skeleton } from "@/components/ui";

export function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <header className="mb-6">
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-1 text-sm text-[var(--color-fg-muted)]">{description}</p>
    </header>
  );
}

export interface Column<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  align?: "left" | "right";
  className?: string;
}

/** Compact, responsive data table. Wide content scrolls inside its own container. */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] text-sm">
          <thead>
            <tr className="border-b border-[var(--color-border)] text-xs text-[var(--color-fg-muted)]">
              {columns.map((c) => (
                <th
                  key={c.key}
                  className={`px-4 py-2.5 font-medium ${c.align === "right" ? "text-right" : "text-left"}`}
                >
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {rows.map((row) => (
              <tr key={rowKey(row)} className="hover:bg-[var(--color-surface-muted)]">
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={`px-4 py-2.5 ${c.align === "right" ? "text-right" : ""} ${c.className ?? ""}`}
                  >
                    {c.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card className="p-4 transition-shadow duration-150 hover:shadow-[var(--shadow-sm)]">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-fg-muted)]">
        {label}
      </p>
      <p className="mt-1.5 text-2xl font-semibold tracking-tight tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs text-[var(--color-fg-muted)]">{hint}</p>}
    </Card>
  );
}

/** Uniform loading / error / empty handling for a TanStack query. */
export function QueryBoundary<T>({
  query,
  isEmpty,
  emptyState,
  children,
  skeletonRows = 3,
}: {
  query: { isLoading: boolean; isError: boolean; error: unknown; data: T | undefined; refetch: () => void };
  isEmpty?: (data: T) => boolean;
  emptyState?: ReactNode;
  children: (data: T) => ReactNode;
  skeletonRows?: number;
}) {
  if (query.isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: skeletonRows }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    );
  }
  if (query.isError || query.data === undefined) {
    const message =
      query.error instanceof Error ? query.error.message : "Could not load this data.";
    return <ErrorState description={message} onRetry={query.refetch} />;
  }
  if (isEmpty?.(query.data) && emptyState) {
    return <>{emptyState}</>;
  }
  return <>{children(query.data)}</>;
}
