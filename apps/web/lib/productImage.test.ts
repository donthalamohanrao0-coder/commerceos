import { describe, expect, it } from "vitest";

import { productImageUrl } from "./productImage";

describe("productImageUrl", () => {
  it("returns a category-specific Unsplash CDN url", () => {
    const url = productImageUrl("Laptops");
    expect(url).toMatch(/^https:\/\/images\.unsplash\.com\/photo-/);
    expect(url).toContain("w=480");
  });

  it("maps distinct categories to distinct images", () => {
    expect(productImageUrl("Laptops")).not.toBe(productImageUrl("Audio"));
  });

  it("falls back to a default image for unknown / missing categories", () => {
    const fallback = productImageUrl(null);
    expect(fallback).toMatch(/^https:\/\/images\.unsplash\.com\/photo-/);
    expect(productImageUrl("Something New")).toBe(fallback);
  });

  it("prefers a per-product image_key over the category", () => {
    const byKey = productImageUrl("Accessories", "backpack_01");
    const byCategory = productImageUrl("Accessories");
    expect(byKey).not.toBe(byCategory);
  });

  it("honours a custom width", () => {
    expect(productImageUrl("Mice", null, 96)).toContain("w=96");
  });
});
