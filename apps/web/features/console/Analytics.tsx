"use client";

import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui";
import { Chip, PageHeader, QueryBoundary, StatCard } from "@/features/console/Shared";
import { useAnalytics } from "@/features/console/hooks";
import { rupees } from "@/lib/format";
import type { ConsoleAnalytics } from "@/lib/types";

const INK = "#1c1c1a";
const MUTED = "#9a978f";
const GRID = "#e7e6e2";
const SERIES = ["#1d4ed8", "#1a7f4b", "#9a6700", "#b3261e", "#0891b2", "#7c3aed", "#c2410c", "#6b6b66"];
const SOURCE_COLOR: Record<string, string> = {
  ai_assisted: "#1d4ed8",
  customer: "#1a7f4b",
  external_ai_buyer: "#9a6700",
};
const STATUS_COLOR: Record<string, string> = {
  paid: "#1a7f4b",
  fulfilled: "#0891b2",
  created: "#9a978f",
  payment_pending: "#9a6700",
  failed: "#b3261e",
  cancelled: "#b3261e",
};
const SOURCE_LABEL: Record<string, string> = {
  ai_assisted: "In-app agent",
  customer: "Customer",
  external_ai_buyer: "AI buyer",
};

function ChartCard({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-4">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        {hint && <span className="text-xs text-[var(--color-fg-muted)]">{hint}</span>}
      </div>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          {children as React.ReactElement}
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

const tooltipStyle = {
  fontSize: 12,
  borderRadius: 10,
  border: `1px solid ${GRID}`,
  background: "#fff",
};

function shortDate(d: string) {
  return new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function Charts({ data }: { data: ConsoleAnalytics }) {
  const revenueSeries = data.timeseries.map((p) => ({
    date: p.date,
    revenue: Math.round(p.revenue_paise / 100),
    orders: p.orders,
  }));
  const categories = data.category_revenue
    .map((c) => ({ name: c.category, value: Math.round(c.revenue_paise / 100) }))
    .filter((c) => c.value > 0);
  const sources = data.sources
    .map((s) => ({ name: SOURCE_LABEL[s.source] ?? s.source, key: s.source, value: s.orders }))
    .filter((s) => s.value > 0);
  const statuses = data.statuses.filter((s) => s.count > 0);
  const products = data.top_products
    .map((p) => ({ name: p.name.replace(/^Nova/, ""), units: p.units }))
    .slice(0, 6)
    .reverse();

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard title="Revenue" hint={`last ${data.window_days} days · paid`}>
        <AreaChart data={revenueSeries} margin={{ top: 4, right: 8, bottom: 0, left: -12 }}>
          <defs>
            <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={INK} stopOpacity={0.18} />
              <stop offset="100%" stopColor={INK} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tickFormatter={shortDate}
            tick={{ fontSize: 11, fill: MUTED }}
            interval="preserveStartEnd"
            minTickGap={40}
            stroke={GRID}
          />
          <YAxis
            tick={{ fontSize: 11, fill: MUTED }}
            tickFormatter={(v) => (v >= 1000 ? `${Math.round(v / 1000)}k` : `${v}`)}
            stroke={GRID}
            width={44}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(v: number) => [rupees(v * 100), "Revenue"]}
            labelFormatter={shortDate}
          />
          <Area type="monotone" dataKey="revenue" stroke={INK} strokeWidth={2} fill="url(#rev)" />
        </AreaChart>
      </ChartCard>

      <ChartCard title="Orders per day" hint={`last ${data.window_days} days`}>
        <BarChart data={revenueSeries} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
          <XAxis
            dataKey="date"
            tickFormatter={shortDate}
            tick={{ fontSize: 11, fill: MUTED }}
            interval="preserveStartEnd"
            minTickGap={40}
            stroke={GRID}
          />
          <YAxis tick={{ fontSize: 11, fill: MUTED }} stroke={GRID} width={36} allowDecimals={false} />
          <Tooltip contentStyle={tooltipStyle} labelFormatter={shortDate} />
          <Bar dataKey="orders" fill={MUTED} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ChartCard>

      <ChartCard title="Revenue by category">
        <BarChart
          data={categories}
          layout="vertical"
          margin={{ top: 0, right: 12, bottom: 0, left: 8 }}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: MUTED }}
            width={90}
            stroke={GRID}
          />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => rupees(v * 100)} />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {categories.map((_, i) => (
              <Cell key={i} fill={SERIES[i % SERIES.length]} />
            ))}
          </Bar>
        </BarChart>
      </ChartCard>

      <ChartCard title="Where orders come from" hint="in the window">
        <PieChart>
          <Pie
            data={sources}
            dataKey="value"
            nameKey="name"
            innerRadius={44}
            outerRadius={70}
            paddingAngle={2}
          >
            {sources.map((s, i) => (
              <Cell key={i} fill={SOURCE_COLOR[s.key] ?? SERIES[i % SERIES.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} formatter={(v: number, n) => [`${v} orders`, n]} />
        </PieChart>
      </ChartCard>

      <ChartCard title="Order status mix">
        <BarChart data={statuses} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
          <XAxis dataKey="status" tick={{ fontSize: 10, fill: MUTED }} stroke={GRID} />
          <YAxis tick={{ fontSize: 11, fill: MUTED }} stroke={GRID} width={30} allowDecimals={false} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" radius={[3, 3, 0, 0]}>
            {statuses.map((s, i) => (
              <Cell key={i} fill={STATUS_COLOR[s.status] ?? MUTED} />
            ))}
          </Bar>
        </BarChart>
      </ChartCard>

      <ChartCard title="Top products" hint="units sold">
        <BarChart data={products} layout="vertical" margin={{ top: 0, right: 12, bottom: 0, left: 8 }}>
          <XAxis type="number" hide allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: MUTED }}
            width={96}
            stroke={GRID}
          />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [`${v} units`, ""]} />
          <Bar dataKey="units" fill={INK} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ChartCard>
    </div>
  );
}

const RANGES = [30, 45, 90] as const;

/** Full-page analytics: KPI row + range selector + the chart grid. */
export function AnalyticsPage() {
  const [days, setDays] = useState<number>(45);
  const analytics = useAnalytics(days);

  return (
    <div>
      <div className="mb-6 flex items-start justify-between gap-4">
        <PageHeader
          title="Analytics"
          description="Revenue, orders and channel mix over a rolling window. Figures are computed from orders, not anything the agent reported."
        />
        <div className="flex shrink-0 gap-1 pt-1">
          {RANGES.map((r) => (
            <Chip key={r} active={days === r} onClick={() => setDays(r)}>
              {r}d
            </Chip>
          ))}
        </div>
      </div>

      <QueryBoundary query={analytics} skeletonRows={5}>
        {(d) => (
          <>
            <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatCard
                label={`Revenue · ${d.window_days}d`}
                value={rupees(d.summary.revenue_paise)}
                hint="paid + fulfilled"
              />
              <StatCard label="Orders" value={String(d.summary.order_count)} />
              <StatCard label="Paid orders" value={String(d.summary.paid_order_count)} />
              <StatCard label="Avg order value" value={rupees(d.summary.aov_paise)} />
            </div>
            <Charts data={d} />
          </>
        )}
      </QueryBoundary>
    </div>
  );
}
