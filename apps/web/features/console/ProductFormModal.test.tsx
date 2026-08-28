import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api";
import type { ConsoleProduct } from "@/lib/types";

import { ProductFormModal } from "./ProductFormModal";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, api: vi.fn().mockResolvedValue({}) };
});
const apiMock = vi.mocked(api);

function wrap(node: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

beforeEach(() => apiMock.mockClear());

describe("ProductFormModal", () => {
  it("POSTs a new product with rupees converted to paise", async () => {
    const onClose = vi.fn();
    wrap(<ProductFormModal open onClose={onClose} />);

    await userEvent.type(screen.getByLabelText("Name"), "Desk Mat");
    await userEvent.type(screen.getByLabelText("Price (₹)"), "750");
    await userEvent.click(screen.getByRole("button", { name: /^add product$/i }));

    const [path, opts] = apiMock.mock.calls[0];
    expect(path).toBe("/console/products");
    expect(opts).toMatchObject({ method: "POST", body: { name: "Desk Mat", price_paise: 75000 } });
  });

  it("PATCHes when editing an existing product", async () => {
    const product = {
      id: "p1",
      name: "NovaBook Pro 14",
      category: "Laptops",
      brand: "NovaTech",
      description: null,
      price_paise: 7499900,
      compare_at_price_paise: null,
      tags: ["coding"],
      sku: "NT-LAP-001",
      rating: 4.7,
      review_count: 10,
      image_key: null,
      status: "active",
    } satisfies ConsoleProduct;

    wrap(<ProductFormModal open onClose={vi.fn()} product={product} />);
    const price = screen.getByLabelText("Price (₹)");
    await userEvent.clear(price);
    await userEvent.type(price, "69999");
    await userEvent.click(screen.getByRole("button", { name: /save changes/i }));

    const [path, opts] = apiMock.mock.calls[0];
    expect(path).toBe("/console/products/p1");
    expect(opts).toMatchObject({ method: "PATCH", body: { price_paise: 6999900 } });
  });
});
