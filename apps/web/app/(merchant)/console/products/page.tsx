"use client";

import { useMemo, useState } from "react";

import { Badge, Button, EmptyState } from "@/components/ui";
import { ProductTile } from "@/features/chat/blocks/ProductTile";
import { ProductFormModal } from "@/features/console/ProductFormModal";
import { DataTable, PageHeader, QueryBoundary, type Column } from "@/features/console/Shared";
import { useArchiveProduct, useProducts, useUpdateProduct } from "@/features/console/hooks";
import { rupees } from "@/lib/format";
import type { ConsoleProduct } from "@/lib/types";

export default function ProductsPage() {
  const products = useProducts();
  const archive = useArchiveProduct();
  const update = useUpdateProduct();
  const [showArchived, setShowArchived] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<ConsoleProduct | null>(null);

  const rows = useMemo(
    () => (products.data?.products ?? []).filter((p) => showArchived || p.status !== "archived"),
    [products.data, showArchived],
  );

  const columns: Column<ConsoleProduct>[] = [
    {
      key: "name",
      header: "Product",
      cell: (p) => (
        <div className="flex items-center gap-3">
          <ProductTile
            name={p.name}
            category={p.category}
            imageKey={p.image_key}
            className={`size-9 shrink-0 rounded-[var(--radius-control)] ${
              p.status === "archived" ? "opacity-40" : ""
            }`}
          />
          <div className="min-w-0">
            <p className="truncate font-medium">{p.name}</p>
            <p className="truncate text-xs text-[var(--color-fg-muted)]">
              {p.brand ?? "—"} · <span className="font-mono">{p.sku}</span>
            </p>
          </div>
        </div>
      ),
    },
    { key: "category", header: "Category", cell: (p) => p.category },
    {
      key: "price",
      header: "Price",
      align: "right",
      cell: (p) => (
        <span className="whitespace-nowrap">
          {rupees(p.price_paise)}
          {p.compare_at_price_paise ? (
            <span className="ml-1 text-xs text-[var(--color-fg-muted)] line-through">
              {rupees(p.compare_at_price_paise)}
            </span>
          ) : null}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      cell: (p) => (
        <Badge tone={p.status === "active" ? "success" : "neutral"}>{p.status}</Badge>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      cell: (p) => (
        <div className="flex justify-end gap-1">
          <button
            type="button"
            onClick={() => {
              setEditing(p);
              setModalOpen(true);
            }}
            className="rounded px-2 py-1 text-xs text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-muted)] hover:text-[var(--color-fg)]"
          >
            Edit
          </button>
          {p.status === "archived" ? (
            <button
              type="button"
              onClick={() => update.mutate({ id: p.id, patch: { status: "active" } })}
              className="rounded px-2 py-1 text-xs text-[var(--color-info)] hover:underline"
            >
              Restore
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                if (confirm(`Archive "${p.name}"? It stays in order history but leaves the storefront.`))
                  archive.mutate(p.id);
              }}
              className="rounded px-2 py-1 text-xs text-[var(--color-danger)] hover:underline"
            >
              Archive
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Products"
        description="The merchant catalogue the agents read from. Prices here are the authoritative source for every quote and order."
      />

      <div className="mb-4 flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm text-[var(--color-fg-muted)]">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="size-4"
          />
          Show archived
        </label>
        <Button
          onClick={() => {
            setEditing(null);
            setModalOpen(true);
          }}
        >
          Add product
        </Button>
      </div>

      <QueryBoundary
        query={products}
        isEmpty={() => rows.length === 0}
        emptyState={
          <EmptyState
            title="No products"
            description="Add your first product, or seed the demo catalogue."
            action={
              <Button
                onClick={() => {
                  setEditing(null);
                  setModalOpen(true);
                }}
              >
                Add product
              </Button>
            }
          />
        }
        skeletonRows={6}
      >
        {() => <DataTable columns={columns} rows={rows} rowKey={(p) => p.id} />}
      </QueryBoundary>

      <ProductFormModal
        open={modalOpen}
        product={editing}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}
