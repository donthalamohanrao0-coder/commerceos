"use client";

import { useState } from "react";

import { Badge, Button, Card, EmptyState } from "@/components/ui";
import { PageHeader, QueryBoundary } from "@/features/console/Shared";
import { useApprovals, useResolveApproval } from "@/features/console/hooks";
import { relativeTime, rupees } from "@/lib/format";
import type { ConsoleApproval } from "@/lib/types";

function ApprovalCard({ approval }: { approval: ConsoleApproval }) {
  const resolve = useResolveApproval();
  const [decision, setDecision] = useState<"approved" | "declined" | null>(null);

  const canAct = !!approval.session_id && !decision && !resolve.isPending;

  function act(approved: boolean) {
    if (!approval.session_id) return;
    resolve.mutate(
      { sessionId: approval.session_id, approvalId: approval.approval_id, approved },
      { onSuccess: () => setDecision(approved ? "approved" : "declined") },
    );
  }

  const isCampaign = approval.requested_action.includes("campaign");

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge tone="warning">Requires approval</Badge>
          {approval.workflow && <Badge tone="neutral">{approval.workflow}</Badge>}
        </div>
        <time className="font-mono text-xs text-[var(--color-fg-muted)]">
          {relativeTime(approval.created_at)}
        </time>
      </div>

      <p className="mt-3 text-sm font-medium">
        {isCampaign ? "Activate a drafted campaign" : "Initiate a payment"}
      </p>
      <p className="mt-0.5 text-xs text-[var(--color-fg-muted)]">
        Proposed by the {approval.requested_by} · action{" "}
        <span className="font-mono">{approval.requested_action}</span>
      </p>

      {approval.order && (
        <dl className="mt-3 space-y-1 rounded-[var(--radius-control)] bg-[var(--color-surface-muted)] p-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-[var(--color-fg-muted)]">Order</dt>
            <dd className="font-mono text-xs">{approval.order.order_number}</dd>
          </div>
          {approval.order.discount_paise > 0 && (
            <div className="flex justify-between">
              <dt className="text-[var(--color-fg-muted)]">Discount</dt>
              <dd className="text-[var(--color-success)]">
                -{rupees(approval.order.discount_paise)}
              </dd>
            </div>
          )}
          <div className="flex justify-between font-semibold">
            <dt>Total</dt>
            <dd>{rupees(approval.order.total_paise)}</dd>
          </div>
        </dl>
      )}

      {isCampaign && typeof approval.payload.campaign_id === "string" && (
        <p className="mt-3 font-mono text-xs text-[var(--color-fg-muted)]">
          campaign {approval.payload.campaign_id}
        </p>
      )}

      {!approval.session_id ? (
        <p className="mt-4 text-xs text-[var(--color-fg-muted)]">
          This approval has no linked session and can&apos;t be resolved from here.
        </p>
      ) : decision ? (
        <p className="mt-4 text-xs font-medium text-[var(--color-fg-muted)]">
          {decision === "approved" ? "Approved — the backend executed the action." : "Declined."}
        </p>
      ) : (
        <div className="mt-4 flex gap-2">
          <Button variant="secondary" disabled={!canAct} onClick={() => act(false)}>
            Decline
          </Button>
          <Button loading={resolve.isPending} disabled={!canAct} onClick={() => act(true)}>
            {isCampaign ? "Approve & activate" : "Approve payment"}
          </Button>
        </div>
      )}

      {resolve.isError && (
        <p className="mt-2 text-xs text-[var(--color-danger)]">
          Could not record the decision. Nothing was executed — try again.
        </p>
      )}
    </Card>
  );
}

export default function ApprovalsPage() {
  const approvals = useApprovals();

  return (
    <div>
      <PageHeader
        title="Approvals"
        description="Actions the agent has proposed but cannot execute alone. Approving here runs the same gated backend path the customer confirmation uses."
      />

      <QueryBoundary
        query={approvals}
        isEmpty={(d) => d.approvals.length === 0}
        emptyState={
          <EmptyState
            title="Nothing waiting"
            description="When an agent proposes a payment or a campaign activation, it appears here for a human decision."
          />
        }
        skeletonRows={2}
      >
        {(d) => (
          <div className="space-y-4">
            {d.approvals.map((a) => (
              <ApprovalCard key={a.approval_id} approval={a} />
            ))}
          </div>
        )}
      </QueryBoundary>
    </div>
  );
}
