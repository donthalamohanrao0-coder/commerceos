"use client";

import { useState } from "react";

import { Badge, Button, Card, EmptyState, Field } from "@/components/ui";
import { PageHeader, QueryBoundary } from "@/features/console/Shared";
import { useAgentKeys, useIssueKey, useRevokeKey } from "@/features/console/hooks";
import { relativeTime } from "@/lib/format";
import type { IssuedAgentKey } from "@/lib/types";

const ALL_SCOPES = [
  "catalog:read",
  "catalog:search",
  "quote:create",
  "order:create",
  "payment:request",
] as const;

const API_MAP: { method: string; path: string; scope: string }[] = [
  { method: "GET", path: "/agent-commerce/catalog", scope: "catalog:read" },
  { method: "POST", path: "/agent-commerce/catalog/search", scope: "catalog:search" },
  { method: "POST", path: "/agent-commerce/quote", scope: "quote:create" },
  { method: "POST", path: "/agent-commerce/orders", scope: "order:create" },
  { method: "POST", path: "/agent-commerce/orders/{id}/payment", scope: "payment:request" },
];

function IssueForm({ onIssued }: { onIssued: (key: IssuedAgentKey) => void }) {
  const issue = useIssueKey();
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<string[]>([...ALL_SCOPES]);
  const [rateLimit, setRateLimit] = useState(60);

  function toggle(scope: string) {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
    );
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || scopes.length === 0) return;
    issue.mutate(
      { name: name.trim(), scopes, rate_limit_per_minute: rateLimit },
      {
        onSuccess: (key) => {
          onIssued(key);
          setName("");
          setScopes([...ALL_SCOPES]);
          setRateLimit(60);
        },
      },
    );
  }

  return (
    <Card className="p-4">
      <h2 className="text-sm font-semibold">Issue a key</h2>
      <p className="mt-1 text-xs text-[var(--color-fg-muted)]">
        Scoped to this merchant. Sensitive actions (refunds, discount overrides) are not grantable
        scopes at all.
      </p>
      <form onSubmit={submit} className="mt-4 space-y-4">
        <Field
          label="Label"
          name="name"
          placeholder="e.g. Acme buying agent"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <div>
          <span className="text-sm font-medium">Scopes</span>
          <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
            {ALL_SCOPES.map((scope) => (
              <label key={scope} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={scopes.includes(scope)}
                  onChange={() => toggle(scope)}
                  className="size-4 rounded border-[var(--color-border)]"
                />
                <span className="font-mono text-xs">{scope}</span>
              </label>
            ))}
          </div>
        </div>
        <Field
          label="Rate limit (requests / minute)"
          name="rate"
          type="number"
          min={1}
          max={6000}
          value={rateLimit}
          onChange={(e) => setRateLimit(Number(e.target.value) || 1)}
        />
        {issue.isError && (
          <p className="text-xs text-[var(--color-danger)]">Could not issue the key. Try again.</p>
        )}
        <Button type="submit" loading={issue.isPending} disabled={!name.trim() || scopes.length === 0}>
          Generate key
        </Button>
      </form>
    </Card>
  );
}

export default function AiBuyersPage() {
  const keys = useAgentKeys();
  const revoke = useRevokeKey();
  const [issued, setIssued] = useState<IssuedAgentKey | null>(null);

  return (
    <div>
      <PageHeader
        title="AI buyers"
        description="API keys that let an external AI buyer transact with this merchant end to end — catalog → quote → order → payment, with a confirmation gate."
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <div className="space-y-6">
          <IssueForm onIssued={setIssued} />

          {issued && (
            <Card className="border-[var(--color-success)] bg-[var(--color-success-bg)] p-4">
              <p className="text-sm font-semibold text-[var(--color-success)]">
                Key created — copy it now
              </p>
              <p className="mt-1 text-xs text-[var(--color-fg-muted)]">
                This is the only time the full key is shown.
              </p>
              <code className="mt-2 block break-all rounded-[var(--radius-control)] bg-[var(--color-surface)] p-2 font-mono text-xs">
                {issued.api_key}
              </code>
              <button
                type="button"
                onClick={() => navigator.clipboard?.writeText(issued.api_key)}
                className="mt-2 text-xs text-[var(--color-info)] hover:underline"
              >
                Copy to clipboard
              </button>
            </Card>
          )}

          <Card className="p-4">
            <h2 className="text-sm font-semibold">Agent Commerce API</h2>
            <ul className="mt-3 space-y-1.5">
              {API_MAP.map((row) => (
                <li key={row.path} className="flex items-center gap-2 text-xs">
                  <span className="w-12 shrink-0 font-mono text-[var(--color-fg-muted)]">
                    {row.method}
                  </span>
                  <span className="min-w-0 flex-1 truncate font-mono">{row.path}</span>
                  <Badge tone="neutral">{row.scope}</Badge>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-[var(--color-fg-muted)]">
              An unconfirmed payment call returns <span className="font-mono">approval_required</span>;
              the buyer must repeat it with <span className="font-mono">?confirmed=true</span> as the
              consent signal. Order and payment calls are idempotent.
            </p>
          </Card>
        </div>

        <div>
          <h2 className="mb-3 text-sm font-semibold">Active keys</h2>
          <QueryBoundary
            query={keys}
            isEmpty={(d) => d.keys.length === 0}
            emptyState={
              <EmptyState
                title="No keys yet"
                description="Issue a key to let an external AI buyer start transacting."
              />
            }
            skeletonRows={3}
          >
            {(d) => (
              <div className="space-y-3">
                {d.keys.map((k) => (
                  <Card key={k.key_id} className="p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{k.name}</p>
                      <Badge tone={k.status === "active" ? "success" : "neutral"}>{k.status}</Badge>
                    </div>
                    <code className="mt-1 block font-mono text-xs text-[var(--color-fg-muted)]">
                      {k.key_prefix}…
                    </code>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {k.scopes.map((s) => (
                        <Badge key={s} tone="neutral">
                          {s}
                        </Badge>
                      ))}
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-[var(--color-fg-muted)]">
                      <span>
                        {k.rate_limit_per_minute}/min ·{" "}
                        {k.last_used_at ? `used ${relativeTime(k.last_used_at)}` : "never used"}
                      </span>
                      {k.status === "active" && (
                        <button
                          type="button"
                          onClick={() => revoke.mutate(k.key_id)}
                          disabled={revoke.isPending}
                          className="text-[var(--color-danger)] hover:underline disabled:opacity-50"
                        >
                          Revoke
                        </button>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </QueryBoundary>
        </div>
      </div>
    </div>
  );
}
