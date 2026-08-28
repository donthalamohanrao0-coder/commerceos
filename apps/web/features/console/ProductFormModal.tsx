"use client";

import { useState } from "react";

import { Button, Field } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { ApiError } from "@/lib/api";
import type { ConsoleProduct } from "@/lib/types";

import { useCreateProduct, useUpdateProduct, type ProductInput } from "./hooks";

const CATEGORIES = [
  "Laptops",
  "Smartphones",
  "Audio",
  "Keyboards",
  "Mice",
  "Wearables",
  "Accessories",
  "Storage",
  "Displays",
  "Bags",
  "Power",
];

export function ProductFormModal({
  open,
  onClose,
  product,
}: {
  open: boolean;
  onClose: () => void;
  product?: ConsoleProduct | null;
}) {
  const editing = !!product;
  const create = useCreateProduct();
  const update = useUpdateProduct();
  const pending = create.isPending || update.isPending;

  const [name, setName] = useState(product?.name ?? "");
  const [category, setCategory] = useState(product?.category ?? "Accessories");
  const [brand, setBrand] = useState(product?.brand ?? "NovaTech");
  const [priceRupees, setPriceRupees] = useState(
    product ? String(Math.round(product.price_paise / 100)) : "",
  );
  const [compareRupees, setCompareRupees] = useState(
    product?.compare_at_price_paise ? String(Math.round(product.compare_at_price_paise / 100)) : "",
  );
  const [tags, setTags] = useState((product?.tags ?? []).join(", "));
  const [description, setDescription] = useState(product?.description ?? "");
  const [stock, setStock] = useState("25");
  const [error, setError] = useState<string | null>(null);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const price = Math.round(Number(priceRupees) * 100);
    if (!name.trim() || !price || price <= 0) {
      setError("A name and a positive price are required.");
      return;
    }
    const payload: ProductInput = {
      name: name.trim(),
      category,
      brand: brand.trim() || null,
      description: description.trim() || null,
      price_paise: price,
      compare_at_price_paise: compareRupees ? Math.round(Number(compareRupees) * 100) : null,
      tags: tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    };

    const onError = (e: unknown) =>
      setError(e instanceof ApiError ? e.friendlyMessage : "Could not save the product.");

    if (editing && product) {
      update.mutate({ id: product.id, patch: payload }, { onSuccess: onClose, onError });
    } else {
      create.mutate(
        { ...payload, stock: Math.max(0, Number(stock) || 0) },
        { onSuccess: onClose, onError },
      );
    }
  }

  return (
    <Modal title={editing ? "Edit product" : "Add product"} open={open} onClose={onClose}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <Field label="Name" name="name" value={name} onChange={(e) => setName(e.target.value)} required />
        <div className="flex flex-col gap-1.5">
          <label htmlFor="category" className="text-sm font-medium">
            Category
          </label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-[var(--radius-input)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
          >
            {CATEGORIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
        <Field label="Brand" name="brand" value={brand} onChange={(e) => setBrand(e.target.value)} />
        <div className="grid grid-cols-2 gap-3">
          <Field
            label="Price (₹)"
            name="price"
            type="number"
            min={1}
            value={priceRupees}
            onChange={(e) => setPriceRupees(e.target.value)}
            required
          />
          <Field
            label="Compare-at (₹)"
            name="compare"
            type="number"
            min={0}
            value={compareRupees}
            onChange={(e) => setCompareRupees(e.target.value)}
          />
        </div>
        {!editing && (
          <Field
            label="Initial stock"
            name="stock"
            type="number"
            min={0}
            value={stock}
            onChange={(e) => setStock(e.target.value)}
          />
        )}
        <Field
          label="Tags (comma-separated)"
          name="tags"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />
        <div className="flex flex-col gap-1.5">
          <label htmlFor="desc" className="text-sm font-medium">
            Description
          </label>
          <textarea
            id="desc"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="resize-none rounded-[var(--radius-input)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
          />
        </div>

        {error && <p className="text-xs text-[var(--color-danger)]">{error}</p>}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={pending}>
            {editing ? "Save changes" : "Add product"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
