"use client";

import { useRef, useState } from "react";

import { Badge, Button, Card, EmptyState, Field } from "@/components/ui";
import {
  DataTable,
  PageHeader,
  QueryBoundary,
  StatCard,
  type Column,
} from "@/features/console/Shared";
import {
  useKnowledge,
  useKnowledgePreview,
  useUploadKnowledge,
} from "@/features/console/hooks";
import { relativeTime } from "@/lib/format";
import type { KnowledgeChunk, KnowledgeDocument } from "@/lib/types";

const TYPE_LABEL: Record<string, string> = {
  merchant_policy: "Policy",
  faq_or_guide: "FAQ / guide",
};

function typeBadge(t: string) {
  return (
    <Badge tone={t === "merchant_policy" ? "info" : "neutral"}>{TYPE_LABEL[t] ?? t}</Badge>
  );
}

const columns: Column<KnowledgeDocument>[] = [
  {
    key: "title",
    header: "Document",
    cell: (d) => (
      <div className="min-w-0">
        <p className="truncate font-medium">{d.title}</p>
        <p className="truncate font-mono text-xs text-[var(--color-fg-muted)]">{d.source_path}</p>
      </div>
    ),
  },
  { key: "type", header: "Type", cell: (d) => typeBadge(d.document_type) },
  {
    key: "status",
    header: "Status",
    cell: (d) => (
      <Badge tone={d.status === "indexed" ? "success" : "warning"}>{d.status}</Badge>
    ),
  },
  { key: "chunks", header: "Chunks", align: "right", cell: (d) => d.chunk_count },
  {
    key: "version",
    header: "Version",
    align: "right",
    cell: (d) => (d.version_number ? `v${d.version_number}` : "—"),
  },
  {
    key: "indexed",
    header: "Indexed",
    align: "right",
    cell: (d) => (
      <span className="text-[var(--color-fg-muted)]">
        {d.indexed_at ? relativeTime(d.indexed_at) : "—"}
      </span>
    ),
  },
];

const FILTERS = [
  { label: "All documents", value: null },
  { label: "Policies", value: "merchant_policy" },
  { label: "FAQ & guides", value: "faq_or_guide" },
] as const;

function ChunkResult({ chunk, rank, topScore }: { chunk: KnowledgeChunk; rank: number; topScore: number }) {
  const pct = topScore > 0 ? Math.max(6, Math.round((chunk.score / topScore) * 100)) : 0;
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-xs font-semibold text-[var(--color-fg-muted)]">
            {rank}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{chunk.heading || "Untitled section"}</p>
            <p className="truncate font-mono text-xs text-[var(--color-fg-muted)]">
              {chunk.document_id}
            </p>
          </div>
        </div>
        {typeBadge(chunk.document_type)}
      </div>

      <div className="mt-3 flex items-center gap-2">
        <div className="h-1.5 w-28 overflow-hidden rounded-full bg-[var(--color-surface-muted)]">
          <div className="h-full rounded-full bg-[var(--color-primary)]" style={{ width: `${pct}%` }} />
        </div>
        <span className="font-mono text-xs text-[var(--color-fg-muted)]">
          {chunk.score.toFixed(3)}
        </span>
      </div>

      <p className="mt-3 whitespace-pre-wrap border-l-2 border-[var(--color-border)] pl-3 text-sm text-[var(--color-fg-muted)]">
        {chunk.text}
      </p>
    </Card>
  );
}

function UploadCard() {
  const upload = useUploadKnowledge();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState("merchant_policy");
  const inputRef = useRef<HTMLInputElement | null>(null);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || title.trim().length < 2) return;
    upload.mutate(
      { file, title: title.trim(), documentType },
      {
        onSuccess: () => {
          setFile(null);
          setTitle("");
          if (inputRef.current) inputRef.current.value = "";
        },
      },
    );
  }

  return (
    <Card className="p-4">
      <h3 className="text-sm font-semibold">Add a document</h3>
      <p className="mt-1 text-sm text-[var(--color-fg-muted)]">
        A markdown or text file (≤300&nbsp;KB). It&apos;s chunked, embedded and indexed into
        this merchant&apos;s vector namespace — the agent can cite it immediately.
      </p>
      <form onSubmit={submit} className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-sm sm:col-span-2">
          <span className="font-medium">File</span>
          <input
            ref={inputRef}
            type="file"
            accept=".md,.markdown,.txt,text/markdown,text/plain"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm file:mr-3 file:rounded-[var(--radius-input)] file:border-0 file:bg-[var(--color-surface-muted)] file:px-3 file:py-1.5 file:text-sm file:font-medium"
          />
        </label>
        <Field
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Bulk & business orders"
        />
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium">Type</span>
          <select
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value)}
            className="rounded-[var(--radius-input)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
          >
            <option value="merchant_policy">Policy</option>
            <option value="faq_or_guide">FAQ / guide</option>
          </select>
        </label>
        <div className="flex items-center gap-3 sm:col-span-2">
          <Button
            type="submit"
            loading={upload.isPending}
            disabled={!file || title.trim().length < 2}
          >
            Upload &amp; index
          </Button>
          {upload.isSuccess && (
            <span className="text-sm text-[var(--color-success)]">
              Indexed — {upload.data.chunk_count} chunk
              {upload.data.chunk_count === 1 ? "" : "s"} (v{upload.data.version_number}).
            </span>
          )}
          {upload.isError && (
            <span className="text-sm text-[var(--color-danger)]">
              {upload.error instanceof Error ? upload.error.message : "Upload failed."}
            </span>
          )}
        </div>
      </form>
    </Card>
  );
}

export default function KnowledgePage() {
  const knowledge = useKnowledge();
  const preview = useKnowledgePreview();
  const [query, setQuery] = useState("");
  const [docType, setDocType] = useState<string | null>(null);

  const results = preview.data?.results ?? [];
  const topScore = results[0]?.score ?? 0;

  function run() {
    if (query.trim().length < 2) return;
    preview.mutate({ query: query.trim(), document_type: docType });
  }

  return (
    <div>
      <PageHeader
        title="Knowledge base"
        description="The grounding corpus the shopping agent retrieves from. Test what a customer question surfaces before it ships."
      />

      <QueryBoundary query={knowledge} skeletonRows={4}>
        {(d) => (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatCard label="Documents" value={String(d.summary.document_count)} />
              <StatCard
                label="Indexed"
                value={`${d.summary.indexed_count}/${d.summary.document_count}`}
                hint="ready for retrieval"
              />
              <StatCard label="Chunks" value={String(d.summary.chunk_count)} hint="vectors in the index" />
              <StatCard
                label="Agent retrievals"
                value={String(d.summary.retrieval_calls)}
                hint="knowledge_search calls"
              />
            </div>

            <section className="mt-8">
              <h2 className="text-sm font-semibold">Retrieval preview</h2>
              <p className="mt-1 text-sm text-[var(--color-fg-muted)]">
                Runs the exact semantic search the agent runs. Retrieved text is treated as
                reference data, never as instructions.
              </p>

              <Card className="mt-3 p-4">
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run();
                  }}
                  rows={2}
                  placeholder="e.g. How long does delivery take to Bangalore?"
                  className="w-full resize-y rounded-[var(--radius-input)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm placeholder:text-[var(--color-fg-muted)] focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-[var(--color-info)]"
                />
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {FILTERS.map((f) => (
                    <button
                      key={f.label}
                      type="button"
                      onClick={() => setDocType(f.value)}
                      className={
                        "rounded-full border px-3 py-1 text-xs transition-colors " +
                        (docType === f.value
                          ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-primary-fg)]"
                          : "border-[var(--color-border)] text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-muted)]")
                      }
                    >
                      {f.label}
                    </button>
                  ))}
                  <Button
                    className="ml-auto"
                    onClick={run}
                    loading={preview.isPending}
                    disabled={query.trim().length < 2}
                  >
                    Run retrieval
                  </Button>
                </div>
              </Card>

              {preview.isError && (
                <div
                  role="alert"
                  className="mt-3 rounded-[var(--radius-card)] border border-[var(--color-danger)] bg-[var(--color-danger-bg)] px-4 py-3 text-sm text-[var(--color-danger)]"
                >
                  {preview.error instanceof Error
                    ? preview.error.message
                    : "Retrieval failed. Try again."}
                </div>
              )}

              {preview.isSuccess && results.length === 0 && (
                <p className="mt-3 text-sm text-[var(--color-fg-muted)]">
                  No matching passages — the agent would tell the customer it doesn&apos;t have
                  that information.
                </p>
              )}

              {results.length > 0 && (
                <div className="mt-3 space-y-3">
                  {results.map((c, i) => (
                    <ChunkResult key={i} chunk={c} rank={i + 1} topScore={topScore} />
                  ))}
                </div>
              )}
            </section>

            <section className="mt-8">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold">Documents</h2>
              </div>
              <div className="space-y-4">
                <UploadCard />
                {d.documents.length === 0 ? (
                  <EmptyState
                    title="No documents indexed"
                    description="Upload a file above, or run the ingestion script to seed the corpus."
                  />
                ) : (
                  <DataTable columns={columns} rows={d.documents} rowKey={(x) => x.id} />
                )}
              </div>
            </section>
          </>
        )}
      </QueryBoundary>
    </div>
  );
}
