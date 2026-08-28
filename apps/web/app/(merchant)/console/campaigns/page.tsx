"use client";

import { Badge, EmptyState } from "@/components/ui";
import { DataTable, PageHeader, QueryBoundary, type Column } from "@/features/console/Shared";
import { useCampaigns, useSetCampaignStatus } from "@/features/console/hooks";
import { relativeTime, rupees } from "@/lib/format";
import type { ConsoleCampaign } from "@/lib/types";

const statusTone: Record<string, "success" | "warning" | "neutral"> = {
  active: "success",
  draft: "warning",
  paused: "neutral",
  archived: "neutral",
};

function discount(c: ConsoleCampaign): string {
  if (c.discount_type === "percentage" && c.discount_percent != null) {
    const cap = c.max_discount_paise ? ` (max ${rupees(c.max_discount_paise)})` : "";
    return `${c.discount_percent}% off${cap}`;
  }
  if (c.discount_fixed_paise != null) return `${rupees(c.discount_fixed_paise)} off`;
  return "—";
}

function StatusActions({ campaign }: { campaign: ConsoleCampaign }) {
  const set = useSetCampaignStatus();
  const act = (status: "active" | "paused" | "archived") =>
    set.mutate({ id: campaign.id, status });

  if (campaign.status === "archived") return null;
  return (
    <div className="flex gap-1">
      {campaign.status === "active" ? (
        <button
          type="button"
          disabled={set.isPending}
          onClick={() => act("paused")}
          className="rounded px-2 py-1 text-xs text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-fg)]"
        >
          Pause
        </button>
      ) : (
        <button
          type="button"
          disabled={set.isPending}
          onClick={() => act("active")}
          className="rounded px-2 py-1 text-xs text-[var(--color-success)] hover:underline"
        >
          {campaign.status === "draft" ? "Activate" : "Resume"}
        </button>
      )}
      <button
        type="button"
        disabled={set.isPending}
        onClick={() => act("archived")}
        className="rounded px-2 py-1 text-xs text-[var(--color-danger)] hover:underline"
      >
        Archive
      </button>
    </div>
  );
}

const columns: Column<ConsoleCampaign>[] = [
  {
    key: "name",
    header: "Campaign",
    cell: (c) => (
      <div>
        <p className="font-medium">{c.name}</p>
        <p className="font-mono text-xs text-[var(--color-fg-muted)]">{c.external_campaign_code}</p>
      </div>
    ),
  },
  { key: "discount", header: "Discount", cell: (c) => discount(c) },
  {
    key: "gate",
    header: "Gate",
    cell: (c) =>
      c.requires_merchant_approval ? (
        <Badge tone="warning">Merchant approval</Badge>
      ) : (
        <Badge tone="neutral">Auto</Badge>
      ),
  },
  {
    key: "status",
    header: "Status",
    cell: (c) => (
      <div className="flex items-center gap-2">
        <Badge tone={statusTone[c.status] ?? "neutral"}>{c.status}</Badge>
        <span className="text-xs text-[var(--color-fg-muted)]">{relativeTime(c.created_at)}</span>
      </div>
    ),
  },
  { key: "actions", header: "", align: "right", cell: (c) => <StatusActions campaign={c} /> },
];

export default function CampaignsPage() {
  const campaigns = useCampaigns();
  return (
    <div>
      <PageHeader
        title="Campaigns"
        description="Discount campaigns. The growth agent can draft one, but activation is always a human decision (see Approvals). Pause or archive a live campaign here."
      />
      <QueryBoundary
        query={campaigns}
        isEmpty={(d) => d.campaigns.length === 0}
        emptyState={
          <EmptyState
            title="No campaigns"
            description="Ask the growth agent to analyse sales and propose one."
          />
        }
        skeletonRows={4}
      >
        {(d) => <DataTable columns={columns} rows={d.campaigns} rowKey={(c) => c.id} />}
      </QueryBoundary>
    </div>
  );
}
