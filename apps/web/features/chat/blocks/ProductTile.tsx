"use client";

import { useState } from "react";

import { productImageUrl } from "@/lib/productImage";

/**
 * Product image. Real photography from Unsplash's CDN (plain <img>, so it works
 * without the Next image optimiser), with a deterministic category-tinted
 * monogram tile as the always-present fallback — shown while loading and if the
 * image fails, so there is never a broken image and no layout shift.
 */

const CATEGORY_TINT: Record<string, [string, string]> = {
  Laptops: ["#eef2f8", "#dbe4f0"],
  Smartphones: ["#f0eef8", "#e0dcf0"],
  Audio: ["#fdf1e7", "#f7e2cd"],
  Keyboards: ["#e9f5f0", "#d3ebe1"],
  Mice: ["#fbeef0", "#f4dbe0"],
  Wearables: ["#e8f4f6", "#d0e9ee"],
  Accessories: ["#f2f2f0", "#e4e4e0"],
  Storage: ["#eef1f6", "#dfe4ee"],
  Displays: ["#eef4f1", "#dae9e2"],
  Bags: ["#f4efe9", "#e7dccb"],
  Power: ["#fdf1e7", "#f6e0c9"],
};
const FALLBACK: [string, string] = ["#f2f2f0", "#e4e4e0"];

export function ProductTile({
  name,
  category,
  imageKey,
  className = "",
}: {
  name: string;
  category: string | null;
  imageKey?: string | null;
  className?: string;
}) {
  const [loaded, setLoaded] = useState(false);
  const [broken, setBroken] = useState(false);
  const [from, to] = (category && CATEGORY_TINT[category]) || FALLBACK;
  const initial = name.trim().charAt(0).toUpperCase() || "?";

  return (
    <div
      className={`relative flex items-center justify-center overflow-hidden ${className}`}
      style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}
    >
      <span className="text-4xl font-light text-[var(--color-fg)]/35 select-none">{initial}</span>
      {category && (
        <span className="absolute bottom-1.5 left-2 text-[10px] font-medium uppercase tracking-wide text-[var(--color-fg)]/30">
          {category}
        </span>
      )}
      {!broken && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={productImageUrl(category, imageKey)}
          alt={category ? `${name} — ${category}` : name}
          loading="lazy"
          onLoad={() => setLoaded(true)}
          onError={() => setBroken(true)}
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-300 ${
            loaded ? "opacity-100" : "opacity-0"
          }`}
        />
      )}
    </div>
  );
}
