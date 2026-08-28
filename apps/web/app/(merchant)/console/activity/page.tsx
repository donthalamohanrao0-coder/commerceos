"use client";

import { useMemo, useState } from "react";

import { Badge, Card, EmptyState } from "@/components/ui";
import { SessionTrace } from "@/features/console/SessionTrace";
import { Chip, PageHeader, QueryBoundary } from "@/features/console/Shared";
import { useActivity } from "@/features/console/hooks";
import { clockTime, relativeTime } from "@/lib/format";
import type { ActivitySession } from "@/lib/types";

const workflowTone: Record<string, "info" | "success" | "warning" | "neutral"> = {
  shopping: "info",
  growth: "success",
  support: "neutral",
  external_ai_buyer: "warning",
};

const BUCKETS = ["Today", "Yesterday", "Earlier this week", "This month", "Older"] as const;

function bucketFor(iso: string): (typeof BUCKETS)[number] {
  const d = new Date(iso);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const dayMs = 86_400_000;
  const diffDays = Math.floor((startOfToday - new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()) / dayMs);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays <= 6) return "Earlier this week";
  if (diffDays <= 31) return "This month";
  return "Older";
}

function groupByTime(sessions: ActivitySession[]) {
  const groups = new Map<string, ActivitySession[]>();
  for (const s of [...sessions].sort((a, b) => b.started_at.localeCompare(a.started_at))) {
    const b = bucketFor(s.started_at);
    (groups.get(b) ?? groups.set(b, []).get(b)!).push(s);
  }
  return BUCKETS.filter((b) => groups.has(b)).map((b) => ({ label: b, items: groups.get(b)! }));
}

export default function ActivityPage() {
  const activity = useActivity();
  const [selected, setSelected] = useState<string | null>(null);
  const [workflow, setWorkflow] = useState<string>("all");

  const grouped = useMemo(() => {
    const all = activity.data?.sessions ?? [];
    const filtered = workflow === "all" ? all : all.filter((s) => s.workflow === workflow);
    return groupByTime(filtered);
  }, [activity.data, workflow]);

  const workflows = useMemo(
    () => Array.from(new Set((activity.data?.sessions ?? []).map((s) => s.workflow))).sort(),
    [activity.data],
  );

  return (
    <div>
      <PageHeader
        title="Agent activity"
        description="Every agent session for this merchant, newest first, grouped by when it ran. Open one for the full node/tool trace, inputs, outputs and policy decisions."
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="text-xs text-[var(--color-fg-muted)]">Workflow:</span>
        {["all", ...workflows].map((w) => (
          <Chip key={w} active={workflow === w} onClick={() => setWorkflow(w)}>
            {w}
          </Chip>
        ))}
      </div>

      <QueryBoundary
        query={activity}
        isEmpty={(d) => d.sessions.length === 0}
        emptyState={
          <EmptyState
            title="No agent sessions yet"
            description="Start a conversation in the customer chat, or run the growth agent, and it will show up here."
          />
        }
        skeletonRows={5}
      >
        {() =>
          grouped.length === 0 ? (
            <p className="text-sm text-[var(--color-fg-muted)]">No sessions for this filter.</p>
          ) : (
            <div className="space-y-6">
              {grouped.map((group) => (
                <div key={group.label}>
                  <div className="mb-2 flex items-baseline justify-between">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-fg-muted)]">
                      {group.label}
                    </h3>
                    <span className="text-xs text-[var(--color-fg-muted)]">
                      {group.items.length} session{group.items.length === 1 ? "" : "s"}
                    </span>
                  </div>
                  <Card className="divide-y divide-[var(--color-border)]">
                    {group.items.map((s) => (
                      <button
                        key={s.session_id}
                        type="button"
                        onClick={() => setSelected(s.session_id)}
                        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm hover:bg-[var(--color-surface-muted)]"
                      >
                        <div className="flex min-w-0 items-center gap-2">
                          <Badge tone={workflowTone[s.workflow] ?? "neutral"}>{s.workflow}</Badge>
                          <span className="truncate text-[var(--color-fg-muted)]">
                            {s.action_count} tool call{s.action_count === 1 ? "" : "s"} ·{" "}
                            {s.message_count} msg
                          </span>
                          <span className="hidden font-mono text-xs text-[var(--color-fg-muted)]/70 sm:inline">
                            {s.session_id.slice(0, 8)}
                          </span>
                        </div>
                        <div className="flex shrink-0 items-center gap-3">
                          <Badge tone={s.status === "waiting_for_approval" ? "warning" : "neutral"}>
                            {s.status}
                          </Badge>
                          <time
                            dateTime={s.started_at}
                            title={new Date(s.started_at).toLocaleString()}
                            className="font-mono text-xs text-[var(--color-fg-muted)]"
                          >
                            {group.label === "Today" || group.label === "Yesterday"
                              ? clockTime(s.started_at)
                              : relativeTime(s.started_at)}
                          </time>
                        </div>
                      </button>
                    ))}
                  </Card>
                </div>
              ))}
            </div>
          )
        }
      </QueryBoundary>

      {selected && <SessionTrace sessionId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
