"use client";

import { Card } from "@/components/ui";
import { PageHeader, QueryBoundary } from "@/features/console/Shared";
import { useSettings } from "@/features/console/hooks";
import { rupees } from "@/lib/format";

const POLICY_LABELS: Record<string, string> = {
  max_transaction_amount_paise: "Max auto transaction amount",
  max_auto_discount_paise: "Max auto discount",
  max_auto_refund_paise: "Max auto refund",
};

function policyValue(key: string, value: unknown): string {
  const raw =
    typeof value === "object" && value !== null && "value" in value
      ? (value as { value: unknown }).value
      : value;
  if (key.endsWith("_paise") && typeof raw === "number") return rupees(raw);
  return String(raw);
}

export default function SettingsPage() {
  const settings = useSettings();
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Merchant profile and the policy limits the PolicyEngine enforces on every money action. Read-only in this build."
      />
      <QueryBoundary query={settings} skeletonRows={2}>
        {(d) => (
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-4">
              <h2 className="text-sm font-semibold">Business</h2>
              <dl className="mt-3 space-y-2 text-sm">
                {d.merchant &&
                  (
                    [
                      ["Name", d.merchant.business_name],
                      ["Legal name", d.merchant.legal_name ?? "—"],
                      ["Code", d.merchant.merchant_code],
                      ["Currency", d.merchant.currency],
                      ["Country", d.merchant.country],
                      ["Timezone", d.merchant.timezone],
                      ["GST", `${d.merchant.gst_percent}%`],
                      ["Prices tax-inclusive", d.merchant.prices_tax_inclusive ? "Yes" : "No"],
                      ["Status", d.merchant.status],
                    ] as [string, string][]
                  ).map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-4">
                      <dt className="text-[var(--color-fg-muted)]">{k}</dt>
                      <dd className="text-right">{v}</dd>
                    </div>
                  ))}
              </dl>
            </Card>

            <Card className="p-4">
              <h2 className="text-sm font-semibold">Policy limits</h2>
              <p className="mt-1 text-xs text-[var(--color-fg-muted)]">
                The agent never edits these — only PolicyEngine reads them.
              </p>
              <dl className="mt-3 space-y-2 text-sm">
                {d.policies.length === 0 && (
                  <p className="text-[var(--color-fg-muted)]">No policies configured.</p>
                )}
                {d.policies.map((p) => (
                  <div key={p.key} className="flex justify-between gap-4">
                    <dt className="text-[var(--color-fg-muted)]">
                      {POLICY_LABELS[p.key] ?? p.key}
                    </dt>
                    <dd className="text-right font-medium">{policyValue(p.key, p.value)}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          </div>
        )}
      </QueryBoundary>
    </div>
  );
}
